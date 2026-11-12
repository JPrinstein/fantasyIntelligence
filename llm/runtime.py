"""Switchable production LLM: GGUF/llama.cpp default, original HF NF4 fallback.

All llama.cpp communication stays on 127.0.0.1. This module only shuts down
its own subprocess and never touches the benchmark cache or running servers.
"""
import atexit
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

_ROOT = Path(__file__).resolve().parents[1]
_GGUF_FILE = _ROOT / 'models' / 'qwen35-4b-q4' / 'Qwen3.5-4B-Q4_K_M.gguf'
_lock = threading.RLock()
_server = None
_address = None
_model = None
_tokenizer = None
_last_metrics = {}

def get_last_generation_metrics():
    return _last_metrics.copy()


def backend():
    name = os.getenv('FANTASY_LLM_BACKEND', 'gguf').strip().lower()
    if name not in {'gguf', 'transformers'}:
        raise ValueError('FANTASY_LLM_BACKEND must be gguf or transformers')
    return name


def get_generator():
    """Original (model, tokenizer) accessor, available in transformers mode."""
    global _model, _tokenizer
    if backend() != 'transformers':
        raise RuntimeError('get_generator is only available for transformers; use generate_chat')
    with _lock:
        if _model is None:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            import torch
            model_id = 'Qwen/Qwen3-4B'
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                      bnb_4bit_compute_dtype=torch.bfloat16,
                                      bnb_4bit_use_double_quant=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_id, quantization_config=quant, device_map='cuda')
            _tokenizer, _model = tokenizer, model
        return _model, _tokenizer


def _find_binary():
    configured = os.getenv('LLAMA_SERVER_BIN', '').strip().strip('"')
    if configured:
        if not Path(configured).is_file():
            raise FileNotFoundError(f'LLAMA_SERVER_BIN not found: {configured}')
        return configured
    found = shutil.which('llama-server') or shutil.which('llama-server.exe')
    if found:
        return found
    # Windows winget layout, as found on this laptop.
    local = Path(os.getenv('LOCALAPPDATA', '')) / 'Microsoft' / 'WinGet' / 'Packages'
    if local.is_dir():
        for candidate in local.glob('ggml.llamacpp_*/llama-server.exe'):
            if candidate.is_file():
                return str(candidate)
    raise FileNotFoundError('llama-server.exe not found; set LLAMA_SERVER_BIN to its full path')


def _port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _health(address):
    try:
        with urlopen(address + '/health', timeout=2) as resp:
            return resp.status == 200
    except (URLError, OSError, TimeoutError):
        return False


def _shutdown():
    global _server, _address
    with _lock:
        p = _server
        _server, _address = None, None
        if p is not None and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()


atexit.register(_shutdown)


def _start_server():
    global _server, _address
    if _server is not None and _server.poll() is None and _health(_address):
        return _address
    if _server is not None:
        _shutdown()
    model_path = Path(os.getenv('FANTASY_GGUF_PATH', str(_GGUF_FILE))).expanduser()
    if not model_path.is_file():
        raise FileNotFoundError(
            f'GGUF model missing: {model_path}\n'
            'Download first: .\\.venv\\Scripts\\python.exe -m llm.download_gguf\n'
            'Or use fallback: $env:FANTASY_LLM_BACKEND="transformers"')
    executable = _find_binary()
    port = _port()
    ctx = int(os.getenv('FANTASY_CTX_SIZE', '8192'))
    layers = int(os.getenv('FANTASY_GPU_LAYERS', '99'))
    if ctx < 512 or ctx > 131072 or layers < 0:
        raise ValueError('Invalid FANTASY_CTX_SIZE or FANTASY_GPU_LAYERS')
    args = [executable, '--model', str(model_path), '--host', '127.0.0.1',
            '--port', str(port), '--ctx-size', str(ctx), '--n-gpu-layers', str(layers),
            '--no-webui', '--jinja', '--chat-template-kwargs',
            json.dumps({'enable_thinking': False})]
    print(f'Starting local llama.cpp: {model_path.name} (context {ctx})', flush=True)
    # DEVNULL avoids unconsumed pipe deadlocks on Windows and preserves normal app output.
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _server, _address = proc, f'http://127.0.0.1:{port}'
    deadline = time.monotonic() + int(os.getenv('FANTASY_MODEL_LOAD_TIMEOUT', '180'))
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            code = proc.returncode
            _shutdown()
            raise RuntimeError(f'llama-server exited during startup (code {code}); check GGUF compatibility')
        if _health(_address):
            print('llama.cpp ready at ' + _address, flush=True)
            return _address
        time.sleep(0.5)
    _shutdown()
    raise TimeoutError('llama-server startup timed out')


def planner_schema():
    """Mirror the successful benchmark's JSON structure; validate tools separately."""
    return {'type': 'object', 'properties': {'tools': {'type': 'array', 'items': {
        'type': 'object', 'properties': {'tool': {'type': 'string'},
                                        'args': {'type': 'object'}},
        'required': ['tool', 'args'], 'additionalProperties': False}}},
        'required': ['tools'], 'additionalProperties': False}


def _gguf_chat(messages, *, json_mode, max_tokens):
    address = _start_server()
    body = {'messages': messages, 'temperature': 0, 'max_tokens': max_tokens,
            'stream': False, 'seed': 42}
    if json_mode:
        body['response_format'] = {'type': 'json_schema', 'schema': planner_schema()}
    request = Request(address + '/v1/chat/completions',
                      data=json.dumps(body).encode('utf-8'),
                      headers={'Content-Type': 'application/json'}, method='POST')
    timeout = int(os.getenv('FANTASY_REQUEST_TIMEOUT', '180'))
    global _last_metrics

    start = time.perf_counter()

    with urlopen(request, timeout=timeout) as response:
        data = json.load(response)

    elapsed = time.perf_counter() - start

    content = data["choices"][0]["message"].get("content") or ""

    usage = data.get("usage", {})
    timings = data.get("timings", {})

    tokens = usage.get("completion_tokens", 0)

    # llama.cpp reports generation throughput directly.
    generation_tps = timings.get("predicted_per_second")

    if generation_tps is None:
        generation_ms = timings.get("predicted_ms")
        predicted_tokens = timings.get("predicted_n", tokens)

        if generation_ms and predicted_tokens:
            generation_tps = predicted_tokens / (generation_ms / 1000)

    _last_metrics = {
        "tokens": tokens,
        "tokens_per_second": generation_tps,
        "request_seconds": elapsed,
    }
    # Some templates wrap reasoning even with thinking disabled.
    return content.rsplit('</think>', 1)[-1].strip()


def _transformers_chat(messages, *, max_tokens, thinking):
    model, tokenizer = get_generator()
    template = tokenizer.apply_chat_template(messages, tokenize=False,
                                              add_generation_prompt=True,
                                              enable_thinking=thinking)
    inputs = tokenizer(template, return_tensors='pt').to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
    raw = outputs[0][inputs['input_ids'].shape[1]:]
    return tokenizer.decode(raw, skip_special_tokens=True).strip()


def generate_chat(messages, *, json_mode=False, max_tokens=350, thinking=False):
    """Shared planner/answer entrypoint. JSON constraints only on planner calls."""
    with _lock:
        if backend() == 'gguf':
            return _gguf_chat(messages, json_mode=json_mode, max_tokens=max_tokens)
        return _transformers_chat(messages, max_tokens=max_tokens, thinking=thinking)

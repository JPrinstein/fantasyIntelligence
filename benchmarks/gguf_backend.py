"""llama.cpp server backend. Only listens on localhost and runs one model at a time."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def post_json(url, body, timeout=600):
    request = Request(url, data=json.dumps(body).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def find_server():
    configured = os.environ.get("LLAMA_SERVER_BIN", "").strip()
    executable = configured or shutil.which("llama-server") or shutil.which("llama-server.exe")
    if not executable:
        raise RuntimeError("llama-server not found. Install llama.cpp for Windows or set LLAMA_SERVER_BIN")
    if configured and not Path(configured).is_file():
        raise RuntimeError(f"LLAMA_SERVER_BIN does not exist: {configured}")
    return executable


def reserve_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(server, base_url, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"llama-server exited with code {server.returncode}")
        try:
            with urlopen(base_url + "/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    raise TimeoutError("Timed out waiting for local llama-server health endpoint")


def tool_json_schema():
    return {"type": "object", "properties": {"tools": {
        "type": "array", "items": {"type": "object",
            "properties": {"tool": {"type": "string"}, "args": {"type": "object"}},
            "required": ["tool", "args"], "additionalProperties": False}}},
        "required": ["tools"], "additionalProperties": False}


def server_command(config, executable, model_path, port):
    command = [executable, "--model", str(model_path), "--host", "127.0.0.1",
               "--port", str(port), "--ctx-size", str(config.get("ctx_size", 4096)),
               "--n-gpu-layers", str(config.get("gpu_layers", 99)),
               "--no-webui", "--jinja"]
    if config.get("thinking_template"):
        command.extend(["--chat-template-kwargs", json.dumps({
            "enable_thinking": bool(config.get("thinking", False))})])
    return command


def request_body(config, case, messages):
    body = {"messages": messages,
            "max_tokens": 650 if config.get("thinking") else 300,
            "temperature": 0, "stream": False, "seed": 42}
    # This is a separate *constrained decoding* experiment. Raw NF4 and
    # ordinary GGUF runs are intentionally left unconstrained for comparison.
    if case["kind"] == "planner" and config.get("json_mode", False):
        # llama.cpp's documented OpenAI-style endpoint accepts schema at the
        # top level of response_format; older versions may reject this mode.
        body["response_format"] = {"type": "json_schema", "schema": tool_json_schema()}
    return body


def stop_server(server):
    if server.poll() is not None:
        return
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()


def launch_with_offload_fallback(config, executable, model_path, log_handle):
    """If full GPU offload OOMs, retry a bounded partial/CPU offload."""
    preferred = int(config.get("gpu_layers", 99))
    layers_to_try = [preferred]
    if preferred > 24:
        layers_to_try.append(24)
    if preferred > 0:
        layers_to_try.append(0)
    # Remove duplicates (e.g., configured 0 layers).
    layers_to_try = list(dict.fromkeys(layers_to_try))
    failures = []
    for layers in layers_to_try:
        port = reserve_port()
        base_url = f"http://127.0.0.1:{port}"
        command = server_command({**config, "gpu_layers": layers}, executable, model_path, port)
        log_handle.write(f"\nBENCHMARK OFFLOAD ATTEMPT: {layers} GPU layers\n")
        log_handle.flush()
        server = subprocess.Popen(command, stdout=log_handle, stderr=subprocess.STDOUT)
        try:
            wait_for_server(server, base_url, timeout=int(config.get("load_timeout", 120)))
            return server, base_url, layers
        except Exception as exc:
            failures.append(f"{layers} layers: {exc}")
            stop_server(server)
    raise RuntimeError("All local GPU/CPU offload attempts failed: " + " | ".join(failures))


def run(config, cases, offline, build_messages, tools_prompt):
    from huggingface_hub import hf_hub_download

    if not config.get("filename", "").lower().endswith(".gguf"):
        raise ValueError("GGUF profiles require a verified .gguf filename")

    start_load = time.perf_counter()
    model_path = hf_hub_download(repo_id=config["model_id"], filename=config["filename"],
                                 local_files_only=offline)
    executable = find_server()
    with tempfile.TemporaryDirectory(prefix="fantasy-llama-") as temporary:
        server_log = Path(temporary) / "llama-server.log"
        with server_log.open("w+", encoding="utf-8") as handle:
            server = None
            try:
                server, base_url, used_layers = launch_with_offload_fallback(
                    config, executable, model_path, handle)
                load_seconds = time.perf_counter() - start_load
                samples = []
                for case in cases:
                    messages = build_messages(case, tools_prompt)
                    body = request_body(config, case, messages)
                    began = time.perf_counter()
                    response = post_json(base_url + "/v1/chat/completions", body,
                                         timeout=int(config.get("request_timeout", 600)))
                    elapsed = time.perf_counter() - began
                    choice = response["choices"][0]
                    answer = choice["message"].get("content") or ""
                    answer = answer.rsplit("</think>", 1)[-1].strip()
                    used_tokens = response.get("usage", {}).get("completion_tokens")
                    samples.append({
                        "id": case["id"], "output": answer,
                        "generated_tokens": used_tokens,
                        "generation_seconds": round(elapsed, 3),
                        "tokens_per_second": round(used_tokens / elapsed, 2) if used_tokens and elapsed else None,
                        "peak_torch_allocated_gb": None,
                        "finish_reason": choice.get("finish_reason")})
                return {"load_seconds": round(load_seconds, 2), "samples": samples,
                        "device": f"llama.cpp (requested {used_layers} GPU layers)",
                        "quantization": config["quantization"],
                        "checkpoint_revision": None,
                        "note": "Peak VRAM unavailable from llama.cpp in this version"}
            except Exception as exc:
                handle.flush()
                server_log_text = server_log.read_text(encoding="utf-8", errors="replace")[-2500:]
                raise RuntimeError(f"{exc}\nllama-server log tail:\n{server_log_text}") from exc
            finally:
                if server is not None:
                    stop_server(server)

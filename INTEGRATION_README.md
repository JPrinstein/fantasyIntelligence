# Fantasy assistant llama.cpp integration (production, not benchmark)

## Install

From the **fantasyIntelligence project root** (not inside `benchmarks`):

1. Extract this ZIP into the project root, overwriting these five existing source files:
   `main.py`, `agent/planner.py`, `llm/generator.py`, plus adding
   `llm/runtime.py`, `llm/download_gguf.py` and `tests/test_llm_runtime.py`.
   Back up or commit your current source first if you have local edits.
2. Download the winner **once** into `models/qwen35-4b-q4/`:
   ```powershell
   .\.venv\Scripts\python.exe -m llm.download_gguf
   ```
3. Run tests and then chat:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v
   .\.venv\Scripts\python.exe main.py
   ```
   The app automatically discovers the WinGet llama-server binary on Windows,
   including the known ggml.llamacpp package folder. To override:
   ```powershell
   $env:LLAMA_SERVER_BIN = 'C:\path\to\llama-server.exe'
   ```

## Configuration

- Default: `$env:FANTASY_LLM_BACKEND='gguf'` or unset.
- Original fallback: `$env:FANTASY_LLM_BACKEND='transformers'` (Qwen3-4B NF4).
- Optional model path: `$env:FANTASY_GGUF_PATH='D:\models\some.gguf'`.
- Optional context tokens: `$env:FANTASY_CTX_SIZE='8192'` (increase only if VRAM allows).
- Optional GPU layers: `$env:FANTASY_GPU_LAYERS='99'`.

llama-server runs once for the duration of the chat and stops on normal Python
exit. One model serves both the JSON-constrained tool planner and the **normal
text** answer generator. The tool plan is still validated by the existing
allowlist and argument validator; JSON format alone does not make tool calls safe.

## Safety and data handling

- All endpoints bind to `127.0.0.1`; the server uses an OS-selected port.
- This does **not** modify your RAG index, league files, NFL tools, MCP server,
  benchmark configs/results, other models, or shared Hugging Face caches.
- No model files are shipped in this ZIP. The app-owned download is preserved
  after use (not affected by benchmark `--cleanup-after`).
- Add `models/` and `benchmarks/model_cache/` to `.gitignore` before committing.
- Existing non-model inference modules were deliberately left untouched.
- This initial integration requires the llama.cpp binary to support the Qwen3.5
  GGUF/chat template and `response_format=json_schema`, as it did in benchmarking.
- If startup fails, switch to `transformers` for your original working setup.

## Validation scope

Unit tests check backend switching, planner JSON mode, answer normal mode,
planner league phrase enforcement, and missing-file handling. No GPU model load,
real NFL data, FAISS integration, or end-to-end interactive test can run in this
packaging environment. Verify locally with the commands above.

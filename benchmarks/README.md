# Fantasy AI local model benchmark — version 4

This standalone harness benchmarks local LLMs for your fantasy assistant, without
modifying `main.py`, `llm/generator.py`, the agent, or the existing project tools.
The 45 test cases and scoring rules stay consistent across model profiles.

## Setup (Windows 11 / RTX 4070)

1. Extract the ZIP into the `fantasyIntelligence` repository root, replacing only
   the `benchmarks` files. Your previous results and caches are untouched.
2. To use the **GGUF** profiles, install recent llama.cpp with `llama-server.exe`:

   ```powershell
   winget install llama.cpp
   ```

   Then **open a new PowerShell terminal** (PATH may need refreshing) and check:

   ```powershell
   llama-server --help
   ```

   The default package may not include CUDA acceleration. Check the model
   loading log for GPU offloading; if it uses CPU only, use the official
   [CUDA-enabled Windows release](https://github.com/ggml-org/llama.cpp/releases)
   and set its path with, for example,
   `$env:LLAMA_SERVER_BIN = 'D:\llama\llama-server.exe'` in that terminal.
   The CLI backend will **not** install any packages itself. GGUF models need
   a recent llama.cpp version with Qwen3.5 support.

## Safest full overnight run — one command

Test first, without downloading or starting an LLM:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s benchmarks -p 'test_*.py' -v
.\.venv\Scripts\python.exe -m benchmarks.run --overnight --allow-download --cleanup-after --max-cache-gb 75 --timeout 3600 --dry-run
```

With your laptop plugged in, plugged-in sleep disabled for the evening, and the
`llama-server --help` check passing, start the full sweep:

```powershell
.\.venv\Scripts\python.exe -m benchmarks.run --overnight --allow-download --cleanup-after --max-cache-gb 75 --timeout 3600
```

This runs **13 new profiles sequentially** (not concurrently):

| Group | Profiles | Purpose |
|---|---|---|
| Transformers | Qwen3.5-4B NF4 thinking; Qwen3-4B INT8; Phi-4-mini NF4 | Thinking, quantization, non-Qwen |
| GGUF 4B | Qwen3-4B Q4; Qwen3.5-4B Q4, Q4 with JSON constraint, Q8 | Runtime, raw JSON vs constrained JSON, quality/speed |
| GGUF 8–9B | Qwen3-8B Q4 and Q5; Qwen3.5-9B Q4 | Bigger model tests on 8 GB VRAM |
| Other GGUF | Phi-4-mini Q4; Gemma 3 4B Q4 | Non-Qwen model families |
| Moonshot/Kimi-family | **Moonlight 16B-A3B Q2** (experimental) | Larger mixture-of-experts; CPU offload likely |

Existing baseline **Qwen3-4B NF4** and **Qwen3.5-4B NF4** results are reused
through `benchmarks/results/` for the final comparison, not rerun overnight.
The baseline results were 38/45 and 26/45 respectively before a minor scoring
fix that accepts the word *one* for the digit *1*. The leaderboard now
re-scores saved raw outputs consistently (the shared runs become 39/45 and
27/45 respectively).

## Storage and cleanup

- An individual GGUF Q4 model is generally ~2.5–6 GB for 4–9B sizes.
  Qwen3-8B Q4 is ~5.0 GB, Qwen3.5-9B Q4 ~5.7 GB, and Moonlight 16B
  Q2 ~6.6 GB. The **3 GiB peak PyTorch allocation** shown on your earlier
  runs was *not* the total VRAM use; system overhead, CUDA kernels, and
  KV cache need room too.
- Downloads go to **`benchmarks/model_cache/` only** when `--allow-download`
  is present. The normal Hugging Face cache is not touched by cleanup.
- `--cleanup-after` deletes each benchmark-owned model's Hub revision(s)
  **after saving its results, even after a failed model**. Consecutive profiles
  using the same repository temporarily share the download and clean together.
  This means you can redownload the winner later; most test weights need not stay.
- `--max-cache-gb 75` is a monitored **safety cutoff**, not a hard quota;
  temporary overshoot or unreclaimed auxiliary Xet download cache is possible.
  Check storage after the run if you see unusual growth.
- With cleanup, expect a **temporary peak roughly 10–25 GB** in the benchmark
  cache under normal conditions, rather than storing all the models at once.
  These figures are estimates; a failed/incomplete download could raise the peak.
- The 13 profiles may take **several hours, potentially most of the night**,
  depending on server build, model throughput, downloads, and CPU offload.
  Each model has a 3,600-second maximum; errors do not abort the rest.
- GGUF startup automatically tries full GPU offloading, then partial and finally
  CPU if a model cannot load on the GPU. This helps larger models run but can
  make them dramatically slower; the achieved offload setting is recorded.
- Your laptop must remain awake; screen-off is fine, actual sleep is not.

**Kimi caveat:** This Moonlight candidate was published by Moonshot AI, the
maker of Kimi; it is *not* Kimi K2. Kimi K2's trillion-parameter weights are
far too large for an 8-GB GPU. The Moonlight GGUF conversion is experimental:
the community conversion's chat-template compatibility is unverified, so the
model may fail chat formatting, which is recorded as a failed run. The optional
10.5-GB Q4 variant exists in `models.json`, but is **not** in `--overnight`.

## Inspect results after the run

Outputs land under `benchmarks/results/<date_time>/`, each model's log,
the exact case/config snapshot, `results.json`, and `report.md`.
After a complete run, a cross-run leaderboard is also produced at
`benchmarks/results/comparison.md`.

Regenerate the leaderboard without loading weights:

```powershell
.\.venv\Scripts\python.exe -m benchmarks.compare --save
```

Rescore earlier saved results after scoring changes:

```powershell
.\.venv\Scripts\python.exe -m benchmarks.run --rescore benchmarks\results\20261110_232725\results.json
.\.venv\Scripts\python.exe -m benchmarks.run --rescore benchmarks\results\20261110_233022\results.json
```

If the overnight run is interrupted, resume from the last `results.json`:

```powershell
.\.venv\Scripts\python.exe -m benchmarks.run --overnight --allow-download --cleanup-after --max-cache-gb 75 --timeout 3600 --resume benchmarks\results\REPLACE_WITH_RUN_FOLDER\results.json
```

For any specific experiment (including the 10.5-GB Moonlight Q4 opt-in):

```powershell
.\.venv\Scripts\python.exe -m benchmarks.run --list
.\.venv\Scripts\python.exe -m benchmarks.run --model moonlight16b-a3b-gguf-q4-experimental --allow-download --cleanup-after --timeout 3600
```

`--all` runs *every* registry profile, including the large experimental Q4
Moonlight variant. Prefer `--overnight`, or repeat `--model NAME` to curate a list.

## Interpreting the numbers

- **45 checks** combine strict planner JSON/tool/argument tests and limited
  expected/forbidden answer-string checks. High score does **not** guarantee
  real-world fantasy advice, mathematical accuracy, or current injury data.
- `tokens_per_second` is decoding throughput; entire planner + answer latency
  also matters. GGUF and Transformers use different runtimes, so treat direct
  speed comparisons as practical rather than perfectly controlled.
- `qwen35-4b-gguf-q4-json` uses grammar-constrained JSON for planner queries.
  The other profiles are raw output. Keep this distinction when comparing scores.
- A slow model is not necessarily higher quality. Thinking models may consume
  substantial generation time without improving tool calls.
- Even a winning model still needs your fantasy project's **daily/hourly data
  refresh**, season handling, provenance checks, and tool correctness. The
  benchmark only selects the language model.

## Git hygiene

Commit `benchmarks/*.py`, `benchmarks/models.json`, `benchmarks/cases.json`,
`benchmarks/README.md`, and the included `benchmarks/.gitignore`.
The included ignore file keeps model weights and bulky logs out of Git:

```gitignore
model_cache/
results/
```

Everything is opt-in. This harness does not alter default model inference,
delete weights outside its dedicated cache, or connect to a hosted model API.

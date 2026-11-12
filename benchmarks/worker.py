"""One model per process; stdout result line starts with BENCH_RESULT=."""
import argparse
import json
import time
import traceback


def build_messages(case, tools_prompt):
    if case["kind"] == "planner":
        return [
            {"role": "system", "content": (
                "You are a fantasy football tool planner. Select tools; do not answer. "
                "Use rag_search for general concepts, player_stats for actual historical statistics, "
                "player_depth_chart for team/depth chart, and league_context whenever the user "
                "says 'my league' or asks for their league's scoring. Do not invent optional arguments: "
                "week and recent_games must be omitted unless explicitly requested. "
                "If none of the listed tools can supply the requested facts (for example live weather, "
                "current injuries, news, or non-fantasy advice), return an empty tools array. "
                "Return JSON only: {\"tools\":[{\"tool\":\"name\",\"args\":{}}]}."
            )},
            {"role": "user", "content": (
                f"AVAILABLE TOOLS:\n{tools_prompt}\nQUESTION: {case['question']}\n"
                "Return valid JSON with a tools array only."
            )}
        ]
    return [
        {"role": "system", "content": (
            "Answer using only supplied evidence. Do not invent statistics, calculate unrequested "
            "averages, or claim access to current information. Be concise."
        )},
        {"role": "user", "content": f"EVIDENCE:\n{case['evidence']}\nQUESTION:\n{case['question']}"}
    ]


def run(config, cases, offline):
    # Shared dataset and tool descriptions across inference backends.
    tools_prompt = (
        "rag_search(query: string) - search general fantasy knowledge\n"
        "league_context() - configured league scoring and roster settings\n"
        "player_stats(player_name: string, season: integer, week?: integer, recent_games?: integer) "
        "- actual player stats\n"
        "player_depth_chart(player_name: string, season: integer) - season depth chart rank/team"
    )
    if config["backend"] == "gguf":
        from benchmarks.gguf_backend import run as run_gguf
        return run_gguf(config, cases, offline, build_messages, tools_prompt)
    if config["backend"] != "transformers":
        raise ValueError(f"Unknown backend: {config['backend']}")

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    model_id = config["model_id"]
    local = bool(offline)
    start_load = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_id, local_files_only=local)
    kwargs = {"device_map": "auto", "local_files_only": local}
    quant = config["quantization"].lower()
    if quant == "nf4":
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    elif quant == "int8":
        kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
    elif quant == "bf16":
        kwargs["torch_dtype"] = torch.bfloat16
    else:
        raise ValueError(f"Unsupported quantization: {quant}")
    model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    model.eval()
    load_s = time.perf_counter() - start_load

    samples = []
    for case in cases:
        messages = build_messages(case, tools_prompt)
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=bool(config.get("thinking", False)))
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
        start = time.perf_counter()
        with torch.inference_mode():
            outputs = model.generate(**inputs,
                                     max_new_tokens=650 if config.get("thinking", False) else 300,
                                     do_sample=False, pad_token_id=tokenizer.eos_token_id)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - start
        produced = outputs[0][inputs["input_ids"].shape[1]:]
        decoded = tokenizer.decode(produced, skip_special_tokens=True).strip()
        # Thinking-capable Qwen models sometimes emit reasoning before a
        # </think> separator. Only the final answer should be graded.
        answer = decoded.rsplit("</think>", 1)[-1].strip() if "</think>" in decoded else decoded
        samples.append({
            "id": case["id"], "output": answer, "generated_tokens": len(produced),
            "generation_seconds": round(elapsed, 3),
            "tokens_per_second": round(len(produced) / elapsed, 2) if elapsed else 0,
            "peak_torch_allocated_gb": round(torch.cuda.max_memory_allocated() / 2**30, 3)
                if torch.cuda.is_available() else None
        })
    return {"load_seconds": round(load_s, 2), "samples": samples,
            "device": str(model.device), "quantization": quant,
            "checkpoint_revision": getattr(model.config, "_commit_hash", None),
            "pytorch_version": torch.__version__,
            "note": "VRAM metric is PyTorch allocations only, not total device usage"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    with open(args.payload, encoding="utf-8") as stream:
        payload = json.load(stream)
    try:
        result = {"success": True, **run(payload["model"], payload["cases"], args.offline)}
    except Exception:
        result = {"success": False, "error": traceback.format_exc()[-5000:]}
    print("BENCH_RESULT=" + json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

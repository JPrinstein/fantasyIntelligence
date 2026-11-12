"""Sequential benchmark coordinator; only downloads when --allow-download is given."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from .scoring import score_case
from .cache import checked_hub_path, directory_size_bytes, cleanup_repo

ROOT = Path(__file__).resolve().parent


def load_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def check_registry(registry):
    names = set()
    for entry in registry["models"]:
        name = entry["name"]
        if name in names:
            raise ValueError(f"Duplicate model name: {name}")
        names.add(name)
        if not all(key in entry for key in ("model_id", "backend", "quantization")):
            raise ValueError(f"Incomplete model: {name}")
        if entry["backend"] not in ("transformers", "gguf"):
            raise ValueError(f"Unsupported backend for {name}")
        if entry["backend"] == "gguf" and not entry.get("filename", "").endswith(".gguf"):
            raise ValueError(f"GGUF filename missing for {name}")


def stop_process_tree(proc):
    """Terminate model worker AND llama-server child on Windows timeouts."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        import signal
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if proc.poll() is None:
        proc.kill()


def execute_one(model, cases, timeout, allow_download, run_dir, max_cache_gb):
    with tempfile.TemporaryDirectory(prefix="fantasy-bench-") as temporary:
        payload = Path(temporary) / "payload.json"
        payload.write_text(json.dumps({"model": model, "cases": cases}), encoding="utf-8")
        cmd = [sys.executable, "-m", "benchmarks.worker", "--payload", str(payload)]
        if not allow_download:
            cmd.append("--offline")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        # Default offline mode sees the user's pre-existing HF cache, read-only.
        # Explicit download mode uses an isolated benchmark-owned cache.
        if allow_download:
            cache_dir = ROOT / "model_cache"
            checked_hub_path(cache_dir)
            cache_dir.mkdir(exist_ok=True)
            env["HF_HOME"] = str(cache_dir)
            env["HF_HUB_CACHE"] = str(cache_dir / "hub")
            # Prefer regular Hub transfers; keep any existing auxiliary Xet
            # cache separate so Hub-revision cleanup remains predictable.
            env["HF_HUB_DISABLE_XET"] = "1"
        started = time.perf_counter()
        try:
            proc = subprocess.Popen(cmd, cwd=ROOT.parent, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                    start_new_session=(os.name != "nt"))
            forced_error = None
            while True:
                try:
                    stdout, stderr = proc.communicate(timeout=2)
                    break
                except subprocess.TimeoutExpired:
                    if time.perf_counter() - started > timeout:
                        forced_error = f"Model timeout after {timeout} seconds"
                    elif allow_download and directory_size_bytes(ROOT / "model_cache") > max_cache_gb * 2**30:
                        forced_error = f"Cache exceeded {max_cache_gb:g} GiB limit"
                    if forced_error:
                        stop_process_tree(proc)
                        stdout, stderr = proc.communicate()
                        break
            output = stdout + "\n" + stderr
            marker = [line.removeprefix("BENCH_RESULT=") for line in stdout.splitlines()
                      if line.startswith("BENCH_RESULT=")]
            parsed = json.loads(marker[-1]) if marker and not forced_error else {
                "success": False, "error": f"Worker exited {proc.returncode} without result"}
            if forced_error:
                parsed = {"success": False, "error": forced_error}
        except Exception as exc:
            output = repr(exc)
            parsed = {"success": False, "error": output}
        (run_dir / f"{model['name']}.log").write_text(output, encoding="utf-8")
        parsed["wall_seconds"] = round(time.perf_counter() - started, 2)
        return parsed


def main():
    parser = argparse.ArgumentParser(description="Run sequential local model benchmarks")
    parser.add_argument("--list", action="store_true", help="Show registry; do not load models")
    parser.add_argument("--model", action="append", help="Select model by name; repeat for several")
    parser.add_argument("--all", action="store_true", help="Run all registry entries sequentially")
    parser.add_argument("--overnight", action="store_true", help="Run the curated overnight profiles; includes experimental Kimi-family last")
    parser.add_argument("--allow-download", action="store_true", help="Permit downloads into benchmark-owned cache")
    parser.add_argument("--cleanup-after", action="store_true", help="After each saved run, delete that model's revisions from benchmark-owned cache")
    parser.add_argument("--max-cache-gb", type=float, default=75, help="Benchmark cache size threshold in GiB (default: 75)")
    parser.add_argument("--timeout", type=int, default=1800, help="Maximum seconds per model")
    parser.add_argument("--dry-run", action="store_true", help="Print selection without loading or downloading")
    parser.add_argument("--rescore", type=Path, help="Re-evaluate an existing results.json without running models")
    parser.add_argument("--resume", type=Path, help="Resume an interrupted results.json from this project's results directory")
    args = parser.parse_args()
    if args.cleanup_after and not args.allow_download:
        parser.error("--cleanup-after requires --allow-download")
    if args.max_cache_gb <= 0 or args.timeout <= 0:
        parser.error("timeout and cache limit must be positive")
    if args.rescore:
        cases = {case["id"]: case for case in load_json(ROOT / "cases.json")["cases"]}
        for entry in load_json(args.rescore):
            outcome = entry["outcome"]
            if not outcome.get("success"):
                print(f"{entry['model']['name']}: model failed; no score")
                continue
            scored = [(sample["id"], score_case(cases[sample["id"]], sample["output"])["passed"])
                      for sample in outcome["samples"]]
            print(f"{entry['model']['name']}: {sum(p for _, p in scored)}/{len(scored)} passed")
            for name, passed in scored:
                if not passed:
                    print(f"  FAIL: {name}")
        return
    registry = load_json(ROOT / "models.json")
    check_registry(registry)
    models = registry["models"]
    if args.list:
        for item in models:
            print(f"{item['name']} | {item['model_id']} | {item['quantization']}"
                  f" | default={item.get('enabled', False)} | overnight={item.get('overnight', False)}"
                  f" | experimental={item.get('experimental', False)}")
        return
    if sum(bool(value) for value in (args.all, args.overnight, args.model)) > 1:
        parser.error("Use only one of --all, --overnight, or --model")
    selected = models if args.all else [m for m in models if m.get("overnight", False)] if args.overnight else (
        [m for m in models if m["name"] in args.model] if args.model else [
            m for m in models if m.get("enabled", False)])
    if not selected:
        parser.error("No models selected")
    if args.model and len(selected) != len(set(args.model)):
        parser.error("Unknown model name or duplicate --model")
    cases = load_json(ROOT / "cases.json")["cases"]
    print(f"Selected: {[m['name'] for m in selected]} | cases={len(cases)} | downloads={args.allow_download} | cleanup={args.cleanup_after}")
    if args.dry_run:
        return
    if any(m["backend"] == "gguf" for m in selected):
        from .gguf_backend import find_server
        try:
            print(f"GGUF server: {find_server()}", flush=True)
        except RuntimeError as exc:
            parser.error(str(exc) + ". Install llama.cpp before the overnight run.")
    if args.resume:
        results_path = args.resume.resolve()
        allowed_root = (ROOT / "results").resolve()
        if results_path.name != "results.json" or not results_path.parent.is_relative_to(allowed_root):
            parser.error("--resume must point to a benchmarks/results/<run>/results.json")
        run_dir = results_path.parent
        saved_config = load_json(run_dir / "run_config.json")
        if saved_config["models"] != selected or saved_config["cases"] != cases:
            parser.error("Saved models/cases differ from this selection; refusing unsafe resume")
        summary = load_json(results_path)
        finished_names = [e["model"]["name"] for e in summary]
        if finished_names != [m["name"] for m in selected[:len(summary)]]:
            parser.error("Saved results are not a prefix of selected models")
        print(f"Resuming {run_dir.name}: {len(summary)} model(s) already saved", flush=True)
    else:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        run_dir = ROOT / "results" / stamp
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "run_config.json").write_text(
            json.dumps({"models": selected, "cases": cases, "allow_download": args.allow_download,
                        "cleanup_after": args.cleanup_after, "timeout": args.timeout,
                        "max_cache_gb": args.max_cache_gb}, indent=2), encoding="utf-8")
        summary = []
    for index, model in enumerate(selected, 1):
        if index <= len(summary):
            continue
        print(f"[{index}/{len(selected)}] Testing {model['name']}...", flush=True)
        outcome = execute_one(model, cases, args.timeout, args.allow_download, run_dir, args.max_cache_gb)
        if outcome["success"]:
            scored = []
            by_id = {case["id"]: case for case in cases}
            for sample in outcome["samples"]:
                sample["score"] = score_case(by_id[sample["id"]], sample["output"])
                scored.append(sample["score"]["passed"])
            outcome["passed"] = sum(scored)
            outcome["total"] = len(scored)
            print(f"  {sum(scored)}/{len(scored)} case checks passed", flush=True)
        else:
            print(f"  FAILED: {outcome['error'].splitlines()[-1]}", flush=True)
        entry = {"model": model, "outcome": outcome}
        summary.append(entry)
        # Save after EVERY model; interruption does not lose prior results.
        results_path = run_dir / "results.json"
        results_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        # When adjacent profiles share a Hub repo, keep the weights until its
        # last profile (Q4 vs JSON mode and Q4 vs Q8). Then reclaim them once.
        next_model = selected[index] if index < len(selected) else None
        same_repo_next = next_model is not None and next_model["model_id"] == model["model_id"]
        if args.cleanup_after and results_path.is_file() and not same_repo_next:
            try:
                cleanup = cleanup_repo(ROOT / "model_cache", model["model_id"])
                print(f"  Cleaned benchmark-owned model: {cleanup['deleted_revisions']} revision(s)"
                      f" (~{cleanup['freed_bytes']/2**30:.2f} GiB), including failed runs", flush=True)
            except Exception as exc:
                print(f"  Cleanup skipped due to error: {exc}", flush=True)
    report = ["# Fantasy model benchmark", "", f"Cases: {len(cases)}", "",
              "| Model | Score | Mean generation tok/s | Status |",
              "|---|---:|---:|---|"]
    for entry in summary:
        outcome = entry["outcome"]
        if outcome["success"]:
            speeds = [s["tokens_per_second"] for s in outcome["samples"]
                      if s.get("tokens_per_second") is not None]
            average = sum(speeds) / len(speeds) if speeds else 0
            invalid = sum(s.get("score", {}).get("json_valid") is False for s in outcome["samples"])
            report.append(f"| {entry['model']['name']} | {outcome['passed']}/{outcome['total']} | {average:.2f} | completed; {invalid} invalid JSON |")
        else:
            report.append(f"| {entry['model']['name']} | — | — | failed (see log) |")
    report.extend(["", "Raw JSON and per-model logs are saved beside this report.",
                   "These are limited deterministic checks, not a comprehensive measure of model quality."])
    (run_dir / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Results: {run_dir / 'results.json'}")
    print(f"Report: {run_dir / 'report.md'}")
    from .compare import collect, markdown
    comparison_path = ROOT / "results" / "comparison.md"
    comparison_path.write_text(markdown(collect()), encoding="utf-8")
    print(f"Comparison: {comparison_path}")


if __name__ == "__main__":
    main()

"""Compare complete 45-case benchmark results across saved runs, without inference."""
import argparse
import json
from pathlib import Path
from statistics import mean

from .scoring import score_case

ROOT = Path(__file__).resolve().parent


def collect(root=ROOT):
    current_cases = json.loads((root / "cases.json").read_text(encoding="utf-8"))["cases"]
    expected_ids = [case["id"] for case in current_cases]
    by_id = {case["id"]: case for case in current_cases}
    latest = {}
    for path in sorted((root / "results").glob("*/results.json")):
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for entry in entries:
            result = entry.get("outcome", {})
            samples = result.get("samples", [])
            if not result.get("success") or [sample.get("id") for sample in samples] != expected_ids:
                continue
            if not all("output" in sample for sample in samples):
                continue
            # Re-score *raw* saved output with the CURRENT scoring rules. This
            # ensures older 38/45 and 26/45 runs get the same word/number fix.
            scores = [score_case(by_id[sample["id"]], sample["output"]) for sample in samples]
            model_name = entry["model"]["name"]
            speeds = [sample["tokens_per_second"] for sample in samples
                      if isinstance(sample.get("tokens_per_second"), (int, float))]
            times = [sample["generation_seconds"] for sample in samples
                     if isinstance(sample.get("generation_seconds"), (int, float))]
            latest[model_name] = {
                "name": model_name, "passed": sum(bool(score["passed"]) for score in scores),
                "total": len(samples), "invalid_json": sum(score.get("json_valid") is False
                                                       for score in scores),
                "avg_tps": mean(speeds) if speeds else 0,
                "avg_seconds": mean(times) if times else 0,
                "source": path.parent.name,
            }
    return sorted(latest.values(), key=lambda row: (-row["passed"], -row["avg_tps"], row["name"]))


def markdown(rows):
    lines = ["# Fantasy AI model comparison", "",
             "Latest complete run for each model profile, ranked by passed checks then speed.",
             "Only runs with the current case IDs and recorded per-case scores are included.",
             "", "| Rank | Model | Passed | Invalid JSON | Mean tok/s | Mean s/case | Run |",
             "|---:|---|---:|---:|---:|---:|---|"]
    for index, row in enumerate(rows, 1):
        lines.append(f"| {index} | {row['name']} | {row['passed']}/{row['total']} | "
                     f"{row['invalid_json']} | {row['avg_tps']:.2f} | {row['avg_seconds']:.1f} | {row['source']} |")
    lines += ["", "**Limits:** Heuristic checks; not verified football accuracy, model consistency,",
              "real-time data quality, or production latency. NF4 and GGUF backend timing includes",
              "different inference runtimes, so speed is indicative, not a controlled cross-backend test."]
    if not rows:
        lines += ["", "No complete matching runs found yet."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Build an offline comparison from existing results")
    parser.add_argument("--save", action="store_true", help="Save comparison.md under benchmarks/results")
    args = parser.parse_args()
    report = markdown(collect())
    print(report)
    if args.save:
        path = ROOT / "results" / "comparison.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(report, encoding="utf-8")
        print(f"Saved: {path}")


if __name__ == "__main__":
    main()

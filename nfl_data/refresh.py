"""Safely fetch and maintain NFL data snapshots without changing legacy caches."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

DEFAULT_ROOT = Path(__file__).resolve().parent / "snapshots"
# Freshness is our fetch cadence, NOT a guarantee the upstream feed has updated.
REFRESH_HOURS = {
    "player_stats": 6,
    "depth_charts": 6,
    "schedules": 12,
    "injuries": 3,
    "rosters": 6,
    "rosters_weekly": 6,
}
REQUIRED_COLUMNS = {
    "player_stats": {"season", "week"},
    "depth_charts": set(),
    "schedules": set(),
    "injuries": set(),
    "rosters": set(),
    "rosters_weekly": set(),
}


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def load_manifest(root=DEFAULT_ROOT):
    path = Path(root) / "manifest.json"
    if not path.exists():
        return {"version": 1, "entries": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("entries"), dict):
        raise ValueError("Unsupported snapshot manifest format")
    return payload


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("x", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def key(dataset, season):
    return f"{dataset}:{int(season)}"


def age_hours(entry, current=None):
    current = current or now_utc()
    return max(0., (current - parse_utc(entry["fetched_at_utc"])).total_seconds() / 3600)

def fetch_dataset(nfl, dataset, season):
    season = int(season)

    if dataset == "player_stats":
        return nfl.load_player_stats(
            seasons=season,
            summary_level="week",
        )

    loaders = {
        "depth_charts": "load_depth_charts",
        "schedules": "load_schedules",
        "injuries": "load_injuries",
        "rosters": "load_rosters",
        "rosters_weekly": "load_rosters_weekly",
    }

    if dataset not in loaders:
        raise ValueError(f"Unknown dataset: {dataset}")

    loader = getattr(nfl, loaders[dataset])
    return loader(seasons=season)

def refresh_one(dataset, season, root=DEFAULT_ROOT, provider=None, current=None):
    """Publish an independently validated snapshot; preserve the old one on failure.

    No legacy ingestion path, model file, RAG index or user cache is modified.
    """
    if dataset not in REFRESH_HOURS:
        raise ValueError(f"Unknown dataset: {dataset}")
    season = int(season)
    if not 1999 <= season <= now_utc().year + 1:
        raise ValueError("Unreasonable NFL season")
    if provider is None:
        import nflreadpy as provider
    root = Path(root)
    frame = fetch_dataset(provider, dataset, season)
    rows = int(frame.height)
    columns = [str(c) for c in frame.columns]
    if rows <= 0:
        raise ValueError(f"Upstream returned zero {dataset} rows for {season}; refusing to overwrite")
    missing = REQUIRED_COLUMNS[dataset] - set(columns)
    if missing:
        raise ValueError(f"Missing required {dataset} columns: {sorted(missing)}")
    path = root / str(season) / f"{dataset}-{uuid.uuid4().hex}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{uuid.uuid4().hex}.parquet")
    try:
        frame.write_parquet(str(tmp))
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise IOError("No parquet bytes written")
        file_hash = hashlib.sha256(tmp.read_bytes()).hexdigest()
        manifest = load_manifest(root)
        entry = {
            "dataset": dataset, "season": season,
            "fetched_at_utc": iso(current or now_utc()),
            "rows": rows, "columns": columns,
            "path": f"{season}/{path.name}",
            "sha256": file_hash,
            "source": "nflreadpy/nflverse", "upstream_updated_at": None,
            "freshness_note": "Fetch time is not source publication time",
        }
        # Immutable snapshot filename: a crash before manifest publication cannot
        # corrupt the previously published version.
        previous = manifest["entries"].get(key(dataset, season))
        os.replace(tmp, path)
        manifest["entries"][key(dataset, season)] = entry
        try:
            atomic_json(root / "manifest.json", manifest)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        if previous and previous.get("path") != entry["path"]:
            old = root / previous["path"]
            # Only remove a prior snapshot under the same season directory.
            if old.parent.resolve() == path.parent.resolve() and old.name.startswith(dataset + "-"):
                old.unlink(missing_ok=True)
        return entry
    finally:
        tmp.unlink(missing_ok=True)


def describe(dataset, season, root=DEFAULT_ROOT, current=None):
    root = Path(root)
    entry = load_manifest(root)["entries"].get(key(dataset, season))
    if not entry:
        return {"dataset": dataset, "season": season, "status": "missing"}
    path = root / entry["path"]
    if not path.is_file():
        return {"dataset": dataset, "season": season, "status": "missing_file"}
    # Guard against stale metadata and corrupted/replaced snapshots.
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        return {"dataset": dataset, "season": season, "status": "hash_mismatch"}
    hours = round(age_hours(entry, current), 2)
    return {**entry, "age_hours": hours,
            "status": "fresh" if hours < REFRESH_HOURS[dataset] else "stale",
            "refresh_interval_hours": REFRESH_HOURS[dataset]}


def _selected(args):
    return [args.dataset] if args.dataset != "all" else list(REFRESH_HOURS)


def run_once(args, provider=None):
    failures = 0
    for dataset in _selected(args):
        prior = describe(dataset, args.season, args.root)
        if not args.force and prior["status"] == "fresh":
            print(f"[SKIP] {dataset}: snapshot age {prior['age_hours']}h", flush=True)
            continue
        started = time.monotonic()
        try:
            entry = refresh_one(dataset, args.season, args.root, provider=provider)
            print(f"[OK] {dataset}: {entry['rows']:,} rows, {time.monotonic()-started:.1f}s, {entry['fetched_at_utc']}", flush=True)
        except Exception as exc:
            failures += 1
            print(f"[ERROR] {dataset}: {type(exc).__name__}: {exc} (existing snapshot preserved when fetch/validation failed)", file=sys.stderr, flush=True)
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("once", "status", "watch"))
    parser.add_argument("--season", type=int, help="NFL season; default uses nflreadpy's current season")
    parser.add_argument("--dataset", choices=["all", *REFRESH_HOURS], default="all")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--force", action="store_true", help="Fetch even when the snapshot is recent")
    parser.add_argument("--poll-minutes", type=int, default=15, help="Watch mode polling interval")
    args = parser.parse_args(argv)
    if args.season is None:
        try:
            import nflreadpy
            args.season = int(nflreadpy.get_current_season())
        except Exception as exc:
            parser.error(f"Specify --season or install nflreadpy: {exc}")
    if args.command == "status":
        for ds in _selected(args):
            status = describe(ds, args.season, args.root)
            print(f"{ds}: {status['status']}" + (f" | {status['rows']:,} rows | age {status['age_hours']}h | fetched {status['fetched_at_utc']}" if "rows" in status else ""))
        return 0
    if args.command == "once":
        return run_once(args)
    if args.poll_minutes < 1:
        parser.error("--poll-minutes must be at least 1")
    print(f"Watching season {args.season}; poll every {args.poll_minutes} minutes. Ctrl+C to stop.", flush=True)
    try:
        while True:
            run_once(args)
            time.sleep(args.poll_minutes * 60)
    except KeyboardInterrupt:
        print("Stopped watch.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

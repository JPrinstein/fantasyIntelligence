"""Verified NFL snapshot readers with a legacy-cache fallback."""
from __future__ import annotations

from pathlib import Path
import warnings

from nfl_data.refresh import DEFAULT_ROOT, REFRESH_HOURS, describe, load_manifest, key


class SnapshotIntegrityError(RuntimeError):
    """A published snapshot cannot be safely consumed."""


def read_dataset(dataset, season, legacy_path, required_columns, *, root=None, with_metadata=False):
    import polars as pl

    if dataset not in REFRESH_HOURS:
        raise ValueError(f"Unsupported dataset: {dataset}")
    season = int(season)
    root = Path(root) if root is not None else DEFAULT_ROOT
    legacy_path = Path(legacy_path)
    expected = set(required_columns)

    # Resolve a published immutable snapshot; absent snapshots use the old cache.
    # A corrupt published snapshot never silently falls back to older data.
    for attempt in range(2):
        entry = load_manifest(root)["entries"].get(key(dataset, season))
        if entry is None:
            if not legacy_path.is_file():
                raise FileNotFoundError(
                    f"No {dataset} snapshot for {season} and no legacy cache at {legacy_path}. "
                    f"Run: python -m nfl_data.refresh once --season {season}"
                )
            frame = pl.read_parquet(legacy_path)
            meta = {"source": "legacy_cache", "freshness": "unknown", "fetched_at_utc": None}
            break

        # Reject paths outside the controlled snapshot root and named season folder.
        rel = Path(entry.get("path", ""))
        expected_dir = (root / str(season)).resolve()
        full_path = (root / rel).resolve()
        if full_path.parent != expected_dir or not full_path.name.startswith(dataset + "-") or full_path.suffix != ".parquet":
            raise SnapshotIntegrityError(f"Unsafe snapshot path for {dataset}:{season}")

        info = describe(dataset, season, root)
        if info["status"] in {"missing_file", "hash_mismatch"}:
            # Concurrent refresh may replace the manifest and delete an old file.
            if attempt == 0 and load_manifest(root)["entries"].get(key(dataset, season)) != entry:
                continue
            raise SnapshotIntegrityError(
                f"Published {dataset}:{season} failed integrity verification ({info['status']}). "
                "Re-run the refresh; no legacy fallback was used."
            )
        if info.get("path") != entry["path"]:
            continue
        try:
            frame = pl.read_parquet(full_path)
        except FileNotFoundError:
            if attempt == 0:
                continue
            raise SnapshotIntegrityError(f"Snapshot replaced during load: {dataset}:{season}")
        meta = {
            "source": "verified_snapshot",
            "freshness": info["status"],
            "fetched_at_utc": entry["fetched_at_utc"],
            "age_hours": info["age_hours"],
        }
        if meta["freshness"] == "stale":
            warnings.warn(
                f"{dataset} season {season} snapshot is {meta['age_hours']}h old; "
                "fetch age does not establish upstream publication freshness",
                RuntimeWarning,
                stacklevel=2,
            )
        break
    else:
        raise SnapshotIntegrityError(f"Unable to read a consistent snapshot: {dataset}:{season}")

    missing = expected - set(frame.columns)
    if missing:
        raise SnapshotIntegrityError(
            f"{dataset}:{season} from {meta['source']} lacks columns required by the existing tool: "
            f"{sorted(missing)}"
        )
    return (frame, meta) if with_metadata else frame

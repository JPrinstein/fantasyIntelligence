import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from datetime import datetime, timedelta, timezone

from nfl_data.refresh import (
    REFRESH_HOURS, age_hours, describe, fetch_dataset, load_manifest,
    refresh_one, run_once, iso,
)


class Frame:
    def __init__(self, rows=3, columns=None, fail=False):
        self.height = rows
        self.columns = columns or ["season", "week", "player_id"]
        self.fail = fail

    def write_parquet(self, path):
        if self.fail:
            raise IOError("failed write")
        Path(path).write_bytes(b"PAR1fake-offline-test")


class Provider:
    def __init__(self, frame=None):
        self.frame = frame or Frame()
        self.calls = []
        self.raise_on = None

    def _get(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        if self.raise_on == name:
            raise ConnectionError("simulated outage")
        return self.frame

    def load_player_stats(self, **kwargs):
        return self._get("player_stats", **kwargs)
    def load_depth_charts(self, **kwargs):
        return self._get("depth_charts", **kwargs)
    def load_schedules(self, **kwargs):
        return self._get("schedules", **kwargs)
    def load_injuries(self, **kwargs):
        return self._get("injuries", **kwargs)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.provider = Provider()
        self.date = datetime(2026, 11, 11, tzinfo=timezone.utc)

    def test_missing(self):
        self.assertEqual(describe("player_stats", 2026, self.root)["status"], "missing")

    def test_publishes(self):
        entry = refresh_one("player_stats", 2026, self.root, self.provider, self.date)
        self.assertEqual(entry["rows"], 3)
        self.assertEqual(describe("player_stats", 2026, self.root, self.date)["status"], "fresh")
        self.assertEqual(self.provider.calls[0][2], {"seasons": 2026, "summary_level": "week"})

    def test_fetch_all(self):
        for ds in REFRESH_HOURS:
            refresh_one(ds, 2026, self.root, self.provider, self.date)
            self.assertEqual(describe(ds, 2026, self.root, self.date)["status"], "fresh")

    def test_stale(self):
        refresh_one("injuries", 2026, self.root, self.provider, self.date)
        later = self.date + timedelta(hours=7)
        self.assertEqual(describe("injuries", 2026, self.root, later)["status"], "stale")

    def test_failed_fetch_keeps_previous(self):
        before = refresh_one("player_stats", 2026, self.root, self.provider, self.date)
        self.provider.raise_on = "player_stats"
        with self.assertRaises(ConnectionError):
            refresh_one("player_stats", 2026, self.root, self.provider)
        self.assertEqual(load_manifest(self.root)["entries"]["player_stats:2026"], before)
        self.assertTrue((self.root / before["path"]).exists())

    def test_empty_frame_refused(self):
        self.provider.frame = Frame(rows=0)
        with self.assertRaisesRegex(ValueError, "zero"):
            refresh_one("player_stats", 2026, self.root, self.provider)

    def test_missing_stats_columns_refused(self):
        self.provider.frame = Frame(columns=["season", "player_name"])
        with self.assertRaisesRegex(ValueError, "week"):
            refresh_one("player_stats", 2026, self.root, self.provider)

    def test_failed_write_no_manifest(self):
        self.provider.frame = Frame(fail=True)
        with self.assertRaises(IOError):
            refresh_one("player_stats", 2026, self.root, self.provider)
        self.assertEqual(load_manifest(self.root)["entries"], {})

    def test_refresh_replaces_only_owned_version(self):
        first = refresh_one("player_stats", 2026, self.root, self.provider, self.date)
        second = refresh_one("player_stats", 2026, self.root, self.provider, self.date)
        self.assertNotEqual(first["path"], second["path"])
        self.assertFalse((self.root / first["path"]).exists())
        self.assertTrue((self.root / second["path"]).exists())

    def test_detects_corruption(self):
        entry = refresh_one("player_stats", 2026, self.root, self.provider, self.date)
        (self.root / entry["path"]).write_bytes(b"bad")
        self.assertEqual(describe("player_stats", 2026, self.root)["status"], "hash_mismatch")

    def test_skip_fresh(self):
        refresh_one("player_stats", 2026, self.root, self.provider)
        self.provider.calls.clear()
        args = SimpleNamespace(dataset="player_stats", season=2026, root=self.root, force=False)
        self.assertEqual(run_once(args, self.provider), 0)
        self.assertEqual(self.provider.calls, [])

    def test_failure_does_not_interrupt_other_datasets(self):
        self.provider.raise_on = "depth_charts"
        args = SimpleNamespace(dataset="all", season=2026, root=self.root, force=True)
        self.assertEqual(run_once(args, self.provider), 1)
        self.assertEqual(describe("player_stats", 2026, self.root)["status"], "fresh")
        self.assertEqual(describe("schedules", 2026, self.root)["status"], "fresh")
        self.assertEqual(describe("injuries", 2026, self.root)["status"], "fresh")


if __name__ == "__main__":
    unittest.main()

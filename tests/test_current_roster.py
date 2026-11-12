
"""Tests for current NFL roster resolution."""

import unittest
from unittest.mock import patch

import polars as pl

from nfl_data.roster import get_player_roster


class RosterTests(unittest.TestCase):

    def setUp(self):
        self.frame = pl.DataFrame({
            "season": [2026, 2026],
            "week": [4, 9],
            "gsis_id": ["00-TEST", "00-TEST"],
            "full_name": ["Example Player", "Example Player"],
            "team": ["AAA", "BBB"],
            "position": ["WR", "WR"],
            "status": ["ACT", "ACT"],
            "depth_chart_position": ["WR", "WR"],
        })

        self.metadata = {
            "source": "verified_snapshot",
            "freshness": "fresh",
            "fetched_at_utc": "2026-11-11T20:00:00Z",
        }

    def lookup(self, name, frame=None):
        with patch(
            "nfl_data.roster.read_dataset",
            return_value=(
                self.frame if frame is None else frame,
                self.metadata,
            ),
        ):
            return get_player_roster(name, 2026)

    def test_latest_team_wins(self):
        result = self.lookup("Example Player")

        self.assertTrue(result["success"])
        self.assertEqual(result["team"], "BBB")
        self.assertEqual(result["week"], 9)

    def test_case_insensitive_lookup(self):
        result = self.lookup("example player")

        self.assertTrue(result["success"])

    def test_missing_player(self):
        result = self.lookup("Unknown Player")

        self.assertFalse(result["success"])

    def test_ambiguous_player_name(self):
        other = self.frame.with_columns(
            pl.lit("00-OTHER").alias("gsis_id")
        )

        frame = pl.concat([self.frame, other])

        result = self.lookup("Example Player", frame)

        self.assertFalse(result["success"])

    def test_conflicting_latest_teams(self):
        extra = self.frame.tail(1).with_columns(
            pl.lit("CCC").alias("team")
        )

        frame = pl.concat([self.frame, extra])

        result = self.lookup("Example Player", frame)

        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()


"""Tests for verified NFL injury report lookup."""

import unittest
from unittest.mock import patch

import polars as pl

from nfl_data.injuries import get_player_injury


class PlayerInjuryTests(unittest.TestCase):

    def setUp(self):
        self.frame = pl.DataFrame({
            "season": [2026, 2026, 2026, 2026],
            "week": [8, 10, 10, 11],
            "gsis_id": [
                "00-PLAYER", "00-PLAYER",
                "00-PLAYER", "00-OTHER",
            ],
            "full_name": [
                "Example Player", "Example Player",
                "Example Player", "Other Player",
            ],
            "team": ["AAA", "AAA", "AAA", "BBB"],
            "report_status": [None, "Questionable", None, "Out"],
            "practice_status": [
                "Did Not Participate In Practice",
                "Limited Participation in Practice",
                "Full Participation in Practice",
                "Did Not Participate In Practice",
            ],
            "report_primary_injury": [
                "Ankle", "Ankle", "Ankle", "Knee",
            ],
            "report_secondary_injury": [None] * 4,
            "practice_primary_injury": [
                "Ankle", "Ankle", "Ankle", "Knee",
            ],
            "practice_secondary_injury": [None] * 4,
        })

    def lookup(self, name, frame=None):
        with patch(
            "nfl_data.injuries.read_dataset",
            return_value=(
                self.frame if frame is None else frame,
                {
                    "source": "verified_snapshot",
                    "freshness": "fresh",
                },
            ),
        ):
            return get_player_injury(name, 2026)

    def test_latest_player_report_week(self):
        result = self.lookup("Example Player")

        self.assertTrue(result["success"])
        self.assertEqual(result["report_week"], 10)
        self.assertEqual(result["latest_dataset_week"], 11)

    def test_preserves_multiple_practice_reports(self):
        result = self.lookup("Example Player")

        self.assertEqual(len(result["practice_statuses"]), 2)
        self.assertIn(
            "Full Participation in Practice",
            result["practice_statuses"],
        )
        self.assertIn(
            "Limited Participation in Practice",
            result["practice_statuses"],
        )

    def test_missing_report_not_healthy(self):
        result = self.lookup("Unknown Player")

        self.assertFalse(result["success"])
        self.assertIn("does not establish", result["error"])

    def test_case_insensitive_match(self):
        result = self.lookup("example player")

        self.assertTrue(result["success"])

    def test_ambiguous_identity(self):
        extra = self.frame.head(1).with_columns(
            pl.lit("00-DIFFERENT").alias("gsis_id")
        )
        result = self.lookup(
            "Example Player",
            pl.concat([self.frame, extra]),
        )

        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()

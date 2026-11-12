"""Tests for verified NFL schedule lookups."""

import unittest
from unittest.mock import patch

import polars as pl

from nfl_data.schedules import get_team_schedule


class TeamScheduleTests(unittest.TestCase):

    def setUp(self):
        self.frame = pl.DataFrame({
            "season": [2026, 2026, 2026],
            "week": [8, 9, 10],
            "game_type": ["REG", "REG", "REG"],
            "gameday": [
                "2026-10-25",
                "2026-11-01",
                "2026-11-15",
            ],
            "gametime": ["13:00", "13:00", "13:00"],
            "home_team": ["AAA", "CCC", "AAA"],
            "away_team": ["BBB", "DDD", "EEE"],
            "home_score": [21, 10, None],
            "away_score": [14, 7, None],
            "game_id": ["game8", "game9", "game10"],
        })

    def lookup(self, team, week=None, as_of="2026-11-11"):
        with patch(
            "nfl_data.schedules.read_dataset",
            return_value=(
                self.frame,
                {"source": "verified_snapshot"},
            ),
        ):
            return get_team_schedule(
                team, 2026, week, as_of=as_of
            )

    def test_next_game(self):
        result = self.lookup("AAA")

        self.assertTrue(result["success"])
        self.assertEqual(result["opponent"], "EEE")
        self.assertEqual(result["week"], 10)

    def test_completed_game(self):
        result = self.lookup("AAA", week=8)

        self.assertTrue(result["completed"])
        self.assertEqual(result["home_score"], 21)

    def test_bye_week(self):
        result = self.lookup("AAA", week=9)

        self.assertTrue(result["success"])
        self.assertTrue(result["bye_week"])

    def test_no_upcoming_game(self):
        result = self.lookup("BBB", as_of="2026-11-11")

        self.assertFalse(result["success"])
        self.assertIn("No upcoming", result["error"])

    def test_unknown_team(self):
        result = self.lookup("ZZZ")

        self.assertFalse(result["success"])

    def test_invalid_week(self):
        with self.assertRaises(ValueError):
            self.lookup("AAA", week=20)


if __name__ == "__main__":
    unittest.main()

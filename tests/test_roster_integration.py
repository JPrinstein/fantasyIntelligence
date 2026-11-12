
"""Tests for roster tool integration."""

import unittest
from unittest.mock import patch

from agent.planner import AVAILABLE_TOOLS, enforce_required_tools
from agent.executor import execute_plan
from agent.evidence import build_evidence


class RosterIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.roster_result = {
            "success": True,
            "player": "Example Player",
            "player_id": "00-TEST",
            "season": 2026,
            "week": 9,
            "team": "BBB",
            "position": "WR",
            "status": "ACT",
            "depth_chart_position": "WR",
            "data_source": {
                "source": "verified_snapshot",
                "freshness": "fresh",
            },
        }

    def test_tool_registered(self):
        self.assertIn("player_roster", AVAILABLE_TOOLS)
        self.assertIn(
            "player_name",
            AVAILABLE_TOOLS["player_roster"]["arguments"],
        )

    def test_current_roster_season(self):
        plan = {
            "tools": [{
                "tool": "player_roster",
                "args": {
                    "player_name": "Example Player",
                    "season": 2025,
                },
            }]
        }

        with patch(
            "agent.planner.nflreadpy.get_current_season",
            return_value=2026,
        ):
            result = enforce_required_tools(
                "What team does Example Player play for?",
                plan,
            )

        self.assertEqual(
            result["tools"][0]["args"]["season"],
            2026,
        )

    def test_historical_roster_season(self):
        plan = {
            "tools": [{
                "tool": "player_roster",
                "args": {
                    "player_name": "Example Player",
                    "season": 2025,
                },
            }]
        }

        result = enforce_required_tools(
            "What team was Example Player on in 2025?",
            plan,
        )

        self.assertEqual(
            result["tools"][0]["args"]["season"],
            2025,
        )

    def test_executor_calls_roster_lookup(self):
        plan = {
            "tools": [{
                "tool": "player_roster",
                "args": {
                    "player_name": "Example Player",
                    "season": 2026,
                },
            }]
        }

        with patch(
            "agent.executor.player_roster",
            return_value=self.roster_result,
        ) as lookup:
            execution = execute_plan(plan, None, None, None)

        lookup.assert_called_once_with("Example Player", 2026)
        self.assertTrue(execution["results"][0]["result"]["success"])

    def test_roster_evidence(self):
        execution = {
            "success": True,
            "results": [{
                "tool": "player_roster",
                "result": self.roster_result,
            }],
        }

        evidence = build_evidence(execution)
        text = evidence["tool_context"]

        self.assertIn("BBB", text)
        self.assertIn("Roster week: 9", text)
        self.assertIn("verified_snapshot", text)
        self.assertIn("does not independently prove", text)

    def test_missing_roster_evidence(self):
        execution = {
            "success": True,
            "results": [{
                "tool": "player_roster",
                "result": {
                    "success": False,
                    "error": "No roster record found",
                },
            }],
        }

        evidence = build_evidence(execution)

        self.assertIn(
            "No roster record found",
            evidence["tool_context"],
        )


if __name__ == "__main__":
    unittest.main()

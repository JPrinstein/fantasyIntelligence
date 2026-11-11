import unittest

from agent.evidence import build_evidence


class TestEvidence(unittest.TestCase):

    def test_rag_only(self):
        execution = {
            "success": True,
            "results": [
                {
                    "tool": "rag_search",
                    "result": {
                        "success": True,
                        "content": "PPR means points per reception."
                    }
                }
            ]
        }

        evidence = build_evidence(execution)

        self.assertEqual(
            evidence["rag_context"],
            "PPR means points per reception."
        )
        self.assertEqual(evidence["tool_context"], "")

    def test_player_stats_only(self):
        execution = {
            "success": True,
            "results": [
                {
                    "tool": "player_stats",
                    "result": {
                        "success": True,
                        "player": "Lamar Jackson",
                        "position": "QB",
                        "season": 2025,
                        "games": 3,
                        "stats": {"passing_yards": 489}
                    }
                }
            ]
        }

        evidence = build_evidence(execution)

        self.assertIn("Player: Lamar Jackson", evidence["tool_context"])
        self.assertIn("passing_yards: 489", evidence["tool_context"])

    def test_depth_chart_only(self):
        execution = {
            "success": True,
            "results": [
                {
                    "tool": "player_depth_chart",
                    "result": {
                        "success": True,
                        "player": "Lamar Jackson",
                        "season": 2025,
                        "team": "BAL",
                        "position": "QB",
                        "position_name": "Quarterback",
                        "position_rank": 1
                    }
                }
            ]
        }

        evidence = build_evidence(execution)

        self.assertIn("Depth chart rank: 1", evidence["tool_context"])

    def test_mixed_tools_no_duplicate_context(self):
        execution = {
            "success": True,
            "results": [
                {
                    "tool": "player_stats",
                    "result": {
                        "success": True,
                        "player": "Lamar Jackson",
                        "position": "QB",
                        "season": 2025,
                        "games": 3,
                        "stats": {"passing_yards": 489}
                    }
                },
                {
                    "tool": "league_context",
                    "result": {
                        "success": True,
                        "content": "League: Test League"
                    }
                }
            ]
        }

        evidence = build_evidence(execution)

        self.assertEqual(
            evidence["tool_context"].count("Player: Lamar Jackson"),
            1
        )
        self.assertEqual(
            evidence["league_context"],
            "League: Test League"
        )


if __name__ == "__main__":
    unittest.main()
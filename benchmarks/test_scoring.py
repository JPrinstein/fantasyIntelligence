import unittest

from benchmarks.scoring import parse_plan, score_case


class ScoringTests(unittest.TestCase):
    def test_valid_plan(self):
        case = {"kind": "planner", "expected_tools": ["player_stats"],
                "expected_args": {"player_stats": [{"player_name": "Lamar Jackson", "season": 2025}]}}
        self.assertTrue(score_case(case, '{"tools":[{"tool":"player_stats","args":{"player_name":"Lamar Jackson","season":2025}}]}')["passed"])

    def test_invented_recent_games_fails(self):
        case = {"kind": "planner", "expected_tools": ["player_stats"],
                "expected_args": {"player_stats": [{"player_name": "Lamar Jackson", "season": 2025}]}}
        bad = '{"tools":[{"tool":"player_stats","args":{"player_name":"Lamar Jackson","season":2025,"recent_games":3}}]}'
        self.assertFalse(score_case(case, bad)["passed"])

    def test_repeated_tools_count_matters(self):
        case = {"kind": "planner", "expected_tools": ["player_stats", "player_stats"]}
        self.assertFalse(score_case(case, '{"tools":[{"tool":"player_stats","args":{}}]}')["passed"])

    def test_invalid_json(self):
        self.assertIsNone(parse_plan("hello"))

    def test_answer_forbidden_phrase(self):
        case = {"kind": "answer", "must_contain": ["2549"], "forbidden_phrases": ["per game"]}
        self.assertFalse(score_case(case, "2549 passing yards per game")["passed"])

    def test_number_thousands_separator_equivalence(self):
        case = {"kind": "answer", "must_contain": ["2,549", "4,224"]}
        self.assertTrue(score_case(case, "Lamar: 2549; Josh: 4224")["passed"])

    def test_any_of_supported_refusal(self):
        case = {"kind": "answer", "must_contain_any": ["not enough", "unknown"]}
        self.assertTrue(score_case(case, "There is not enough information")["passed"])
        self.assertFalse(score_case(case, "He is definitely healthy")["passed"])

    def test_written_number_equivalence(self):
        case = {"kind": "answer", "must_contain": ["1"]}
        self.assertTrue(score_case(case, "One point per reception")["passed"])
        self.assertFalse(score_case(case, "Two points per reception")["passed"])


if __name__ == "__main__":
    unittest.main()

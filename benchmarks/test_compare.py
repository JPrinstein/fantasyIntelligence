import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.compare import collect, markdown


class CompareTests(unittest.TestCase):
    def test_selects_latest_complete_and_sorts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "cases.json").write_text(json.dumps({"cases": [
                {"id": "a", "kind": "answer", "must_contain": ["yes"]},
                {"id": "b", "kind": "answer", "must_contain": ["yes"]}]}))
            for folder, score_count in (("20260101_100000", 1), ("20260102_100000", 2)):
                result_folder = root / "results" / folder
                result_folder.mkdir(parents=True)
                samples = [{"id": name, "output": "yes" if i < score_count else "no",
                            "tokens_per_second": 9.5, "generation_seconds": 2.3}
                           for i, name in enumerate(("a", "b"))]
                (result_folder / "results.json").write_text(json.dumps([{
                    "model": {"name": "qwen"}, "outcome": {"success": True, "samples": samples}}]))
            results = collect(root)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["passed"], 2)
            self.assertIn("2/2", markdown(results))


if __name__ == "__main__":
    unittest.main()

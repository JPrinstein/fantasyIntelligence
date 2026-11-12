import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.cache import checked_hub_path, cleanup_repo, directory_size_bytes


class CacheTests(unittest.TestCase):
    def test_cache_size(self):
        with tempfile.TemporaryDirectory() as folder:
            sub = Path(folder) / "a"
            sub.mkdir()
            (sub / "weights.bin").write_bytes(b"12345678")
            self.assertEqual(directory_size_bytes(folder), 8)

    def test_refuses_symlinked_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            target = path / "real"
            target.mkdir()
            try:
                (path / "link").symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable")
            with self.assertRaises(ValueError):
                checked_hub_path(path / "link")

    def test_targeted_cleanup_does_not_select_other_repo(self):
        class Revision:
            commit_hash = "abc123"

        class Repository:
            def __init__(self, identifier):
                self.repo_type = "model"
                self.repo_id = identifier
                self.revisions = [Revision()]

        class Strategy:
            expected_freed_size = 123

            def __init__(self):
                self.executed = False

            def execute(self):
                self.executed = True

        class Info:
            repos = [Repository("Qwen/Qwen3.5-4B"), Repository("Keep/SomethingElse")]

            def __init__(self):
                self.selected = None
                self.strategy = Strategy()

            def delete_revisions(self, *revisions):
                self.selected = revisions
                return self.strategy

        info = Info()
        fake = types.ModuleType("huggingface_hub")
        fake.scan_cache_dir = lambda cache_dir: info
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "hub").mkdir()
            with patch.dict("sys.modules", {"huggingface_hub": fake}):
                result = cleanup_repo(folder, "Keep/DoesNotExist")
                self.assertEqual(result["deleted_revisions"], 0)
                self.assertIsNone(info.selected)
                result = cleanup_repo(folder, "Qwen/Qwen3.5-4B")
                self.assertEqual(info.selected, ("abc123",))
                self.assertTrue(info.strategy.executed)
                self.assertEqual(result["freed_bytes"], 123)


if __name__ == "__main__":
    unittest.main()

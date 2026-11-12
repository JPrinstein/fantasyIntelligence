"""Offline verification of read-through snapshot selection and guardrails."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from nfl_data.readers import SnapshotIntegrityError, read_dataset
from nfl_data.refresh import key
from scripts.enable_auto_refresh import patch as patch_main


class FakeFrame:
    def __init__(self, columns):
        self.columns = columns


class SnapshotReadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name) / 'snapshots'
        self.root.mkdir()
        self.legacy = Path(self.folder.name) / 'legacy.parquet'
        self.legacy.write_bytes(b'legacy')
        self.columns = ['season', 'week', 'player_id']
        self.paths = []
        self.fake = types.SimpleNamespace(read_parquet=self.read_fake)

    def read_fake(self, path):
        self.paths.append(str(path))
        return FakeFrame(self.columns)

    def add_snapshot(self, season=2026):
        directory = self.root / str(season)
        directory.mkdir(exist_ok=True)
        data = b'snapshot bytes'
        file = directory / 'player_stats-test.parquet'
        file.write_bytes(data)
        entry = {'dataset':'player_stats','season':season,
                 'path':f'{season}/{file.name}',
                 'sha256':hashlib.sha256(data).hexdigest(),
                 'fetched_at_utc':'2026-11-11T18:00:00Z'}
        (self.root/'manifest.json').write_text(json.dumps({'version':1,'entries':{key('player_stats',season):entry}}))
        return file

    def call(self):
        with patch.dict(sys.modules, {'polars': self.fake}):
            return read_dataset('player_stats',2026,self.legacy,self.columns,
                                root=self.root,with_metadata=True)

    def test_legacy_if_unpublished(self):
        _, meta = self.call()
        self.assertEqual(meta['source'], 'legacy_cache')
        self.assertEqual(self.paths[-1], str(self.legacy))

    def test_uses_verified_snapshot(self):
        path = self.add_snapshot()
        with patch('nfl_data.readers.describe', return_value={'status':'fresh','age_hours':0.1,'path':'2026/player_stats-test.parquet'}):
            _, meta = self.call()
        self.assertEqual(meta['source'], 'verified_snapshot')
        self.assertEqual(self.paths[-1],str(path))

    def test_refuses_tampered_snapshot(self):
        path = self.add_snapshot()
        path.write_bytes(b'bad')
        with self.assertRaises(SnapshotIntegrityError):
            self.call()
        self.assertEqual(self.paths, [])

    def test_refuses_unsafe_path(self):
        self.add_snapshot()
        manifest_path = self.root/'manifest.json'
        payload = json.loads(manifest_path.read_text())
        payload['entries']['player_stats:2026']['path'] = '../legacy.parquet'
        manifest_path.write_text(json.dumps(payload))
        with self.assertRaises(SnapshotIntegrityError):
            self.call()

    def test_refuses_missing_tool_columns(self):
        self.add_snapshot()
        self.columns = ['season']
        with patch('nfl_data.readers.describe', return_value={'status':'fresh','age_hours':0.1,'path':'2026/player_stats-test.parquet'}):
            with self.assertRaises(SnapshotIntegrityError):
                self.call_with_expected(['season','week'])

    def call_with_expected(self, columns):
        with patch.dict(sys.modules, {'polars':self.fake}):
            return read_dataset('player_stats',2026,self.legacy,columns,root=self.root)

    def test_disabled_auto_refresh(self):
        from nfl_data.auto_refresh import start_background_refresh
        with patch.dict('os.environ', {'FANTASY_NFL_AUTO_REFRESH':'0'}):
            self.assertIsNone(start_background_refresh(season=2026))

    def test_patch_keeps_existing_metrics(self):
        code = 'from llm.runtime import backend\nprint("Inference backend:", backend())\nprint_generation_metrics()\n'
        revised, changed = patch_main(code)
        self.assertTrue(changed)
        self.assertIn('print_generation_metrics()', revised)
        twice, changed = patch_main(revised)
        self.assertFalse(changed)
        self.assertEqual(twice, revised)

    def test_patch_refuses_unknown_main(self):
        with self.assertRaises(ValueError):
            patch_main('print("other")')


if __name__ == '__main__':
    unittest.main()

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from token_booster.diagnostics import doctor,cache_stats
ROOT=Path(__file__).resolve().parents[1]
class DiagnosticTests(unittest.TestCase):
    def test_doctor_package(self):
        d=doctor(ROOT)
        self.assertEqual(d['manifest_version'],'5.0.1')
        self.assertTrue(d['expected_hooks_registered'])
        self.assertTrue(d['plugin_files_present'])
    def test_doctor_safe_default(self):
        with patch.dict(os.environ,{'TOKEN_BOOSTER_READ_CACHE':'0','TOKEN_BOOSTER_READ_BLOCK':'1'}):
            self.assertFalse(doctor(ROOT)['read_blocking_on'])
    def test_empty_stats(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ,{'TOKEN_BOOSTER_STATE_DIR':d}):
                s=cache_stats()
                self.assertEqual(s['sessions_with_state'],0)
                self.assertEqual(s['counters'],{})
    def test_stats_ignores_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'junk.json').write_text('not-json')
            (Path(d)/'valid.json').write_text('{"records":{"hash":{}},"stats":{"reads_observed":3,"oops":"bad"}}')
            with patch.dict(os.environ,{'TOKEN_BOOSTER_STATE_DIR':d}):
                s=cache_stats()
                self.assertEqual(s['sessions_with_state'],1)
                self.assertEqual(s['counters']['reads_observed'],3)
                self.assertNotIn('oops',s['counters'])
if __name__=='__main__':unittest.main()

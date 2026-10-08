import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'audit.py'

class AuditTest(unittest.TestCase):
    def test_reports_metadata_and_excludes_node_modules(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / 'CLAUDE.md').write_text('abc', encoding='utf-8')
            (root / 'big.log').write_bytes(b'x' * 100001)
            (root / 'node_modules').mkdir()
            (root / 'node_modules' / 'secret.txt').write_text('ignored', encoding='utf-8')
            r = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True, check=True)
            self.assertIn('Dateien geprüft: 2', r.stdout)
            self.assertIn('CLAUDE.md', r.stdout)
            self.assertIn('big.log', r.stdout)
            self.assertNotIn('secret.txt', r.stdout)

if __name__ == '__main__':
    unittest.main()

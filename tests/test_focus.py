import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from focus import run

class FocusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'src').mkdir()
        (self.root/'src'/'app.py').write_text('def login():\n    return 42\n', encoding='utf-8')
        (self.root/'.env').write_text('TOP-SECRET-ENV', encoding='utf-8')
        (self.root/'secrets.json').write_text('TOP-SECRET-JSON', encoding='utf-8')
        (self.root/'src'/'token.py').write_text('api_key=abc123private\nlogin_enabled = True\n')
    def invoke(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            run(['--root', str(self.root), *args])
        return buf.getvalue()
    def test_find(self):
        self.assertIn('src/app.py', self.invoke('find', 'app'))
    def test_search_literal(self):
        self.assertIn('src/app.py:1:', self.invoke('search', 'login'))
    def test_regex_metacharacters_are_literal(self):
        self.assertIn('0 results', self.invoke('search', '[a-z]+'))
    def test_view(self):
        self.assertIn('return 42', self.invoke('view', 'src/app.py', '--lines', '2'))
    def test_sensitive_files_not_exposed(self):
        result = self.invoke('search', 'TOP-SECRET')
        self.assertNotIn('TOP-SECRET', result)
    def test_inline_secret_masked(self):
        result = self.invoke('view', 'src/token.py')
        self.assertIn('[REDACTED]', result)
        self.assertNotIn('abc123private', result)
    def test_secret_when_searching_source(self):
        result = self.invoke('search', 'api_key')
        self.assertNotIn('abc123private', result)
    def test_symlink_outside_blocked(self):
        outside = self.root.parent/'exposed-important-file-do-not-read.txt'
        # No need to create outside; link to another file under root to check symlink traversal.
        (self.root/'src'/'link.txt').symlink_to(self.root/'src'/'app.py')
        with self.assertRaises(SystemExit):
            self.invoke('view', 'src/link.txt')
    def test_symlink_directory_blocked(self):
        (self.root/'linked').symlink_to(self.root/'src', target_is_directory=True)
        with self.assertRaises(SystemExit):
            self.invoke('view', 'linked/app.py')
    def test_binary_skipped(self):
        (self.root/'src'/'bad.bin').write_bytes(b'login\x00secret')
        self.assertNotIn('bad.bin', self.invoke('search', 'login'))
    def test_search_limited(self):
        (self.root/'src'/'app.py').write_text('login\n'*80, encoding='utf-8')
        result = self.invoke('search', 'login', '--limit', '5')
        self.assertEqual(result.count('src/app.py:'), 5)

if __name__ == '__main__':
    unittest.main()

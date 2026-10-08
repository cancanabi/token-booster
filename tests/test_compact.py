import random
import string
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compact import compact, redact_text, important_count
from benchmark import evaluate

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'

class CompactTests(unittest.TestCase):
    def test_short_unchanged(self):
        self.assertEqual(compact('hello\r\nworld\r\n'), 'hello\r\nworld\r\n')
    def test_empty_unchanged(self):
        self.assertEqual(compact(''), '')
    def test_noisy_output(self):
        raw = '\n'.join(f'log {i}' for i in range(300))
        result = compact(raw, max_lines=35)
        self.assertIn('lines omitted', result)
        self.assertLess(len(result), len(raw))
    def test_important_error(self):
        raw = '\n'.join('ERROR crash!' if i == 140 else f'log {i}' for i in range(300))
        self.assertIn('ERROR crash!', compact(raw, max_lines=35))
    def test_warning_and_context(self):
        raw = '\n'.join('warning potential issue' if i == 150 else f'log {i}' for i in range(300))
        result = compact(raw, max_lines=35)
        self.assertIn('warning potential issue', result)
        self.assertIn('log 149', result)
    def test_long_lines_clipped(self):
        raw = 'Z'*1000+'\n'
        out = compact(raw, max_chars=70)
        self.assertIn('930 chars omitted', out)
        self.assertNotIn('Z'*71, out)
    def test_many_errors_report_omissions(self):
        raw = '\n'.join('ERROR line '+str(i) for i in range(200))
        out = compact(raw, max_lines=10)
        self.assertIn('190 diagnostic lines omitted', out)
    def test_redact_auth_bearer(self):
        raw = 'Authorization: Bearer secret-token-value-123456\n'
        out = compact(raw)
        self.assertIn('Authorization:', out)
        self.assertNotIn('secret-token-value-123456', out)
    def test_redact_basic(self):
        self.assertNotIn('abcde012345', redact_text('Authorization: Basic abcde012345'))
    def test_redact_header(self):
        self.assertNotIn('abc1234token', redact_text('x-api-key: abc1234token'))
    def test_redact_json(self):
        out = redact_text('{"token": "all_my_secret_value", "api_key": "private123"}')
        self.assertNotIn('all_my_secret_value', out)
        self.assertNotIn('private123', out)
    def test_redact_quote_with_spaces(self):
        self.assertNotIn('secret pass', redact_text("password='secret pass'"))
    def test_redact_url_credentials(self):
        self.assertNotIn('password123', redact_text('https://jane:password123@private.test/api'))
    def test_redact_github_pat(self):
        self.assertNotIn('github_pat_ABCDEFabcdef1234567890', redact_text('github_pat_ABCDEFabcdef1234567890'))
    def test_redact_private_key(self):
        raw = '-----BEGIN PRIVATE KEY-----\nMIIExampleDataShouldNotBePrinted\n-----END PRIVATE KEY-----'
        self.assertNotIn('MIIExampleDataShouldNotBePrinted', redact_text(raw))
    def test_no_plain_token_placeholder_false_positive(self):
        self.assertEqual(redact_text('token budget counts\n'), 'token budget counts\n')
    def test_bounded_params(self):
        for kwargs in ({'max_lines': 0}, {'max_chars': 1}, {'context': -1}):
            with self.assertRaises(ValueError):
                compact('foo', **kwargs)
    def test_binary_refused(self):
        with self.assertRaises(ValueError):
            compact('hi\x00world')
    def test_randomized_bounded_and_no_crash(self):
        rng = random.Random(20261008)
        chars = string.ascii_letters + string.digits + ' \n\r\t:;'
        for _ in range(250):
            s = ''.join(rng.choices(chars, k=rng.randint(0, 12000)))
            out = compact(s, max_lines=25, max_chars=120)
            self.assertLess(len(out), 50000)
            self.assertIsInstance(out, str)
    def test_benchmark_no_fake_tokens(self):
        result = evaluate([('sample', '\n'.join('log '+str(i) for i in range(400)))])
        self.assertIn('No model tokenizer', result['disclaimer'])
        row = result['cases'][0]
        self.assertGreater(row['byte_reduction_pct'], 0)
        self.assertNotIn('estimated_tokens', row['before'])
    def test_piped_cli_refuses_binary(self):
        cp = subprocess.run([sys.executable, str(SCRIPTS/'compact.py')], input=b'one\x00two', capture_output=True)
        self.assertEqual(cp.returncode, 2)
    def test_piped_cli_size_marker(self):
        cp = subprocess.run([sys.executable, str(SCRIPTS/'compact.py'), '--max-input-bytes', '12'], input=b'a'*100, capture_output=True)
        self.assertEqual(cp.returncode, 0)
        self.assertIn(b'input truncated', cp.stdout)
    def test_benchmark_secret_not_in_output(self):
        metrics = str(evaluate([('fixture', 'password=superSecret123\n'*15)]))
        self.assertNotIn('superSecret123', metrics)
    def test_unterminated_private_key_never_leaks(self):
        text = 'prefix\n-----BEGIN PRIVATE KEY-----\nULTRA_SECRET_KEY_MATERIAL\nremaining'
        after = redact_text(text)
        self.assertNotIn('ULTRA_SECRET_KEY_MATERIAL', after)
        self.assertNotIn('remaining', after)
    def test_multiple_separate_pem_blocks(self):
        text = ('-----BEGIN PRIVATE KEY-----\nFIRSTSECRET\n-----END PRIVATE KEY-----\n'
                'normal\n-----BEGIN PRIVATE KEY-----\nSECONDSECRET\n-----END PRIVATE KEY-----\n')
        after = redact_text(text)
        self.assertNotIn('FIRSTSECRET', after)
        self.assertNotIn('SECONDSECRET', after)
        self.assertIn('normal', after)
    def test_short_authorization_header_masked(self):
        self.assertNotIn('abc', redact_text('Authorization: Bearer abc'))
    def test_important_count(self):
        self.assertEqual(important_count('ok\nERROR crash\nWARNING caution'), 2)

if __name__ == '__main__':
    unittest.main()

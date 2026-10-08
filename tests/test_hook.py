import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from post_tool_use import rewrite, is_safe_test_command
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'post_tool_use.py'

def event(text, command='pytest -q', **overrides):
    result = {'stdout': text, 'stderr': '', 'isImage': False, 'interrupted': False, 'exitCode': 0}
    result.update(overrides)
    return {'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
            'tool_input': {'command': command}, 'tool_response': result}

BIG = '\n'.join('passed suite row '+str(i) for i in range(900))+'\n'

class HookTests(unittest.TestCase):
    def test_safe_test_command(self):
        self.assertTrue(is_safe_test_command('pytest -q'))
        self.assertTrue(is_safe_test_command('npm test -- --runInBand'))
        self.assertTrue(is_safe_test_command('python -m pytest -x'))
    def test_unsafe_commands(self):
        for cmd in ('cat app.py', 'pytest | cat', 'pytest && rm -rf /', 'pytest; echo hi',
                    'pytest $(cat .env)', 'pytest > results.txt', 'pytest\ncat .env', 'pytest `whoami`'):
            self.assertFalse(is_safe_test_command(cmd), cmd)
    def test_valid_large_success_is_compacted(self):
        result = rewrite(event(BIG))
        self.assertIsNotNone(result)
        updated = result['hookSpecificOutput']['updatedToolOutput']
        self.assertLess(len(updated['stdout']), len(BIG)*.7)
        self.assertIn('INCOMPLETE', updated['stdout'])
    def test_small_passthrough(self):
        self.assertIsNone(rewrite(event('passed\n')))
    def test_failures_pass_through(self):
        self.assertIsNone(rewrite(event(BIG, exitCode=1)))
        self.assertIsNone(rewrite(event(BIG, stderr='problem')))
        self.assertIsNone(rewrite(event(BIG, interrupted=True)))
        self.assertIsNone(rewrite(event(BIG, isImage=True)))
    def test_critical_diagnostics_pass_through(self):
        self.assertIsNone(rewrite(event(BIG+'ERROR: something failed\n')))
        self.assertIsNone(rewrite(event(BIG+'Warning output\n')))
    def test_structured_json_passthrough(self):
        self.assertIsNone(rewrite(event('{"events": [' + BIG + ']}')))
    def test_terminal_ansi_and_binary_passthrough(self):
        self.assertIsNone(rewrite(event(BIG+'\x1b[0m')))
        self.assertIsNone(rewrite(event(BIG+'\x00')))
    def test_nonbash_passthrough(self):
        e = event(BIG)
        e['tool_name'] = 'Read'
        self.assertIsNone(rewrite(e))
    def test_missing_fields_passthrough(self):
        e = event(BIG)
        del e['tool_response']['stderr']
        self.assertIsNone(rewrite(e))
    def test_keep_other_fields(self):
        result = rewrite(event(BIG, note='same'))
        self.assertEqual(result['hookSpecificOutput']['updatedToolOutput']['note'], 'same')
    def test_disabled_is_noop_no_stdout(self):
        env = os.environ.copy(); env.pop('TOKEN_BOOSTER_AUTO', None)
        run = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(event(BIG)), text=True, capture_output=True, env=env)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(run.stdout, '')
    def test_enabled_produces_valid_json(self):
        env = os.environ.copy(); env['TOKEN_BOOSTER_AUTO'] = '1'
        run = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(event(BIG)), text=True, capture_output=True, env=env)
        self.assertEqual(run.returncode, 0)
        self.assertIn('updatedToolOutput', json.loads(run.stdout)['hookSpecificOutput'])
    def test_auto_redacts_auth_header_when_rewriting(self):
        text = 'Authorization: Bearer do-not-leak-me\n' + BIG
        result = rewrite(event(text))
        self.assertIsNotNone(result)
        self.assertNotIn('do-not-leak-me', result['hookSpecificOutput']['updatedToolOutput']['stdout'])
    def test_powershell_tool_passthrough(self):
        e = event(BIG)
        e['tool_name'] = 'PowerShell'
        self.assertIsNone(rewrite(e))
    def test_bad_json_noop(self):
        env = os.environ.copy(); env['TOKEN_BOOSTER_AUTO'] = '1'
        run = subprocess.run([sys.executable, str(SCRIPT)], input='{wrong JSON', text=True, capture_output=True, env=env)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(run.stdout, '')
    def test_oversized_input_noop(self):
        env = os.environ.copy(); env['TOKEN_BOOSTER_AUTO'] = '1'
        run = subprocess.run([sys.executable, str(SCRIPT)], input=b'a'*5_000_100, capture_output=True, env=env)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(run.stdout, b'')

if __name__ == '__main__':
    unittest.main()

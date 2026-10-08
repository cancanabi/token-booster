import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
from token_booster.read_cache import observe, pre_read, reset, report


class ReadCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root/'repo';self.repo.mkdir()
        self.cache = self.root/'private-cache';self.cache.mkdir(mode=0o700)
        self.file = self.repo/'app.py'
        self.file.write_text('def login(user):\n    return user != None\n' * 90)
        self.env = patch.dict(os.environ, {
            'TOKEN_BOOSTER_READ_CACHE':'1',
            'TOKEN_BOOSTER_READ_BLOCK':'1',
            'TOKEN_BOOSTER_STATE_DIR':str(self.cache),
        })
        self.env.start();self.addCleanup(self.env.stop)

    def event(self, stage='PostToolUse', **custom):
        d={'session_id':'session-one','transcript_path':str(self.root/'session-one.jsonl'),
           'cwd':str(self.repo), 'hook_event_name':stage,'tool_name':'Read',
           'tool_input':{'file_path':str(self.file)},
           'tool_response':'  1  def login(user): ...'}
        d.update(custom)
        return d

    def warm(self):
        observe(self.event(), now=1000)

    def test_first_read_allowed(self):
        self.assertIsNone(pre_read(self.event('PreToolUse'),now=1000))

    def test_duplicate_read_single_use(self):
        self.warm()
        blocked=pre_read(self.event('PreToolUse'),now=1005)
        self.assertEqual(blocked['hookSpecificOutput']['permissionDecision'],'deny')
        self.assertIsNone(pre_read(self.event('PreToolUse'),now=1006))
        stats=report(self.event())['counters']
        self.assertEqual(stats['duplicate_reads_blocked'],1)
        self.assertEqual(stats['file_bytes_avoided_estimate'],self.file.stat().st_size)
        self.assertGreater(stats['file_bytes_avoided_estimate'],stats['injected_message_bytes'])

    def test_same_length_mutation_invalidates_hash(self):
        self.warm()
        original=self.file.read_text()
        self.file.write_text(original.replace('login','loGin'))
        self.assertEqual(self.file.stat().st_size,len(original.encode()))
        self.assertIsNone(pre_read(self.event('PreToolUse'),now=1005))

    def test_expired_read_allowed(self):
        self.warm()
        self.assertIsNone(pre_read(self.event('PreToolUse'),now=1100))
        self.assertIsNone(pre_read(self.event('PreToolUse'),now=999))

    def test_session_compaction_reset(self):
        self.warm()
        reset(self.event('SessionStart',source='compact'))
        self.assertIsNone(pre_read(self.event('PreToolUse'),now=1005))

    def test_clear_and_resume_reset(self):
        for source in ('clear','resume','startup'):
            self.warm()
            reset(self.event('SessionStart',source=source))
            self.assertIsNone(pre_read(self.event('PreToolUse'),now=1005))

    def test_other_transcript_not_shared(self):
        self.warm()
        self.assertIsNone(pre_read(self.event('PreToolUse',transcript_path='other.jsonl'),now=1005))

    def test_other_session_not_shared(self):
        self.warm()
        self.assertIsNone(pre_read(self.event('PreToolUse',session_id='other-session'),now=1005))

    def test_ranged_reads_are_never_blocked(self):
        self.warm()
        for data in ({'file_path':str(self.file),'offset':1},
                     {'file_path':str(self.file),'limit':20},
                     {'file_path':str(self.file),'offset':1,'limit':20}):
            self.assertIsNone(pre_read(self.event('PreToolUse',tool_input=data),now=1005))

    def test_unknown_input_fields_fail_open(self):
        self.warm()
        self.assertIsNone(pre_read(self.event('PreToolUse', tool_input={'file_path':str(self.file),'custom':True}),now=1005))

    def test_edit_stales(self):
        self.warm()
        self.file.write_text('changed function body\n' * 100)
        self.assertIsNone(pre_read(self.event('PreToolUse'),now=1005))

    def test_bad_path_outside_project(self):
        path=self.root/'outside.py';path.write_text('abc\n'*500)
        self.assertIsNone(pre_read(self.event('PreToolUse',tool_input={'file_path':str(path)}),now=1005))
        self.assertIsNone(pre_read(self.event('PreToolUse',tool_input={'file_path':'app.py'}),now=1005))

    def test_symlink_blocked(self):
        link=self.repo/'link.py';link.symlink_to(self.file)
        e=self.event('PostToolUse',tool_input={'file_path':str(link)})
        observe(e,now=1000)
        self.assertEqual(report(self.event())['cached_file_count'],0)

    def test_symlinked_parent_blocked(self):
        link=self.repo/'linked';link.symlink_to(self.repo,target_is_directory=True)
        observe(self.event(tool_input={'file_path':str(link/'app.py')}),now=1000)
        self.assertEqual(report(self.event())['cached_file_count'],0)

    def test_secret_names_blocked(self):
        for name in ('.env','credentials.json','api_secret.py','auth_passwords.txt','private_key.pem'):
            path=self.repo/name;path.write_text('supersecret\n'*180)
            observe(self.event(tool_input={'file_path':str(path)}),now=1000)
        self.assertEqual(report(self.event())['cached_file_count'],0)

    def test_small_and_oversize_files_ignored(self):
        self.file.write_text('hello\n')
        observe(self.event(),now=1000)
        self.file.write_bytes(b'a'*1_000_001)
        observe(self.event(),now=1000)
        self.assertEqual(report(self.event())['cached_file_count'],0)

    def test_bad_response_ignored(self):
        for response in ('', 'Error reading file xyz', {'isError':True},[],None):
            observe(self.event(tool_response=response),now=1000)
        self.assertEqual(report(self.event())['cached_file_count'],0)

    def test_sensitive_data_not_persisted(self):
        self.warm()
        pre_read(self.event('PreToolUse'),now=1005)
        combined=''.join(p.read_text(errors='ignore') for p in self.cache.glob('*.json'))
        self.assertNotIn(str(self.file),combined)
        self.assertNotIn('def login',combined)
        self.assertNotIn('session-one',combined)
        self.assertNotIn('session-one.jsonl',combined)

    def test_cache_disabled_is_noop(self):
        self.warm()
        with patch.dict(os.environ,{'TOKEN_BOOSTER_READ_BLOCK':'0'}):
            self.assertIsNone(pre_read(self.event('PreToolUse'),now=1005))
        with patch.dict(os.environ,{'TOKEN_BOOSTER_READ_CACHE':'0'}):
            self.assertIsNone(pre_read(self.event('PreToolUse'),now=1005))
            observe(self.event(),now=1005)

    def test_invalid_state_does_not_crash(self):
        self.warm()
        state=next(self.cache.glob('*.json'))
        state.write_text('{invalid!')
        self.assertIsNone(pre_read(self.event('PreToolUse'),now=1005))

    def test_cli_disabled_is_silent(self):
        script=ROOT/'scripts'/'read_cache_hook.py'
        env=os.environ.copy();env.pop('TOKEN_BOOSTER_READ_CACHE',None)
        proc=subprocess.run([sys.executable,str(script)],input=json.dumps(self.event('PreToolUse')),
                            text=True,capture_output=True,env=env)
        self.assertEqual(proc.returncode,0)
        self.assertEqual(proc.stdout,'')

    def test_cli_opt_in_json_and_no_output_on_post(self):
        script=ROOT/'scripts'/'read_cache_hook.py'
        env=os.environ.copy()
        post=subprocess.run([sys.executable,str(script)],input=json.dumps(self.event()),text=True,capture_output=True,env=env)
        self.assertEqual(post.returncode,0)
        self.assertEqual(post.stdout,'')
        pre=subprocess.run([sys.executable,str(script)],input=json.dumps(self.event('PreToolUse')),
                           text=True,capture_output=True,env=env)
        self.assertEqual(pre.returncode,0)
        self.assertEqual(json.loads(pre.stdout)['hookSpecificOutput']['permissionDecision'],'deny')

    def test_cli_bad_json_and_oversize(self):
        script=ROOT/'scripts'/'read_cache_hook.py'
        for data in ('{bad', 'x'*1_000_010):
            p=subprocess.run([sys.executable,str(script)],input=data,text=True,capture_output=True)
            self.assertEqual((p.returncode,p.stdout),(0,''))

    def test_no_state_if_no_session_context(self):
        e=self.event(session_id='')
        observe(e,now=1000)
        self.assertEqual(list(self.cache.glob('*.json')),[])

    def test_state_file_permissions_private(self):
        self.warm()
        if os.name=='posix':
            state=next(self.cache.glob('*.json'))
            self.assertEqual(state.stat().st_mode & 0o777,0o600)

    def test_group_readable_dir_disabled(self):
        if os.name!='posix':return
        self.cache.chmod(0o755)
        self.assertIsNone(pre_read(self.event('PreToolUse'),now=1005))
        self.assertEqual(list(self.cache.glob('*.json')),[])


if __name__ == '__main__':unittest.main()

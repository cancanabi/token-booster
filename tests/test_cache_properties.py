import os
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from token_booster.read_cache import observe,pre_read,reset

class CachePropertyTests(unittest.TestCase):
    def test_80_random_invalidate_and_allow(self):
        rng=random.Random(554488)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); repo=root/'repo';repo.mkdir(); state=root/'state';state.mkdir(mode=0o700)
            with patch.dict(os.environ,{'TOKEN_BOOSTER_STATE_DIR':str(state),'TOKEN_BOOSTER_READ_CACHE':'1','TOKEN_BOOSTER_READ_BLOCK':'1'}):
                for trial in range(80):
                    path=repo/f'file_{trial}.txt'
                    n=rng.randint(850, 2000)
                    path.write_text('a'*n)
                    event={'session_id':f'{trial}', 'transcript_path':str(root/f'{trial}.jsonl'), 'cwd':str(repo),
                           'hook_event_name':'PostToolUse','tool_name':'Read','tool_input':{'file_path':str(path)},
                           'tool_response':' 1  a'}
                    now=1000+trial
                    observe(event,now)
                    pre={**event,'hook_event_name':'PreToolUse'}
                    if trial%4==0:
                        path.write_text('b'*n) # same length, different bytes
                        self.assertIsNone(pre_read(pre,now+1))
                    elif trial%4==1:
                        pre['tool_input']={'file_path':str(path),'limit':100}
                        self.assertIsNone(pre_read(pre,now+1))
                    elif trial%4==2:
                        reset({**event,'hook_event_name':'SessionStart'})
                        self.assertIsNone(pre_read(pre,now+1))
                    else:
                        self.assertIsNotNone(pre_read(pre,now+1))
                        self.assertIsNone(pre_read(pre,now+2))

    def test_64_deterministic_wrong_input_ignored(self):
        rng=random.Random(21887)
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            state=repo/'state';state.mkdir(mode=0o700)
            with patch.dict(os.environ,{'TOKEN_BOOSTER_STATE_DIR':str(state),'TOKEN_BOOSTER_READ_CACHE':'1','TOKEN_BOOSTER_READ_BLOCK':'1'}):
                for trial in range(64):
                    e={'session_id':'z','transcript_path':'z.jsonl','cwd':str(repo),
                       'hook_event_name':'PreToolUse','tool_name':'Read',
                       'tool_input':{'file_path':rng.choice(['', '../escape', '/etc/passwd', 'foo'])}}
                    self.assertIsNone(pre_read(e,now=100))
if __name__=='__main__':unittest.main()

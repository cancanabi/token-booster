#!/usr/bin/env python3
"""Deterministic offline V5 benchmark. Strictly NOT real model-token usage."""
from __future__ import annotations
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from token_booster.read_cache import observe,pre_read,reset,report
from benchmark_v4 import run as legacy_bench


def run()->dict:
    cases=[]
    latencies=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); repo=root/'project';repo.mkdir(); private=root/'state';private.mkdir(mode=0o700)
        with patch.dict(os.environ,{'TOKEN_BOOSTER_READ_CACHE':'1','TOKEN_BOOSTER_READ_BLOCK':'1',
                                    'TOKEN_BOOSTER_STATE_DIR':str(private)}):
            for i in range(24):
                path=repo/f'source_{i}.py'
                path.write_text((f'def process_{i}(value):\n    return value + {i}\n')*220)
                session=f'deterministic-case-{i}'
                def ev(stage='PostToolUse',**changed):
                    event={'session_id':session,'cwd':str(repo),'transcript_path':str(root/f'{session}.jsonl'),
                           'hook_event_name':stage,'tool_name':'Read',
                           'tool_input':{'file_path':str(path)},'tool_response':'1\t def process(): ...'}
                    event.update(changed)
                    return event
                start=time.perf_counter_ns()
                observe(ev(),now=1000)
                first=pre_read(ev('PreToolUse'),now=1001)
                second=pre_read(ev('PreToolUse'),now=1002)
                end=time.perf_counter_ns()
                assert first and first['hookSpecificOutput']['permissionDecision']=='deny'
                assert second is None, 'repeat denial would risk a loop'
                self_stats=report(ev())['counters']
                cases.append({'case':i,'file_bytes':path.stat().st_size,
                              'single_duplicate_prevented':bool(first), 'subsequent_read_allowed':second is None,
                              'estimated_avoided_file_bytes':self_stats['file_bytes_avoided_estimate'],
                              'hook_injected_message_bytes':self_stats['injected_message_bytes']})
                latencies.append((end-start)/1e6)
                # Verify changed file, partial read, and compaction are all fail-open.
                original=path.read_text()
                path.write_text(original.replace('value','Value'))
                assert pre_read(ev('PreToolUse'),now=1003) is None, 'change was not detected'
                assert pre_read(ev('PreToolUse',tool_input={'file_path':str(path),'offset':1,'limit':100}),now=1003) is None
                reset(ev('SessionStart',source='compact'))
                assert pre_read(ev('PreToolUse'),now=1004) is None, 'compaction did not clear cache'
    saved=sum(x['estimated_avoided_file_bytes'] for x in cases)
    injected=sum(x['hook_injected_message_bytes'] for x in cases)
    legacy=legacy_bench()
    return {'offline_only':True,'real_model_or_claude_token_usage_measured':False,
            'read_cache':{'cases':len(cases),'duplicate_reads_prevented':sum(x['single_duplicate_prevented'] for x in cases),
                          'no_denial_loop_cases':sum(x['subsequent_read_allowed'] for x in cases),
                          'estimated_avoided_file_content_bytes':saved,
                          'injected_message_bytes':injected,
                          'naive_byte_balance_excluding_hook_cpu_and_model_overhead':saved-injected,
                          'mean_three_hook_operations_ms_in_process':round(statistics.mean(latencies),3),
                          'median_three_hook_operations_ms_in_process':round(statistics.median(latencies),3),
                          'reminder':'Hooks launch separate Python processes in real Claude Code; this CPU timing excludes interpreter start.'},
            'context_budget':legacy['knapsack'],'bash_outputs':legacy['hooks'],
            'limitations':'Synthetic events, deterministic local fixtures. Read bytes, Unicode chars, token count, cached prompt tokens and billing are different metrics. No external competitor was executed.'}

if __name__=='__main__':
    result=run()
    out=ROOT/'results'/'v5-benchmark.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if result['context_budget']['regressions'] or result['read_cache']['duplicate_reads_prevented']!=24:
        raise SystemExit(1)

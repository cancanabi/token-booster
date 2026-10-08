#!/usr/bin/env python3
"""Offline, deterministic synthetic benchmark, never a real Claude comparison."""
import json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from token_booster.context import Candidate,exact_budget_choice
from token_booster.compress import compress_for_hook
from post_tool_use import rewrite
from compact import compact


def greedies(items,budget):
    used=0;score=0
    for c in sorted(items,key=lambda c:(-c.utility/c.bytes,c.bytes,c.path)):
        if used+c.bytes<=budget:used+=c.bytes;score+=c.utility
    return score


def run():
    rng=random.Random(20261008)
    trials=400;ties=0;wins=0;violations=0
    improvements=[]
    for j in range(trials):
        size=rng.randint(7,17)
        cs=[Candidate(str(i),'',rng.randrange(20,800),rng.randrange(1,500),0) for i in range(size)]
        budget=rng.randint(100,2000)
        opt=sum(c.utility for c in exact_budget_choice(cs,budget))
        greedy=greedies(cs,budget)
        if opt<greedy:violations+=1
        if opt==greedy:ties+=1
        if opt>greedy:wins+=1;improvements.append((opt-greedy)/max(1,greedy))
    samples=[]
    for name,cmd,text in [
        ('verbose-success','pytest -q', (ROOT/'fixtures/verbose-success.log').read_text(encoding='utf8')+'TOTAL 1200 TESTS PASS\n'),
        ('verbose-failure','pytest -q', (ROOT/'fixtures/failing-tests.log').read_text(encoding='utf8')),
        ('short-success','pytest -q','4 passed in 0.05s')
    ]:
        event={'hook_event_name':'PostToolUse','tool_name':'Bash','tool_input':{'command':cmd},
               'tool_response':{'stdout':text,'stderr':'','isImage':False,'interrupted':False,'exitCode':0 if 'failure' not in name else 1}}
        result=rewrite(event)
        new=(result or {}).get('hookSpecificOutput',{}).get('updatedToolOutput',{}).get('stdout',text)
        samples.append({'name':name,'hook_rewrote':bool(result),'utf8_before':len(text.encode('utf8')),
                        'utf8_after':len(new.encode('utf8')),'text_size_reduction_percent':round(100*(1-len(new.encode('utf8'))/len(text.encode('utf8'))),2)})
    return {'offline_only':True,'not_real_tokens':True,
            'knapsack':{'trials':trials,'optimal_better_than_greedy':wins,'optimal_ties_greedy':ties,'regressions':violations,
                        'random_seed':20261008, 'utility':'synthetic integer relevance',
                        'constraint':'sum UTF-8 preview bytes <= budget',
                        'note':'Exact optimality for the finite candidate set and this score, not semantic quality or token billing.'},
            'hooks':samples,'disclaimer':'Synthetic data. No Claude account, no API calls, no external competitor.'}

if __name__=='__main__':
    result=run();dst=ROOT/'results'/'v4-benchmark.json';dst.parent.mkdir(exist_ok=True)
    dst.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2,ensure_ascii=False))
    if result['knapsack']['regressions']:raise SystemExit(1)

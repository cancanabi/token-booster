#!/usr/bin/env python3
"""Two controlled fresh print sessions, no autonomous broad tool approval."""
from __future__ import annotations
import json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROMPT=('Execute `npm test` exactly once in this directory using Bash. '
        'Tell me if all tests passed and how many passed. Do not edit files or run other commands.')
def run(label,optimized):
 env=os.environ.copy()
 if optimized:env['TOKEN_BOOSTER_AUTO']='1'
 else:env.pop('TOKEN_BOOSTER_AUTO',None)
 cmd=['claude','-p','--output-format','json','--no-session-persistence',
      '--max-turns','4','--model','sonnet','--allowedTools','Bash(npm test)']
 if optimized:cmd+=['--plugin-dir',str(ROOT)]
 cmd.append(PROMPT)
 start=time.monotonic()
 proc=subprocess.run(cmd,cwd=ROOT/'demo',env=env,text=True,capture_output=True,timeout=240)
 try:doc=json.loads(proc.stdout)
 except json.JSONDecodeError:
  raise ValueError(f'{label}: Invalid CLI JSON, returncode={proc.returncode}, stderr={proc.stderr[:250]!r}')
 usage=doc.get('usage') or {}
 fields=('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')
 counts={k:usage[k] for k in fields if isinstance(usage.get(k),int)}
 return {'variant':label,'returncode':proc.returncode,'seconds':round(time.monotonic()-start,2),
         'usage':counts,'naive_total_tokens':sum(counts.values()) if counts else None,
         'is_error':doc.get('is_error'), 'answer_excerpt':str(doc.get('result',''))[:300]}
def main():
 if not shutil.which('claude'):
  print('ERROR: Install CLI first via bash scripts/setup_codespace.sh',file=sys.stderr);return 2
 if os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('ANTHROPIC_AUTH_TOKEN'):
  print('ERROR: API credential set; use Claude Pro/Max login to avoid pay-as-you-go.',file=sys.stderr);return 2
 print('Starting TWO model requests. Uses existing Claude Pro/Max quota, not a free model.',flush=True)
 result=[]
 for label,mode in [('baseline',False),('token_booster',True)]:
  print('Testing',label,flush=True)
  try: result.append(run(label,mode))
  except (ValueError,subprocess.TimeoutExpired) as err:print('FAILED:',err,file=sys.stderr);return 1
 out=ROOT/'results'/'ab_summary.json';out.parent.mkdir(exist_ok=True)
 out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 for r in result:print(json.dumps(r,indent=2,ensure_ascii=False))
 print('Saved',out,'; compare quality first, token numbers second.')
 return 0 if all(r['returncode']==0 for r in result) else 1
if __name__=='__main__':raise SystemExit(main())

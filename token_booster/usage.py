"""Aggregate usage *reported* in opt-in, local Claude JSONL transcripts.

Never expose messages, prompts, file paths, model output, or API keys.
Individual message objects may be re-emitted as streaming chunks; the last
observation per (session, message id) is used instead of naive summation.
"""
from __future__ import annotations
import json
from pathlib import Path

FIELDS=('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')


def summarize(path:Path,max_bytes:int=60_000_000,max_lines:int=200_000)->dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size>max_bytes:
        raise ValueError('transcript missing, symlink or exceeds max bytes')
    final={};anonymous=[]; skipped=0; observed=0; linecount=0
    with path.open('r',encoding='utf-8',errors='replace') as f:
        for line in f:
            linecount+=1
            if linecount>max_lines:raise ValueError('transcript exceeds record limit')
            if len(line)>2_000_000:skipped+=1;continue
            try:
                ev=json.loads(line)
                if not isinstance(ev,dict):continue
                msg=ev.get('message',ev)
                if not isinstance(msg,dict):continue
                usage=msg.get('usage')
                if not isinstance(usage,dict):continue
                row={k:max(0,v) for k in FIELDS if isinstance((v:=usage.get(k)),int) and not isinstance(v,bool) and v>=0}
                if not row:continue
                observed+=1
                message_id=msg.get('id')
                if isinstance(message_id,str) and message_id:
                    final[message_id]=row
                else:
                    anonymous.append(row)
            except (ValueError,TypeError):skipped+=1
    results={k:sum(row.get(k,0) for row in list(final.values())+anonymous) for k in FIELDS}
    return {'observed_usage_entries':observed,'unique_identified_messages':len(final),
            'anonymous_usage_entries':len(anonymous),'unparsed_lines':skipped,
            'tokens_reported':results,'summed_reported_tokens':sum(results.values()),
            'notes':'These are transcript-reported usage counts, not local guesses. Identical message IDs are deduplicated using the last observation. Anonymous usage entries may duplicate; values are NOT billing, quota, or causal plugin savings. No content retained.'}


def compare(a:dict,b:dict)->dict:
    baseline=a['tokens_reported'];optimized=b['tokens_reported']
    rows={k:{'baseline':baseline[k],'optimized':optimized[k],
             'delta':optimized[k]-baseline[k],
             'change_pct':round((optimized[k]/baseline[k]-1)*100,2) if baseline[k] else None}
          for k in FIELDS}
    return {'usage_comparison':rows,
            'warning':'Valid A/B needs same task, same Claude model/version, independent clean sessions, equivalent code quality and multiple randomized runs. Observational token count changes alone cannot prove a plugin benefit.'}

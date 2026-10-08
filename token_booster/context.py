"""Safe, bounded source discovery, structural summaries and context budgeting.

The 'optimal' knapsack solves ONLY the explicitly defined finite weighted-utility
problem. It does NOT optimize unknown true model cost, semantic quality, or
proprietary token billing.
"""
from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re

from typing import Iterable

SKIP_DIRS = {'.git','.svn','.hg','.ssh','.aws','.gnupg','.kube','.terraform',
             'node_modules','.venv','venv','dist','build','.next','coverage',
             '__pycache__','.cache','target','.turbo','.idea','.tox','vendor'}
SENSITIVE = {'.env','.npmrc','.pypirc','id_rsa','id_ed25519','credentials.json',
             'secrets.json','secrets.yaml','secrets.yml','config.json.secret'}
BLOCK_EXT = {'.pem','.key','.p12','.pfx','.keystore','.jks','.sqlite','.db'}
ALLOWED_EXT = {'.py','.js','.jsx','.ts','.tsx','.go','.rs','.java','.c','.h','.cpp',
               '.hpp','.cs','.rb','.php','.swift','.kt','.md','.rst','.txt',
               '.json','.yml','.yaml','.toml','.sql','.sh','.css','.html','.vue','.svelte'}
MAX_SOURCE_BYTES=128_000
MAX_FILES=5000
WORD = re.compile(r'[a-zA-Z_][a-zA-Z_0-9]{1,63}')
# Names that commonly carry secrets, including low-level and backup artifacts.
SUSPECT_NAME = re.compile(r'(?i)((^|\.)env([._-]|$)|(^|[._-])(secret|private[-_]?key|credentials?|passwords?|id_rsa|id_ed25519)([._-]|$)|\.env\.)')
SYMBOLS = re.compile(r'^\s*(?:export\s+)?(?:async\s+)?(?:function\s+|class\s+|interface\s+|type\s+|def\s+|fn\s+|func\s+|struct\s+|enum\s+|public\s+(?:static\s+)?(?:class\s+)?|const\s+)([A-Za-z_$][\w$]*)',re.MULTILINE)
MD_HEADER = re.compile(r'^\s*#{1,6}\s+(.{1,120})$', re.MULTILINE)


def safe_file(root:Path, path:Path)->bool:
    """Do not read paths outside root or any symlink on the path."""
    try:
        root=root.resolve(strict=True)
        relative=path.relative_to(root)
        if not relative.parts or any(p in ('.','..') for p in relative.parts): return False
        if any(p in SKIP_DIRS for p in relative.parts[:-1]): return False
        if any(ord(c)<32 for c in str(relative)): return False
        if path.name.casefold() in SENSITIVE or path.suffix.casefold() in BLOCK_EXT: return False
        if SUSPECT_NAME.search(path.name): return False
        if path.suffix.casefold() not in ALLOWED_EXT: return False
        current=root
        for part in relative.parts:
            current=current/part
            if current.is_symlink(): return False
        if not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES: return False
        if not path.resolve(strict=True).is_relative_to(root): return False
        return True
    except (OSError, ValueError): return False


def collect(root:Path, limit:int=MAX_FILES)->list[Path]:
    root=root.resolve(strict=True)
    chosen=[]; inspected=0
    for base, dirs, files in os.walk(root,followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(base)/d).is_symlink())
        for name in sorted(files):
            inspected+=1
            if inspected > limit: return chosen
            path=Path(base)/name
            if safe_file(root,path):chosen.append(path)
    return chosen


def read_safe(root:Path,path:Path)->str|None:
    """Bounded read with an O_NOFOLLOW final-component check on POSIX.

    Metadata and read can still race for parent directories; don't use on
    adversarial concurrently mutable trees. No security guarantee for secrets
    accidentally stored under ordinary filenames.
    """
    if not safe_file(root,path): return None
    try:
        flags=os.O_RDONLY | getattr(os,'O_NOFOLLOW',0) | getattr(os,'O_NONBLOCK',0)
        fd=os.open(path,flags)
        try:
            import stat
            s=os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_size>MAX_SOURCE_BYTES:return None
            with os.fdopen(fd,'rb',closefd=False) as f: raw=f.read(MAX_SOURCE_BYTES+1)
        finally: os.close(fd)
        if len(raw)>MAX_SOURCE_BYTES or b'\x00' in raw:return None
        return raw.decode('utf-8','strict')
    except (OSError,UnicodeError): return None


def terms(s:str)->list[str]:
    return [w.casefold() for w in WORD.findall(s)][:64]


def outline(path:Path,text:str,max_lines:int=32)->str:
    """Structural preview; never show full source; fail closed on parse errors."""
    out=[]
    if path.suffix.casefold()=='.py':
        try:
            mod=ast.parse(text)
            for node in mod.body:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                    out.append(f'L{node.lineno}: {type(node).__name__} {node.name}')
                    if isinstance(node,ast.ClassDef):
                        for child in node.body:
                            if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
                                out.append(f'L{child.lineno}: method {node.name}.{child.name}')
        except (SyntaxError, ValueError, RecursionError, MemoryError): pass
    elif path.suffix.casefold()=='.md':
        out=[f'L{text.count(chr(10),0,m.start())+1}: {m.group(1).strip()[:100]}' for m in MD_HEADER.finditer(text)]
    elif path.suffix.casefold()=='.json':
        try:
            value=json.loads(text)
            if isinstance(value,dict):out=['JSON root keys: '+', '.join(sorted(str(k)[:32] for k in value.keys())[:25])]
            elif isinstance(value,list):out=[f'JSON array: {len(value)} entries']
        except (ValueError,TypeError,RecursionError,MemoryError):pass
    else:
        out=[f'L{text.count(chr(10),0,m.start())+1}: {m.group(1)[:70]}' for m in SYMBOLS.finditer(text)]
    if not out:out=[f'No supported top-level symbols; {len(text.splitlines())} lines']
    if len(out)>max_lines:out=out[:max_lines]+[f'... {len(out)-max_lines} additional symbols omitted']
    # Do not print raw lines containing credentials; this is a best-effort
    # safeguard, not proof of secret detection.
    # Never assume symbol names are secret-free: apply the same conservative
    # redaction as the legacy diagnostic tooling.
    return '\n'.join(out)+'\n'

@dataclass(frozen=True)
class Candidate:
    path:str
    preview:str
    bytes:int
    utility:int
    bm25:float


def candidates(root:Path,query:str,max_items:int=24)->list[Candidate]:
    """BM25 using term presence/frequency in a capped subset of safe files."""
    files=collect(root)
    docs=[]
    q=Counter(terms(query))
    total_source=0
    for path in files:
        if total_source >= 12_000_000:break
        data=read_safe(root,path)
        if data is None:continue
        relative=path.relative_to(root).as_posix()
        total_source+=len(data.encode('utf-8'))
        # Score at most 32K chars, but all 5K allowed words (not merely 64).
        freq=Counter(w.casefold() for w in WORD.findall(relative+' '+data[:32_000])[:5000])
        docs.append((relative,data,freq))
    if not docs:return []
    N=len(docs)
    df=Counter({term:sum(term in fr for _,_,fr in docs) for term in q})
    lengths=[sum(f.values()) for _,_,f in docs]
    avglen=max(1,sum(lengths)/N)
    rows=[]
    for (relative,data,freq),ln in zip(docs,lengths):
        score=0.0
        for word in q:
            tf=freq.get(word,0)
            if not tf:continue
            idf=math.log(1+(N-df[word]+0.5)/(df[word]+0.5))
            score+=idf*(tf*2.2)/(tf+1.2*(0.25+0.75*ln/avglen))
            if word in terms(relative):score+=0.8
        if score<=0:continue
        # Explicit coding requests get a modest code-file preference; tests
        # and docs remain searchable if their lexical relevance is higher.
        if any(w in q for w in ('code','coding','function','implement','fix','bug','method','class','programmieren')):
            if Path(relative).suffix in {'.py','.ts','.tsx','.js','.jsx','.go','.rs','.java','.cpp','.c','.cs','.rb','.php'}:
                score*=1.15
        preview=outline(Path(relative),data)
        # Weighed integer utility provides fully specified, deterministic objective.
        value=max(1,round(score*1000))
        cost=len((relative+'\n'+preview).encode('utf-8'))
        rows.append(Candidate(relative,preview,cost,value,round(score,4)))
    return sorted(rows,key=lambda r:(-r.utility,r.path))[:max_items]


def exact_budget_choice(items:list[Candidate],budget:int)->list[Candidate]:
    """Exact zero-one knapsack for the provided candidates and UTF-8 byte budget.

    Utility and byte costs are only proxies for usefulness and model tokens.
    Fixed tie breaks: higher utility, then lower byte cost, then fewer items.
    """
    if budget<0 or budget>100_000:raise ValueError('budget must be 0..100000 bytes')
    if len(items)>24:raise ValueError('max 24 candidates')
    # Sparse nondominated frontier; state maps used bytes -> (score, bitmask).
    states={0:(0,0)}
    for i,c in enumerate(items):
        if c.bytes<=0:raise ValueError('item cost must be positive')
        next_states=states.copy()
        for cost,(score,mask) in states.items():
            next_cost=cost+c.bytes
            if next_cost>budget:continue
            potential=(score+c.utility,mask|(1<<i))
            prior=next_states.get(next_cost)
            if prior is None or potential[0]>prior[0] or (potential[0]==prior[0] and potential[1]<prior[1]):
                next_states[next_cost]=potential
        # Pareto pruning: skip states whose utility is <= that of a cheaper state.
        best=-1; pruned={}
        for price, state in sorted(next_states.items()):
            if state[0]>best:
                pruned[price]=state;best=state[0]
        states=pruned
    used,(score,mask)=min(states.items(),key=lambda e:(-e[1][0],e[0],e[1][1]))
    return [item for i,item in enumerate(items) if mask&(1<<i)]


def plan(root:Path,query:str,budget:int=2500)->dict:
    if not 200<=budget<=60_000:raise ValueError('budget range 200..60000 bytes')
    pool=candidates(root,query)
    # Reserve a bounded 240 bytes for JSON summary overhead; payload capped at budget.
    chosen=exact_budget_choice(pool,max(0,budget-240))
    return {'query':query[:120], 'budget_preview_bytes':budget,
            'selected_previews':[
                {'file':c.path,'bm25':c.bm25,'utf8_bytes':c.bytes,'outline':c.preview}
                for c in chosen],
            'total_outline_bytes':sum(c.bytes for c in chosen),
            'objective_utility':sum(c.utility for c in chosen),
            'candidates_considered':len(pool),
            'disclaimer':'Optimal only for defined candidate set, integer BM25-derived utility and UTF-8 preview byte costs; NOT true tokens or guaranteed task quality.'}

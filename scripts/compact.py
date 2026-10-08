#!/usr/bin/env python3
"""Bounded offline compaction for *diagnostic text*, not source or structured data.

Text-size reductions are NOT token usage measurements. No original content stored.
"""
from __future__ import annotations
import argparse
import re
import sys

MAX_INPUT = 2_000_000
ERROR = re.compile(r'(?i)\b(?:error|failed|failure|exception|traceback|fatal|panic|assertionerror|warning|warn|not\s+ok|segmentation\s+fault)\b|[✗×❌]')
KNOWN = re.compile(r'(?<![\w])(?:sk-ant-[\w-]{12,}|sk-proj-[\w-]{12,}|gh[pousr]_[\w-]{12,}|github_pat_[\w-]{12,}|AKIA[0-9A-Z]{16})(?![\w])')
BEARER = re.compile(r'(?i)\b(Bearer|Basic)\s+([a-z0-9_./+~=-]{8,})')
LABEL = r'(?:api[_-]?key|x-api-key|secret|client[_-]?secret|access[_-]?token|refresh[_-]?token|auth[_-]?token|token|password|passwd|authorization|cookie|set-cookie)'
QUOTED = re.compile(r'(?i)(?P<prefix>\b'+LABEL+r'\b[\"\']?\s*[:=]\s*)(?P<q>["\'])(?P<value>[^\r\n]*?)(?P=q)')
PLAIN = re.compile(r'(?i)(?P<prefix>\b'+LABEL+r'\b[\"\']?\s*[:=]\s*)(?P<value>[^\s,"\'`;]+)')
AUTH = re.compile(r'(?i)(?P<prefix>\bAuthorization\s*:\s*(?:Bearer|Basic|Token)\s+)(?P<value>\S+)')
URL_CREDS = re.compile(r'(?i)(https?://)([^\s/@:]+):([^\s/@]+)@')
PRIVATE_KEY_BEGIN = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')
PRIVATE_KEY_END = re.compile(r'-----END [A-Z ]*PRIVATE KEY-----')
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def redact_pem(text: str) -> str:
    """Linear-time private key masking, even for unterminated PEM blocks."""
    output = []
    inside = False
    for original in text.splitlines(keepends=True):
        line = original
        while line:
            if inside:
                ending = PRIVATE_KEY_END.search(line)
                if ending is None:
                    break
                inside = False
                line = line[ending.end():]
            else:
                begin = PRIVATE_KEY_BEGIN.search(line)
                if begin is None:
                    output.append(line)
                    break
                output.append(line[:begin.start()] + '[REDACTED PRIVATE KEY]')
                line = line[begin.end():]
                inside = True
    return ''.join(output)


def redact_text(text: str) -> str:
    """Best-effort common credentials masking; never a guarantee of full detection."""
    text = redact_pem(text)
    text = URL_CREDS.sub(lambda m: m.group(1)+'[REDACTED]@', text)
    text = KNOWN.sub('[REDACTED]', text)
    text = AUTH.sub(lambda m: m.group('prefix')+'[REDACTED]', text)
    text = BEARER.sub(lambda m: m.group(1)+' [REDACTED]', text)
    text = QUOTED.sub(lambda m: m.group('prefix')+m.group('q')+'[REDACTED]'+m.group('q'), text)
    text = PLAIN.sub(lambda m: m.group('prefix')+'[REDACTED]', text)
    return text


def important_count(text: str) -> int:
    return sum(bool(ERROR.search(line)) for line in text.splitlines())


def compact(data: str, max_lines: int = 80, max_chars: int = 220, context: int = 2) -> str:
    """Prefer diagnostic lines and neighborhoods; disclose everything omitted."""
    if not 10 <= max_lines <= 1000 or not 40 <= max_chars <= 2000 or not 0 <= context <= 5:
        raise ValueError('limits out of bounds')
    if '\x00' in data:
        raise ValueError('binary input; refusing to compact')
    sanitized = redact_text(data)
    lines = sanitized.splitlines()
    if not lines:
        return sanitized
    if len(lines) <= max_lines and all(len(line) <= max_chars for line in lines):
        return sanitized
    n = len(lines)
    important = [i for i, l in enumerate(lines) if ERROR.search(l)]
    def choices():
        # Important lines first; error context, first and last lines, remaining rows.
        yield from important
        for i in important:
            for d in range(1, context + 1):
                yield i-d
                yield i+d
        yield from range(min(8, n))
        yield from range(max(0, n-8), n)
        yield from range(n)
    selected = set()
    for i in choices():
        if 0 <= i < n:
            selected.add(i)
        if len(selected) >= min(n, max_lines):
            break
    result = []
    prev = -1
    chars_removed = 0
    for i in sorted(selected):
        if i > prev+1:
            result.append(f'... [token-booster: {i-prev-1} lines omitted] ...')
        line = lines[i]
        if len(line) > max_chars:
            chars_removed += len(line)-max_chars
            line = line[:max_chars]+f' ... [token-booster: {len(line)-max_chars} chars omitted]'
        result.append(line)
        prev = i
    if prev < n-1:
        result.append(f'... [token-booster: {n-prev-1} lines omitted] ...')
    important_lost = sum(i not in selected for i in important)
    result.append(f'[token-booster: shown {len(selected)}/{n} lines; '
                  f'{chars_removed} chars clipped; '
                  f'{important_lost} diagnostic lines omitted; INCOMPLETE — inspect raw output when needed]')
    return '\n'.join(result)+'\n'


def main(argv=None):
    p = argparse.ArgumentParser(description='Offline, bounded log compaction (not token billing)')
    p.add_argument('--max-lines', type=int, default=80)
    p.add_argument('--max-chars', type=int, default=220)
    p.add_argument('--max-input-bytes', type=int, default=MAX_INPUT)
    args = p.parse_args(argv)
    if not 10 <= args.max_lines <= 1000 or not 40 <= args.max_chars <= 2000 or not 1 <= args.max_input_bytes <= 10_000_000:
        p.error('limits out of bounds')
    raw = sys.stdin.buffer.read(args.max_input_bytes+1)
    truncated = len(raw) > args.max_input_bytes
    try:
        output = compact(raw[:args.max_input_bytes].decode('utf-8', errors='replace'), args.max_lines, args.max_chars)
    except ValueError as exc:
        print(f'token-booster: {exc}', file=sys.stderr)
        return 2
    sys.stdout.write(output)
    if truncated:
        sys.stdout.write('[token-booster: input truncated at byte limit; original may contain missing errors]\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())

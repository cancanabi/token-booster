#!/usr/bin/env python3
"""Reproducible offline UTF-8/character comparison. No actual token billing."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from compact import compact, redact_text, ERROR


def measure(text):
    return {'characters': len(text), 'utf8_bytes': len(text.encode('utf-8'))}


def evaluate(samples, max_lines=80, max_chars=220):
    rows = []
    for name, original in samples:
        after = compact(original, max_lines=max_lines, max_chars=max_chars)
        before_size, after_size = measure(original), measure(after)
        baseline = redact_text(original)
        important = [l for l in baseline.splitlines() if ERROR.search(l)]
        preserve = sum(line in after for line in important)
        reduction = round((1-after_size['utf8_bytes']/before_size['utf8_bytes'])*100, 2) if before_size['utf8_bytes'] else 0
        rows.append({'case': name, 'before': before_size, 'after': after_size,
                     'byte_reduction_pct': reduction, 'diagnostic_lines_preserved': preserve,
                     'diagnostic_lines_total': len(important)})
    return {'disclaimer': 'Measured offline text footprint only. No model tokenizer, Claude token counts, billing, or competitor results.',
            'cases': rows}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('files', nargs='+', help='Local UTF-8 text log fixtures')
    p.add_argument('--max-lines', type=int, default=80)
    p.add_argument('--max-chars', type=int, default=220)
    args = p.parse_args(argv)
    if not 10 <= args.max_lines <= 1000 or not 40 <= args.max_chars <= 2000:
        p.error('invalid compact limits')
    samples = []
    for name in args.files:
        path = Path(name)
        if not path.is_file() or path.stat().st_size > 2_000_000:
            p.error(f'missing or oversized fixture: {name}')
        samples.append((path.name, path.read_text(encoding='utf-8', errors='replace')))
    print(json.dumps(evaluate(samples, args.max_lines, args.max_chars), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()

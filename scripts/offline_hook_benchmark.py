#!/usr/bin/env python3
"""Offline hook contract verification and output-size benchmark. No Claude/API usage.

Measures UTF-8 bytes, never bills or LLM tokens. Cases are synthetic or fixtures.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from post_tool_use import rewrite


def make_event(text: str, cmd: str = 'npm test', **changes) -> dict:
    response = {'stdout': text, 'stderr': '', 'isImage': False,
                'interrupted': False, 'exitCode': 0}
    response.update(changes)
    return {'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
            'tool_input': {'command': cmd}, 'tool_response': response}


def evaluate() -> dict:
    fixture = (ROOT / 'fixtures' / 'verbose-success.log').read_text(encoding='utf-8') + 'TOTAL 1200 TESTS PASS\n'
    assert len(fixture) > 5_000
    cases = [
        ('successful_test', make_event(fixture), True),
        ('successful_test_with_secret', make_event('Authorization: Bearer SecretLongTokenValue123456\n' + fixture), True),
        ('failing_test', make_event(fixture, exitCode=1), False),
        ('stderr_present', make_event(fixture, stderr='diagnostic data'), False),
        ('warning_present', make_event(fixture + '\nWARNING: unstable result'), False),
        ('short_output', make_event('2 passed in 0.03s'), False),
        ('structured_json', make_event('{"data":"' + ('abc'*2500) + '"}'), False),
        ('unsafe_command', make_event(fixture, cmd='cat /etc/passwd'), False),
        ('shell_pipeline', make_event(fixture, cmd='npm test | tail -5'), False),
        ('interrupted', make_event(fixture, interrupted=True), False),
        ('ansi_output', make_event(fixture + '\x1b[0m'), False),
    ]
    rows = []
    good = True
    for name, event, expected_rewrite in cases:
        original = event['tool_response']['stdout']
        decision = rewrite(event)
        rewritten = decision is not None
        result = decision['hookSpecificOutput']['updatedToolOutput']['stdout'] if rewritten else original
        original_bytes = len(original.encode('utf-8'))
        new_bytes = len(result.encode('utf-8'))
        case_ok = (rewritten == expected_rewrite)
        if rewritten:
            case_ok &= ('INCOMPLETE' in result and new_bytes < original_bytes)
            case_ok &= (result.count('TOTAL 1200 TESTS PASS') == 1)
        if name == 'successful_test_with_secret':
            case_ok &= ('SecretLongTokenValue123456' not in result)
        if not rewritten:
            case_ok &= (result == original)
        rows.append({'case': name, 'pass': bool(case_ok), 'rewritten': rewritten,
                     'original_utf8_bytes': original_bytes, 'output_utf8_bytes': new_bytes,
                     'reduction_percent': round((1 - new_bytes / original_bytes)*100, 2) if original_bytes else 0})
        good &= bool(case_ok)
    return {'pass': good, 'test_cases': len(rows),
            'description': 'Mocked PostToolUse contract; not the Claude Code application itself.',
            'metric': 'UTF-8 text bytes, NOT Claude token usage or cost savings', 'cases': rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results/offline-report.json')
    args = parser.parse_args()
    report = evaluate()
    dest = Path(args.output)
    if not dest.is_absolute():
        dest = ROOT / dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Offline hook contract:', 'PASS' if report['pass'] else 'FAIL')
    for case in report['cases']:
        print(f"  {case['case']:<29} {'PASS' if case['pass'] else 'FAIL'}  {case['reduction_percent']:6.2f}% text reduction")
    print('Report:', dest)
    print('No Claude tokens used. Results are not real Claude Code integration measurements.')
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Opt-in PostToolUse hook. Silent pass-through when any guard is uncertain.

Only trims successful large plain-text output of isolated allowlisted test commands.
Never writes data to disk; never alters tool execution or permissions.
"""
from __future__ import annotations
import json
import os
import re
import shlex
import sys
from compact import compact, ERROR
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from token_booster.compress import compress_for_hook

LIMIT = 5_000_000
ALLOWED = {('pytest',), ('python', '-m', 'pytest'), ('python3', '-m', 'pytest'),
           ('npm', 'test'), ('npm', 'run', 'test'), ('pnpm', 'test'),
           ('yarn', 'test'), ('cargo', 'test'), ('go', 'test')}
# Reject shell metacharacters/embedded control operators, even if tokens split okay.
UNSAFE = re.compile(r'[;&|`$<>\\\n\r]')


def is_safe_test_command(command: str) -> bool:
    if not isinstance(command, str) or len(command) > 300 or UNSAFE.search(command):
        return False
    try:
        args = shlex.split(command)
    except ValueError:
        return False
    return any(tuple(args[:len(prefix)]) == prefix for prefix in ALLOWED)


def rewrite(event: dict) -> dict | None:
    if not isinstance(event, dict) or event.get('hook_event_name') != 'PostToolUse' or event.get('tool_name') != 'Bash':
        return None
    inp, response = event.get('tool_input'), event.get('tool_response')
    if not isinstance(inp, dict) or not isinstance(response, dict):
        return None
    if not is_safe_test_command(inp.get('command')):
        return None
    if response.get('isImage') is not False or response.get('interrupted') is not False:
        return None
    stdout, stderr = response.get('stdout'), response.get('stderr')
    if not isinstance(stdout, str) or not isinstance(stderr, str) or stderr.strip():
        return None
    if response.get('exitCode', response.get('exit_code', 0)) not in (0, None):
        return None
    if len(stdout) < 5_000 or '\x00' in stdout or '\x1b' in stdout or '\ufffd' in stdout:
        return None
    if any(ord(c) < 32 and c not in '\n\r\t' for c in stdout):
        return None
    # Preserve errors, warnings and all test diagnostics (even if exit code 0).
    if ERROR.search(stdout):
        return None
    if stdout.lstrip().startswith(('{', '[')):
        return None  # JSON or other structured output
    short = compress_for_hook(stdout, lambda data: compact(data, max_lines=65, max_chars=220, context=0))
    if short is None:
        return None  # summary invariant or savings threshold not met
    updated = dict(response)
    updated['stdout'] = short
    return {'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'updatedToolOutput': updated}}


def main():
    # Do not do any work unless explicitly enabled for the current Claude CLI process.
    if os.environ.get('TOKEN_BOOSTER_AUTO') != '1':
        return 0
    try:
        blob = sys.stdin.buffer.read(LIMIT+1)
        if len(blob) > LIMIT:
            return 0
        decision = rewrite(json.loads(blob))
        if decision:
            print(json.dumps(decision, ensure_ascii=False))
    except (ValueError, TypeError, UnicodeError, OSError):
        return 0  # original result is retained; never block tools on a hook error
    return 0


if __name__ == '__main__':
    sys.exit(main())

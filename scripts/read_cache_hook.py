#!/usr/bin/env python3
"""Claude Code Read-cache hook dispatcher. Silent except for strict single-use denial."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from token_booster.read_cache import enabled, observe, pre_read, reset


def handle(event: dict) -> dict | None:
    if not isinstance(event, dict) or not enabled():
        return None
    action = event.get('hook_event_name')
    if action == 'PreToolUse':
        return pre_read(event)
    if action == 'PostToolUse':
        observe(event)
    if action == 'SessionStart':
        reset(event)
    return None


def main() -> int:
    if not enabled():
        return 0
    try:
        raw = sys.stdin.buffer.read(1_000_001)
        if len(raw) > 1_000_000:
            return 0
        result = handle(json.loads(raw))
        if result:
            print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
    except (OSError, ValueError, UnicodeError, TypeError, KeyError, RuntimeError):
        pass  # fail open
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

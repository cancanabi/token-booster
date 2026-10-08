"""Conservative session-scoped Read deduplication.

Defaults: disabled. If enabled, silent metadata-only observation. If additionally
strictly opted in, deny AT MOST ONCE per unchanged full-file read (same session,
transcript and cwd, <90s). No source contents or cleartext paths are persisted.

This is NOT a substitute for Claude's context window or tokenizer; it is a
narrow repeated-tool-call guard. Errors always fail open.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import tempfile
import time
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # no sound cross-process lock on Windows; disable rather than race
    fcntl = None

STATE_LIMIT = 300_000
MAX_FILE = 1_000_000
MAX_RECORDS = 128
TTL = 90.0
MIN_FILE_TO_BLOCK = 768
SAFE_FIELDS = frozenset({'file_path', 'offset', 'limit'})
EXCLUDE_NAMES = {'.env', '.npmrc', '.pypirc', 'credentials.json', 'secrets.json',
                 'secrets.yaml', 'secrets.yml', 'id_rsa', 'id_ed25519', '.git-credentials'}
EXCLUDE_PARTS = {'.git', 'node_modules', '.venv', '.ssh', '.aws', 'dist', 'build',
                 '.cache', '__pycache__'}


def enabled() -> bool:
    return os.environ.get('TOKEN_BOOSTER_READ_CACHE') == '1'


def blocking_enabled() -> bool:
    return enabled() and os.environ.get('TOKEN_BOOSTER_READ_BLOCK') == '1'


def _session_key(event: dict) -> str | None:
    session = event.get('session_id')
    transcript = event.get('transcript_path')
    cwd = event.get('cwd')
    if not (isinstance(session, str) and 1 <= len(session) <= 256 and
            isinstance(transcript, str) and 1 <= len(transcript) <= 4096 and
            isinstance(cwd, str) and 1 <= len(cwd) <= 4096):
        return None
    try:
        cwd_resolved = str(Path(cwd).resolve(strict=True))
    except (ValueError, OSError):
        return None
    return sha256(json.dumps([session, transcript, cwd_resolved], separators=(',', ':')).encode()).hexdigest()


def _state_dir() -> Path | None:
    raw = os.environ.get('TOKEN_BOOSTER_STATE_DIR') or os.environ.get('CLAUDE_PLUGIN_DATA')
    if not raw:
        raw = str(Path.home() / '.local' / 'state' / 'token-booster')
    try:
        root = Path(raw).expanduser()
        if root.is_symlink():
            return None
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not root.is_dir() or root.is_symlink():
            return None
        # Avoid writing confidential metadata to group/world-readable folders.
        if os.name != 'nt' and (root.stat().st_mode & 0o077):
            return None
        return root
    except (OSError, ValueError):
        return None


@contextmanager
def _locked_session(event: dict) -> Iterator[tuple[dict, Path] | None]:
    """Process-locked metadata state; fail open if inaccessible or corrupted."""
    key = _session_key(event)
    root = _state_dir() if fcntl is not None and key else None
    if root is None:
        yield None
        return
    lock_path = root / (key + '.lock')
    state_path = root / (key + '.json')
    try:
        flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(lock_path, flags, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError:
        yield None
        return
    try:
        state: dict = {'records': {}, 'blocked': {}, 'stats': {}}
        try:
            flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
            state_fd = os.open(state_path, flags)
            try:
                with os.fdopen(state_fd, 'rb', closefd=False) as f:
                    data = f.read(STATE_LIMIT + 1)
            finally:
                os.close(state_fd)
            if len(data) <= STATE_LIMIT:
                saved = json.loads(data)
                if isinstance(saved, dict) and all(isinstance(saved.get(k), dict) for k in ('records', 'blocked', 'stats')):
                    state = saved
        except (FileNotFoundError, UnicodeError, json.JSONDecodeError, OSError, ValueError):
            pass
        yield state, state_path
        if len(state['records']) > MAX_RECORDS:
            newest = sorted(state['records'].items(), key=lambda p: p[1].get('time', 0) if isinstance(p[1], dict) else 0, reverse=True)
            state['records'] = dict(newest[:MAX_RECORDS])
        if len(state['blocked']) > MAX_RECORDS:
            state['blocked'] = dict(list(state['blocked'].items())[-MAX_RECORDS:])
        raw = json.dumps(state, separators=(',', ':'), sort_keys=True).encode()
        if len(raw) <= STATE_LIMIT:
            tmp_fd, temp = tempfile.mkstemp(prefix='.tb-', dir=root)
            try:
                os.fchmod(tmp_fd, 0o600)
                with os.fdopen(tmp_fd, 'wb') as f:
                    f.write(raw)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp, state_path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _fingerprint(event: dict) -> tuple[str, str, int] | None:
    """Return hashed absolute path, stable content fingerprint and file byte count.

    Only full in-project reads are considered. Reject symlinks (including parent
    symlinks), secrets by filename, nonregular files and oversized files.
    """
    data = event.get('tool_input')
    if not isinstance(data, dict) or not SAFE_FIELDS.issuperset(data):
        return None
    if data.get('offset') is not None or data.get('limit') is not None:
        return None  # partial/ranged reads are deliberately never denied
    name = data.get('file_path')
    cwd = event.get('cwd')
    if not isinstance(name, str) or not isinstance(cwd, str) or len(name) > 4096:
        return None
    try:
        root = Path(cwd).resolve(strict=True)
        path = Path(name)
        if not path.is_absolute():
            return None
        rel = path.relative_to(root)
        if not rel.parts or any(part in EXCLUDE_PARTS or part.startswith('.env') for part in rel.parts):
            return None
        if (path.name.casefold() in EXCLUDE_NAMES or
                any(term in path.name.casefold() for term in ('credential', 'secret', 'password', 'private_key')) or
                path.suffix.casefold() in {'.key', '.pem', '.p12', '.pfx'}):
            return None
        curr = root
        for part in rel.parts:
            curr = curr / part
            if curr.is_symlink():
                return None
        if not path.resolve(strict=True).is_relative_to(root):
            return None
        s0 = path.stat()
        if not stat.S_ISREG(s0.st_mode) or not MIN_FILE_TO_BLOCK <= s0.st_size <= MAX_FILE:
            return None
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        fd = os.open(path, flags)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size != s0.st_size:
                return None
            h = sha256()
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                h.update(chunk)
            after = os.fstat(fd)
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                return None
        finally:
            os.close(fd)
        key = sha256(str(path).encode()).hexdigest()
        fingerprint = sha256(f'{after.st_size}|{after.st_mtime_ns}|{after.st_ino}|{h.hexdigest()}'.encode()).hexdigest()
        return key, fingerprint, after.st_size
    except (OSError, ValueError, PermissionError):
        return None


def _response_ok(event: dict) -> bool:
    if event.get('hook_event_name') != 'PostToolUse' or event.get('tool_name') != 'Read':
        return False
    response = event.get('tool_response')
    if isinstance(response, str):
        return len(response) > 0 and not response.startswith(('Error:', 'Error reading', 'File not found'))
    if isinstance(response, list):
        return bool(response) and all(isinstance(x, dict) and x.get('type') == 'text' and
                                      isinstance(x.get('text'), str) for x in response)
    if isinstance(response, dict):
        if response.get('isError') is True or response.get('error'):
            return False
        return bool(response.get('content') or response.get('text') or response.get('file'))
    return False


def _inc(stats: dict, name: str, val: int = 1) -> None:
    current = stats.get(name, 0)
    stats[name] = max(0, current + val) if type(current) is int else val


def observe(event: dict, now: float | None = None) -> None:
    """Register a successful read; no tool-output modification or injected text."""
    if not enabled() or not _response_ok(event):
        return
    fp = _fingerprint(event)
    if fp is None:
        return
    now = time.time() if now is None else now
    with _locked_session(event) as handle:
        if handle is None:
            return
        state, _ = handle
        key, digest, size = fp
        state['records'][key] = {'digest': digest, 'size': size, 'time': now}
        _inc(state['stats'], 'reads_observed')


def pre_read(event: dict, now: float | None = None) -> dict | None:
    """Opt-in, single-use blocker, never auto-approves or alters permissions."""
    if not blocking_enabled() or event.get('hook_event_name') != 'PreToolUse' or event.get('tool_name') != 'Read':
        return None
    fp = _fingerprint(event)
    if fp is None:
        return None
    now = time.time() if now is None else now
    with _locked_session(event) as handle:
        if handle is None:
            return None
        state, _ = handle
        key, digest, size = fp
        previous = state['records'].get(key)
        if not isinstance(previous, dict) or previous.get('digest') != digest:
            return None
        t = previous.get('time')
        if type(t) not in (int, float) or not 0 <= now - t <= TTL:
            return None
        block_key = sha256(f'{key}{digest}'.encode()).hexdigest()
        if state['blocked'].get(block_key):
            return None  # prevent denial loops; next read always allowed
        reason = ('Token Booster: identical, unchanged full-file read was already delivered in this session. '
                  'Use Read with offset/limit to inspect another section, or retry once to allow the full read.')
        state['blocked'][block_key] = True
        _inc(state['stats'], 'duplicate_reads_blocked')
        _inc(state['stats'], 'file_bytes_avoided_estimate', size)
        _inc(state['stats'], 'injected_message_bytes', len(reason.encode('utf-8')))
        return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                                       'permissionDecision': 'deny',
                                       'permissionDecisionReason': reason}}


def reset(event: dict) -> None:
    """Clear records upon new/resumed/compacted/cleared session."""
    if not enabled() or event.get('hook_event_name') != 'SessionStart':
        return
    with _locked_session(event) as handle:
        if handle is None:
            return
        state, _ = handle
        state['records'].clear()
        state['blocked'].clear()
        _inc(state['stats'], 'session_resets')


def report(event: dict) -> dict:
    """Local counters only; not token counts or monetary savings."""
    with _locked_session(event) as handle:
        if handle is None:
            return {'error': 'state unavailable; no session data'}
        state, _ = handle
        stats = dict(state.get('stats', {}))
        return {'counters': stats, 'cached_file_count': len(state['records']),
                'note': 'File bytes avoided are estimates, NOT actual Claude tokens. Hook execution costs are separate.'}

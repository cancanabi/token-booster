#!/usr/bin/env python3
"""Offline bounded literal project discovery. Not a secrets scanner."""
from __future__ import annotations
import argparse
import os
import re
from pathlib import Path
from compact import redact_text

SKIP_DIRS = {'.git', '.svn', '.hg', '.ssh', '.aws', '.gnupg', '.kube', '.terraform',
             'node_modules', '.venv', 'venv', 'dist', 'build', '.next', 'coverage',
             '__pycache__', '.cache', 'target', '.turbo', '.idea'}
SENSITIVE = {'.env', '.env.local', '.env.production', '.npmrc', '.pypirc', 'id_rsa',
             'id_ed25519', 'credentials.json', 'secrets.json', 'secrets.yaml', 'secrets.yml'}
BLOCK_EXT = {'.pem', '.key', '.p12', '.pfx', '.keystore', '.jks'}
MAX_FILES = 20000
MAX_BYTES = 256 * 1024
CONTROL = re.compile(r'[\x00-\x1f\x7f\x1b]')


def safe_print(text: str) -> str:
    return CONTROL.sub(' ', text)


def allowed_file(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
        if rel.is_absolute() or '..' in rel.parts or not rel.parts:
            return False
        if any(p in SKIP_DIRS for p in rel.parts[:-1]):
            return False
        if path.name in SENSITIVE or path.name.startswith('.env.') or path.suffix.casefold() in BLOCK_EXT:
            return False
        cur = root
        for part in rel.parts:
            cur = cur / part
            if cur.is_symlink():
                return False
        if not path.resolve().is_relative_to(root.resolve()):
            return False
        return path.is_file()
    except (OSError, ValueError):
        return False


def files(root: Path):
    count = 0
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(base)/d).is_symlink())
        for name in sorted(names):
            if count >= MAX_FILES:
                return
            path = Path(base)/name
            count += 1
            if allowed_file(path, root):
                yield path


def contents(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        raw = path.read_bytes()
        if b'\x00' in raw[:2048]:
            return None
        return redact_text(raw.decode('utf-8', errors='replace'))
    except (OSError, UnicodeError):
        return None


def run(argv=None):
    parser = argparse.ArgumentParser(description='Bounded literal search; no regex or network')
    parser.add_argument('--root', default='.')
    sub = parser.add_subparsers(dest='mode', required=True)
    find = sub.add_parser('find'); find.add_argument('term'); find.add_argument('--limit', type=int, default=30)
    search = sub.add_parser('search'); search.add_argument('term'); search.add_argument('--limit', type=int, default=30)
    view = sub.add_parser('view'); view.add_argument('path'); view.add_argument('--start', type=int, default=1); view.add_argument('--lines', type=int, default=80)
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error('project root not found')
    if args.mode == 'view':
        path = root / args.path
        if not allowed_file(path, root):
            parser.error('file blocked, symlink, or outside project')
        data = contents(path)
        if data is None:
            parser.error('binary, too large, or unreadable file')
        start, length = max(1, args.start), max(1, min(args.lines, 150))
        for i, line in enumerate(data.splitlines(), 1):
            if start <= i < start + length:
                print(f'{i:>5}: {safe_print(line)[:350]}')
        return
    if not args.term or len(args.term) > 200:
        parser.error('search term must be 1–200 chars')
    limit = max(1, min(args.limit, 100))
    hits = 0
    for path in files(root):
        relative = path.relative_to(root).as_posix()
        if args.mode == 'find':
            if args.term.casefold() in relative.casefold():
                print(safe_print(relative)); hits += 1
        else:
            data = contents(path)
            if data is None:
                continue
            for i, line in enumerate(data.splitlines(), 1):
                if args.term.casefold() in line.casefold():
                    print(f'{safe_print(relative)}:{i}: {safe_print(line)[:250]}'); hits += 1
                    if hits >= limit:
                        break
        if hits >= limit:
            break
    print(f'-- {hits} results (limit {limit}); literal search, secret masking is best-effort --')


if __name__ == '__main__':
    run()

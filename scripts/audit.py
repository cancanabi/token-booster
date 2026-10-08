#!/usr/bin/env python3
"""Metadatenbasiertes Projekt-Audit ohne Upload und ohne Datei-Inhalte."""
import os
import sys
from pathlib import Path

SKIP = {'.git', 'node_modules', '.venv', 'venv', 'dist', 'build', '.next', 'coverage', '__pycache__', '.cache', 'target'}
MAX_FILES = 20000


def audit(root: Path):
    total = 0
    large = []
    instructions = []
    errors = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(base) / d).is_symlink())
        for name in sorted(files):
            path = Path(base) / name
            if path.is_symlink():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                errors += 1
                continue
            total += 1
            if name == 'CLAUDE.md':
                instructions.append((size, path.relative_to(root)))
            if size >= 100_000:
                large.append((size, path.relative_to(root)))
            if total >= MAX_FILES:
                break
        if total >= MAX_FILES:
            break
    print(f'Dateien geprüft: {total}' + (' (Scan-Limit erreicht)' if total >= MAX_FILES else ''))
    print(f'Übersprungene Ordnernamen: {", ".join(sorted(SKIP))}')
    print('CLAUDE.md-Dateien (Größe):')
    for size, path in sorted(instructions, key=lambda x: -x[0])[:15]:
        print(f'  {size:>9} Bytes  {path}')
    if not instructions:
        print('  keine gefunden')
    print('Große Dateien >= 100 KB (max. 10):')
    for size, path in sorted(large, key=lambda x: -x[0])[:10]:
        print(f'  {size:>9} Bytes  {path}')
    if not large:
        print('  keine gefunden')
    if errors:
        print(f'Nicht lesbare Metadaten: {errors}')
    print('Hinweis: Dateigröße ist KEINE Tokenverbrauchs-Messung; es werden keine Dateiinhalte gelesen.')


if __name__ == '__main__':
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else '.').expanduser().resolve()
    if not folder.is_dir():
        print(f'Kein Projektordner: {folder}', file=sys.stderr)
        sys.exit(2)
    audit(folder)

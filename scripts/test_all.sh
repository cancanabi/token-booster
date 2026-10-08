#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q
python3 - <<'PY_VALIDATE_839'
import ast,json
from pathlib import Path
for p in [*Path('scripts').glob('*.py'),*Path('tests').glob('*.py')]:ast.parse(p.read_text(encoding='utf-8'))
for f in ['.claude-plugin/plugin.json','hooks/hooks.json','.devcontainer/devcontainer.json','demo/package.json']:
 json.loads(Path(f).read_text(encoding='utf-8'))
print('OK: Python syntax + 4 JSON configurations')
PY_VALIDATE_839
if command -v node >/dev/null; then
  out="$(cd demo && node verbose-tests.js | tail -1)"
  test "$out" = 'TOTAL 1200 TESTS PASS'
  echo 'OK: 1200 synthetic demo tests'
else echo 'NOTICE: Node demo could not run (Node missing)'; fi
echo 'OK: Local smoke tests done. These are not real Claude Code integration tests.'

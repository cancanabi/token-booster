#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo 'Running free offline tests (no Claude, no API key)...'
bash scripts/test_all.sh
python3 scripts/offline_hook_benchmark.py

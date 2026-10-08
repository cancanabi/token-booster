#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m compileall -q scripts token_booster
python3 -m unittest discover -s tests -q
python3 scripts/offline_hook_benchmark.py --output results/offline-report.json
python3 scripts/benchmark_v4.py
printf '\nDone: no Claude account/API key/network required.\n'

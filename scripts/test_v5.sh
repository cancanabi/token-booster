#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m unittest discover -s tests -q
python3 scripts/benchmark_v5.py
python3 scripts/offline_hook_benchmark.py
python3 scripts/tb.py doctor

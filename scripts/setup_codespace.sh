#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
bash scripts/test_all.sh
if ! command -v claude >/dev/null 2>&1; then
  echo 'Installing official Claude Code CLI from claude.ai'
  temp="$(mktemp)"; trap 'rm -f "$temp"' EXIT
  curl -fLsS --retry 2 https://claude.ai/install.sh -o "$temp"
  bash "$temp"
fi
export PATH="$HOME/.local/bin:$PATH"
claude --version
if claude plugin validate "$ROOT"; then
  echo 'OK: Claude Code plugin validated by installed CLI'
else
  echo 'WARNING: Claude CLI plugin validation did not pass. Please check before enabling auto optimization.' >&2
fi
printf '\nNEXT: Run `claude`, log in via your Claude Pro/Max account, then `/exit`.\n'
printf 'After login: run `python3 scripts/ab_claude.py` for two A/B requests.\n'

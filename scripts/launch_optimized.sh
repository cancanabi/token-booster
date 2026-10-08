#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/demo"
export TOKEN_BOOSTER_AUTO=1
export TOKEN_BOOSTER_READ_CACHE=1
# TOKEN_BOOSTER_READ_BLOCK=1 must be explicitly requested; safe default is observation only.
exec claude --plugin-dir "$ROOT" "$@"

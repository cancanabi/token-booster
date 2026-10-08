#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/demo"
unset TOKEN_BOOSTER_AUTO
exec claude "$@"

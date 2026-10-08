---
name: cache
description: Zeigt lokale Cache-Messwerte; Read-Blocking ist nur auf ausdrücklichen Nutzerwunsch aktivierbar.
disable-model-invocation: true
---

Führe `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tb.py" cache-stats` aus. Ausgabe ausschließlich statistisch und lokal. Eine Einsparung in Dateibytes ist **kein** gemessener Claude-Tokenvorteil. Setze `TOKEN_BOOSTER_READ_CACHE=1` nur auf ausdrücklichen Wunsch; aktives Verhindern eines wiederholten Reads erfordert zusätzlich `TOKEN_BOOSTER_READ_BLOCK=1` **vor** dem Start von Claude Code und kann gewollte Reads beeinflussen.

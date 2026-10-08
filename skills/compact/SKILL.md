---
name: compact
description: Große unstrukturierte Testlogs lokal und mit Verlusthinweis begrenzen.
disable-model-invocation: true
---

Aufgabe: $ARGUMENTS

Nur für laute Log-/Diagnosetexte: `set -o pipefail; COMMAND 2>&1 | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compact.py" --max-lines 80`. Fehlercode darf nicht verloren gehen. Ausgabe hat möglicherweise fehlende Zeilen; Original im Zweifel erneut abrufen. Nie Quellcode, JSON oder Binärdaten blind kürzen. Maskierung vertraulicher Angaben ist best-effort. Keine unbelegten Einsparungen behaupten.

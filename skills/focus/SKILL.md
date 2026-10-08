---
name: focus
description: Lokal und begrenzt nach Dateinamen oder wörtlichen Texten suchen und kleine Ausschnitte zeigen.
disable-model-invocation: true
---

Anfrage: $ARGUMENTS

Im Projektroot `${CLAUDE_PLUGIN_ROOT}/scripts/focus.py` nutzen: `find TERM`, `search LITERAL --limit 30` oder `view RELATIVER_PFAD --start 1 --lines 80`. `search` verwendet **keine Regex**. Keine pauschalen Repository-Dumps. Gesperrte Dateien, Maskierung und Größenlimits respektieren. Nur benötigte Ausschnitte und relevante Pfade wiedergeben. Sicherheit hat Vorrang vor Kürze.

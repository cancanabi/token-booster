---
name: plan
description: Berechne lokal einen begrenzten, relevanzgewichteten Code-Kontextplan, ohne komplette Dateien zu laden.
disable-model-invocation: true
---

Aufgabe: $ARGUMENTS

Vom Projektroot aus `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tb.py" plan "SUCHBEGRIFFE" --root . --budget-bytes 2500` ausführen. Die erzeugten Dateistrukturen sind nur Vorschläge; den tatsächlichen Code bei Bedarf gezielt einsehen. Die Optimierung maximiert ganzzahlig BM25-basierte Relevanz unter einem UTF-8-Bytebudget. Das sind keine Anthropic-Tokens und kein Beweis höherer Codequalität. Niemals automatisch Dateien verändern.

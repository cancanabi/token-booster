---
name: usage
description: Explizit gewählte Claude-Transkriptdateien lokal und ohne Inhaltsausgabe auf Nutzungstoken auswerten.
disable-model-invocation: true
---

Aufgabe: $ARGUMENTS

Nur nach ausdrücklicher Auswahl durch den Nutzer: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tb.py" usage /PFAD/TRANSKRIPT.jsonl`. Zum Vergleich zweier Läufe `compare-usage BASELINE.jsonl OPTIMIERT.jsonl`. Es werden gemeldete Felder aggregiert; bei Streaming-Metadaten kann die Zählung unvollständig/mehrdeutig sein. Keine Inhalte aus Transkripten wiedergeben. Niemals Kosteneinsparungen aus nur einem A/B-Test versprechen.

---
name: optimize
description: Konkrete Codeaufgabe mit gezielter lokaler Suche und reduziertem Kontext ausführen.
disable-model-invocation: true
---

Aufgabe: $ARGUMENTS

- Erst bestehende Hinweise und `git diff --stat`, dann kleinste relevanten Stellen lesen.
- `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/focus.py" find TERM` oder `search LITERAL --limit 30` nutzen; `view DATEI --start N --lines 80` für Ausschnitte. Wörtlich suchen, keine Regex. Bei Bedarf gezielt mit Standardtools nachlesen.
- Keine Geheimnisse, kompletten Projekte oder lange Logs ungeprüft ausgeben. Lokale Maskierung ist nicht unfehlbar.
- Code korrekt ändern, notwendige Tests laufen lassen; bei Fehlern Originaldiagnosen vollständig lesen.
- Kurz mit Dateien, Tests und offenen Problemen antworten; keine nicht gemessenen Tokenprozente erfinden.
- Falls keine Aufgabe angegeben wurde, kurz nach der Aufgabe fragen.

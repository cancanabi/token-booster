---
name: outline
description: Strukturelle Vorschau für Code, Markdown oder JSON erstellen statt ganze Dateien zu lesen.
disable-model-invocation: true
---

Aufgabe: $ARGUMENTS

Nutze `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tb.py" outline RELATIVER_PFAD --root .`. Das Skript prüft Pfad, Größe, Symlinks, Texttyp und sensible Dateinamen. Bei unbekannter Struktur oder fehlender Datei nicht raten. Nur benötigte Codebereiche mit gezielten Leseoperationen nachladen.

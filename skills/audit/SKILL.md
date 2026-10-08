---
name: audit
description: Finde Kontextfallen wie übergroße CLAUDE.md-Dateien und zahlreiche Projektdateien, ohne deren Inhalte an Claude zu schicken.
disable-model-invocation: true
---

Führe im aktuellen Projektordner das lokale Audit aus:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" .
```

Fasse die Ausgabe auf Deutsch kompakt zusammen. Weise darauf hin, dass Dateigrößen keine tatsächlichen Claude-Tokenmessungen sind. Empfiehl nur konkrete, sichere Maßnahmen, insbesondere CLAUDE.md kürzen, ungenutzte MCP-Tools deaktivieren und Suchergebnisse eingrenzen. Ändere keine Konfiguration ohne Auftrag.

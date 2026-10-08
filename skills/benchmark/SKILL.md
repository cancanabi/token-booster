---
name: benchmark
description: Offline Ausgabegrößen von Log-Dateien vor und nach Komprimierung vergleichen.
disable-model-invocation: true
---

Aufgabe: $ARGUMENTS

Nutze `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/benchmark.py" DATEI1 [DATEI2 ...]` für UTF-8-Testlogs. Interpretiere nur Zeichen, UTF-8-Bytes und erkannten Diagnosezeilen-Erhalt. Es sind **keine Claude-Tokens**. Für einen echten A/B-Vergleich siehe `${CLAUDE_PLUGIN_ROOT}/BENCHMARK.md`: gleiche Aufgaben, Modell, Version, frische Sitzungen; Qualität vor Optimierungsquote.

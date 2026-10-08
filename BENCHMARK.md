# Token Booster 5.0 — Benchmark-Zusammenfassung

**Wichtig:** Alle hier gemessenen Daten sind lokal synthetisch und keine realen Claude-Tokens. Ein Marktvergleich mit Konkurrenz-Plugins wurde nicht durchgeführt. Details: `METHODOLOGY.md`.

`python3 scripts/benchmark_v5.py` schreibt `results/v5-benchmark.json`.

- 24 synthetische Sitzungen mit einer unveränderten Wiederholung pro Datei: 24 von 24 ersten Doppel-Reads nach aktivierter Read-Blockierung wurden abgefangen; eine unmittelbar folgende Wiederholung wurde jeweils zugelassen.
- Geschätzte vermiedene gelesene Datei-Inhaltsbytes: 233.200; ausgegebene Hinweistextbytes: 4.368; naive Differenz: 228.832 Bytes **ohne** Hook-CPU, CLI-Startkosten oder Modell-Tokenisierung.
- Knapsack gegen einfache Greedy-Heuristik: in 400 synthetischen Instanzen 139-mal besser, 261-mal gleich, 0-mal schlechter bei identischer definierter Utility.
- 1 großes erfolgreiches Beispiel-Testlog: 92,34 % UTF-8-Ausgabetextreduktion. Fehlerlog: 0 % Veränderung.
- Der Read-Cache ist standardmäßig aus. Blockieren benötigt `TOKEN_BOOSTER_READ_CACHE=1 TOKEN_BOOSTER_READ_BLOCK=1` und kann trotz Sicherheitsgrenzen eine vom Modell gewünschte Wiederholung verhindern.

Reproduzierbarkeit: `bash scripts/test_v5.sh` oder `python3 -m unittest discover -s tests -q` + `python3 scripts/benchmark_v5.py` + `python3 scripts/offline_hook_benchmark.py`.

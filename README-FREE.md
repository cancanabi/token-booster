# Offline testing

No Claude account or API key is necessary to check the local tooling.

```bash
python3 -m unittest discover -s tests -q
python3 scripts/tb.py doctor
python3 scripts/benchmark_v5.py
```

`benchmark_v5.py` uses synthetic events, local files and byte counts. It does
not access a Claude model or measure model-token usage. Run the commands in a
throwaway project before pointing the source scanner at a private repository.

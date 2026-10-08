# Methodology / Benchmark 5.0

## Offline test scope

`python3 -m unittest discover -s tests -q` exercises prior compaction and retrieval, safe source scanning, invalid input, hook JSON, security failures, read-cache mutation/invalidation, subprocess CLI and randomized mutation cases.

`python3 scripts/benchmark_v5.py` produces a deterministic **synthetic** report:

- 24 distinct synthetic session keys, each with a Python text file and a successful first Read result.
- Check first duplicate unchanged full-file Read is denied once; next identical read is allowed.
- Check content mutations (same byte length), range reads and compaction all allow a read.
- Sum the original file sizes for denied requests, subtract the bytes in denial text **only as a rough byte balance**. No Claude request is made and no real token metric is inferred.
- Independently run 400 knapsack-vs-greedy synthetic trials, along with verbose-success/failure log fixtures.

Results: `results/v5-benchmark.json`.

## True A/B study to run later

1. Register identical tasks and test suites; use clean repository snapshots and same Claude Code version/model for baseline/optimized trials.
2. Randomize or alternate the order, run more than one seed for stochastic tasks, and allow the same time/quality budget.
3. Collect actual `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` from the provider's session transcript metadata, and explicitly distinguish cached-read costs from fresh input.
4. Independently verify task success, correct source changes, human-readable errors and elapsed wall-clock time.
5. Report per-task differences and confidence intervals, include all failures and plugin overhead, and compare to a representative competitor under an identical workload.
6. Publish reproducible scripts and anonymized data before claiming general dominance.

## Why raw UTF-8 bytes are not tokens

Actual tokenization depends on the model and surrounding prompt; caching and hidden CLI behavior affect billable usage. A `PostToolUse` rewrite applies after the command runs, so command duration and I/O costs are unchanged. A denied `PreToolUse` read may require a retry, and its explanatory message itself consumes context.

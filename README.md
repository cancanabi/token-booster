# Token Booster

Local context tooling for Claude Code workflows.

Token Booster helps keep repository exploration and test output manageable. It offers
source discovery, bounded context selection, opt-in Read deduplication and conservative
Bash output compression. The local CLI and test suite work without a Claude account.

**Status:** experimental integration. The code has offline tests, but has not been
validated against a live, authenticated Claude Code session. No real-world Claude
token savings or cost reductions are claimed.

## Features

| Tool | Purpose | Default behavior |
| --- | --- | --- |
| Source discovery | BM25-style ranking of eligible project files | Explicit CLI invocation |
| Context planner | Exact bounded 0/1 selection using a byte budget | Explicit CLI invocation |
| Source outline | Lists structural symbols without dumping entire files | Explicit CLI invocation |
| Read monitor | Tracks repeated full-file Reads using content fingerprints | Disabled |
| Read blocker | Denies one identical repeated Read per unchanged file/session | Disabled; experimental |
| Bash output compaction | Trims large successful test logs when safe to do so | Disabled |
| Usage reports | Aggregates usage metadata from selected JSONL transcripts | Explicit CLI invocation |

All automatic behavior is opt-in. The plugin does not make network requests or
require a separate API key.

## Requirements

- Python 3.10 or newer
- Linux, macOS or WSL for the Read-cache locking mechanism (`fcntl`)
- Claude Code only when using the plugin hooks or slash commands; **not** required
  for offline analysis and tests

## Quick start (no Claude account needed)

From the repository root:

```bash
python3 -m unittest discover -s tests -q
python3 scripts/tb.py doctor
python3 scripts/tb.py map . --limit 20
python3 scripts/tb.py rank "authentication bug" --root . --limit 10
python3 scripts/tb.py plan "authentication bug" --root . --budget-bytes 2500
```

To run the local synthetic benchmark:

```bash
python3 scripts/benchmark_v5.py
```

It records *estimated avoided file bytes*, not model tokens. Replacing tool
responses can also affect answer quality, which these offline tests do not measure.

## Using it with Claude Code

After installing Claude Code separately, run it with the absolute path to this
repository:

```bash
claude --plugin-dir /absolute/path/to/token-booster
```

You can enable each hook behavior separately:

```bash
# Compact only eligible successful test output.
TOKEN_BOOSTER_AUTO=1 claude --plugin-dir /absolute/path/to/token-booster

# Observe repeated Read requests without changing tool responses.
TOKEN_BOOSTER_READ_CACHE=1 claude --plugin-dir /absolute/path/to/token-booster

# Experimental: deny at most one identical unchanged full-file reread.
TOKEN_BOOSTER_READ_CACHE=1 TOKEN_BOOSTER_READ_BLOCK=1 \
  claude --plugin-dir /absolute/path/to/token-booster
```

**Use observation mode first.** A repeated Read is not necessarily redundant:
Claude may legitimately need to review a file again. The blocker skips partial
Reads, symbolic links and sensitive-looking paths, and fails open on uncertainty.
Disable it by removing `TOKEN_BOOSTER_READ_BLOCK=1` and restarting Claude.

## Command reference

```bash
python3 scripts/tb.py doctor
python3 scripts/tb.py cache-stats
python3 scripts/tb.py outline token_booster/context.py --root .
python3 scripts/tb.py usage /path/to/session.jsonl
python3 scripts/tb.py compare-usage /path/to/baseline.jsonl /path/to/optimized.jsonl
```

Available Claude Code skills include `plan`, `outline`, `focus`, `optimize`,
`audit`, `benchmark`, `cache` and `doctor`; see `skills/` for details.

## What the planner optimizes

The bounded planner solves a 0/1 selection problem: maximize the sum of
BM25-derived integer relevance scores subject to a UTF-8 preview-byte budget.
The objective is **not** actual token cost, repository comprehension or task
success. See [Benchmark methodology](METHODOLOGY.md).

## Privacy and safety

Project scanning excludes several sensitive filename patterns, symlinks and
out-of-root paths, but filename screening cannot detect every secret stored in
ordinary source files. Avoid scanning confidential repositories without review.
The Read cache stores metadata hashes, not source content. Consult
[SECURITY.md](SECURITY.md) for limitations and the shutdown procedure.

## Development

```bash
python3 -m unittest discover -s tests -q
bash scripts/test_v5.sh
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and the
[technical design](docs/architecture.md). CI runs the standard-library test
suite on supported Python versions; it is not a live Claude Code integration test.

## License

MIT. See [LICENSE](LICENSE).

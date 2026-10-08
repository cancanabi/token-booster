# Token Booster

**Less context noise for coding agents. More relevant code in the window.**

An open-source, Python-based toolkit for exploring large repositories, selecting useful source previews under a context budget, and taming noisy tool output. It includes **optional, conservative hooks for Claude Code**.

[Get started](#try-it-in-60-seconds) · [Features](#what-it-does) · [Benchmarks](#what-the-tests-actually-show) · [Claude Code setup](#optional-claude-code-integration) · [Contribute](#help-test-it-in-real-projects)

> **Experimental project.** The offline tools are tested, but the Claude Code integration has not yet been validated in an authenticated live session. **Actual model-token or cost savings have not been measured.**

## The problem

Coding agents can spend context on repetitive or low-value information:

- Reading the same unchanged file again.
- Receiving hundreds of nearly identical successful test lines.
- Searching broadly when only a few files matter.
- Pulling too much source text into a limited context window.

Token Booster provides small, inspectable tools to **measure and reduce this kind of noise**. Automatic changes to Claude Code tool output are **off by default**.

## Try it in 60 seconds

**No Claude account, API key, or paid service is needed for the offline tools.** You need Python 3.10+.

```bash
git clone https://github.com/cancanabi/token-booster.git
cd token-booster

# Run the local tests
python3 -m unittest discover -s tests -q

# See what the toolkit detects
python3 scripts/tb.py doctor

# Find likely relevant files
python3 scripts/tb.py rank "authentication bug" --root . --limit 10

# Make a bounded context plan
python3 scripts/tb.py plan "authentication bug" --root . --budget-bytes 2500
```

Try `rank` and `plan` with a different query against a project you control. Note that project scanning is not a secret detector; review [security limitations](SECURITY.md) before using it on sensitive code.

## What it does

| Tool | Why it's useful | Available without Claude? |
| --- | --- | --- |
| **Relevance search** | BM25-style ranking helps find likely relevant files before reading everything. | Yes |
| **Context planner** | Solves a bounded 0/1 selection problem to maximize defined relevance scores within a UTF-8 byte budget. | Yes |
| **Code outline** | Lists symbols and structural information instead of dumping entire files. | Yes |
| **Log compressor** | Reduces repetitive diagnostic text when invoked explicitly; optional Claude Code hook for eligible successful Bash test output. | Yes (CLI) |
| **Read monitor** | Uses content fingerprints to spot repeated, unchanged full-file reads. | Claude Code hook |
| **Read blocker** | Can stop *one* identical unchanged reread per session, then allows another attempt; experimental and disabled by default. | Claude Code hook |
| **Usage analyzer** | Summarizes selected transcript usage fields and compares baseline versus optimized reports. | Yes, with transcript data |

The source code is in [`token_booster/`](token_booster/) and the CLI is [`scripts/tb.py`](scripts/tb.py). No separate inference API is required for the local analysis.

## What the tests actually show

These figures come from **synthetic offline experiments**, not an authenticated Claude Code benchmark:

| Local check | Observed result | Important caveat |
| --- | --- | --- |
| Python test suite | **139 tests passed** in the packaged local release | Not equivalent to a live Claude Code compatibility test |
| Simulated repeated reads | **24 / 24** first unchanged duplicate reads intercepted | Blocking a read can cause a retry or alter agent behavior |
| Large successful example log | **92.34% fewer UTF-8 output bytes** | One synthetic fixture; **not** measured model-token savings |
| Exact selection vs. simple greedy | **139 better / 261 tied / 0 worse** over 400 synthetic cases | Only for the defined relevance/byte-budget objective |

Reproduce the experiments:

```bash
python3 scripts/benchmark_v5.py
python3 scripts/offline_hook_benchmark.py
```

Read [the benchmark summary](BENCHMARK.md) and [methodology](METHODOLOGY.md) before interpreting the results.

**What isn't proven yet:** lower total token usage, lower costs, improved code quality, zero regressions, or superiority over other Claude Code plugins. We want to measure those rather than guess.

## Optional Claude Code integration

Claude Code must be installed separately. The CLI tools above do not require it.

```bash
claude --plugin-dir /absolute/path/to/token-booster
```

All automatic behaviors are opt-in:

```bash
# Inspect duplicate reads without blocking them.
TOKEN_BOOSTER_READ_CACHE=1 claude --plugin-dir /absolute/path/to/token-booster

# Compact only eligible successful Bash test output.
TOKEN_BOOSTER_AUTO=1 claude --plugin-dir /absolute/path/to/token-booster

# EXPERIMENTAL: block at most one unchanged duplicate full-file read.
TOKEN_BOOSTER_READ_CACHE=1 TOKEN_BOOSTER_READ_BLOCK=1 \
  claude --plugin-dir /absolute/path/to/token-booster
```

The Read-cache locking implementation targets **Linux, macOS, and WSL** (`fcntl`). Start with **monitor-only mode**. Range reads, symlinks, and uncertain cases are deliberately handled conservatively. Read [SECURITY.md](SECURITY.md) before enabling blocking or automatic output modification.

## Help test it in real projects

This is where outside contributors can make the biggest difference:

1. **Test a real codebase:** Does relevance search surface the right files?
2. **Try an A/B workflow:** Same repository, tasks, model, and quality checks with and without the plugin.
3. **Challenge the safety logic:** Find cases where logs should not be compressed or a repeated read should be allowed.
4. **Share a reproducible report:** Include the task, tool versions, outcome, and anonymized input/output token usage where available.

[**Open an issue**](https://github.com/cancanabi/token-booster/issues/new) · [Read contribution guidelines](CONTRIBUTING.md) · [Review the architecture](docs/architecture.md)

If you find the approach useful, starring the repository helps other developers discover it. Constructive criticism, failed cases, and independent benchmarks are especially welcome.

## Project status & license

**Status:** experimental/open source. Offline functionality has local tests; Claude Code integration and real token savings require external validation. This toolkit cannot create free Claude tokens, change a provider's limits, or guarantee savings.

**License:** [MIT](LICENSE). See [SECURITY.md](SECURITY.md) for sensitive-data caveats.

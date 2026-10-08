# Architecture

Token Booster is a small Python package plus Claude Code plugin metadata.

## Local commands

`scripts/tb.py` is the offline entry point. `token_booster/context.py` handles
bounded file selection and BM25-derived rankings; `token_booster/usage.py`
aggregates transcript usage fields. The CLI never starts a model.

## Hook lifecycle

Claude Code invokes hook scripts as independent short-lived processes.
`hooks/hooks.json` registers:

- `PostToolUse` for eligible Bash output compaction
- `PostToolUse` for successful full-file Read observation
- `PreToolUse` for optional duplicate Read blocking
- `SessionStart` for clearing session cache metadata

The Read cache derives stable fingerprints locally, stores only bounded metadata
and uses file locks on POSIX systems. Hook failures must leave native tool
behavior unchanged. Read blocking is experimental and requires two explicit
environment variables.

## Context planner

File discovery excludes several sensitive paths and size classes. A bounded
lexical relevance calculation ranks structural previews. A dynamic-programming
knapsack step selects previews under a fixed byte budget. This is optimal only
for the defined score and candidate set; relevance scores are a heuristic.

## Measurement

`benchmark_v5.py` uses synthetic Read events and local files. No model is
queried. It tracks avoided file bytes and hook metadata separately. Results
cannot be interpreted as Claude prompt tokens or task-quality improvements.

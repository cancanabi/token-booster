# Contributing

Contributions are welcome, especially small, reproducible bug reports and
tests for real integration behavior.

## Before sending a change

1. Reproduce the issue on a recent Python 3.10+ environment.
2. Add or update a focused `unittest` case.
3. Keep the automatic hooks fail-open and disabled by default.
4. Run `python3 -m unittest discover -s tests -q`.
5. Describe what changed, the tests performed and any remaining limitations.

## Compatibility and privacy

Do not put source code from a confidential repository, credentials, session
transcripts or access tokens into issues or test fixtures. Synthetic examples
are preferable. Changes to Claude Code hook output formats should include an
explanation of which documented schema they target. Avoid new dependencies
unless they make a measurable difference.

## Benchmark claims

Distinguish among byte reduction, estimated token counts, transcript-reported
usage and measured cost. A claim about actual agent efficiency should include
comparable tasks, versions, quality checks and repeated runs.

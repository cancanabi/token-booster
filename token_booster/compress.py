"""Guards for conservative test-output compression."""

from __future__ import annotations

import re
from typing import Callable


SUMMARY = re.compile(
    r"(?i)(?:\b\d[\d,]*\s+(?:tests?\s+)?(?:passed|skipped|successful)\b"
    r"|test result:|\btests?:\s+\d+|\btotal\s+\d+\s+tests?\s+pass\b"
    r"|all tests passed|Ran \d+ tests? in|\bpass(?:ed)?\s+\d+\b"
    r"|\b\d+\s+passing\b|\bcoverage\s*:?\s*\d+%)"
)


def critical_lines(text: str) -> list[str]:
    """Find test-summary lines that must survive a rewrite unchanged."""
    return [line for line in text.splitlines() if SUMMARY.search(line)]


def protects_all_summaries(original: str, rewritten: str) -> bool:
    return all(line in rewritten for line in critical_lines(original))


def compress_for_hook(
    stdout: str,
    legacy_compact: Callable[[str], str],
) -> str | None:
    """Return a safe rewrite, or None to retain the original tool response."""
    result = legacy_compact(stdout)
    if not protects_all_summaries(stdout, result):
        return None

    # Only accept a clearly marked, meaningful reduction.
    if "INCOMPLETE" not in result:
        return None
    if len(result.encode("utf-8")) >= 0.70 * len(stdout.encode("utf-8")):
        return None
    return result

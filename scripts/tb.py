#!/usr/bin/env python3
"""Offline CLI for source selection, log compression and usage inspection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from compact import compact
from token_booster.context import candidates, collect, outline, plan, read_safe
from token_booster.diagnostics import cache_stats, doctor
from token_booster.usage import compare, summarize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline tools for repository context, cache status and usage reports"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    source_map = commands.add_parser("map", help="List eligible project files")
    source_map.add_argument("root", nargs="?", default=".")
    source_map.add_argument("--limit", type=int, default=80)

    source_outline = commands.add_parser("outline", help="List source symbols and headings")
    source_outline.add_argument("file")
    source_outline.add_argument("--root", default=".")

    rank = commands.add_parser("rank", help="Rank source files by lexical relevance")
    rank.add_argument("query")
    rank.add_argument("--root", default=".")
    rank.add_argument("--limit", type=int, default=15)

    context_plan = commands.add_parser("plan", help="Select previews under a byte budget")
    context_plan.add_argument("query")
    context_plan.add_argument("--root", default=".")
    context_plan.add_argument("--budget-bytes", type=int, default=2500)

    compression = commands.add_parser("compress", help="Compress diagnostic logs from stdin")
    compression.add_argument("--max-lines", type=int, default=80)

    usage = commands.add_parser("usage", help="Summarize selected transcript usage metadata")
    usage.add_argument("transcript")

    comparison = commands.add_parser("compare-usage", help="Compare two usage reports")
    comparison.add_argument("baseline")
    comparison.add_argument("optimized")

    commands.add_parser("doctor", help="Check local installation and settings")
    commands.add_parser("cache-stats", help="Report cached fingerprint counters")
    return parser


def local_source_command(args: argparse.Namespace) -> dict | None:
    root = Path(args.root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must be directory")

    if args.command == "map":
        for path in collect(root)[: max(1, min(500, args.limit))]:
            print(path.relative_to(root).as_posix())
        return None

    if args.command == "outline":
        path = root / args.file
        text = read_safe(root, path)
        if text is None:
            raise ValueError("file denied, symlink, oversize, binary or invalid UTF-8")
        print(outline(path, text), end="")
        return None

    if args.command == "rank":
        for match in candidates(root, args.query)[: max(1, min(24, args.limit))]:
            print(f"{match.bm25:8.4f} {match.bytes:5d}B {match.path}")
        return None

    return plan(root, args.query, args.budget_bytes)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor(ROOT)
        elif args.command == "cache-stats":
            result = cache_stats()
        elif args.command == "compress":
            content = sys.stdin.buffer.read(2_000_001)
            if len(content) > 2_000_000:
                raise ValueError("log larger than 2 MB")
            print(compact(content.decode("utf-8", "strict"), max_lines=args.max_lines), end="")
            return 0
        elif args.command == "usage":
            result = summarize(Path(args.transcript))
        elif args.command == "compare-usage":
            baseline = summarize(Path(args.baseline))
            optimized = summarize(Path(args.optimized))
            result = compare(baseline, optimized)
        else:
            result = local_source_command(args)
            if result is None:
                return 0

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"token-booster: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

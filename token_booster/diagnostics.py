"""Local configuration checks and aggregated Read-cache counters."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys

from .read_cache import STATE_LIMIT, _state_dir


REQUIRED_HOOK_EVENTS = ("PreToolUse", "PostToolUse", "SessionStart")


def doctor(plugin_root: Path) -> dict:
    """Check local files and configuration without contacting Claude Code."""
    manifest = plugin_root / ".claude-plugin" / "plugin.json"
    hooks = plugin_root / "hooks" / "hooks.json"
    required_files = [
        manifest,
        hooks,
        plugin_root / "scripts" / "read_cache_hook.py",
        plugin_root / "scripts" / "post_tool_use.py",
    ]

    read_monitor = os.environ.get("TOKEN_BOOSTER_READ_CACHE") == "1"
    details = {
        "python_3_10_plus": sys.version_info >= (3, 10),
        "claude_cli_found": shutil.which("claude") is not None,
        "plugin_files_present": all(path.is_file() for path in required_files),
        "read_observation_on": read_monitor,
        "read_blocking_on": read_monitor
        and os.environ.get("TOKEN_BOOSTER_READ_BLOCK") == "1",
        "bash_compaction_on": os.environ.get("TOKEN_BOOSTER_AUTO") == "1",
    }

    try:
        plugin_meta = json.loads(manifest.read_text(encoding="utf-8"))
        hook_config = json.loads(hooks.read_text(encoding="utf-8"))["hooks"]
        details["manifest_version"] = plugin_meta.get("version")
        details["expected_hooks_registered"] = all(
            event in hook_config for event in REQUIRED_HOOK_EVENTS
        )
    except (ValueError, OSError, KeyError, TypeError):
        details["expected_hooks_registered"] = False

    ready = (
        details["python_3_10_plus"]
        and details["plugin_files_present"]
        and details["expected_hooks_registered"]
    )
    details["status"] = "ok" if ready else "check_installation"
    details["note"] = (
        "Local structural checks only. "
        "Claude Code integration is not validated by this command."
    )
    return details


def cache_stats() -> dict:
    """Aggregate bounded cache statistics without inspecting source contents."""
    root = _state_dir()
    if root is None:
        return {"error": "No secure private state directory available"}

    totals: dict[str, int] = {}
    sessions = 0
    cached = 0
    for path in root.glob("*.json"):
        if sessions >= 500:
            break
        try:
            if path.is_symlink() or path.stat().st_size > STATE_LIMIT:
                continue
            data = json.loads(path.read_bytes())
            if not isinstance(data, dict) or not isinstance(data.get("stats"), dict):
                continue

            sessions += 1
            records = data.get("records")
            if isinstance(records, dict):
                cached += len(records)
            for key, value in data["stats"].items():
                if isinstance(key, str) and type(value) is int and 0 <= value <= 10**12:
                    totals[key] = totals.get(key, 0) + value
        except (OSError, ValueError, TypeError):
            continue

    return {
        "sessions_with_state": sessions,
        "currently_cached_file_fingerprints": cached,
        "counters": totals,
        "interpretation": (
            "File bytes avoided are estimates; "
            "not Claude token usage or financial savings."
        ),
    }

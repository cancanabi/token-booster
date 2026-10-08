# Research basis — Stand 8. Oktober 2026

## Primärquellen

- Anthropic, Claude Code Hooks: https://code.claude.com/docs/en/hooks — `PreToolUse` supports `permissionDecision: deny`; `PostToolUse` supports `updatedToolOutput` only with a compatible output shape. Session lifecycle `SessionStart` includes resume/compact/clear.
- Anthropic, Plugin structure: https://code.claude.com/docs/en/plugins — `.claude-plugin/plugin.json`, `skills/`, `hooks/hooks.json`, portable `${CLAUDE_PLUGIN_ROOT}`.
- Official Anthropic plugin development example: https://github.com/anthropics/claude-code/tree/main/plugins/plugin-dev

## Feature comparison (public documentation, no competitive benchmark)

- https://github.com/egorfedorov/claude-context-optimizer — repeated Read cache, tracking, low-overhead hooks, budget alerts, net savings estimates.
- https://github.com/eiom-it/claudetokenoptimizer — VS Code companion, safe Bash rewriting, repeated-read detection, large-file guard, hash-based summaries.
- https://github.com/AzozzALFiras/claude-context-optimizer — MCP semantic reading and log compaction.

## Architecture decisions

- **Combined:** opt-in native hooks for Read/PostToolUse and Bash/PostToolUse, local byte-budget planner, structural code discovery, privacy-focused metadata statistics.
- **Not copied:** source implementations or proprietary assets from third-party optimizers. These are independent Python implementations of general principles described publicly.
- **Safety > aggressive savings:** one denial per exact full-file content in a session, no partial range blocking, SHA-256 validation, finite TTL, automatic reset on SessionStart, hash-only persisted record and fail-open on errors.
- **No LLM calls:** model APIs are not required for local bench, code mapping or cache fingerprints; no implicit costs.

This research does not demonstrate ranking, real-world quality or market leadership. Future independent A/B trials should include task acceptance tests, cost, run time and failure recovery as well as token usage.

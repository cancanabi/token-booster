# Security model — Token Booster 5.0

All hooks are **off unless explicitly enabled**. Never paste credentials or Claude transcript contents into issue trackers.

### Read deduplication

- No source contents, raw paths or session IDs are written to disk; only hashed session/path keys, SHA-256 content fingerprints, size and timestamps and integer counts.
- Linux/macOS/WSL state directory must be mode 0700; files are mode 0600; atomic replacement and exclusive `fcntl.flock` reduce collision risk.
- Only successful full-file Read operations in the same project/session/transcript are considered; symlinks, file sizes outside 768B–1MB, hidden credential-like filenames, external paths and partial reads are skipped.
- Any content change or reset on `SessionStart` invalidates the cache; TTL is 90 seconds. Each same-content read is blocked at most once to avoid repeated-denial loops. Hashes do not prove semantic redundancy.
- Parent-directory replacement races, unknown secret names, Windows fallback limitations, manipulated OS metadata, interpreter substitution and plugin installation tampering are not fully solved. **Not a sandbox.**

### Bash compression

Only allowlisted standalone test commands with successful, plain-text outputs and without detected diagnostics are eligible for rewriting. The tool result is rewritten after execution; command side effects cannot be undone. On uncertain schemas, outputs are left intact.

### No implicit telemetry or permissions

No HTTP calls, API keys, permission escalation, automatic `CLAUDE.md` edits or background model sessions. Test scripts never log full source-file contents. CLI `usage` reads explicitly chosen local transcript metadata and does not export prompts.

### Emergency disable

Start without `TOKEN_BOOSTER_READ_CACHE`, `TOKEN_BOOSTER_READ_BLOCK`, or `TOKEN_BOOSTER_AUTO`; or unset all three, and restart Claude Code. The plugin remains installed but does not change tool execution. Cached hashes can be removed by deleting the local Token Booster state directory after stopping active sessions.

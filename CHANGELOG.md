# Changelog

## 5.0.1 — Repository preparation

- Reorganized the offline CLI, diagnostics and compression guard for readability.
- Added concise English documentation and contributor instructions.
- Added GitHub Actions tests for Python 3.10–3.13.
- Kept automatic behavior opt-in and synthetic measurements clearly labeled.
- No changes to Read-cache behavior or model-token claims.

## 5.0.0 — October 8, 2026

- Added privacy-first, per-session Read fingerprint cache with SHA-256 and atomic private state.
- Added opt-in, single-use, 90-second unchanged-full-read denial (never blocks range reads; safe fallback).
- Added SessionStart invalidation, fail-open behavior for stale/changed/unknown input and self-loop avoidance.
- Added `doctor`, `cache-stats`, two on-demand skills, random mutation tests and a synthetic v5 benchmark.
- Preserved v4 BM25, exact bounded knapsack, structural outline, usage analysis and safe Bash test-output compression.
- Retained default silent non-invasive mode. Actual Claude-Code integration still untested without a Claude account.

Earlier v1–v4 development details are documented in the previous tagged archives.

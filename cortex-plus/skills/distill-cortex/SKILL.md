---
name: distill-cortex
description: >
  This skill should be used when the user says "distill cortex", "compress
  memories", "distill my memories", "run LTM distillation", "consolidate
  cortex", "purge STM", or wants to synthesize Cortex short-term memories
  (STM) into long-term memory (LTM). Apply when Cortex has accumulated
  many sessions and the user wants a durable, compressed memory layer.
version: 0.1.0
dependencies:
  - type: script
    path: ${CLAUDE_PLUGIN_ROOT}/scripts/distill.py
---

## What this skill does

Reads all STM fragments from Cortex SQLite, distills them project-by-project
via Haiku, and writes LTM back to Cortex. Optionally synthesizes a global
LTM across all projects.

**LTM storage convention:**
- Per-project: `_ltm-{projectId}` (e.g., `_ltm-claude-essence`)
- Cross-project: `_ltm-global`
- Decay metadata: `_ltm___time` — stores `{"lastDistilledAt": "<ISO>"}` for monthly 10% decay
- LTM fragment prefix: `[LTM:1.00]` (score decays over time; fragments below 0.10 dropped)

STM is only deleted when `--purge` is passed. Default (no flag) is read-only distillation.

## Algorithm

1. For each project: read STM grouped by `source_session` from SQLite
2. Per session: call Haiku to extract durable facts (one session = one Haiku call)
3. Oversized sessions (>400 memories): sub-chunked → intermediate summaries → merged
4. All session summaries → hierarchical merge (batches of 8) → per-project LTM
5. Merge with existing LTM (applying decay based on `_ltm___time`)
6. Write LTM fragments to `_ltm-{projectId}` via `cortex_remember`
7. Update `_ltm___time`
8. Optionally: collect all per-project LTMs → Haiku → `_ltm-global`

## Invocation

Run via Bash using the bundled script. MUST use Python 3.10+.

```bash
# Distill all projects + global, then prune STM (default — recommended)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/distill.py

# Distill but keep STM intact (skip pruning)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/distill.py --keep-stm

# Distill one project (+ prune that project's STM)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/distill.py --project <project_id>

# Dry run (print LTM, do not store or prune)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/distill.py --project <project_id> --dry-run

# Delete STM fragments older than 90 days (unconditional, no distillation)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/distill.py --purge-old

# Synthesize global LTM only (from existing per-project LTMs)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/distill.py --global
```

## When invoked

1. Ask the user: distill all projects or specific ones?
2. Run the script with `--dry-run` first to preview LTM output
3. User confirms → run without `--dry-run` (STM will be pruned automatically after LTM is confirmed)
4. Mention `--keep-stm` if the user wants to retain STM after distillation
5. Optionally suggest `--purge-old` to clean up fragments older than 90 days

## Failure modes

- **"Haiku error"**: API call failed — check internet/auth; retry
- **"Nothing to distill"**: all memories were noise — inspect project manually
- **Store fails for a fragment**: logged with ✗ — re-run to retry; idempotent
- **`cortex_remember` MCP not found**: Cortex plugin must be installed and cached at
  `~/.claude/plugins/cache/cortex/cortex/2.1.3/dist/mcp-server.js`
- **STM not deleted despite `--purge`**: LTM write unconfirmed — check store step for ✗ failures, re-run
- **Active session detected at startup**: script auto-detects running `claude` processes and caps all operations to fragments before the earliest session start. Fragments from active sessions are preserved.

## Running outside Claude Code

Distillation works inside or outside Claude, but **purge operations are safest from a plain terminal** to avoid SQLite lock contention with the live Cortex MCP server.

```bash
# Open a new terminal (not a Claude Code session)
cd /path/to/cortex-plus

# Full workflow: dry run → store → purge
python3 skills/distill-cortex/scripts/distill.py --dry-run
python3 skills/distill-cortex/scripts/distill.py
python3 skills/distill-cortex/scripts/distill.py --purge

# Or clean up old fragments only
python3 skills/distill-cortex/scripts/distill.py --purge-old
```

When run from a plain terminal with no active Claude sessions, `_CUTOFF` is `None` and all STM is in scope. When run from inside Claude (or alongside active sessions), the script auto-detects and logs the cutoff — no manual adjustment needed.

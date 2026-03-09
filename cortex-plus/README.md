# cortex-ext

Claude Code plugin for Cortex memory management. Provides STM→LTM distillation and pre-compression skills.

## Skills

- **cortex-plus** — Transparent LTM enhancement: augments every Cortex recall with project LTM + global LTM lookups automatically
- **distill-cortex** — Reads STM from Cortex SQLite, distills per session via Haiku, writes LTM back to Cortex, then prunes STM
- **compress** — Deterministic pre-compression pipeline (ANSI strip, dedup, near-dedup, dict encode)

## Quick Start

Distillation is designed to run from a **plain terminal outside Claude Code**, especially since it prunes STM by default.

```bash
# Prerequisites: Python 3.10+, claude CLI authenticated
SCRIPT=skills/distill-cortex/scripts/distill.py

# 1. Dry run — preview LTM output without storing or pruning
python3 $SCRIPT --dry-run

# 2. Distill all projects + global, then prune STM (default)
python3 $SCRIPT

# 3. Distill but keep STM intact
python3 $SCRIPT --keep-stm

# 4. Synthesize cross-project global LTM only
python3 $SCRIPT --global

# 5. Delete STM older than 90 days (unconditional)
python3 $SCRIPT --purge-old

# Scope to one project
python3 $SCRIPT --project <project_id> --dry-run
```

### Active session handling

The script auto-detects running `claude` processes. If any are found, it caps all operations to fragments before the earliest session start — fragments from active sessions are never touched.

```
ℹ Active Claude session detected — capping at 2026-03-09 10:30:00 UTC
  Fragments from active sessions will not be distilled or deleted.
```

Running from inside Claude works fine for dry runs. For the default run (which prunes STM), open a separate terminal to avoid SQLite lock contention.

## Load as plugin

```bash
claude --plugin-dir ./cortex-plus
```

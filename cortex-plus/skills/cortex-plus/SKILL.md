---
name: cortex-plus
description: >
  Use this skill ALWAYS and PROACTIVELY whenever you are about to recall
  memory, look up past context, search Cortex for historical information, or
  answer any question that depends on what happened in previous sessions. This
  skill transparently enhances every Cortex memory lookup by also querying the
  LTM (long-term memory) layers — the distilled, durable knowledge buckets —
  so you always surface both recent STM and synthesized long-term knowledge.
  Trigger on: "what did we decide about X", "do you remember X", "what's the
  context for X", "recall X", any cortex_recall usage, session-start context
  restoration, or any time past work is referenced. Never skip the LTM layers
  — they contain distilled knowledge that may not appear in STM results.
model: haiku
---

## What this skill does

Every time you recall from Cortex, you MUST also query the LTM layers. This
is not optional — the LTM contains distilled, high-signal knowledge that
survives STM pruning. Skipping it means missing the most durable context.

**LTM project ID conventions:**
- Per-project LTM: `_ltm-{projectId}` (e.g. `_ltm-claude-essence`)
- Cross-project: `_ltm-global`

The current project ID is the Cortex project associated with the working
directory (e.g. directory `claude-essence` → project ID `claude-essence`).

## Enhanced recall procedure

Replace your normal `cortex_recall` call with this three-call pattern:

### Step 1 — Standard recall (STM + recent)

```
cortex_recall(query="<topic>")          # default project, STM + recent
```

### Step 2 — Project LTM (parallel with step 1 when possible)

```
cortex_recall(query="<topic>", projectId="_ltm-{currentProjectId}", limit=8)
```

### Step 3 — Global LTM (parallel with step 1 when possible)

```
cortex_recall(query="<topic>", projectId="_ltm-global", limit=5)
```

Run steps 1–3 in parallel whenever the tool allows multiple calls in one
turn. Use the same query string across all three calls.

### Step 4 — Synthesize

Combine all hits:
- Deduplicate fragments that convey the same fact (keep the more specific one)
- When presenting results, note the source tier: `[STM]`, `[project LTM]`,
  or `[global LTM]` — this helps the user know how fresh/durable each fact is
- Surface LTM facts prominently; they represent synthesized, durable knowledge

If all three searches return empty, say so clearly and suggest running
`distill-cortex` to build LTM from accumulated sessions.

Do not fabricate context. Only report what was actually retrieved.

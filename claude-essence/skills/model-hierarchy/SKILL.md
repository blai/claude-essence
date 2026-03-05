---
name: model-hierarchy
description: >
  Route tasks to the cheapest Claude model that can handle them.
  Use when: spawning sub-agents, considering cost, or current model feels like overkill.
---

# Model Hierarchy

80% of agent tasks are janitorial. Route to the cheapest model that works.

## Claude Tiers

| Tier | Model ID | Alias | Price (input/output /MTok) | Use When |
|------|----------|-------|---------------------------|----------|
| 1 (Cheap) | `claude-haiku-4-5` | `haiku` | $1 / $5 | Single-step, deterministic, no judgment needed |
| 2 (Mid) | `claude-sonnet-4-6` | `sonnet` | $3 / $15 | Multi-step, synthesis, standard patterns |
| 3 (Premium) | `claude-opus-4-6` | `opus` | $5 / $25 | Maximum quality, failed Sonnet escalation |

Target split: **80% Haiku / 15% Sonnet / 5% Opus** (~5x savings vs pure Opus).

> Sonnet 4.6 is substantially more capable than prior Sonnet generations. For many tasks it approaches Opus quality — but Opus 4.6 remains the stronger model. Prefer Sonnet for cost; escalate to Opus when quality matters.

## Task Routing

**Tier 1 - Haiku:** file ops, status checks, lookups, formatting, list transforms, API calls with known params, URL fetching, cron/heartbeat tasks, entity extraction, structured output/JSON, boolean classification, simple single-file edits.

**Tier 2 - Sonnet:** code generation, summarization, drafts, data analysis, multi-file ops, tool orchestration, code review, search/research, architecture decisions, security review.

**Tier 3 - Opus:** tasks that failed at Sonnet, adversarial/edge-case handling, maximum quality required, complex multi-agent orchestration, long-context reasoning (>150K tokens).

## Decision Rules

1. **Escalation override** - if a cheaper model failed, bump one tier up
2. **Try effort first** - before escalating tiers, try `effort: high` on the current model; Sonnet 4.6 at high effort approaches Opus-level reasoning
3. **Intent signals** - extraction/classification/JSON → Tier 1; generation/analysis/synthesis → Tier 2; failed-lower-tier/adversarial → Tier 3
4. **Default** - interactive sessions: use `opusplan`; sub-agents: explicitly set `model: haiku`

## Recommended Defaults

- **Interactive sessions:** set model to `opusplan` — auto-uses Opus during `/plan` mode, Sonnet during execution. Zero-config cost split.
- **Sub-agents:** set `CLAUDE_CODE_SUBAGENT_MODEL=haiku` to pin all sub-agents to Haiku by default.

## Claude Code Subagent Configuration

Subagent frontmatter uses alias strings only (full model ID strings are not supported):

```yaml
model: haiku    # or: sonnet, opus, inherit
```

Built-in defaults: `Explore` → Haiku; `general-purpose` and `Plan` → inherit from parent session. **Explicitly set `model: haiku`** in custom subagent definitions — `inherit` will use the parent's model (potentially Opus if that's your session model).

## Effort Levels (Pre-Escalation)

Before bumping to a higher tier, increase effort on the current model:

| Effort | Use When |
|--------|----------|
| `low` | Routine, mechanical, high-throughput |
| `medium` | Standard (default) |
| `high` | Complex reasoning — try before escalating Sonnet → Opus |

Set via `/model` slider in Claude Code or `CLAUDE_CODE_EFFORT_LEVEL` env var.

## Context Thresholds

- **< 150K tokens:** Sonnet 4.6 handles natively (200K context window)
- **> 150K tokens with complexity:** consider Opus; or Sonnet with 1M beta
- **Note:** Haiku 4.5 supports standard 200K context; no 1M extended option

## Anti-Patterns

- Running heartbeats/file I/O on Opus
- Spawning sub-agents with `model: inherit` when parent session is Opus
- Staying on an expensive model for routine work
- Escalating to Opus based on task type alone — try `effort: high` on Sonnet first
- Using `>50K tokens` as an Opus trigger — Sonnet 4.6 handles this comfortably

## Origin

Adapted from [zscole/model-hierarchy-skill](https://github.com/zscole/model-hierarchy-skill).
Original is multi-provider (DeepSeek, GPT, Gemini, Claude); this version is Claude-only and condensed.

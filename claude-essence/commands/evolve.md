---
name: evolve
description: >
  Evolve any tool across all marketplace plugins by researching prior art (sorted by popularity), checking canonical spec compliance, and applying critically-evaluated enhancements.
  Use when: a tool needs improvement, feels over-engineered, or hasn't been validated against external standards.
version: 1.2.0
argument-hint: "[plugin/type/name]"
allowed-tools: ["Agent", "Read", "Edit", "Write", "Glob", "Grep", "WebSearch", "WebFetch", "AskUserQuestion", "Bash"]
---

# Evolve: Self-Improving Plugin Tools

Your job is to discover all tools across all plugins in this marketplace, let the user pick one, research improvements, and apply enhancements.

## Step 1: Build Tool Registry

Read the marketplace manifest at `${CLAUDE_PLUGIN_ROOT}/../.claude-plugin/marketplace.json` to discover all plugins.

For each plugin, resolve its root as `${CLAUDE_PLUGIN_ROOT}/../{source}` (where `source` is the plugin's `source` field). Scan these directories (skip silently if missing):

| Type | Path | Pattern |
|------|------|---------|
| command | `{plugin_root}/commands/` | `*.md` |
| skill | `{plugin_root}/skills/` | `**/SKILL.md` |
| output-style | `{plugin_root}/output-styles/` | `*.md` |
| agent | `{plugin_root}/agents/` | `*.md` |

For each file found:
1. Read the file
2. Extract `name` and `description` from YAML frontmatter (between first `---` and second `---`)
3. If no `name`, derive from filename (strip `.md`, convert hyphens to spaces)
4. Note the file path for later editing
5. Build registry: `{plugin-name}/{type}/{name}` with description and file path

If `$ARGUMENTS` is non-empty:
1. Check if it matches any `{plugin-name}/{type}/{name}` key in the registry
2. If matched: skip to Step 3 with that tool pre-selected
3. If not matched: fall through to Step 2 and surface a warning: `"Argument '{$ARGUMENTS}' not found in registry. Choose from:"`

If no tools found: report "No tools found." and stop.

## Step 2: Present Tool Selection

Use AskUserQuestion:
- header: "Evolve"
- question: "Which tool would you like to evolve?"
- multiSelect: false
- options: each tool as label `{plugin-name}/{type}/{name}`, description from frontmatter

## Step 3: Read Current Version

Read the full contents of the selected tool. The file contents are the `CURRENT_VERSION`.

Identify:
- Purpose and focus area
- Current structure and patterns
- Assumptions the tool makes that may not be universally correct
- Rules it enforces that lack external validation
- Any pinned model or special configuration
- Dependencies declared in frontmatter (note names and versions for Step 6)

## Step 4: Parallel Research

Launch TWO parallel sub-agents using `model: "sonnet"`:

**Agent A — Prior Art by Popularity:**

Prompt the agent:
```
Research prior art for this Claude Code {type}. Sort findings by popularity and adoption. Be critical — do not assume the current version is correct.

Tool: {plugin-name}/{type}/{name}
File: {file_path}
Description: {description}

Current version:
---
{CURRENT_VERSION}
---

Tasks:
1. WebSearch for popular prior art for this type of tool (include star counts, company adoption, or citation signals in your queries)
2. WebSearch for what practitioners consider over-engineered or wrong about similar tools
3. WebFetch top 3 most relevant results

For each source, evaluate against the current version:
- What does it confirm the current approach gets RIGHT?
- What does it say the current approach gets WRONG or OVERENGINEERS?
- What does the current approach MISS entirely?

Return findings ranked by popularity/adoption:
- Source: [name + URL + popularity signal]
- Agreements: [what current approach gets right]
- Contradictions: [what current approach gets wrong or overengineers]
- Missing: [what current approach omits]
- Priority: [high/medium/low]
```

**Agent B — Canonical Spec Compliance:**

Prompt the agent:
```
Check this Claude Code {type} against canonical Claude Code platform specifications. Find spec violations, over-engineering relative to the spec, and required patterns the tool misses.

Tool: {plugin-name}/{type}/{name}
File: {file_path}
Type: {type}

Current version:
---
{CURRENT_VERSION}
---

Tasks:
1. WebFetch the canonical spec for this tool type:
   - Skills: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
   - Commands/plugins: https://code.claude.com/docs/en/plugins
2. WebSearch for recent Claude Code plugin or {type} specification updates (2025-2026)
3. Compare current version field-by-field against the spec:
   - What required fields are absent?
   - What fields or patterns violate the spec?
   - What does the spec allow that the current version prohibits unnecessarily?
   - What does the current version claim as standard that the spec doesn't require?

Return findings:
- Spec requirement: [what the canonical spec says]
- Current status: [compliant | violation | missing | over-engineered]
- Fix: [specific change]
- Priority: [high/medium/low]
```

## Step 5: Synthesize and Propose

After both agents return:

1. Merge findings, deduplicate overlapping suggestions
2. Structure into three categories:
   - **Validated**: what the current tool gets right (no action needed, cite sources)
   - **Contradicted**: what prior art or the canonical spec says is wrong or over-engineered
   - **Missing**: gaps the current tool doesn't address
3. Derive enhancements from Contradicted + Missing only
4. Rank by impact and keep the top 4 (AskUserQuestion MUST NOT exceed 4 options)

Present to user:

```
## Evolve Proposal: {plugin-name}/{type}/{name}

### What's Validated (keep)
- {finding} — Source: {URL}

### Proposed Enhancements (ranked by impact)
1. **{Title}** [contradicted | missing] — {description}
   Source: {URL + popularity signal}
   Impact: {what improves}
```

Then use AskUserQuestion:
- header: "Apply"
- question: "Which enhancements to apply?"
- multiSelect: true
- options: top 4 enhancements (max allowed by AskUserQuestion)

## Step 6: Apply Enhancements

For each approved enhancement:
1. Read the file again (fresh state)
2. Apply changes using Edit tool
3. Preserve existing structure where the enhancement doesn't touch

After all edits are applied:
4. Bump the `version` field in frontmatter (patch for fixes, minor for new capabilities)
5. If the tool declares `dependencies` in frontmatter, check whether any referenced dependency versions need updating to match changes applied

## Step 7: Verify

After all edits:
1. Re-read the modified file
2. Confirm: frontmatter keys (`name`/`description` or `description`) still present and parseable
3. Confirm: no content appears truncated (section headers intact, Rules section present)
4. Apply the `md-quality:ai-doc-quality` skill to validate the updated content
5. If any check fails, report "Warning: possible corruption at line N" and stop

Present a brief diff summary.

Report: "Evolved {plugin-name}/{type}/{name}. {N} enhancements applied. To undo: `git checkout -- {file_path}`"

## Rules

- **Non-destructive**: Read before edit. Preserve what works.
- **Research-driven**: Enhancements MUST cite sources. No arbitrary changes.
- **User approval**: Never apply without confirmation.
- **One tool at a time**: Quality over breadth.
- **Cost-aware**: Sonnet for research agents (synthesis requires interpretation). Haiku only for raw file scanning.

## Examples

### Example 1: Evolve by picker

```
/evolve
```

Scans all marketplace plugins, presents a picker, user selects a tool, research runs, enhancements proposed and applied.

### Example 2: Evolve by direct argument

```
/evolve claude-essence/command/evolve
```

Skips the picker and jumps directly to Step 3 for the named tool. If the argument does not match any registry key, falls back to the picker with a warning.

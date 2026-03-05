---
name: ai-doc-quality
description: >
  Enforce AI doc principles on any SKILL.md, command, agent, or AI-consumable markdown.
  Apply when writing, updating, or reviewing AI-consumable docs to catch RFC 2119 violations, missing triggers, duplicates, and metadata issues.
version: 3.0.0
dependencies:
  - type: document
    path: ${CLAUDE_PLUGIN_ROOT}/skills/ai-doc-quality/ai-doc-principles.md
    version: 4.0
---

# Skill: ai-doc-quality

## Scope

Validates structure, language, and metadata. Does NOT validate semantic correctness, logical consistency, or domain accuracy. Depends on `ai-doc-principles.md` v4.0 for all rule definitions.

## Input

- `text` (string, required): AI-consumable text to validate
- `file_path` (string, optional): File path for context-aware validation

## Output

- `valid` (boolean): Whether content follows AI doc principles
- `violations` (array): Violations with `type`, `rule`, `line`, `text`, `suggestion`, `severity`
- `reason` (string | null): Explanation if invalid
- `suggestion` (string | null): Overall improvement suggestion

### Violation Types

`missing_metadata`, `unnecessary_metadata`, `invalid_requirement_keyword`, `vague_quantifier`, `ambiguous_pronoun`, `vague_temporal_indicator`, `conversational_softener`, `patronizing_word`, `non_imperative_mood`, `passive_voice`, `duplicate_concept`, `insufficient_examples`

## Algorithm

### Step 1: Parse Input

Extract YAML frontmatter and content from text.

Build a segment map of excluded ranges — positions that Steps 3–4 MUST skip when checking for violations:
- Fenced code blocks: content between ` ``` ` delimiters
- Indented code blocks: lines with 4+ leading spaces
- Inline code spans: content between single backticks
- Example sections: content under any `## Examples` heading until the next `##` heading

### Step 2: Validate Frontmatter

Check required fields: `name`, `description`

Add `missing_metadata` violation if any required field is absent. `version` is optional but recommended.

If `description` is present, validate it contains a trigger condition — at least one of: `when`, `before`, `after`, `during`, `PROACTIVELY`, `Apply`, `Enforce`, `Retrieve`, `Transform`. If absent, add `missing_metadata` violation: `"description must include a trigger condition (when/before/after/PROACTIVELY/Enforce/Apply)"`.

Check for unnecessary fields: `author`, `created_date`, `modified_date`, `timezone`, `type`, `target_audience`, `scope`, `enforcement`, `trigger`, `phase`, `cacheable`

Add `unnecessary_metadata` violation if found (tracked by git history, not needed in frontmatter).

### Step 3: Check Duplicates

**Internal duplicates:**
Scan content (excluding frontmatter and excluded ranges from the segment map) for repeated concepts or near-identical passages with similarity >= 0.7 and length >= 30 chars.

Add `duplicate_concept` violations if found.

### Step 4: Validate Language Rules

Skip all tokens that fall within excluded ranges from the segment map.

| Check | Detect | Violation Type |
|-------|--------|----------------|
| RFC 2119 Keywords | should, could, would, may, might, can — **only in requirement statements** (not in context/rationale prose) | `invalid_requirement_keyword` |
| Ambiguous Pronouns | it, this, that — **only when referent is unclear**; `they/them` are acceptable | `ambiguous_pronoun` |
| Vague Quantifiers | many, few, some, several | `vague_quantifier` |
| Vague Temporal | soon, later, eventually, promptly | `vague_temporal_indicator` |
| Conversational | Can you, I need, probably, alternatively | `conversational_softener` |
| Patronizing | easy, simply, just, obviously, clearly | `patronizing_word` |
| Passive Voice | should be, will be, was processed | `non_imperative_mood`, `passive_voice` |

### Step 5: Validate Examples (Context-Aware)

Infer doc type from content structure (do not read `type` from frontmatter):

| Content Signal | Inferred Type | Examples Required |
|----------------|---------------|-------------------|
| Algorithm section with branches/conditions | Complex atomic | 2-3 examples |
| Algorithm section, linear steps only | Simple atomic | 1-2 examples |
| Contains `invoke(...)` calls | Composite | 1 workflow example |
| `## Usage` section with slash-command syntax | Command | 1-2 usage examples |
| No Algorithm section | Reference/Spec | Inline examples |
| CLAUDE.md or standards file | Standards | Optional |

Add `insufficient_examples` violation if the example count is below the required minimum.

### Step 6: Assign Severity

Assign `severity` to each violation before returning:

| Severity | Violation Types |
|----------|-----------------|
| `error` | `missing_metadata`, `invalid_requirement_keyword` |
| `warning` | `unnecessary_metadata`, `duplicate_concept`, `passive_voice`, `non_imperative_mood`, `ambiguous_pronoun`, `insufficient_examples` |
| `info` | `vague_quantifier`, `vague_temporal_indicator`, `conversational_softener`, `patronizing_word` |

### Step 7: Return Result

Aggregate violations. Return validation result with violations and suggestions.

## Examples

### Example 1: Language Violations

**Input:**
```json
{
  "text": "The system should probably check tokens. It might return errors soon."
}
```

**Output:**
```json
{
  "valid": false,
  "violations": [
    {"type": "invalid_requirement_keyword", "text": "should", "suggestion": "SHOULD"},
    {"type": "conversational_softener", "text": "probably", "suggestion": "Remove"},
    {"type": "invalid_requirement_keyword", "text": "might", "suggestion": "MAY"},
    {"type": "ambiguous_pronoun", "text": "It", "suggestion": "The system"},
    {"type": "vague_temporal_indicator", "text": "soon", "suggestion": "within 2 seconds"}
  ],
  "reason": "5 violations: 2 invalid keywords, 1 softener, 1 pronoun, 1 temporal",
  "suggestion": "The system SHOULD validate tokens. The system MAY return errors within 2 seconds."
}
```

### Example 2: Insufficient Examples

**Input:**
```json
{
  "text": "---\nname: validate-task-size\ntype: atomic\n---\n\nValidate task size.\n\n## Algorithm\n1. Estimate hours\n2. Compare to threshold\n\n(No examples)"
}
```

**Output:**
```json
{
  "valid": false,
  "violations": [
    {
      "type": "insufficient_examples",
      "rule": "Complex atomic skills MUST provide 2-3 examples",
      "suggestion": "Add examples: valid case, error case, edge case"
    }
  ],
  "reason": "1 violation: insufficient examples for complex atomic skill",
  "suggestion": "Add 2-3 examples showing valid, error, and edge cases."
}
```

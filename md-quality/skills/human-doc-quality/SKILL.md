---
name: human-doc-quality
description: >
  This skill should be used when the user asks to "review my README",
  "improve my docs", "check writing quality", "clean up this roadmap",
  "make this more concise", "fix passive voice in my docs", "edit this
  plan for clarity", or "improve human-readable documentation".
  Apply when writing or reviewing README, docs/*, roadmap, story, or
  plan markdown for a human audience.
  Does NOT apply to AI-consumable files — SKILL.md, commands, agents,
  hooks, or CLAUDE.md — use ai-doc-quality for those.
model: haiku
version: 2.0.0
---

# Skill: human-doc-quality

## Scope

Enforces active voice, concision, and specificity in human-readable markdown. Applies to README, docs/*, roadmaps, story files, and plan files.

Does NOT apply to AI-consumable files (SKILL.md, commands, agents, hooks, CLAUDE.md) — those follow different rules enforced by `ai-doc-quality`.

## Output Format

Return a list of violations grouped by principle, each with:
- **line** (string): quoted sentence or phrase
- **issue** (string): principle violated
- **fix** (string): corrected version

Then output the full revised text with all fixes applied.

## Revision Rules

Fix style violations only. Do NOT invent missing content.

When a violation is vague language (e.g., "various changes"), the fix is a placeholder: `[describe specific changes]`. Do not supply technical details that aren't in the original. The author supplies substance; this skill supplies style.

## Style Principles

### 1. Active Voice

Use active voice. Passive constructions hide the actor and add words.

**Good:** "The team implemented the feature."
**Bad:** "The feature was implemented by the team."

**Common passive patterns to rewrite:**
- "X was done by Y" → "Y did X"
- "X is handled by" → "Y handles X"
- "X will be updated" → "Update X" (imperative) or "Y updates X"

### 2. Omit Needless Words

Remove phrases that add length without meaning.

| Wordy | Concise |
|-------|---------|
| in order to | to |
| due to the fact that | because |
| at this point in time | now |
| for the purpose of | for |
| in the event that | if |
| it is important to note that | (delete) |
| please be advised that | (delete) |

### 3. Specific Language

Replace vague quantifiers with numbers or observable facts.

**Good:** "Process 1000 requests per second."
**Bad:** "Process many requests quickly."

**Avoid:** many, few, some, several, soon, later, eventually, various, numerous

### 4. Direct Tone

State facts. Avoid hedging.

**Good:** "The bug is in the validation logic."
**Bad:** "It seems the bug might be in the validation logic."

**Avoid:** seems, appears, perhaps, might, could, possibly, I think, we believe

### 5. Imperative Mood for Instructions

Start instructions with action verbs.

**Good:** "Validate input before processing."
**Bad:** "The input should be validated before processing."

### 6. One Idea Per Sentence

Split compound sentences. Keep sentences under 20 words.

**Good:** "Validate input. Log errors. Return the result."
**Bad:** "The system validates input and logs errors and returns the result to the caller."

## Algorithm

**Quick reference:** `identify file type → scan each principle → collect violations → output violation list → output revised text`

### Step 1: Confirm Scope

If the file is a SKILL.md, command, agent, hook, or CLAUDE.md — stop and tell the user to use `ai-doc-quality` instead.

### Step 2: Scan for Violations

For each principle, scan the document and collect violations:

| Principle | Patterns to detect |
|-----------|--------------------|
| Active voice | "was/were/is/are/been + past participle + by" |
| Needless words | phrases from the needless-words table |
| Vague quantifiers | many, few, some, several, various, numerous, soon, later |
| Hedging | seems, appears, perhaps, might, could, possibly |
| Passive instructions | "should be [verb]ed", "must be [verb]ed" in imperative context |
| Run-on sentences | sentences > 20 words or with 3+ conjunctions |

### Step 3: Report and Revise

Output a grouped violation list. Then output the full revised document with all fixes applied inline.

## Failure Modes

| Condition | Recovery |
|-----------|----------|
| File is a SKILL.md or AI-consumable doc | Stop; redirect to `ai-doc-quality` |
| No violations found | Output "No violations found." — do not fabricate suggestions |
| Document is too large (>500 lines) | Process in sections; note which section was reviewed |

## Examples

### Example 1: Multi-Violation Paragraph

**Input:**
> "In order to complete the setup process, the configuration file should be edited by the user. It is important to note that many settings might need to be changed, and the process will take some time."

**Violations:**
- `"In order to"` → active voice / needless words: use "To"
- `"should be edited by the user"` → passive voice: "Edit the configuration file"
- `"It is important to note that"` → needless words: delete
- `"many settings"` → vague quantifier: specify count or say "all relevant settings"
- `"might need"` → hedging: "need"
- `"some time"` → vague quantifier: specify or say "a few minutes"

**Revised:**
> "To complete setup, edit the configuration file. All relevant settings need to be updated — allow 5 minutes."

---

### Example 2: Clean Document Passes

**Input:**
> "Run `make test` to execute the test suite. Fix any failures before opening a PR. The CI pipeline runs the same suite on every push."

**Output:**
No violations found.

---

### Example 3: Roadmap Story Cleanup

**Input:**
> "Story 14 is about improvements that will be made to the onboarding flow. Various enhancements are being considered and it seems like the work could be completed soon."

**Violations:**
- `"is about improvements that will be made"` → passive: "improves the onboarding flow"
- `"Various enhancements are being considered"` → passive + vague: use `[describe specific enhancements]` — do NOT invent details
- `"it seems like"` → hedging: delete
- `"could be completed soon"` → hedging + vague temporal: use `[target milestone]` or delete

**Revised:**
> "Story 14 improves the onboarding flow. [Describe specific enhancements.] Target: [milestone]."

Note: placeholders signal that the author needs to supply specifics — the revision fixes style, not content.

---
name: human-doc-quality
description: >
  Guide human-readable documentation with active voice, specific language, and concise sentences.
  Use when: writing or reviewing README, docs/*, roadmaps, or any human-facing markdown.
version: 1.1.0
---

# Human Documentation Quality

## Scope

These are defaults, not absolute rules. Apply judgment — a guideline that produces awkward prose in a specific context should yield to clarity.

## Style Principles

### 1. Active Voice

Default to active voice. Passive is appropriate when the agent is unknown, irrelevant, or when the result matters more than who did it.

**Good:** "The system validates input"
**Bad:** "Input is validated by the system" (agent known and relevant)
**OK passive:** "The token is hashed before storage" (process-focused; agent is implementation detail)

### 2. Omit Needless Words

Remove words that add no meaning.

**Good:** "To validate input"
**Bad:** "In order to validate the input"

**Common needless phrases:**
- "in order to" → "to"
- "due to the fact that" → "because"
- "at this point in time" → "now"
- "for the purpose of" → "for"
- "in the event that" → "if"

### 3. Specific Language

Use specific numbers, not vague quantifiers.

**Good:** "Process 1000 requests per second"
**Bad:** "Process many requests quickly"

**Avoid:** many, few, some, several, soon, later, eventually

### 4. Direct Tone

Avoid epistemic hedging — words that signal the writer is unsure of their own content. These undermine credibility.

**Bad (epistemic hedging):** "The system seems to validate input" / "It might possibly work"
**Avoid:** seems, appears, perhaps, possibly, maybe, sort of, kind of

Appropriate qualification is not hedging — it's accurate scope.
**OK:** "This typically takes 2–5 minutes" / "Most deployments use the default config"

### 5. Imperative Mood

Use imperative for instructions.

**Good:** "Validate the input"
**Bad:** "The input should be validated"

### 6. Concise Sentences

Keep sentences short. One idea per sentence.

**Good:** "Validate input. Log errors. Return result."
**Bad:** "The system validates input and logs errors and returns the result."

### 7. Front-Load Key Information

Lead with what matters most. Readers scan before they read — put the answer before the explanation.

**Good:** "This library parses JWT tokens. Install with `npm install jwt-parse`."
**Bad:** "This library was built to solve a common problem in modern web apps where authentication tokens need to be parsed..."

For READMEs: the first paragraph must answer what the project does and why someone would use it.

### 8. Structure for Scannability

Use headings, bullets, and short paragraphs. A reader looking for a specific answer should find it in under 10 seconds.

- Use H2/H3 headings to segment topics
- Use bullets for 3+ parallel items
- Keep paragraphs to 3–5 sentences max
- Use code blocks for any command or code snippet — never inline prose

### 9. Show, Don't Just Tell

A working example communicates more per token than any prose description. For any feature, command, or behavior, provide a concrete example.

**Bad:** "The library supports multiple output formats."
**Good:**
```
client.export({ format: 'csv' })  // → data.csv
client.export({ format: 'json' }) // → data.json
```

## Application

When generating human-readable markdown:
1. Default to active voice (passive is OK when agent is unknown or irrelevant)
2. Omit needless words
3. Use specific numbers
4. State directly — avoid epistemic hedging, not appropriate qualification
5. Use imperative for instructions
6. Keep sentences short, one idea per sentence
7. Front-load: answer first, context second
8. Structure for scannability with headings and bullets
9. Show examples for any feature or behavior

## Examples

### Example 1: Active Voice

**Bad:** "The feature was implemented by the team"
**Good:** "The team implemented the feature"

### Example 2: Omit Needless Words

**Bad:** "In order to complete the task, we need to implement the feature"
**Good:** "To complete the task, implement the feature"

### Example 3: Specific Language

**Bad:** "The system handles many requests quickly"
**Good:** "The system handles 1000 requests per second"

### Example 4: Direct Tone

**Bad:** "It seems the bug might be in the validation logic"
**Good:** "The bug is in the validation logic"

### Example 5: Imperative Mood

**Bad:** "The input should be validated before processing"
**Good:** "Validate input before processing"

### Example 6: Concise Sentences

**Bad:** "The system validates the input and checks for errors and logs any issues that are found and returns the validation result to the caller"
**Good:** "The system validates input, checks for errors, logs issues, and returns the result"

### Example 7: Front-Load

**Bad:** "Given the complexity of modern distributed systems and the need for reliable message delivery across unreliable networks, this library was created to..."
**Good:** "Reliable message queue for Node.js. Handles retries, backoff, and dead-letter queues out of the box."

### Example 8: Show, Don't Just Tell

**Bad:** "The CLI supports several output formats for different use cases."
**Good:**
```sh
$ mytool export --format csv   # outputs data.csv
$ mytool export --format json  # outputs data.json
$ mytool export --format table # pretty-prints to stdout
```

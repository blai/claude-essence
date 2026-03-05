---
name: ai-doc-principles
description: Rules for writing AI-consumable documentation. Use when: authoring or validating any AI-consumable doc.
version: 4.0
---

# AI Documentation Principles

## I. Core Principles

Make every requirement explicit, testable, and self-contained. Use one term per concept consistently. Never assume hidden context.

**Prioritize directives over explanations.** State WHAT to do and HOW to do it. Include rationale only when it helps the model make better decisions in ambiguous situations — not as general justification.

Make all dependencies, contexts, behaviors, and error cases explicit. Apply principles universally across all AI-consumable documentation. Maintain traceability through frontmatter versioning.

---

## II. Required Format

### A. YAML Frontmatter

Include YAML frontmatter in every AI-consumable document (between `---` delimiters):

```yaml
---
name: [document-name]
description: [One-sentence description with WHEN to use]
version: [Semantic version]
model: [haiku | sonnet]  # Optional
dependencies:  # Optional
  - type: [skill | document | subagent]
    name: [name]
    path: [path]  # For subagents
    version: [version]  # For skills/documents
---
```

**Required fields:** `name`, `description`

**Optional fields:** `version`, `model`, `dependencies`, `execution_order`

**Description conventions:**
- MUST include WHEN to use this skill/document
- MUST be specific with trigger conditions
- SHOULD be under 200 characters
- Use patterns: "PROACTIVELY", "Apply before", "Enforce during", "Retrieve", "Transform"

**Name conventions:**
- MUST use lowercase letters, numbers, hyphens only
- MUST NOT exceed 64 characters
- MUST NOT use reserved words: "anthropic", "claude"

**Unnecessary fields (tracked by git):** `author`, `created_date`, `modified_date`, `timezone`, `type`, `target_audience`, `scope`, `enforcement`, `trigger`, `phase`, `cacheable`

**Allowed exceptions:**
- `type: task_plan` - Used in task plan files to distinguish from other documents

### B. RFC 2119 Keywords

Use RFC 2119 keywords in requirement statements — sentences that prescribe behavior the system MUST or SHOULD enforce:

| Keyword | Meaning |
|---------|---------|
| MUST | Absolute requirement |
| MUST NOT | Absolute prohibition |
| SHOULD | Recommended with exceptions allowed |
| SHOULD NOT | Not recommended except for exceptions |
| MAY | Optional |

Use plain markdown. No special markup required.

Natural lowercase modal verbs (`should`, `can`, `may`) are acceptable in context, overview, and rationale prose — only requirement statements require uppercase RFC 2119.

**Requirement statement (use RFC 2119):**
```markdown
The authentication system MUST validate OAuth 2.0 tokens.
Invalid tokens MUST return HTTP 401.
```

**Context/rationale prose (lowercase is fine):**
```markdown
This step validates tokens because downstream services rely on authenticated requests.
```

**Incorrect (lowercase in a requirement statement):**
```markdown
The system should check tokens and might return errors.
```

### C. Imperative Mood

Use imperative mood. Start instructions with action verbs.

**Correct:** "Validate the input."

**Incorrect:** "The input should be validated."

---

## III. Language Rules

### A. No Vague Language

Avoid ambiguous elements:

**1. Ambiguous pronouns:** it, this, that (when referent is unclear)
- Use: "The callback function returns the response."
- Avoid: "It returns the response." (when "it" could refer to multiple things)
- Note: `they`/`them` are acceptable as singular inclusive pronouns or when referent is unambiguous.

**2. Vague verbs:** support, handle, process, manage
- Define algorithmically with specific steps

**3. Vague quantifiers:** several, many, few, some
- Use: "Process at least 1000 requests per second."
- Avoid: "Process many requests quickly."

**4. Vague temporal indicators:** soon, later, eventually, promptly
- Use: "Respond within 2 seconds."
- Avoid: "Respond soon."

**5. Modal verbs in requirement statements:** should, could, would, may, might, can
- In requirement statements: use RFC 2119 uppercase keywords instead
- In context, overview, and rationale prose: lowercase is acceptable

**6. Vague negatives:** Avoid requirements that prohibit a vague outcome without specifying the expected behavior.
- Use: "The system MUST return HTTP 200 on success."
- Avoid: "The system MUST NOT fail." (`fail` is undefined)
- Note: `MUST NOT` is valid RFC 2119 when the prohibited action is specific (e.g., "The system MUST NOT store plaintext passwords.").

### B. Action Verbs

Start instructions with action verbs: Generate, Validate, Extract, Return, Save, Process, Transform.

Do not use passive voice or conversational softeners ("Can you...", "I need...").

### C. Consistent Terminology

Use one term per concept. Define terms at first use. Do not vary terms for style.

### D. Quantification

Use specific numbers or ranges with explicit boundaries.

**Correct:** "Response time MUST be less than 2 seconds under load of 1000 concurrent users."

**Incorrect:** "Response time should be fast."

### E. Words to Avoid

Do not use: easy, easily, simple, simply, just, merely, only, obviously, clearly.

**Incorrect:** "Simply click the button."

**Correct:** "Select the button."

### F. Device-Agnostic Language

Use device-agnostic language:
- Use "Select" instead of "Click"
- Use "Choose" for decisions
- Avoid platform-specific terms unless documenting that platform

### G. Atomic Requirements

Make each requirement atomic. Do not combine multiple requirements with "and".

**Incorrect:**
```markdown
The system MUST validate input and log errors and send notifications.
```

**Correct:**
```markdown
The system MUST validate all input parameters.
The system MUST log all validation errors.
The system MUST send notifications for critical errors.
```

---

## IV. Examples

Examples MUST be sufficient to understand the requirement. Requirements vary by document type:

| Document Type | Examples Required | Notes |
|---------------|-------------------|-------|
| Simple atomic skill | 1-2 examples | Single input/output pattern (e.g., `detect-creation-intent`) |
| Complex atomic skill | 2-3 examples | Multiple cases or branches (e.g., `validate-task-size`: valid, error, edge) |
| Composite skill | 1 workflow example | Show skill invocation sequence (e.g., `planning-workflow`) |
| Command | 1-2 usage examples | Show command syntax with parameters (e.g., `/start-next-task --task="ET-1234"`) |
| Reference/Specification | Inline examples | Embed within explanations (correct vs incorrect patterns) |
| Standards (CLAUDE.md) | Optional | Principles and references are sufficient |

---

## V. Structure Requirements

### A. Self-Contained Sections

Make each section include sufficient context for independent understanding.

Avoid phrases like "as mentioned above" or "as discussed earlier."

**Correct:** "The authentication system validates OAuth 2.0 tokens. For token format specifications, see Section 4.2."

**Incorrect:** "The authentication system validates tokens as mentioned above."

### B. Explicit Dependencies

State dependencies upfront in frontmatter. Link related concepts explicitly with clear references.

### C. Procedures

Format step-by-step instructions:
1. Number steps sequentially
2. Start each step with an action verb
3. Include one action per step
4. Use device-agnostic language ("Select" not "Click")
5. Keep procedures to 7 or fewer steps

### D. Algorithm Structure with Execution Order

For skills with sequential algorithms:

**Frontmatter:**
```yaml
execution_order: sequential
```

**Algorithm header:**
```markdown
**Sequential execution:** Execute steps 1-N in order. Each step MUST complete before proceeding to next step.
```

**Blocking operations:**
```markdown
result = AWAIT invoke(workflow-name, param1, param2)
selection = AWAIT user_response
```

**Transitions:**
```markdown
Route to Step X
```

**Flowchart:** Include Mermaid diagram showing steps, decisions, branches.

---

## VI. Output Format

When the AI component produces structured output, specify the format explicitly.

Include:
- Output schema (field names, types, required vs optional)
- Example of a valid output
- What to return on failure or partial results

**Correct:**
```markdown
Return JSON: `{"valid": boolean, "violations": [{type, rule, line, suggestion, severity}], "reason": string | null}`
On parse failure, return `{"valid": false, "violations": [], "reason": "parse error: {message}"}`.
```

**Incorrect:**
```markdown
Return the validation result.
```

---

## VII. Token Budget

Minimize tokens without losing precision. Every sentence MUST justify its presence.

- Remove sections that restate the frontmatter description
- Remove rationale that does not change model behavior
- Prefer tables over prose lists when comparing 3+ items
- Prefer examples over explanatory paragraphs — a concrete example conveys more per token than abstract description

**Test:** Remove a sentence. If the model would behave identically without it, remove it permanently.

---

## IX. Testable Requirements

Every requirement MUST be: Complete, Correct, Feasible, Necessary, Prioritized, Unambiguous, Consistent, Traceable, Concise, and Verifiable.

---

## X. Common Errors to Avoid

### A. Requirements Without Behavior

**Incorrect:** "An XML file MUST be well-formed."

**Problem:** Cannot test - no outcome specified.

**Correct:** "The XML parser MUST reject malformed XML files and return error code ERR_MALFORMED_XML."

### B. Passive Voice Hiding Actor

**Incorrect:** "An invalid XML file must be ignored."

**Problem:** No actor specified.

**Correct:** "The parser MUST reject invalid XML files with error code 400."

### C. Under-Defined Behaviors

**Incorrect:** "The system MUST reject malformed XML."

**Problem:** "Reject" undefined algorithmically.

**Correct:** "The system MUST stop processing, return error code ERR_MALFORMED_XML, and display the error message defined in Section 4.2."

---

## XI. User Interaction Pattern

All user prompts MUST use multi-choice format:

```markdown
Prompt user - [Context]:
1. [Option A]
2. [Option B]
3. [Option C]

selection = AWAIT user_response
```

**Requirements:**
- Provide 2-4 options (hard limit of `AskUserQuestion` tool)
- Use imperative mood
- Include "Other" option for flexibility

**Prohibited:**
- Yes/No questions
- Informal questions ("Should we...", "Do you want...")
- Vague options

---

## XII. Sub-Agent, Skill, and Workflow Invocation Pattern

When AI components invoke other AI components (sub-agents, skills, workflows), use the unified `invoke` syntax.

### A. Unified Invocation

Use `invoke` for both workflows and sub-agents. The system resolves the target using the `dependencies` map in frontmatter.

**Correct:**
```
result = invoke(classify-task-input, input=${input})
```

**Incorrect (Deprecated):**
```
result = Task(
  prompt: READ("sub-agents/classify-task-input/prompt.md") + |
    INPUT: ${input}
)
```

### B. Dependency Declaration

All invoked sub-agents MUST be declared in the `dependencies` section of the frontmatter.

```yaml
dependencies:
  - type: subagent
    name: classify-task-input
    path: sub-agents/classify-task-input
```

### C. Model Configuration

Sub-agents declare their optimal model in their own frontmatter. The `invoke` command automatically respects this configuration.

**Sub-agent declares model:**
```yaml
---
name: classify-task-input
model: haiku
---
```

**Benefits:**
- **Consistency:** Same syntax for workflows and sub-agents
- **Abstraction:** Hides file paths and implementation details
- **Maintainability:** Dependencies managed in one place (frontmatter)
- **Token optimization:** Preserves Haiku/Sonnet selection defined in sub-agent

---

## XIII. Three Forms of Technical Terms

Express every technical term as Algorithm, Definition, or Statement of Fact.

**Algorithm:** Step-by-step process with explicit ordering
```
To ignore an element: 1) Stop processing 2) Ignore attributes/children 3) Record attempt 4) Proceed to next
```

**Definition:** Explicit meaning of a concept
```
Parser: Implementation that processes XML per XML 1.0 spec and validates structure per schemas
```

**Statement of Fact:** Observable truth about the system
```
Keep record of all element types attempted, even if ignored, to determine if already processed
```


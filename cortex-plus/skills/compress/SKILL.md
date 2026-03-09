---
name: compress
description: >
  This skill should be used when the user wants to "compress text",
  "deduplicate memories", "reduce token usage", "shrink a file before
  passing to an LLM", "remove near-duplicates", "apply lossless compression",
  "run the compression pipeline", or needs to pre-process a large list of
  text items before an LLM call. Use proactively before any bulk LLM
  processing step to reduce cost and noise.
version: 0.1.0
dependencies:
  - type: script
    path: ${CLAUDE_PLUGIN_ROOT}/scripts/compress.py
---

## What this skill does

Deterministic, no-LLM compression pipeline for lists of text items.
All operations are lossless except near-duplicate removal (keeps the
longer/more-specific item).

**Pipeline layers (applied in order):**

| Layer | Operation | Typical savings |
|---|---|---|
| L1 | Strip ANSI escape codes + emoji | varies |
| L2 | Markdown filler removal (blank consolidation, empty sections, duplicate lines) | 4–8% |
| L3 | Exact deduplication (MD5 hash) | varies |
| L4 | Near-duplicate removal (shingle hash + Jaccard ≥ 0.6) | varies |
| L5 | Dictionary encoding (path prefixes + repeated n-grams → `$XX` tokens) | 4–5% |

## Invocation

Input/output: JSON array of strings (default) or newline-delimited lines.

```bash
# Compress a JSON array
echo '["item1","item2",...]' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compress.py --stats

# Compress a file, write output + codebook
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compress.py \
  --input items.json --output compressed.json \
  --codebook codebook.json --stats

# Newline-delimited input
cat memories.txt | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compress.py --format lines

# Decompress (requires codebook)
# Load codebook.json and call compress.decompress(items, codebook) in Python
```

**Key options:**
- `--similarity <float>` — Jaccard threshold for near-dup (default: 0.6, range 0–1)
- `--shingle-size <int>` — N-gram size for shingles (default: 3)
- `--no-dedup` / `--no-neardup` / `--no-dict` / `--no-markdown` — disable layers
- `--stats` — print item count + char count reduction to stderr
- `--codebook <path>` — save dictionary for later decompression

## Integration with distill-cortex

`distill.py` calls `compress.py` as a Python import before sending sessions
to Haiku. To use compress.py as a library:

```python
from scripts.compress import compress, decompress, stats

items = ["raw memory 1", "raw memory 2", ...]
compressed, codebook = compress(items, similarity=0.6)
print(stats(items, compressed), file=sys.stderr)
# Pass compressed to Haiku; decompress with codebook if needed
```

## Failure modes

- **Empty output**: all items were noise or duplicates — check `--stats` to confirm
- **No dict savings**: fewer than 10 items or no repeated phrases — L5 skips automatically
- **Near-dup threshold too aggressive**: lower `--similarity` (e.g., 0.4) to keep more items

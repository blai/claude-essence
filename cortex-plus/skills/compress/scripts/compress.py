#!/usr/bin/env python3
"""
Deterministic text compressor — no LLM required.

Applies a layered pipeline to a list of text items:
  L1  Strip ANSI escape codes
  L2  Markdown filler removal (blank consolidation, empty sections, duplicate lines)
  L3  Exact deduplication (content hash)
  L4  Near-duplicate removal (shingle hash + Jaccard similarity)
  L5  Dictionary encoding (path prefixes + repeated n-grams → $XX tokens)

Usage:
  # JSON array in, JSON array out
  echo '["line1","line2"]' | python3 compress.py
  cat items.json | python3 compress.py --stats

  # Newline-delimited in, newline-delimited out
  cat items.txt | python3 compress.py --format lines

  # Write codebook alongside output (for decompression)
  python3 compress.py --input items.json --output out.json --codebook codebook.json

  # Tune thresholds
  python3 compress.py --similarity 0.7 --shingle-size 3

Options:
  --format json|lines   Input/output format (default: json)
  --input <path>        Read from file instead of stdin
  --output <path>       Write to file instead of stdout
  --codebook <path>     Write dictionary codebook to file (enables decompression)
  --similarity <float>  Jaccard threshold for near-dup removal (default: 0.6)
  --shingle-size <int>  N-gram size for shingles (default: 3)
  --no-dedup            Skip exact deduplication
  --no-neardup          Skip near-duplicate removal
  --no-dict             Skip dictionary encoding
  --no-markdown         Skip markdown filler removal
  --stats               Print compression stats to stderr
"""

import sys, re, json, hashlib, argparse
from collections import Counter
from itertools import combinations
from pathlib import Path

# ---------------------------------------------------------------------------
# L1 — ANSI stripping
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
_EMOJI_RE = re.compile(
    r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
    r'\U0001F1E6-\U0001F1FF\u2702-\u27B0\u2654-\u265F\U0001F900-\U0001F9FF]'
)

def strip_ansi(text: str) -> str:
    text = _ANSI_RE.sub('', text)
    text = _EMOJI_RE.sub('', text)
    return text

# ---------------------------------------------------------------------------
# L2 — Markdown filler removal
# ---------------------------------------------------------------------------

_BLANK3_RE  = re.compile(r'\n{3,}')
_HR_RE      = re.compile(r'^[\-\*_]{3,}\s*$', re.MULTILINE)
_EMPTY_H_RE = re.compile(r'^#{1,6}\s*$', re.MULTILINE)

def clean_markdown(text: str) -> str:
    # Trailing whitespace per line
    lines = [l.rstrip() for l in text.splitlines()]
    # Remove exact duplicate non-blank lines (preserve order, keep first)
    seen = set()
    deduped = []
    for line in lines:
        key = line.strip()
        if not key or key not in seen:
            deduped.append(line)
            if key:
                seen.add(key)
    text = '\n'.join(deduped)
    # Consolidate 3+ blank lines → 2
    text = _BLANK3_RE.sub('\n\n', text)
    # Remove bare horizontal rules
    text = _HR_RE.sub('', text)
    # Remove empty headers
    text = _EMPTY_H_RE.sub('', text)
    return text.strip()

# ---------------------------------------------------------------------------
# L3 — Exact deduplication
# ---------------------------------------------------------------------------

def exact_dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for item in items:
        h = hashlib.md5(item.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            out.append(item)
    return out

# ---------------------------------------------------------------------------
# L4 — Near-duplicate removal (shingle hash + Jaccard)
# ---------------------------------------------------------------------------

def _shingles(text: str, k: int = 3) -> set[int]:
    words = text.lower().split()
    if len(words) < k:
        return {hash(text.lower())}
    return {hash(' '.join(words[i:i+k])) for i in range(len(words) - k + 1)}

def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def near_dedup(items: list[str], threshold: float = 0.6, k: int = 3) -> list[str]:
    if len(items) <= 1:
        return items

    shingle_sets = [_shingles(item, k) for item in items]
    # Mark indices to drop (keep the longer item in each near-dup pair)
    drop: set[int] = set()

    for i in range(len(items)):
        if i in drop:
            continue
        for j in range(i + 1, len(items)):
            if j in drop:
                continue
            sim = _jaccard(shingle_sets[i], shingle_sets[j])
            if sim >= threshold:
                # Drop shorter; ties → drop later one
                if len(items[i]) >= len(items[j]):
                    drop.add(j)
                else:
                    drop.add(i)
                    break  # i is dropped, move to next i

    return [item for idx, item in enumerate(items) if idx not in drop]

# ---------------------------------------------------------------------------
# L5 — Dictionary encoding
# ---------------------------------------------------------------------------

def _gen_codes():
    """Yield $AA … $ZZ, then $AAA … $ZZZ."""
    import string
    alpha = string.ascii_uppercase
    for a in alpha:
        for b in alpha:
            yield f'${a}{b}'
    for a in alpha:
        for b in alpha:
            for c in alpha:
                yield f'${a}{b}{c}'

def _extract_path_prefixes(items: list[str]) -> list[tuple[str, int]]:
    """Find repeated filesystem path prefixes (min 3 occurrences)."""
    path_re = re.compile(r'(/(?:[A-Za-z0-9_.\-~][A-Za-z0-9_.\-~/ ]*)+)')
    prefix_count: Counter = Counter()
    for item in items:
        for m in path_re.finditer(item):
            p = Path(m.group(1))
            # Add parent paths as candidates
            parts = p.parts
            for depth in range(2, len(parts) + 1):
                prefix = str(Path(*parts[:depth]))
                if len(prefix) >= 8:
                    prefix_count[prefix] += 1
    return [(p, c) for p, c in prefix_count.items() if c >= 3]

def _extract_ngrams(items: list[str], min_freq: int = 3, min_len: int = 8) -> list[tuple[str, int]]:
    """Find repeated 2–4 word phrases."""
    counts: Counter = Counter()
    for item in items:
        words = item.split()
        for n in (2, 3, 4):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                if len(phrase) >= min_len:
                    counts[phrase] += 1
    return [(p, c) for p, c in counts.items() if c >= min_freq]

def build_codebook(items: list[str], max_entries: int = 200) -> dict[str, str]:
    """Build {$XX: phrase} codebook ranked by savings potential."""
    candidates = _extract_path_prefixes(items) + _extract_ngrams(items)
    # Sort by savings potential: frequency × phrase_length
    candidates.sort(key=lambda x: x[1] * len(x[0]), reverse=True)

    codebook: dict[str, str] = {}  # {code: phrase}
    used_phrases: set[str] = set()
    code_gen = _gen_codes()

    for phrase, freq in candidates:
        if len(codebook) >= max_entries:
            break
        if phrase in used_phrases:
            continue
        # Only encode if savings > code overhead (3 chars for $XX)
        if freq * (len(phrase) - 3) <= 0:
            continue
        code = next(code_gen)
        codebook[code] = phrase
        used_phrases.add(phrase)

    return codebook

def dict_encode(items: list[str], codebook: dict[str, str]) -> list[str]:
    """Replace phrases with codes. Sort by phrase length to avoid partial matches."""
    if not codebook:
        return items
    # Build replacement map: phrase → code (sorted longest first)
    replacements = sorted(((phrase, code) for code, phrase in codebook.items()),
                          key=lambda x: len(x[0]), reverse=True)
    encoded = []
    for item in items:
        # Escape pre-existing $ to sentinel
        s = item.replace('$', '\x00DOLLAR\x00')
        for phrase, code in replacements:
            s = s.replace(phrase, code)
        encoded.append(s)
    return encoded

def dict_decode(items: list[str], codebook: dict[str, str]) -> list[str]:
    """Reverse dictionary encoding."""
    decoded = []
    for item in items:
        s = item
        for code, phrase in codebook.items():
            s = s.replace(code, phrase)
        s = s.replace('\x00DOLLAR\x00', '$')
        decoded.append(s)
    return decoded

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def compress(
    items: list[str],
    similarity: float = 0.6,
    shingle_size: int = 3,
    do_dedup: bool = True,
    do_neardup: bool = True,
    do_dict: bool = True,
    do_markdown: bool = True,
) -> tuple[list[str], dict[str, str]]:
    """
    Full compression pipeline. Returns (compressed_items, codebook).
    codebook is empty if do_dict=False.
    """
    # L1: strip ANSI from all items
    items = [strip_ansi(item) for item in items]

    # L2: markdown filler
    if do_markdown:
        items = [clean_markdown(item) for item in items]

    # Remove items that became empty after cleaning
    items = [item for item in items if item.strip()]

    # L3: exact dedup
    if do_dedup:
        items = exact_dedup(items)

    # L4: near-dup
    if do_neardup:
        items = near_dedup(items, threshold=similarity, k=shingle_size)

    # L5: dictionary encoding
    codebook: dict[str, str] = {}
    if do_dict and len(items) > 10:  # not worth it for tiny inputs
        codebook = build_codebook(items)
        items = dict_encode(items, codebook)

    return items, codebook

def decompress(items: list[str], codebook: dict[str, str]) -> list[str]:
    return dict_decode(items, codebook)

# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def stats(original: list[str], compressed: list[str], label: str = "") -> str:
    orig_chars  = sum(len(s) for s in original)
    comp_chars  = sum(len(s) for s in compressed)
    orig_count  = len(original)
    comp_count  = len(compressed)
    pct_chars   = 100 * (1 - comp_chars  / orig_chars)  if orig_chars  else 0
    pct_items   = 100 * (1 - comp_count / orig_count) if orig_count else 0
    hdr = f"[compress{' ' + label if label else ''}]"
    return (
        f"{hdr} items: {orig_count} → {comp_count} ({pct_items:.1f}% reduction) | "
        f"chars: {orig_chars:,} → {comp_chars:,} ({pct_chars:.1f}% reduction)"
    )

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Deterministic text compressor")
    p.add_argument('--format',       choices=['json', 'lines'], default='json')
    p.add_argument('--input',        help='Input file (default: stdin)')
    p.add_argument('--output',       help='Output file (default: stdout)')
    p.add_argument('--codebook',     help='Write codebook JSON to file')
    p.add_argument('--similarity',   type=float, default=0.6)
    p.add_argument('--shingle-size', type=int,   default=3)
    p.add_argument('--no-dedup',     action='store_true')
    p.add_argument('--no-neardup',   action='store_true')
    p.add_argument('--no-dict',      action='store_true')
    p.add_argument('--no-markdown',  action='store_true')
    p.add_argument('--stats',        action='store_true')
    args = p.parse_args()

    # Read
    src = open(args.input) if args.input else sys.stdin
    raw = src.read()
    if args.input:
        src.close()

    if args.format == 'json':
        items = json.loads(raw)
    else:
        items = [line for line in raw.splitlines() if line.strip()]

    original = list(items)

    # Compress
    compressed, codebook = compress(
        items,
        similarity   = args.similarity,
        shingle_size = args.shingle_size,
        do_dedup     = not args.no_dedup,
        do_neardup   = not args.no_neardup,
        do_dict      = not args.no_dict,
        do_markdown  = not args.no_markdown,
    )

    # Write output
    if args.format == 'json':
        out_text = json.dumps(compressed, ensure_ascii=False, indent=2)
    else:
        out_text = '\n'.join(compressed)

    dst = open(args.output, 'w') if args.output else sys.stdout
    dst.write(out_text)
    if not args.output:
        dst.write('\n')
    else:
        dst.close()

    # Write codebook
    if args.codebook and codebook:
        with open(args.codebook, 'w') as f:
            json.dump(codebook, f, indent=2)

    # Stats
    if args.stats:
        print(stats(original, compressed), file=sys.stderr)
        if codebook:
            print(f"[compress] codebook: {len(codebook)} entries", file=sys.stderr)

if __name__ == '__main__':
    main()

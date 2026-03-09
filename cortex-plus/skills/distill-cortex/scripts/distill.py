#!/usr/bin/env python3
"""
cortex-distiller — STM → LTM distillation script.

Reads STM fragments from Cortex SQLite, distills per session via Haiku,
writes LTM back to Cortex via MCP (cortex_remember), then prunes STM.

Usage:
  distill.py                        # distill all projects + global, then prune STM
  distill.py --keep-stm             # distill but do NOT delete STM after
  distill.py --project <id>         # distill one project (+ prune that project's STM)
  distill.py --global               # synthesize _ltm-global from all per-project LTMs
  distill.py --dry-run              # print LTM without storing or pruning
  distill.py --project TC --dry-run
  distill.py --prune-distilled      # delete STM for projects that already have LTM (no distillation)
  distill.py --purge-old            # delete STM fragments older than 90 days
"""

import sqlite3, subprocess, json, re, os, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

# Import compress pipeline (sibling skill)
_COMPRESS_SCRIPT = Path(__file__).parent.parent.parent / "compress" / "scripts" / "compress.py"
if _COMPRESS_SCRIPT.exists():
    import importlib.util
    try:
        _spec = importlib.util.spec_from_file_location("compress", _COMPRESS_SCRIPT)
        _compress_mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_compress_mod)
        _compress  = _compress_mod.compress
        _comp_stats = _compress_mod.stats
    except Exception as e:
        print(f"[warn] compress module not loaded: {e}", file=sys.stderr)
        _compress = None
else:
    _compress = None

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH          = Path.home() / ".cortex" / "memory.db"
HAIKU_MODEL      = "claude-haiku-4-5-20251001"
LTM_SCORE        = "[LTM:1.00]"
LTM_PREFIX       = "_ltm-"
LTM_GLOBAL       = "_ltm-global"
LTM_TIME_PRJ     = "_ltm___time"
DECAY_RATE       = 0.9          # per month
DECAY_MIN        = 0.10
CONTENT_CAP      = 400          # chars per memory before sending to Haiku
SESSION_CHUNK    = 400          # max memories per single Haiku call
MERGE_BATCH      = 8            # summaries per merge batch
SUMMARY_CAP      = 800          # chars per summary in merge step
LTM_CAP          = 600          # chars per LTM fragment in global synthesis

# Projects to always skip (LTM buckets + meta)
SKIP_PROJECTS    = {"_ltm-global", "_ltm___time"}

CORTEX_MCP_JS    = Path.home() / ".claude/plugins/cache/cortex/cortex/2.1.3/dist/mcp-server.js"

# Set in main() — if active Claude sessions are running, only process STM before this time.
_CUTOFF: datetime | None = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(t: str) -> str:
    return ANSI_RE.sub('', t)

NOISE_RE = re.compile(
    r'local-command-stdout|local-command-stderr|Context Usage|⛁|⛀|⛶',
    re.MULTILINE
)

def is_noise(t: str) -> bool:
    return bool(NOISE_RE.search(strip_ansi(t)[:300]))

def clean(t: str) -> str:
    return strip_ansi(t).strip()[:CONTENT_CAP]

_ENV = {k: v for k, v in os.environ.items() if k not in ('CLAUDECODE', 'ANTHROPIC_API_KEY')}

def call_haiku(prompt: str, timeout: int = 300) -> str:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(prompt)
        tmp = f.name
    try:
        r = subprocess.run(
            f'claude -p --model {HAIKU_MODEL} < {tmp}',
            shell=True, capture_output=True, text=True, timeout=timeout, env=_ENV
        )
        if r.returncode != 0:
            raise RuntimeError(f"Haiku error (exit {r.returncode}): {r.stderr[:300]}")
        return r.stdout.strip()
    finally:
        os.unlink(tmp)

# ---------------------------------------------------------------------------
# SQLite reads
# ---------------------------------------------------------------------------

def list_projects() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT project_id FROM memories WHERE project_id IS NOT NULL")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return [p for p in rows if not p.startswith('_ltm-') and p not in SKIP_PROJECTS]

def read_sessions(project_id: str) -> dict[str, list]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if _CUTOFF:
        cutoff_iso = _CUTOFF.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        cur.execute("""
            SELECT id, content, timestamp, source_session FROM memories
            WHERE project_id = ? AND content NOT LIKE '[LTM:%'
              AND datetime(timestamp) < datetime(?)
            ORDER BY timestamp ASC
        """, (project_id, cutoff_iso))
    else:
        cur.execute("""
            SELECT id, content, timestamp, source_session FROM memories
            WHERE project_id = ? AND content NOT LIKE '[LTM:%'
            ORDER BY timestamp ASC
        """, (project_id,))
    rows = cur.fetchall()
    conn.close()
    sessions: dict[str, list] = {}
    for id_, content, ts, sess in rows:
        sessions.setdefault(sess, []).append((id_, content, ts))
    return sessions

def read_ltm(project_id: str) -> list[tuple]:
    ltm_proj = LTM_PREFIX + project_id
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, content, timestamp FROM memories
        WHERE project_id = ? ORDER BY timestamp ASC
    """, (ltm_proj,))
    rows = cur.fetchall()
    conn.close()
    return rows

def read_ltm_timestamp() -> str | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT content FROM memories WHERE project_id = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (LTM_TIME_PRJ,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row[0]).get("lastDistilledAt")
    except Exception:
        return None

def read_all_ltms() -> dict[str, list[str]]:
    """Return {project_id: [content, ...]} for all _ltm-* projects (excl global/time)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT project_id, content FROM memories
        WHERE project_id LIKE '_ltm-%'
          AND project_id != '_ltm-global'
          AND project_id != '_ltm___time'
        ORDER BY project_id, timestamp ASC
    """)
    rows = cur.fetchall()
    conn.close()
    result: dict[str, list[str]] = {}
    for proj, content in rows:
        result.setdefault(proj, []).append(content)
    return result

# ---------------------------------------------------------------------------
# STM deletion
# ---------------------------------------------------------------------------

def count_ltm_fragments(project_id: str) -> int:
    ltm_proj = LTM_PREFIX + project_id
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM memories WHERE project_id = ?", (ltm_proj,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def _get_active_session_cutoff() -> datetime | None:
    """Find the earliest start time of any running 'claude' process.

    Returns a UTC datetime — only process/delete STM fragments before this time.
    Returns None if no active Claude sessions found (safe to process everything).
    """
    try:
        r = subprocess.run(
            ['pgrep', '-x', 'claude'],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        pids = [p.strip() for p in r.stdout.strip().splitlines() if p.strip()]
        local_tz = datetime.now().astimezone().tzinfo
        cutoff = None
        for pid in pids:
            r2 = subprocess.run(
                ['ps', '-p', pid, '-o', 'lstart='],
                capture_output=True, text=True, timeout=5
            )
            if r2.returncode != 0:
                continue
            date_str = r2.stdout.strip()
            if not date_str:
                continue
            try:
                # macOS lstart format: "Mon Mar  9 10:30:00 2026"
                dt_local = datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y')
                dt_utc = dt_local.replace(tzinfo=local_tz).astimezone(timezone.utc)
                if cutoff is None or dt_utc < cutoff:
                    cutoff = dt_utc
            except ValueError:
                pass
        return cutoff
    except Exception:
        return None

def delete_stm(project_id: str) -> int:
    """Hard-delete STM fragments for a project. Respects _CUTOFF if set."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if _CUTOFF:
        cutoff_iso = _CUTOFF.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        cur.execute(
            "DELETE FROM memories WHERE project_id = ? AND content NOT LIKE '[LTM:%'"
            " AND datetime(timestamp) < datetime(?)",
            (project_id, cutoff_iso)
        )
    else:
        cur.execute(
            "DELETE FROM memories WHERE project_id = ? AND content NOT LIKE '[LTM:%'",
            (project_id,)
        )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted

def prune_distilled_stm() -> dict[str, int]:
    """Delete STM fragments for any project that has LTM (already distilled).
    If _CUTOFF is set, skips fragments from active sessions."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Find projects that have LTM
    cur.execute("""
        SELECT DISTINCT SUBSTR(project_id, LENGTH(?) + 1)
        FROM memories WHERE project_id LIKE ?
    """, (LTM_PREFIX, LTM_PREFIX + '%'))
    distilled_projects = [r[0] for r in cur.fetchall()
                          if r[0] and r[0] not in ('global', '__time')]
    result: dict[str, int] = {}
    for proj in distilled_projects:
        params: list = [proj]
        extra = ""
        if _CUTOFF:
            cutoff_iso = _CUTOFF.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            extra = " AND datetime(timestamp) < datetime(?)"
            params.append(cutoff_iso)
        cur.execute(f"""
            SELECT COUNT(*) FROM memories
            WHERE project_id = ? AND content NOT LIKE '[LTM:%'{extra}
        """, params)
        count = cur.fetchone()[0]
        if count:
            cur.execute(f"""
                DELETE FROM memories
                WHERE project_id = ? AND content NOT LIKE '[LTM:%'{extra}
            """, params)
            result[proj] = count
    conn.commit()
    conn.close()
    return result


def delete_old_stm(days: int = 90) -> dict[str, int]:
    """Delete STM fragments older than `days` days across all non-LTM projects.
    If _CUTOFF is set, also skips fragments from active sessions (AND condition)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    params: list = [f"-{days} days"]
    extra = ""
    if _CUTOFF:
        cutoff_iso = _CUTOFF.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        extra = " AND datetime(timestamp) < datetime(?)"
        params.append(cutoff_iso)
    cur.execute(f"""
        SELECT project_id, COUNT(*) FROM memories
        WHERE project_id NOT LIKE '_ltm-%'
          AND datetime(timestamp) < datetime('now', ?){extra}
        GROUP BY project_id
    """, params)
    to_delete = dict(cur.fetchall())
    if to_delete:
        cur.execute(f"""
            DELETE FROM memories
            WHERE project_id NOT LIKE '_ltm-%'
              AND datetime(timestamp) < datetime('now', ?){extra}
        """, params)
        conn.commit()
    conn.close()
    return to_delete

# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------

def apply_decay(ltm_rows: list[tuple], last_distilled_at: str | None) -> list[tuple]:
    if not last_distilled_at:
        return [(c, 1.0) for _, c, _ in ltm_rows]
    last_dt = datetime.fromisoformat(last_distilled_at.replace('Z', '+00:00'))
    months = (datetime.now(timezone.utc) - last_dt).days / 30.0
    factor = DECAY_RATE ** months
    result = []
    for _, content, _ in ltm_rows:
        m = re.match(r'^\[LTM:([\d.]+)\]', content)
        if m:
            new_score = round(float(m.group(1)) * factor, 3)
            if new_score < DECAY_MIN:
                continue
            content = re.sub(r'^\[LTM:[\d.]+\]', f'[LTM:{new_score}]', content)
        result.append((content, float(m.group(1)) if m else 1.0))
    return result

# ---------------------------------------------------------------------------
# Distillation
# ---------------------------------------------------------------------------

def _summarize_chunk(lines: list[str], project_id: str, label: str = "") -> str | None:
    if not lines:
        return None
    body = "\n---\n".join(lines)
    prompt = f"""Distill these Claude Code session memories for project "{project_id}" into durable knowledge.{label}

Extract only what's worth remembering long-term:
- Technical decisions and their rationale
- User preferences and workflow patterns
- Architecture conventions and key file paths
- Recurring patterns, principles, lessons learned
- Important domain facts

Ignore: terminal output, raw tool scaffolding, transient status, duplicates.

Format: concise bullet points under bold theme headers (**Theme**).
Be specific: model names, file paths, version numbers, exact names.
If nothing is durable, respond exactly: NOTHING_DURABLE

MEMORIES:
{body}

DURABLE KNOWLEDGE:"""
    out = call_haiku(prompt)
    return None if out.strip() == "NOTHING_DURABLE" else out

def summarize_session(memories: list[tuple], project_id: str, session_id: str) -> str | None:
    raw_lines = [
        f"[{ts[:10]}] {clean(content)}"
        for _, content, ts in memories
        if not is_noise(clean(content)) and clean(content)
    ]

    # Pre-compress with deterministic pipeline before sending to Haiku
    if _compress and raw_lines:
        compressed, _ = _compress(raw_lines, similarity=0.6)
        if len(compressed) < len(raw_lines):
            dropped = len(raw_lines) - len(compressed)
            print(f" [compress: {len(raw_lines)}→{len(compressed)} items, -{dropped} dups]", end="", flush=True)
        lines = compressed
    else:
        lines = raw_lines
    if not lines:
        return None
    if len(lines) <= SESSION_CHUNK:
        return _summarize_chunk(lines, project_id)
    # Oversized session: chunk → intermediates → merge
    parts = [lines[i:i+SESSION_CHUNK] for i in range(0, len(lines), SESSION_CHUNK)]
    intermediates = [
        s for i, part in enumerate(parts)
        if (s := _summarize_chunk(part, project_id, f" (part {i+1}/{len(parts)})"))
    ]
    if not intermediates:
        return None
    if len(intermediates) == 1:
        return intermediates[0]
    body = "\n\n--- PART ---\n".join(intermediates)
    return call_haiku(f"Merge these partial summaries into one set of bullet points under bold headers. Deduplicate.\n\n{body}\n\nMERGED:")

def _merge_batch(summaries: list[str], project_id: str, note: str = "") -> str:
    parts = "\n\n--- SUMMARY ---\n".join(s[:SUMMARY_CAP] for s in summaries)
    prompt = f"""Build long-term memory for Claude Code project "{project_id}".{note}

Synthesize these session summaries into durable knowledge fragments.
Each fragment: bold theme header + 2–8 specific bullets.
Deduplicate; keep most specific version of overlapping facts.
Output ONLY fragments separated by "---".

SUMMARIES:
{parts}

LTM FRAGMENTS:"""
    return call_haiku(prompt, timeout=360)

def merge_summaries(summaries: list[str], surviving_ltm: list[tuple], project_id: str) -> str:
    n = len(summaries)
    batches = [summaries[i:i+MERGE_BATCH] for i in range(0, n, MERGE_BATCH)]
    print(f"  (hierarchical merge: {n} summaries → {len(batches)} batches)")
    intermediates = []
    for i, batch in enumerate(batches):
        print(f"  batch {i+1}/{len(batches)}...", end=" ", flush=True)
        intermediates.append(_merge_batch(batch, project_id, f" (batch {i+1}/{len(batches)})"))
        print("✓")
    while len(intermediates) > 1:
        print(f"  reducing {len(intermediates)} intermediates...", end=" ", flush=True)
        next_lvl = [
            _merge_batch(intermediates[i:i+MERGE_BATCH], project_id, " (reduction)")
            for i in range(0, len(intermediates), MERGE_BATCH)
        ]
        intermediates = next_lvl
        print("✓")
    combined = intermediates[0]
    if not surviving_ltm:
        return combined
    existing = "\n".join(c for c, _ in surviving_ltm[:60])[:3000]
    return call_haiku(
        f"""Merge existing LTM with new distilled knowledge for project "{project_id}".
Supersede outdated facts, deduplicate, keep specifics.
Output fragments separated by "---", each starting with **Bold Header**.

EXISTING LTM:
{existing}

NEW KNOWLEDGE:
{combined[:3000]}

FINAL LTM:""",
        timeout=360
    )

def parse_fragments(text: str) -> list[str]:
    return [f.strip() for f in text.split('---') if f.strip()]

# ---------------------------------------------------------------------------
# Cortex MCP store
# ---------------------------------------------------------------------------

def _mcp_cfg_path() -> str:
    cfg = {"mcpServers": {"cortex": {"command": "node", "args": [str(CORTEX_MCP_JS)]}}}
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(cfg, f); f.close()
    return f.name

def _remember(content: str, project_id: str, mcp_path: str) -> bool:
    prompt = (
        f"Call the cortex_remember tool with these arguments:\n"
        f"- content: {json.dumps(content)}\n"
        f"- projectId: {json.dumps(project_id)}\n"
        f"Do nothing else."
    )
    r = subprocess.run(
        f'claude -p --mcp-config {mcp_path} --dangerously-skip-permissions < /dev/stdin',
        input=prompt, shell=True, capture_output=True, text=True, timeout=60, env=_ENV
    )
    return r.returncode == 0

def store_ltm(fragments: list[str], project_id: str):
    ltm_proj = LTM_PREFIX + project_id
    mcp = _mcp_cfg_path()
    try:
        print(f"▸ Storing to '{ltm_proj}'...")
        ok = fail = 0
        for i, frag in enumerate(fragments):
            print(f"  [{i+1}/{len(fragments)}]", end=" ", flush=True)
            if _remember(f"{LTM_SCORE} {frag}", ltm_proj, mcp):
                print("✓"); ok += 1
            else:
                print("✗"); fail += 1
        print(f"  {ok} stored, {fail} failed")
    finally:
        os.unlink(mcp)

def update_timestamp():
    mcp = _mcp_cfg_path()
    try:
        ts = json.dumps({"lastDistilledAt": datetime.now(timezone.utc).isoformat()})
        print(f"▸ Updating _ltm___time...", end=" ", flush=True)
        ok = _remember(ts, LTM_TIME_PRJ, mcp)
        print("✓" if ok else "✗")
    finally:
        os.unlink(mcp)

# ---------------------------------------------------------------------------
# Global LTM synthesis
# ---------------------------------------------------------------------------

def distill_global(dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"  GLOBAL LTM SYNTHESIS")
    print(f"{'='*60}\n")
    all_ltms = read_all_ltms()
    if not all_ltms:
        print("No per-project LTMs found. Run per-project distillation first.")
        return
    print(f"▸ Collecting LTMs from {len(all_ltms)} projects...")
    # Treat each project's LTM as one "summary" for the global merge
    summaries = []
    for proj, contents in all_ltms.items():
        combined = "\n".join(c[:LTM_CAP] for c in contents[:20])
        summaries.append(f"[{proj}]\n{combined}")
    print(f"▸ Synthesizing global LTM from {len(summaries)} project LTMs via Haiku...")
    merged = _merge_batch(summaries, "global", " (global synthesis)")
    fragments = parse_fragments(merged)
    print(f"  → {len(fragments)} global LTM fragments\n")
    for i, frag in enumerate(fragments):
        print(f"[{i+1}]\n{frag}\n")
    if not dry_run:
        mcp = _mcp_cfg_path()
        try:
            print(f"▸ Storing to '{LTM_GLOBAL}'...")
            ok = fail = 0
            for i, frag in enumerate(fragments):
                print(f"  [{i+1}/{len(fragments)}]", end=" ", flush=True)
                if _remember(f"{LTM_SCORE} {frag}", LTM_GLOBAL, mcp):
                    print("✓"); ok += 1
                else:
                    print("✗"); fail += 1
            print(f"  {ok} stored, {fail} failed")
        finally:
            os.unlink(mcp)

# ---------------------------------------------------------------------------
# Per-project distillation
# ---------------------------------------------------------------------------

def distill_project(project_id: str, dry_run: bool = False, purge: bool = False):
    print(f"\n{'='*60}")
    print(f"  DISTILLING: {project_id}")
    print(f"  mode: {'dry run' if dry_run else 'store to Cortex'}")
    if _CUTOFF:
        print(f"  cutoff: {_CUTOFF.strftime('%Y-%m-%d %H:%M UTC')} (active session)")
    print(f"{'='*60}\n")

    sessions = read_sessions(project_id)
    total = sum(len(v) for v in sessions.values())
    print(f"▸ {len(sessions)} sessions, {total} STM fragments")

    existing_ltm = read_ltm(project_id)
    last_ts = read_ltm_timestamp()
    surviving = apply_decay(existing_ltm, last_ts)
    print(f"▸ Existing LTM: {len(existing_ltm)} → {len(surviving)} survive decay "
          f"(last: {last_ts or 'never'})\n")

    print(f"▸ Summarizing sessions via Haiku...")
    summaries = []
    for i, (sess_id, memories) in enumerate(sessions.items()):
        print(f"  [{i+1}/{len(sessions)}] {sess_id[:8]}… ({len(memories)})", end=" ", flush=True)
        try:
            s = summarize_session(memories, project_id, sess_id)
            if s:
                summaries.append(s); print("✓")
            else:
                print("skip")
        except Exception as e:
            print(f"ERROR: {e}")

    if not summaries:
        print("Nothing to distill."); return []

    print(f"\n▸ Merging {len(summaries)} summaries...")
    merged = merge_summaries(summaries, surviving, project_id)
    fragments = parse_fragments(merged)
    print(f"  → {len(fragments)} LTM fragments\n")

    for i, frag in enumerate(fragments):
        print(f"[{i+1}]\n{frag}\n")

    if not dry_run:
        store_ltm(fragments, project_id)
        if purge:
            ltm_count = count_ltm_fragments(project_id)
            if ltm_count > 0:
                print(f"▸ Purging STM for '{project_id}' ({ltm_count} LTM fragments confirmed)...", end=" ", flush=True)
                deleted = delete_stm(project_id)
                print(f"✓ {deleted} STM fragments deleted")
            else:
                print(f"⚠ LTM write unconfirmed (0 fragments in _ltm-{project_id}) — STM NOT deleted")

    return fragments

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _CUTOFF
    args = sys.argv[1:]
    dry_run          = "--dry-run"          in args
    do_global        = "--global"           in args
    keep_stm         = "--keep-stm"         in args
    purge_old        = "--purge-old"        in args
    prune_distilled  = "--prune-distilled"  in args
    project    = next((args[i+1] for i, a in enumerate(args) if a == "--project" and i+1 < len(args)), None)

    # Default is to purge STM after distillation; --keep-stm opts out.
    purge = not keep_stm and not dry_run

    _CUTOFF = _get_active_session_cutoff()
    if _CUTOFF:
        print(f"ℹ Active Claude session detected — capping at {_CUTOFF.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  Fragments from active sessions will not be distilled or deleted.\n")

    if prune_distilled:
        print("▸ Pruning STM for projects that already have LTM...")
        if _CUTOFF:
            print(f"  (respecting active-session cutoff: {_CUTOFF.strftime('%Y-%m-%d %H:%M UTC')})")
        deleted = prune_distilled_stm()
        if deleted:
            for proj, count in sorted(deleted.items()):
                print(f"  {proj}: {count} STM fragments deleted")
            print(f"  Total: {sum(deleted.values())} fragments removed")
        else:
            print("  Nothing to prune (no STM found for distilled projects).")
        return

    if purge_old:
        print("▸ Deleting STM fragments older than 90 days...")
        deleted = delete_old_stm(days=90)
        if deleted:
            for proj, count in sorted(deleted.items()):
                print(f"  {proj}: {count} deleted")
            print(f"  Total: {sum(deleted.values())} fragments removed")
        else:
            print("  Nothing older than 90 days found.")
        return

    if do_global:
        distill_global(dry_run=dry_run)
        return

    if purge:
        print("ℹ STM will be pruned after distillation (pass --keep-stm to retain it).")

    projects = [project] if project else list_projects()
    print(f"Projects to distill: {projects}\n")

    for pid in projects:
        if pid.startswith('_ltm') or pid in SKIP_PROJECTS:
            continue
        distill_project(pid, dry_run=dry_run, purge=purge)

    if not dry_run:
        update_timestamp()
        distill_global(dry_run=False)
        print("\n✓ All done.")

if __name__ == "__main__":
    main()

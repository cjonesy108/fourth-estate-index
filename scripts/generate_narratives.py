"""
Generate journalist bios and score narratives using Claude.

Reads existing scores and analysis results from the DB, generates
editorial copy, and writes it back. Safe to re-run — overwrites previous
narratives with fresh ones.

Usage:
    python scripts/generate_narratives.py               # all journalists
    python scripts/generate_narratives.py hugo-lowell   # single journalist
"""

import asyncio
import json
import os
import re
import sys
from dotenv import load_dotenv

load_dotenv()

import anthropic
from backend.database.db import get_conn

MODEL = "claude-sonnet-4-6"


def extract_pattern_summary(raw_output: dict) -> str:
    """Pull the pattern_summary field from a stored analysis result."""
    text = raw_output.get("text", "")
    # Strip markdown code fences if present
    text = re.sub(r"^```json\s*", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    try:
        data = json.loads(text)
        return data.get("pattern_summary") or data.get("overall_pattern") or ""
    except (json.JSONDecodeError, AttributeError):
        return ""


async def fetch_journalist_context(conn, journalist_id: str) -> dict:
    """Gather everything needed to generate bio + narrative for one journalist."""

    journalist = await conn.fetchrow(
        "SELECT * FROM journalists WHERE id = $1", journalist_id
    )

    scores = await conn.fetchrow(
        """
        SELECT * FROM pillar_scores
        WHERE journalist_id = $1
        ORDER BY scored_at DESC LIMIT 1
        """,
        journalist_id,
    )

    # Sample headlines for bio generation
    headlines = await conn.fetch(
        """
        SELECT headline, section, published_at
        FROM articles
        WHERE journalist_id = $1
        ORDER BY published_at DESC
        LIMIT 25
        """,
        journalist_id,
    )

    # Latest analysis results — one per type
    analysis_rows = await conn.fetch(
        """
        SELECT DISTINCT ON (analysis_type)
            analysis_type, raw_output, corpus_size
        FROM analysis_results
        WHERE journalist_id = $1
        ORDER BY analysis_type, scored_at DESC
        """,
        journalist_id,
    )

    corrections = await conn.fetch(
        """
        SELECT correction_type, correction_text, corrected_at
        FROM corrections
        WHERE journalist_id = $1
        ORDER BY corrected_at DESC
        """,
        journalist_id,
    )

    corpus = await conn.fetchrow(
        """
        SELECT COUNT(*) as size, MIN(published_at) as start, MAX(published_at) as end
        FROM articles WHERE journalist_id = $1
        """,
        journalist_id,
    )

    pattern_summaries = {}
    for row in analysis_rows:
        raw = row["raw_output"]
        if isinstance(raw, str):
            import json as _json
            raw = _json.loads(raw)
        summary = extract_pattern_summary(raw)
        if summary:
            pattern_summaries[row["analysis_type"]] = summary

    return {
        "journalist": dict(journalist),
        "scores": dict(scores) if scores else None,
        "scores_id": str(scores["id"]) if scores else None,
        "headlines": [dict(h) for h in headlines],
        "pattern_summaries": pattern_summaries,
        "corrections": [dict(c) for c in corrections],
        "corpus_size": corpus["size"] if corpus else 0,
        "corpus_start": str(corpus["start"])[:10] if corpus and corpus["start"] else "",
        "corpus_end": str(corpus["end"])[:10] if corpus and corpus["end"] else "",
    }


def build_bio_prompt(ctx: dict) -> str:
    j = ctx["journalist"]
    headlines_text = "\n".join(
        f"- {h['headline']} ({h['section'] or 'unknown section'})"
        for h in ctx["headlines"]
    )
    return f"""You are writing a factual 2-3 sentence professional bio for {j['full_name']}, a journalist at {j['primary_outlet']}.

Based on analysis of {ctx['corpus_size']} articles published between {ctx['corpus_start']} and {ctx['corpus_end']}, here is a sample of their recent headlines:

{headlines_text}

Write a bio that:
1. Describes their beat and coverage focus (inferred from headlines)
2. Notes the types of stories they cover and subjects they report on
3. Reads as a neutral, factual third-person description

Rules:
- Do not invent credentials, awards, or biographical facts not supported by the headlines
- Do not editorialize or evaluate their quality
- Be specific about what they actually cover
- 2-3 sentences, third person, professional tone
- Do not start with their name — vary the opening

Return only the bio text, no quotes, no JSON wrapper."""


def build_narrative_prompt(ctx: dict) -> str:
    j = ctx["journalist"]
    s = ctx["scores"]
    ps = ctx["pattern_summaries"]

    def fmt_score(v):
        return str(round(v * 100)) if v is not None else "N/A"

    corrections_text = ""
    if ctx["corrections"]:
        corrections_text = f"{len(ctx['corrections'])} correction(s) on record:\n"
        for c in ctx["corrections"][:5]:
            corrections_text += f"  - [{c['correction_type']}] {str(c['corrected_at'])[:10]}: {c['correction_text'][:120]}\n"
    else:
        corrections_text = "No corrections on record."

    return f"""You are writing editorial copy for a journalist integrity profile on the Fourth Estate Index, a transparency project grounded in the SPJ Code of Ethics.

JOURNALIST: {j['full_name']} — {j['primary_outlet']}
CORPUS: {ctx['corpus_size']} articles, {ctx['corpus_start']} to {ctx['corpus_end']}
COMPOSITE SCORE: {fmt_score(s.get('composite_score')) if s else 'N/A'} / 100

PILLAR SCORES AND ANALYSIS FINDINGS:

Pillar 1 — Seek Truth & Report It (weight: 30%): {fmt_score(s.get('pillar_1_score')) if s else 'N/A'}
  Headline Fidelity pattern: {ps.get('headline_fidelity', 'No data')}
  Attribution pattern: {ps.get('attribution_patterns', 'No data')}

Pillar 2 — Minimize Harm (weight: 20%): {fmt_score(s.get('pillar_2_score')) if s else 'N/A'}
  Language patterns: {ps.get('language_patterns', 'No data')}

Pillar 3 — Act Independently (weight: 30%): {fmt_score(s.get('pillar_3_score')) if s else 'N/A'}
  Source diversity: {ps.get('source_diversity', 'No data')}

Pillar 4 — Be Accountable & Transparent (weight: 20%): {fmt_score(s.get('pillar_4_score')) if s else 'N/A'}
  {corrections_text}

Write editorial copy explaining each pillar score. For each section:
- Be specific about what was actually measured and found
- Reference patterns from the analysis (not generic descriptions of the pillar)
- Be fair and non-punitive — a low score reflects what was measured, not a character judgment
- 2-3 sentences per section
- Write for a general reader, not a methodologist

Return a JSON object with exactly these keys:
{{
  "overall": "2-3 sentence summary of what the composite score tells us about this journalist's practice overall",
  "pillar_1": "2-3 sentences on truth-seeking and accuracy findings",
  "pillar_2": "2-3 sentences on language and harm findings",
  "pillar_3": "2-3 sentences on independence and source diversity findings",
  "pillar_4": "2-3 sentences on accountability and corrections findings"
}}

Return only the JSON object."""


async def generate_for_journalist(conn, client: anthropic.Anthropic, journalist_id: str):
    ctx = await fetch_journalist_context(conn, journalist_id)
    name = ctx["journalist"]["full_name"]

    if not ctx["scores"]:
        print(f"  ⚠️  No scores found — skipping {name}")
        return

    print(f"  Generating bio...")
    bio_resp = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": build_bio_prompt(ctx)}],
    )
    bio = bio_resp.content[0].text.strip()

    print(f"  Generating score narrative...")
    narrative_resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": build_narrative_prompt(ctx)}],
    )
    raw = narrative_resp.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    narrative = json.loads(raw[start:end + 1])

    # Save bio to journalists table
    await conn.execute(
        "UPDATE journalists SET bio = $1 WHERE id = $2",
        bio, journalist_id,
    )

    # Save narrative to the latest pillar_scores row
    await conn.execute(
        "UPDATE pillar_scores SET score_narrative = $1 WHERE id = $2",
        json.dumps(narrative), ctx["scores_id"],
    )

    print(f"  ✅ Done")
    print(f"  Bio: {bio[:100]}...")
    print(f"  Overall: {narrative.get('overall', '')[:100]}...")


async def main():
    slug_filter = sys.argv[1] if len(sys.argv) > 1 else None

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    conn = await get_conn()

    try:
        if slug_filter:
            rows = await conn.fetch(
                "SELECT id, full_name FROM journalists WHERE slug = $1 AND data_status != 'paused'",
                slug_filter,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT j.id, j.full_name
                FROM journalists j
                JOIN pillar_scores ps ON ps.journalist_id = j.id
                WHERE j.data_status != 'paused'
                  AND ps.composite_score IS NOT NULL
                GROUP BY j.id, j.full_name
                ORDER BY j.full_name
                """
            )

        print(f"Generating narratives for {len(rows)} journalist(s)...\n")

        for row in rows:
            print(f"{'─' * 50}")
            print(f"  {row['full_name']}")
            try:
                await generate_for_journalist(conn, client, str(row["id"]))
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n{'─' * 50}")
        print("  Done.")

    finally:
        await conn.close()


asyncio.run(main())

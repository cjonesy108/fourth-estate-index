"""
Database query functions for the API layer.
"""

from typing import Optional
import asyncpg


async def get_conn(dsn: str) -> asyncpg.Connection:
    return await asyncpg.connect(dsn)


async def list_journalists(conn) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT
            j.id, j.full_name, j.slug, j.primary_outlet, j.beat, j.data_status,
            ps.composite_score, ps.pillar_1_score, ps.pillar_2_score,
            ps.pillar_3_score, ps.pillar_4_score, ps.scored_at
        FROM journalists j
        LEFT JOIN LATERAL (
            SELECT composite_score, pillar_1_score, pillar_2_score,
                   pillar_3_score, pillar_4_score, scored_at
            FROM pillar_scores
            WHERE journalist_id = j.id
            ORDER BY scored_at DESC
            LIMIT 1
        ) ps ON true
        WHERE j.data_status != 'paused'
        ORDER BY j.full_name
        """
    )
    return [dict(r) for r in rows]


def _outlet_slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


async def list_outlets(conn) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT
            j.primary_outlet AS name,
            COUNT(j.id) AS journalist_count,
            AVG(ps.composite_score)  AS avg_composite,
            AVG(ps.pillar_1_score)   AS avg_pillar_1,
            AVG(ps.pillar_2_score)   AS avg_pillar_2,
            AVG(ps.pillar_3_score)   AS avg_pillar_3,
            AVG(ps.pillar_4_score)   AS avg_pillar_4
        FROM journalists j
        LEFT JOIN LATERAL (
            SELECT composite_score, pillar_1_score, pillar_2_score,
                   pillar_3_score, pillar_4_score
            FROM pillar_scores
            WHERE journalist_id = j.id
            ORDER BY scored_at DESC
            LIMIT 1
        ) ps ON true
        WHERE j.data_status != 'paused'
          AND j.primary_outlet IS NOT NULL
        GROUP BY j.primary_outlet
        ORDER BY j.primary_outlet
        """
    )
    return [
        {**dict(r), "slug": _outlet_slug(r["name"])}
        for r in rows
    ]


async def get_outlet_profile(conn, slug: str) -> Optional[dict]:
    outlets = await list_outlets(conn)
    outlet = next((o for o in outlets if o["slug"] == slug), None)
    if not outlet:
        return None

    name = outlet["name"]
    journalists = await conn.fetch(
        """
        SELECT
            j.id, j.full_name, j.slug, j.primary_outlet, j.beat, j.data_status,
            ps.composite_score, ps.pillar_1_score, ps.pillar_2_score,
            ps.pillar_3_score, ps.pillar_4_score, ps.scored_at
        FROM journalists j
        LEFT JOIN LATERAL (
            SELECT composite_score, pillar_1_score, pillar_2_score,
                   pillar_3_score, pillar_4_score, scored_at
            FROM pillar_scores
            WHERE journalist_id = j.id
            ORDER BY scored_at DESC
            LIMIT 1
        ) ps ON true
        WHERE j.primary_outlet = $1
          AND j.data_status != 'paused'
        ORDER BY ps.composite_score DESC NULLS LAST
        """,
        name,
    )

    return {
        "name": name,
        "slug": slug,
        "journalist_count": outlet["journalist_count"],
        "avg_composite":  outlet["avg_composite"],
        "avg_pillar_1":   outlet["avg_pillar_1"],
        "avg_pillar_2":   outlet["avg_pillar_2"],
        "avg_pillar_3":   outlet["avg_pillar_3"],
        "avg_pillar_4":   outlet["avg_pillar_4"],
        "journalists":    [dict(j) for j in journalists],
    }


async def _corpus_inventory(conn, jid) -> dict:
    try:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*)::int AS size,
                COUNT(*) FILTER (
                    WHERE body IS NOT NULL AND COALESCE(access_level, 'full') = 'full'
                )::int AS full_text,
                COUNT(*) FILTER (WHERE access_level = 'excerpt')::int AS excerpt,
                COUNT(*) FILTER (WHERE access_level = 'metadata')::int AS metadata,
                MIN(published_at) AS start,
                MAX(published_at) AS end
            FROM articles
            WHERE journalist_id = $1
            """,
            jid,
        )
    except Exception:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*)::int AS size,
                COUNT(*) FILTER (WHERE body IS NOT NULL)::int AS full_text,
                0::int AS excerpt,
                0::int AS metadata,
                MIN(published_at) AS start,
                MAX(published_at) AS end
            FROM articles
            WHERE journalist_id = $1
            """,
            jid,
        )
    if not row:
        return {"size": 0, "full_text": 0, "excerpt": 0, "metadata": 0, "start": None, "end": None}
    return dict(row)


async def _analysis_samples(conn, jid) -> list[dict]:
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (analysis_type)
                analysis_type, corpus_size, scored_at
            FROM analysis_results
            WHERE journalist_id = $1
            ORDER BY analysis_type, scored_at DESC
            """,
            jid,
        )
    except Exception:
        return []
    return [dict(r) for r in rows]


async def get_journalist_profile(conn, slug: str) -> Optional[dict]:
    journalist = await conn.fetchrow(
        "SELECT * FROM journalists WHERE slug = $1 AND data_status != 'paused'", slug
    )
    if not journalist:
        return None

    jid = journalist["id"]

    scores = await conn.fetchrow(
        """
        SELECT * FROM pillar_scores
        WHERE journalist_id = $1
        ORDER BY scored_at DESC LIMIT 1
        """,
        jid,
    )

    fec = await conn.fetch(
        "SELECT * FROM fec_records WHERE journalist_id = $1 ORDER BY contribution_date DESC",
        jid,
    )

    corrections = await conn.fetch(
        "SELECT * FROM corrections WHERE journalist_id = $1 ORDER BY corrected_at DESC",
        jid,
    )

    appeals = await conn.fetch(
        "SELECT * FROM appeals WHERE journalist_id = $1 AND published = true ORDER BY submitted_at DESC",
        jid,
    )

    corpus = await _corpus_inventory(conn, jid)
    samples = await _analysis_samples(conn, jid)

    scores_dict = dict(scores) if scores else None
    if scores_dict and scores_dict.get("score_narrative"):
        if isinstance(scores_dict["score_narrative"], str):
            import json
            scores_dict["score_narrative"] = json.loads(scores_dict["score_narrative"])

    return {
        "journalist": dict(journalist),
        "scores": scores_dict,
        "fec_records": [dict(r) for r in fec],
        "corrections": [dict(r) for r in corrections],
        "appeals": [dict(r) for r in appeals],
        "corpus_size": corpus.get("size") or 0,
        "corpus_full_text": corpus.get("full_text") or 0,
        "corpus_excerpt": corpus.get("excerpt") or 0,
        "corpus_metadata": corpus.get("metadata") or 0,
        "corpus_start": corpus.get("start"),
        "corpus_end": corpus.get("end"),
        "analysis_samples": samples,
    }

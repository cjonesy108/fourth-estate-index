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
            ps.composite_score, ps.scored_at
        FROM journalists j
        LEFT JOIN LATERAL (
            SELECT composite_score, scored_at
            FROM pillar_scores
            WHERE journalist_id = j.id
            ORDER BY scored_at DESC
            LIMIT 1
        ) ps ON true
        ORDER BY j.full_name
        """
    )
    return [dict(r) for r in rows]


async def get_journalist_profile(conn, slug: str) -> Optional[dict]:
    journalist = await conn.fetchrow(
        "SELECT * FROM journalists WHERE slug = $1", slug
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

    corpus = await conn.fetchrow(
        """
        SELECT COUNT(*) as size, MIN(published_at) as start, MAX(published_at) as end
        FROM articles WHERE journalist_id = $1
        """,
        jid,
    )

    return {
        "journalist": dict(journalist),
        "scores": dict(scores) if scores else None,
        "fec_records": [dict(r) for r in fec],
        "corrections": [dict(r) for r in corrections],
        "appeals": [dict(r) for r in appeals],
        "corpus_size": corpus["size"] if corpus else 0,
        "corpus_start": corpus["start"] if corpus else None,
        "corpus_end": corpus["end"] if corpus else None,
    }

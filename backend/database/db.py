"""
Database connection and core save functions.
Uses asyncpg directly — plain SQL, no ORM magic.
"""

import os
import asyncpg


def _dsn() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(_dsn())


async def save_journalist(conn, *, full_name: str, slug: str, primary_outlet: str, guardian_tag: str = None, x_handle: str = None) -> str:
    row = await conn.fetchrow(
        """
        INSERT INTO journalists (full_name, slug, primary_outlet, guardian_tag, x_handle)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (slug) DO UPDATE
            SET primary_outlet = EXCLUDED.primary_outlet,
                guardian_tag   = EXCLUDED.guardian_tag,
                x_handle       = COALESCE(EXCLUDED.x_handle, journalists.x_handle),
                updated_at     = NOW()
        RETURNING id
        """,
        full_name, slug, primary_outlet, guardian_tag, x_handle,
    )
    return str(row["id"])


async def save_publication(conn, *, name: str, domain: str, api_source: str) -> str:
    row = await conn.fetchrow(
        """
        INSERT INTO publications (name, domain, api_source)
        VALUES ($1, $2, $3)
        ON CONFLICT (domain) DO UPDATE
            SET api_source = EXCLUDED.api_source
        RETURNING id
        """,
        name, domain, api_source,
    )
    return str(row["id"])


async def save_articles(conn, journalist_id: str, publication_id: str, articles: list, source_api: str = "guardian") -> int:
    inserted = 0
    for a in articles:
        published_at = a.published_at.replace(tzinfo=None) if a.published_at.tzinfo else a.published_at
        access_level = getattr(a, "access_level", None) or ("full" if a.body else "metadata")
        lede = getattr(a, "lede", None) or a.subheadline
        result = await conn.execute(
            """
            INSERT INTO articles
                (journalist_id, publication_id, headline, subheadline, body, lede,
                 access_level, url, published_at, section, word_count, source_api, guardian_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
            ON CONFLICT (guardian_id) DO NOTHING
            """,
            journalist_id, publication_id,
            a.headline, a.subheadline, a.body, lede,
            access_level, a.url, published_at, a.section, a.word_count,
            source_api, a.guardian_id,
        )
        if result == "INSERT 0 1":
            inserted += 1
    return inserted


async def save_analysis_result(conn, journalist_id: str, analysis) -> str:
    import json
    row = await conn.fetchrow(
        """
        INSERT INTO analysis_results
            (journalist_id, analysis_type, methodology_version,
             corpus_size, raw_output, model_id, prompt_version)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        RETURNING id
        """,
        journalist_id,
        analysis.analysis_type,
        analysis.methodology_version,
        analysis.corpus_size,
        json.dumps(analysis.raw_output),
        analysis.model_id,
        analysis.prompt_version,
    )
    return str(row["id"])


async def save_citations(conn, analysis_result_id: str, citations: list, article_id_map: dict):
    for c in citations:
        article_db_id = article_id_map.get(c.article_id) if c.article_id else None
        await conn.execute(
            """
            INSERT INTO citations
                (analysis_result_id, article_id, cited_text, dimension, flag_type, flag_value)
            VALUES ($1,$2,$3,$4,$5,$6)
            """,
            analysis_result_id, article_db_id, c.cited_text, c.dimension, c.flag_type, c.flag_value,
        )


async def save_pillar_scores(conn, journalist_id: str, scores: dict, corpus_size: int, methodology_version: str):
    import json
    await conn.execute(
        """
        INSERT INTO pillar_scores
            (journalist_id, methodology_version,
             pillar_1_score, pillar_2_score, pillar_3_score, pillar_4_score,
             composite_score, corpus_size, dimensions_scored)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        journalist_id, methodology_version,
        scores.get("pillar_1_score"), scores.get("pillar_2_score"),
        scores.get("pillar_3_score"), scores.get("pillar_4_score"),
        scores.get("composite_score"), corpus_size,
        json.dumps(scores.get("dimensions_scored", {})),
    )


async def save_corrections(conn, journalist_id: str, publication_id: str, corrections: list, article_id_map: dict) -> int:
    inserted = 0
    for c in corrections:
        article_db_id = None
        if c.original_headline:
            row = await conn.fetchrow(
                "SELECT id FROM articles WHERE journalist_id = $1 AND headline = $2",
                journalist_id, c.original_headline,
            )
            if row:
                article_db_id = str(row["id"])
        corrected_at = c.corrected_at.replace(tzinfo=None) if c.corrected_at and c.corrected_at.tzinfo else c.corrected_at
        result = await conn.execute(
            """
            INSERT INTO corrections
                (journalist_id, article_id, publication_id, correction_text,
                 correction_type, corrected_at, correction_url)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (journalist_id, correction_text, corrected_at) DO NOTHING
            """,
            journalist_id, article_db_id, publication_id,
            c.correction_text, c.correction_type, corrected_at, c.correction_url,
        )
        if result == "INSERT 0 1":
            inserted += 1
    return inserted


async def save_social_posts(conn, journalist_id: str, posts: list) -> int:
    inserted = 0
    for p in posts:
        posted_at = p.posted_at.replace(tzinfo=None) if p.posted_at.tzinfo else p.posted_at
        result = await conn.execute(
            """
            INSERT INTO social_posts
                (journalist_id, platform, post_id, content, is_reply, is_quote, posted_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (post_id) DO NOTHING
            """,
            journalist_id, p.platform, p.post_id, p.content, p.is_reply, p.is_quote, posted_at,
        )
        if result == "INSERT 0 1":
            inserted += 1
    return inserted


async def get_existing_post_ids(conn, journalist_id: str) -> set[str]:
    rows = await conn.fetch("SELECT post_id FROM social_posts WHERE journalist_id = $1", journalist_id)
    return {r["post_id"] for r in rows}


async def get_social_posts(conn, journalist_id: str) -> list[dict]:
    rows = await conn.fetch(
        """SELECT post_id, content, is_reply, is_quote, posted_at
           FROM social_posts WHERE journalist_id = $1 ORDER BY posted_at DESC""",
        journalist_id,
    )
    return [dict(r) for r in rows]


async def get_existing_guardian_ids(conn, journalist_id: str) -> set[str]:
    rows = await conn.fetch("SELECT guardian_id FROM articles WHERE journalist_id = $1", journalist_id)
    return {r["guardian_id"] for r in rows}


async def get_article_id_map(conn, journalist_id: str) -> dict:
    rows = await conn.fetch("SELECT id, guardian_id FROM articles WHERE journalist_id = $1", journalist_id)
    return {r["guardian_id"]: str(r["id"]) for r in rows}


async def get_articles_for_analysis(conn, journalist_id: str, limit: int = 50) -> list[dict]:
    rows = await conn.fetch(
        """SELECT headline, subheadline, body, guardian_id
           FROM articles
           WHERE journalist_id = $1
             AND body IS NOT NULL
             AND COALESCE(access_level, 'full') = 'full'
           ORDER BY published_at DESC
           LIMIT $2""",
        journalist_id, limit,
    )
    return [
        {"body": r["body"], "headline": r["headline"], "subheadline": r["subheadline"],
         "url": r["guardian_id"], "guardian_id": r["guardian_id"]}
        for r in rows
    ]

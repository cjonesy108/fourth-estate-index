"""Article URL lookup helpers used by /api/lookup."""
import asyncpg


def url_variants(url):
    if not url:
        return []
    variants = {url}
    if url.startswith("https://"):
        variants.add("https://www." + url[len("https://"):])
        variants.add(url.replace("https://", "http://", 1))
    if url.startswith("http://"):
        variants.add(url.replace("http://", "https://", 1))
    if "://" in url and "www." not in url.split("/", 3)[2]:
        scheme, rest = url.split("://", 1)
        variants.add(f"{scheme}://www.{rest}")
    return list(variants)


async def lookup_article_and_journalists(conn, url, author_names):
    article = None
    flags = []
    if url:
        variants = url_variants(url)
        try:
            article = await conn.fetchrow(
                """
                SELECT a.id, a.headline, a.url, a.published_at, a.journalist_id,
                       s.composite_score AS article_composite,
                       s.pillar_1_score AS article_p1,
                       s.pillar_2_score AS article_p2
                FROM articles a
                LEFT JOIN LATERAL (
                    SELECT composite_score, pillar_1_score, pillar_2_score
                    FROM article_scores
                    WHERE article_id = a.id OR url = a.url
                    ORDER BY scored_at DESC LIMIT 1
                ) s ON true
                WHERE a.url = ANY($1::text[])
                ORDER BY a.published_at DESC NULLS LAST LIMIT 1
                """,
                variants,
            )
        except asyncpg.UndefinedTableError:
            article = await conn.fetchrow(
                """
                SELECT a.id, a.headline, a.url, a.published_at, a.journalist_id,
                       NULL::numeric AS article_composite,
                       NULL::numeric AS article_p1,
                       NULL::numeric AS article_p2
                FROM articles a
                WHERE a.url = ANY($1::text[])
                ORDER BY a.published_at DESC NULLS LAST LIMIT 1
                """,
                variants,
            )
        if article is None:
            try:
                scored = await conn.fetchrow(
                    """
                    SELECT url, composite_score AS article_composite,
                           pillar_1_score AS article_p1, pillar_2_score AS article_p2
                    FROM article_scores
                    WHERE url = ANY($1::text[])
                    ORDER BY scored_at DESC LIMIT 1
                    """,
                    variants,
                )
                if scored:
                    article = scored
            except asyncpg.UndefinedTableError:
                pass
        elif article.get("id"):
            try:
                flags = await conn.fetch(
                    """
                    SELECT c.cited_text, c.dimension, c.flag_type, c.flag_value
                    FROM citations c WHERE c.article_id = $1
                    ORDER BY c.created_at DESC LIMIT 20
                    """,
                    article["id"],
                )
            except Exception:
                flags = []

    journalists = []
    if author_names:
        rows = await conn.fetch(
            """
            SELECT j.id, j.full_name, j.slug, j.primary_outlet, j.beat, j.data_status,
                   ps.composite_score, ps.pillar_1_score, ps.pillar_2_score,
                   ps.pillar_3_score, ps.pillar_4_score, ps.scored_at
            FROM journalists j
            LEFT JOIN LATERAL (
                SELECT composite_score, pillar_1_score, pillar_2_score,
                       pillar_3_score, pillar_4_score, scored_at
                FROM pillar_scores WHERE journalist_id = j.id
                ORDER BY scored_at DESC LIMIT 1
            ) ps ON true
            WHERE j.data_status != 'paused'
              AND (
                lower(j.full_name) = ANY($1::text[])
                OR EXISTS (
                    SELECT 1 FROM unnest($1::text[]) AS n
                    WHERE lower(j.full_name) LIKE '%' || n || '%'
                )
              )
            """,
            [n.lower().strip() for n in author_names],
        )
        journalists = [dict(r) for r in rows]

    if article and article.get("journalist_id") and not any(j.get("id") == article["journalist_id"] for j in journalists):
        row = await conn.fetchrow(
            """
            SELECT j.id, j.full_name, j.slug, j.primary_outlet, j.beat, j.data_status,
                   ps.composite_score, ps.pillar_1_score, ps.pillar_2_score,
                   ps.pillar_3_score, ps.pillar_4_score, ps.scored_at
            FROM journalists j
            LEFT JOIN LATERAL (
                SELECT composite_score, pillar_1_score, pillar_2_score,
                       pillar_3_score, pillar_4_score, scored_at
                FROM pillar_scores WHERE journalist_id = j.id
                ORDER BY scored_at DESC LIMIT 1
            ) ps ON true
            WHERE j.id = $1
            """,
            article["journalist_id"],
        )
        if row:
            journalists.insert(0, dict(row))

    return {
        "article": dict(article) if article else None,
        "journalists": journalists,
        "flags": [dict(f) for f in flags],
    }

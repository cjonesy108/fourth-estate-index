"""Page lookup for the browser extension.

GET /api/lookup?url=&author=

Returns the article row if that URL is in the corpus, plus journalist
pillar scores when the byline matches. Does not invent an article score.
"""

import os
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from fastapi import APIRouter, Query

from backend.database.queries import get_conn
from backend.database.queries_lookup import lookup_article_and_journalists

router = APIRouter()


def _dsn():
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


def _canonicalize(url: str | None) -> str | None:
    if not url:
        return None
    try:
        u = urlparse(url)
        q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
        host = u.netloc.lower().removeprefix("www.")
        path = u.path.rstrip("/") if u.path != "/" else u.path
        return urlunparse((u.scheme, host, path, "", urlencode(q), ""))
    except Exception:
        return url


def _serialize(row: dict) -> dict:
    return {
        k: str(v) if hasattr(v, "hex") else
           float(v) if hasattr(v, "__round__") and not isinstance(v, (int, float, bool)) else
           v.isoformat() if hasattr(v, "isoformat") else
           v
        for k, v in row.items()
    }


@router.get("")
async def lookup_route(
    url: str | None = Query(None),
    author: str | None = Query(None),
    authors: str | None = Query(None),
):
    names = []
    raw = authors or author
    if raw:
        for part in raw.replace(";", ",").split(","):
            part = part.replace(" and ", ",").strip()
            if part:
                names.append(part)

    canonical = _canonicalize(url)
    conn = await get_conn(_dsn())
    try:
        result = await lookup_article_and_journalists(conn, canonical, names)
    finally:
        await conn.close()

    article = result.get("article")
    article_out = {
        "found": bool(article),
        "url": article.get("url") if article else canonical,
        "headline": article.get("headline") if article else None,
        "published_at": article["published_at"].isoformat() if article and article.get("published_at") else None,
        "in_corpus": bool(article),
        "composite_score": None,
        "pillar_1_score": None,
        "pillar_2_score": None,
        "note": (
            "This URL is in the corpus. Article-level pillar scores publish after the per-article scorer has run."
            if article
            else "This URL is not in the corpus yet. Journalist totals below are corpus scores, not a grade for this page."
        ),
    }
    if article and article.get("article_composite") is not None:
        article_out["composite_score"] = float(article["article_composite"])
        article_out["pillar_1_score"] = float(article["article_p1"]) if article.get("article_p1") is not None else None
        article_out["pillar_2_score"] = float(article["article_p2"]) if article.get("article_p2") is not None else None
        article_out["note"] = "Published article snapshot. Not a substitute for the journalist corpus score."

    return {
        "article": article_out,
        "journalists": [_serialize(j) for j in result.get("journalists", [])],
        "flags": [_serialize(f) for f in result.get("flags", [])],
    }

"""
Texas Tribune article ingester.

Public WordPress / Newspack REST API. No login.
Author filter: /wp-json/wp/v2/posts?author={user_id}
Full text is in content.rendered.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from backend.ingestion.article_ingestion import IngestionResult, ParsedArticle

logger = logging.getLogger(__name__)

BASE = "https://www.texastribune.org/wp-json/wp/v2"
MIN_WORD_COUNT = 100
PAGE_SIZE = 50
UA = "FourthEstateIndex/0.4 (+https://fourth-estate-index.vercel.app)"


def _strip_html(html: str) -> str:
    clean = re.sub(r"<script[\s\S]*?</script>", " ", html or "", flags=re.I)
    clean = re.sub(r"<style[\s\S]*?</style>", " ", clean, flags=re.I)
    clean = re.sub(r"<[^>]+>", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


class TexasTribuneIngester:
    source_name = "texastribune"

    def __init__(self, timeout: float = 30.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": UA, "Accept": "application/json"},
            follow_redirects=True,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        await self.client.aclose()

    async def resolve_user_id(self, author_slug: str) -> Optional[int]:
        resp = await self.client.get(f"{BASE}/users", params={"slug": author_slug})
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            logger.warning("No Texas Tribune user for slug %s", author_slug)
            return None
        return int(rows[0]["id"])

    async def ingest(
        self,
        journalist_id: str,
        author_slug: str,
        date_from: datetime,
        date_to: datetime,
        existing_ids: set[str],
        user_id: Optional[int] = None,
    ) -> tuple[list[ParsedArticle], IngestionResult]:
        result = IngestionResult(0, 0, 0, 0, None, None, [])
        articles: list[ParsedArticle] = []

        try:
            uid = user_id or await self.resolve_user_id(author_slug)
        except Exception as e:
            result.errors.append(f"user lookup failed: {e}")
            return [], result
        if uid is None:
            result.errors.append(f"no user for {author_slug}")
            return [], result

        start = date_from.replace(tzinfo=date_from.tzinfo or timezone.utc)
        end = date_to.replace(tzinfo=date_to.tzinfo or timezone.utc)
        page = 1

        while True:
            try:
                resp = await self.client.get(
                    f"{BASE}/posts",
                    params={
                        "author": uid,
                        "per_page": PAGE_SIZE,
                        "page": page,
                        "orderby": "date",
                        "order": "desc",
                    },
                )
                if resp.status_code == 400:
                    break
                resp.raise_for_status()
            except Exception as e:
                result.errors.append(f"page {page} failed: {e}")
                break

            posts = resp.json()
            if not posts:
                break

            reached_old = False
            for raw in posts:
                parsed = self._parse(raw)
                if parsed is None:
                    result.articles_skipped_no_body += 1
                    continue
                pub = parsed.published_at.replace(tzinfo=timezone.utc)
                if pub > end:
                    continue
                if pub < start:
                    reached_old = True
                    continue
                if parsed.guardian_id in existing_ids or parsed.url in existing_ids:
                    result.articles_skipped_duplicate += 1
                    continue
                if parsed.access_level == "full" and parsed.word_count < MIN_WORD_COUNT:
                    result.articles_skipped_short += 1
                    continue

                articles.append(parsed)
                existing_ids.add(parsed.guardian_id)
                result.articles_ingested += 1
                if result.corpus_start is None or parsed.published_at < result.corpus_start:
                    result.corpus_start = parsed.published_at
                if result.corpus_end is None or parsed.published_at > result.corpus_end:
                    result.corpus_end = parsed.published_at

            total_pages = int(resp.headers.get("X-WP-TotalPages") or page)
            if reached_old or page >= total_pages:
                break
            page += 1

        return articles, result

    def _parse(self, raw: dict) -> Optional[ParsedArticle]:
        headline = _strip_html((raw.get("title") or {}).get("rendered") or "")
        url = raw.get("link") or ""
        if not headline or not url:
            return None
        body = _strip_html((raw.get("content") or {}).get("rendered") or "")
        lede = _strip_html((raw.get("excerpt") or {}).get("rendered") or "") or None
        try:
            published_at = datetime.fromisoformat(str(raw.get("date")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if body:
            access = "full"
        elif lede:
            access = "excerpt"
        else:
            access = "metadata"
        return ParsedArticle(
            guardian_id=url,
            headline=headline,
            subheadline=lede,
            body=body or None,
            url=url,
            published_at=published_at.replace(tzinfo=None),
            section="",
            word_count=len(body.split()) if body else 0,
            byline=None,
            access_level=access,
            lede=lede,
        )

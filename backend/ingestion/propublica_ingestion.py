"""
ProPublica article ingester.

Public WordPress REST API. No login.
Author filter: /wp-json/wp/v2/posts?profile={profile_id}
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

BASE = "https://www.propublica.org/wp-json/wp/v2"
MIN_WORD_COUNT = 100
PAGE_SIZE = 50
UA = "FourthEstateIndex/0.3 (+https://fourth-estate-index.vercel.app)"


def _strip_html(html: str) -> str:
    clean = re.sub(r"<script[\s\S]*?</script>", " ", html or "", flags=re.I)
    clean = re.sub(r"<style[\s\S]*?</style>", " ", clean, flags=re.I)
    clean = re.sub(r"<[^>]+>", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


def _byline_profile_ids(post: dict) -> list[int]:
    by = (post.get("meta") or {}).get("byline") or {}
    ids = []
    if isinstance(by, dict):
        for profile in by.get("profiles") or []:
            pid = (profile.get("atts") or {}).get("post_id")
            if pid is not None:
                ids.append(int(pid))
    return ids


class ProPublicaIngester:
    source_name = "propublica"

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

    async def resolve_profile_id(self, author_slug: str) -> Optional[int]:
        resp = await self.client.get(f"{BASE}/profile", params={"slug": author_slug})
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            logger.warning("No ProPublica profile for slug %s", author_slug)
            return None
        return int(rows[0]["id"])

    async def ingest(
        self,
        journalist_id: str,
        author_slug: str,
        date_from: datetime,
        date_to: datetime,
        existing_ids: set[str],
        profile_id: Optional[int] = None,
    ) -> tuple[list[ParsedArticle], IngestionResult]:
        result = IngestionResult(0, 0, 0, 0, None, None, [])
        articles: list[ParsedArticle] = []

        try:
            pid = profile_id or await self.resolve_profile_id(author_slug)
        except Exception as e:
            result.errors.append(f"profile lookup failed: {e}")
            return [], result
        if pid is None:
            result.errors.append(f"no profile for {author_slug}")
            return [], result

        start = date_from.replace(tzinfo=date_from.tzinfo or timezone.utc)
        end = date_to.replace(tzinfo=date_to.tzinfo or timezone.utc)
        page = 1

        while True:
            try:
                resp = await self.client.get(
                    f"{BASE}/posts",
                    params={
                        "profile": pid,
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
                parsed = self._parse(raw, expected_profile_id=pid)
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

    def _parse(self, raw: dict, expected_profile_id: int) -> Optional[ParsedArticle]:
        ids = _byline_profile_ids(raw)
        if ids and expected_profile_id not in ids:
            return None
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

"""
NPR article ingester.

Public people pages list stories. Full text is read from text.npr.org.
No login. No official API key.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx

from backend.ingestion.article_ingestion import IngestionResult, ParsedArticle

logger = logging.getLogger(__name__)

UA = "FourthEstateIndex/0.4 (+https://fourth-estate-index.vercel.app)"
MIN_WORD_COUNT = 80
STORY_RE = re.compile(
    r"https://www\.npr\.org/(20\d{2}/\d{2}/\d{2}/[^\s\"'?#]+)"
)
TITLE_RE = re.compile(r"<h1[^>]*class=\"story-title\"[^>]*>(.*?)</h1>", re.I | re.S)
TITLE_FALLBACK_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
BODY_RE = re.compile(
    r"<div[^>]*class=\"paragraphs-container\"[^>]*>(.*?)</div>", re.I | re.S
)


def _strip_html(html: str) -> str:
    clean = re.sub(r"<script[\s\S]*?</script>", " ", html or "", flags=re.I)
    clean = re.sub(r"<style[\s\S]*?</style>", " ", clean, flags=re.I)
    clean = re.sub(r"<[^>]+>", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


class NPRIngester:
    source_name = "npr"

    def __init__(self, timeout: float = 30.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": UA, "Accept": "text/html"},
            follow_redirects=True,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        await self.client.aclose()

    async def ingest(
        self,
        journalist_id: str,
        author_slug: str,
        date_from: datetime,
        date_to: datetime,
        existing_ids: set[str],
    ) -> tuple[list[ParsedArticle], IngestionResult]:
        result = IngestionResult(0, 0, 0, 0, None, None, [])
        articles: list[ParsedArticle] = []
        start = date_from.replace(tzinfo=date_from.tzinfo or timezone.utc)
        end = date_to.replace(tzinfo=date_to.tzinfo or timezone.utc)

        urls = await self._list_story_urls(author_slug)
        if not urls:
            result.errors.append(f"no stories listed for {author_slug}")
            return [], result

        for url in urls:
            if url in existing_ids:
                result.articles_skipped_duplicate += 1
                continue
            parsed = await self._fetch_story(url)
            if parsed is None:
                result.articles_skipped_no_body += 1
                continue
            pub = parsed.published_at.replace(tzinfo=timezone.utc)
            if pub > end:
                continue
            if pub < start:
                continue
            if parsed.guardian_id in existing_ids:
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

        return articles, result

    async def _list_story_urls(self, author_slug: str) -> list[str]:
        seen: list[str] = []
        found: set[str] = set()
        for page in range(1, 9):
            url = f"https://www.npr.org/people/{author_slug}"
            params = {"page": page} if page > 1 else None
            try:
                resp = await self.client.get(url, params=params)
                resp.raise_for_status()
            except Exception as e:
                logger.warning("NPR people page %s p%s failed: %s", author_slug, page, e)
                break
            page_urls = STORY_RE.findall(resp.text)
            new = 0
            for path in page_urls:
                full = f"https://www.npr.org/{path}"
                if full not in found:
                    found.add(full)
                    seen.append(full)
                    new += 1
            if new == 0:
                break
        return seen

    async def _fetch_story(self, url: str) -> Optional[ParsedArticle]:
        path = urlparse(url).path.lstrip("/")
        text_url = f"https://text.npr.org/{path}"
        try:
            resp = await self.client.get(text_url)
            resp.raise_for_status()
        except Exception:
            return None
        html = resp.text
        title_m = TITLE_RE.search(html) or TITLE_FALLBACK_RE.search(html)
        headline = _strip_html(title_m.group(1) if title_m else "")
        headline = re.sub(r"\s+:\s+NPR$", "", headline).strip()
        body_m = BODY_RE.search(html)
        body = _strip_html(body_m.group(1) if body_m else "")
        if not headline:
            return None
        published_at = self._date_from_url(url)
        if published_at is None:
            return None
        access = "full" if body else "metadata"
        return ParsedArticle(
            guardian_id=url.split("?")[0],
            headline=headline,
            subheadline=None,
            body=body or None,
            url=url.split("?")[0],
            published_at=published_at,
            section="",
            word_count=len(body.split()) if body else 0,
            byline=None,
            access_level=access,
            lede=None,
        )

    def _date_from_url(self, url: str) -> Optional[datetime]:
        m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        if not m:
            return None
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

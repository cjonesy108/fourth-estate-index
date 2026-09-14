"""
NPR article ingester.

Lists stories from public people + monthly archive pages.
Reads full text from text.npr.org. No login.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx

from backend.ingestion.article_ingestion import IngestionResult, ParsedArticle

logger = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
MIN_WORD_COUNT = 80
MAX_STORIES = 60
STORY_RE = re.compile(r"https?://(?:www\.|text\.)?npr\.org/(20\d{2}/\d{2}/\d{2}/[^\s\"'?#]+)")
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

    def __init__(self, timeout: float = 25.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.npr.org/",
            },
            follow_redirects=True,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        await self.client.aclose()

    async def _get(self, url: str, params: Optional[dict] = None) -> Optional[httpx.Response]:
        last: Optional[Exception] = None
        for attempt in range(3):
            try:
                resp = await self.client.get(url, params=params)
                if resp.status_code in (403, 429, 503):
                    last = RuntimeError(f"HTTP {resp.status_code}")
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                resp.raise_for_status()
                return resp
            except Exception as e:
                last = e
                await asyncio.sleep(1.2 * (attempt + 1))
        logger.warning("GET failed %s err=%r", url, last)
        return None

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

        urls = await self._list_story_urls(author_slug, start, end)
        if not urls:
            result.errors.append(f"no stories listed for {author_slug}")
            return [], result

        for url in urls[:MAX_STORIES]:
            if url in existing_ids:
                result.articles_skipped_duplicate += 1
                continue
            parsed = await self._fetch_story(url)
            if parsed is None:
                result.articles_skipped_no_body += 1
                continue
            pub = parsed.published_at.replace(tzinfo=timezone.utc)
            if pub > end or pub < start:
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

    async def _list_story_urls(
        self, author_slug: str, start: datetime, end: datetime
    ) -> list[str]:
        found: set[str] = set()
        seen: list[str] = []

        bio = await self._get(f"https://www.npr.org/people/{author_slug}")
        if bio is None:
            return []
        self._collect(bio.text, found, seen)

        year, month = end.year, end.month
        hops = 0
        while datetime(year, month, 1, tzinfo=timezone.utc) >= start and hops < 16:
            page = await self._get(
                f"https://www.npr.org/people/{author_slug}/archive",
                params={"date": f"{month}-28-{year}"},
            )
            if page is not None:
                self._collect(page.text, found, seen)
            hops += 1
            month -= 3
            while month <= 0:
                month += 12
                year -= 1
        return seen

    def _collect(self, html: str, found: set[str], seen: list[str]) -> None:
        for path in STORY_RE.findall(html):
            full = f"https://www.npr.org/{path}"
            if full not in found:
                found.add(full)
                seen.append(full)

    async def _fetch_story(self, url: str) -> Optional[ParsedArticle]:
        path = urlparse(url).path.lstrip("/")
        html = None
        for candidate in (f"https://text.npr.org/{path}", url):
            resp = await self._get(candidate)
            if resp is None:
                continue
            html = resp.text
            if "paragraphs-container" in html or "storytext" in html:
                break
        if not html:
            return None
        title_m = TITLE_RE.search(html) or TITLE_FALLBACK_RE.search(html)
        headline = _strip_html(title_m.group(1) if title_m else "")
        headline = re.sub(r"\s+:\s+NPR$", "", headline).strip()
        body_m = BODY_RE.search(html)
        body = _strip_html(body_m.group(1) if body_m else "")
        if not body:
            body_m = re.search(
                r'<div[^>]*id="storytext"[^>]*>(.*?)</div>', html, re.I | re.S
            )
            if body_m:
                body = _strip_html(body_m.group(1))
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

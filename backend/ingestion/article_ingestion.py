"""
Guardian article ingestion.

Uses the Guardian Open Platform API to pull full article text by journalist.
Articles without a body are kept as excerpt or metadata rather than dropped.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

GUARDIAN_BASE = "https://content.guardianapis.com"
MIN_WORD_COUNT = 100
PAGE_SIZE = 50


@dataclass
class ParsedArticle:
    guardian_id: str
    headline: str
    subheadline: Optional[str]
    body: Optional[str]
    url: str
    published_at: datetime
    section: str
    word_count: int
    byline: Optional[str]
    access_level: str = "full"  # full | excerpt | metadata
    lede: Optional[str] = None


@dataclass
class IngestionResult:
    articles_ingested: int
    articles_skipped_duplicate: int
    articles_skipped_short: int
    articles_skipped_no_body: int
    corpus_start: Optional[datetime]
    corpus_end: Optional[datetime]
    errors: list[str]


class GuardianIngester:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def resolve_contributor_tag(self, name: str) -> Optional[str]:
        params = {"type": "contributor", "q": name, "api-key": self.api_key}
        resp = await self._get(f"{GUARDIAN_BASE}/tags", params)
        results = resp.get("response", {}).get("results", [])
        if not results:
            logger.warning(f"No Guardian contributor tag found for: {name}")
            return None
        tag = results[0]["id"]
        logger.info(f"Resolved '{name}' → Guardian tag: {tag}")
        return tag

    async def ingest(
        self,
        journalist_id: str,
        guardian_tag: str,
        date_from: datetime,
        date_to: datetime,
        existing_guardian_ids: set[str],
    ) -> tuple[list[ParsedArticle], IngestionResult]:
        result = IngestionResult(0, 0, 0, 0, None, None, [])
        articles: list[ParsedArticle] = []
        page = 1

        while True:
            params = {
                "tag": guardian_tag,
                "from-date": date_from.strftime("%Y-%m-%d"),
                "to-date": date_to.strftime("%Y-%m-%d"),
                "show-fields": "headline,trailText,body,byline,wordcount",
                "page-size": PAGE_SIZE,
                "page": page,
                "api-key": self.api_key,
            }
            try:
                data = await self._get(f"{GUARDIAN_BASE}/search", params)
            except Exception as e:
                result.errors.append(f"Page {page} fetch failed: {e}")
                break

            response = data.get("response", {})
            raw_results = response.get("results", [])

            for raw in raw_results:
                parsed = self._parse(raw)
                if parsed is None:
                    result.articles_skipped_no_body += 1
                    continue
                if parsed.guardian_id in existing_guardian_ids:
                    result.articles_skipped_duplicate += 1
                    continue
                if parsed.access_level == "full" and parsed.word_count < MIN_WORD_COUNT:
                    result.articles_skipped_short += 1
                    continue

                articles.append(parsed)
                result.articles_ingested += 1
                existing_guardian_ids.add(parsed.guardian_id)
                if result.corpus_start is None or parsed.published_at < result.corpus_start:
                    result.corpus_start = parsed.published_at
                if result.corpus_end is None or parsed.published_at > result.corpus_end:
                    result.corpus_end = parsed.published_at

            total_pages = response.get("pages", 1)
            if page >= total_pages:
                break
            page += 1
            await asyncio.sleep(0.5)

        return articles, result

    def _parse(self, raw: dict) -> Optional[ParsedArticle]:
        fields = raw.get("fields", {})
        body_html = fields.get("body") or ""
        body = self._strip_html(body_html) if body_html else None
        lede = self._strip_html(fields.get("trailText") or "") or None
        headline = fields.get("headline") or raw.get("webTitle", "")
        if not headline:
            return None
        if body:
            access = "full"
        elif lede:
            access = "excerpt"
        else:
            access = "metadata"
        word_count = int(fields.get("wordcount") or (len(body.split()) if body else 0))
        pub_date_str = raw.get("webPublicationDate", "")
        try:
            published_at = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
        return ParsedArticle(
            guardian_id=raw["id"],
            headline=headline,
            subheadline=lede,
            body=body,
            url=raw.get("webUrl", ""),
            published_at=published_at,
            section=raw.get("sectionName", ""),
            word_count=word_count,
            byline=fields.get("byline"),
            access_level=access,
            lede=lede,
        )

    def _strip_html(self, html: str) -> str:
        import re
        clean = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", clean).strip()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def _get(self, url: str, params: dict) -> dict:
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

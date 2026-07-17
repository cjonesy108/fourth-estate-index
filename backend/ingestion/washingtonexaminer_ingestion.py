"""
Washington Examiner article ingester.

Author pages: https://www.washingtonexaminer.com/author/{slug}/page/{n}/
- 12 articles per page, paginated by /page/N/
- Article list selector: h2 a
- Date: time[datetime] on article page
- Article body: <p> elements on article page
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import Page

from backend.ingestion.article_ingestion import ParsedArticle
from backend.ingestion.web_scraper import PlaywrightIngester

logger = logging.getLogger(__name__)

BASE = "https://www.washingtonexaminer.com"


class WashingtonExaminerIngester(PlaywrightIngester):
    source_name = "washingtonexaminer"

    def author_url(self, slug: str, page: int) -> str:
        if page == 1:
            return f"{BASE}/author/{slug}"
        return f"{BASE}/author/{slug}/page/{page}/"

    async def parse_listing(self, page: Page) -> list[dict]:
        links = await page.query_selector_all("h2 a")
        items = []
        for link in links:
            href = await link.get_attribute("href") or ""
            headline = (await link.inner_text()).strip()
            if not href:
                continue
            if not href.startswith("http"):
                href = BASE + href
            if headline:
                items.append({"url": href, "headline": headline})
        return items

    async def parse_article(self, page: Page, item: dict) -> Optional[ParsedArticle]:
        import json as _json
        url = item["url"]

        # Date from <meta property="article:published_time"> — reliable, present even when JS blocked
        pub_date = None
        meta_el = await page.query_selector("meta[property='article:published_time']")
        if meta_el:
            dt_str = await meta_el.get_attribute("content")
            if dt_str:
                try:
                    pub_date = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

        if pub_date is None:
            pub_date = self.date_from_item(item)
        if pub_date is None:
            return None

        # Body: collect all <p> elements with substantial text
        paras = await page.query_selector_all("p")
        body_parts = []
        for p in paras:
            text = (await p.inner_text()).strip()
            if len(text) > 40:
                body_parts.append(text)
        body = " ".join(body_parts)

        if not body:
            return None

        headline = item.get("headline") or await page.title()

        # Byline from JSON-LD (most reliable on WE)
        byline = None
        for script in await page.query_selector_all("script[type='application/ld+json']"):
            try:
                data = _json.loads(await script.inner_text())
                if isinstance(data, list):
                    data = data[0]
                author = data.get("author")
                if isinstance(author, list) and author:
                    byline = author[0].get("name")
                elif isinstance(author, dict):
                    byline = author.get("name")
                if byline:
                    break
            except Exception:
                pass

        # Section from URL path
        parts = url.replace(BASE, "").strip("/").split("/")
        section = parts[0] if parts else ""

        word_count = len(body.split())

        return ParsedArticle(
            guardian_id=url,
            headline=headline,
            subheadline=None,
            body=body,
            url=url,
            published_at=pub_date.replace(tzinfo=None),
            section=section,
            word_count=word_count,
            byline=byline,
        )

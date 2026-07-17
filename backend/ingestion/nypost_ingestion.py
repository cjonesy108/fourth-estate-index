"""
NY Post article ingester.

Author pages: https://nypost.com/author/{slug}/page/{n}/
- 29 articles per page, paginated by /page/N/
- Article list selector: .archive .story h3 a
- Date: extracted from URL path (YYYY/MM/DD)
- Article body: bare <p> elements (WordPress, no class)
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import Page

from backend.ingestion.article_ingestion import ParsedArticle
from backend.ingestion.web_scraper import PlaywrightIngester

logger = logging.getLogger(__name__)


class NYPostIngester(PlaywrightIngester):
    source_name = "nypost"

    def author_url(self, slug: str, page: int) -> str:
        if page == 1:
            return f"https://nypost.com/author/{slug}/"
        return f"https://nypost.com/author/{slug}/page/{page}/"

    async def parse_listing(self, page: Page) -> list[dict]:
        # Scoped to .archive .story to avoid sidebar/related content
        links = await page.query_selector_all(".archive .story h3 a")
        items = []
        for link in links:
            href = await link.get_attribute("href") or ""
            headline = (await link.inner_text()).strip()
            if href and "/2" in href:  # has year in URL
                items.append({"url": href, "headline": headline})
        return items

    async def parse_article(self, page: Page, item: dict) -> Optional[ParsedArticle]:
        url = item["url"]

        # Body: NY Post is WordPress — article paragraphs have no class
        paras = await page.query_selector_all("p")
        body_parts = []
        for p in paras:
            cls = (await p.get_attribute("class")) or ""
            text = (await p.inner_text()).strip()
            # Skip nav, meta, and short UI strings; keep unmarked paragraphs
            if not cls and len(text) > 40:
                body_parts.append(text)
        body = " ".join(body_parts)

        if not body:
            return None

        # Date from URL
        pub_date = self.date_from_item(item)
        if pub_date is None:
            return None

        # Headline (from listing or page title)
        headline = item.get("headline") or await page.title()

        # Byline
        byline = None
        byline_el = await page.query_selector("[class*='byline'] a, [rel='author'], [class*='author-name']")
        if byline_el:
            byline = (await byline_el.inner_text()).strip() or None

        # Section from URL: /YYYY/MM/DD/{section}/slug
        section = ""
        m = re.search(r"/\d{4}/\d{2}/\d{2}/([^/]+)/", url)
        if m:
            section = m.group(1)

        word_count = len(body.split())

        return ParsedArticle(
            guardian_id=url,  # repurposed as external unique ID
            headline=headline,
            subheadline=None,
            body=body,
            url=url,
            published_at=pub_date.replace(tzinfo=None),
            section=section,
            word_count=word_count,
            byline=byline,
        )

"""
Base Playwright scraper for news outlets without public APIs.

Subclasses implement:
  - author_url(slug, page) -> str
  - parse_listing(page) -> list[dict]  # {url, headline, date_str}
  - parse_article(page, url) -> ParsedArticle | None
  - date_from_listing(item) -> datetime | None  # override if date on listing page

Common behaviour:
  - Browser lifecycle via async context manager
  - Blocks images/fonts/ads to speed up loads
  - Polite delays between requests
  - Stops pagination when articles go past date_from
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext

from backend.ingestion.article_ingestion import ParsedArticle, IngestionResult

logger = logging.getLogger(__name__)

MIN_WORD_COUNT = 100
BLOCKED_RESOURCES = re.compile(
    r"\.(png|jpg|jpeg|gif|webp|svg|ico|woff|woff2|ttf|eot)(\?.*)?$"
    r"|/(ads?|analytics|tracking|metrics|pixel|beacon|gtm|doubleclick|googlesyndication)"
)


class PlaywrightIngester:
    source_name: str = "web"  # overridden by subclass

    def __init__(self, headless: bool = True, delay: float = 1.5):
        self.headless = headless
        self.delay = delay
        self._playwright = None
        self._browser = None
        self._ctx: Optional[BrowserContext] = None

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._ctx = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        return self

    async def __aexit__(self, *_):
        if self._ctx:
            await self._ctx.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def new_page(self) -> Page:
        page = await self._ctx.new_page()
        await page.route(
            "**/*",
            lambda route: route.abort()
            if BLOCKED_RESOURCES.search(route.request.url)
            else route.continue_(),
        )
        return page

    async def goto(self, page: Page, url: str, timeout: int = 25000) -> bool:
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            return resp is not None and resp.status < 400
        except Exception as e:
            logger.warning(f"Failed to load {url}: {e}")
            return False

    async def ingest(
        self,
        journalist_id: str,
        author_slug: str,
        date_from: datetime,
        date_to: datetime,
        existing_ids: set[str],
    ) -> tuple[list[ParsedArticle], IngestionResult]:
        result = IngestionResult(
            articles_ingested=0,
            articles_skipped_duplicate=0,
            articles_skipped_short=0,
            articles_skipped_no_body=0,
            corpus_start=None,
            corpus_end=None,
            errors=[],
        )
        articles: list[ParsedArticle] = []
        page_num = 1
        done = False

        while not done:
            url = self.author_url(author_slug, page_num)
            listing_page = await self.new_page()
            ok = await self.goto(listing_page, url)
            if not ok:
                logger.warning(f"Listing page {page_num} failed: {url}")
                await listing_page.close()
                break

            items = await self.parse_listing(listing_page)
            await listing_page.close()

            if not items:
                logger.info(f"No items on page {page_num} — stopping")
                break

            logger.info(f"Page {page_num}: {len(items)} items")

            for item in items:
                article_url = item["url"]
                pub_date = self.date_from_item(item)

                if pub_date and pub_date < date_from.replace(tzinfo=timezone.utc):
                    logger.info(f"Reached date_from ({date_from.date()}) — stopping")
                    done = True
                    break

                if pub_date and pub_date > date_to.replace(tzinfo=timezone.utc):
                    result.articles_skipped_duplicate += 1
                    continue

                if article_url in existing_ids:
                    result.articles_skipped_duplicate += 1
                    continue

                await asyncio.sleep(self.delay)
                article_page = await self.new_page()
                ok = await self.goto(article_page, article_url)
                if not ok:
                    result.articles_skipped_no_body += 1
                    await article_page.close()
                    continue

                parsed = await self.parse_article(article_page, item)
                await article_page.close()

                if parsed is None:
                    result.articles_skipped_no_body += 1
                    continue
                if parsed.word_count < MIN_WORD_COUNT:
                    result.articles_skipped_short += 1
                    continue

                # Date filter using parsed date (catches outlets with no date in URL/listing)
                if parsed.published_at:
                    art_utc = parsed.published_at.replace(tzinfo=timezone.utc)
                    if art_utc > date_to.replace(tzinfo=timezone.utc):
                        result.articles_skipped_duplicate += 1
                        continue
                    if art_utc < date_from.replace(tzinfo=timezone.utc):
                        logger.info(f"Article date {art_utc.date()} before date_from — stopping")
                        done = True
                        break

                articles.append(parsed)
                existing_ids.add(article_url)
                result.articles_ingested += 1

                if result.corpus_start is None or parsed.published_at < result.corpus_start:
                    result.corpus_start = parsed.published_at
                if result.corpus_end is None or parsed.published_at > result.corpus_end:
                    result.corpus_end = parsed.published_at

            page_num += 1
            await asyncio.sleep(self.delay)

        return articles, result

    # --- Subclass interface ---

    def author_url(self, slug: str, page: int) -> str:
        raise NotImplementedError

    async def parse_listing(self, page: Page) -> list[dict]:
        """Return list of {url, headline, date_str (optional)} dicts."""
        raise NotImplementedError

    async def parse_article(self, page: Page, item: dict) -> Optional[ParsedArticle]:
        """Extract article from a loaded article page. Return None if unusable."""
        raise NotImplementedError

    def date_from_item(self, item: dict) -> Optional[datetime]:
        """Parse date from listing item. Override if date not in URL."""
        date_str = item.get("date_str", "")
        if date_str:
            try:
                return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        # Fall back to URL date pattern YYYY/MM/DD
        url = item.get("url", "")
        m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        if m:
            y, mo, d = m.groups()
            return datetime(int(y), int(mo), int(d), tzinfo=timezone.utc)
        return None

    @staticmethod
    def extract_text(paragraphs: list) -> str:
        """Join paragraph texts, strip whitespace."""
        return " ".join(t.strip() for t in paragraphs if t.strip())

    @staticmethod
    def strip_html(html: str) -> str:
        import re
        clean = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", clean).strip()

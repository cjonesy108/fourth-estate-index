"""
Smoke-test the Playwright scrapers. Fetches 3 articles per outlet, prints results.
Does NOT write to the DB.

Usage:
    PYTHONPATH=. python3 scripts/test_scrapers.py
"""

import asyncio
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from backend.ingestion.nypost_ingestion import NYPostIngester
from backend.ingestion.washingtonexaminer_ingestion import WashingtonExaminerIngester

DATE_FROM = datetime(2023, 1, 1)
DATE_TO   = datetime(2024, 12, 31)

TESTS = [
    {
        "label": "NY Post — Jon Levine (media reporter)",
        "ingester_cls": NYPostIngester,
        "slug": "jon-levine",
    },
    {
        "label": "Washington Examiner — Anna Giaritelli (immigration)",
        "ingester_cls": WashingtonExaminerIngester,
        "slug": "anna-giaritelli",
    },
]


async def run_test(cfg: dict):
    print(f"\n{'─' * 60}")
    print(f"  {cfg['label']}")
    print(f"{'─' * 60}")

    ingester_cls = cfg["ingester_cls"]
    slug = cfg["slug"]

    # Monkey-patch to stop after 3 articles for testing
    original_ingest = ingester_cls.ingest

    async def limited_ingest(self, journalist_id, author_slug, date_from, date_to, existing_ids):
        result_articles = []
        page_num = 1

        async with self:
            while len(result_articles) < 3:
                url = self.author_url(author_slug, page_num)
                listing_page = await self.new_page()
                ok = await self.goto(listing_page, url)
                if not ok:
                    print(f"  ✗ Listing page {page_num} failed")
                    await listing_page.close()
                    break

                items = await self.parse_listing(listing_page)
                await listing_page.close()
                print(f"  Listing page {page_num}: {len(items)} items found")

                import asyncio as _asyncio
                for item in items:
                    if len(result_articles) >= 3:
                        break
                    pub_date = self.date_from_item(item)
                    print(f"    → {item['url'][:70]} | date: {pub_date}")

                    article_page = await self.new_page()
                    ok = await self.goto(article_page, item["url"])
                    if not ok:
                        print(f"      ✗ Article load failed")
                        await article_page.close()
                        continue

                    parsed = await self.parse_article(article_page, item)
                    await article_page.close()

                    if parsed:
                        result_articles.append(parsed)
                        print(f"      ✓ {parsed.word_count} words | byline: {parsed.byline!r}")
                        print(f"        Body: {parsed.body[:120]!r}")
                    else:
                        print(f"      ✗ parse_article returned None")

                    await _asyncio.sleep(1)

                page_num += 1

        return result_articles

    ing = ingester_cls()
    await limited_ingest(ing, "test-id", slug, DATE_FROM, DATE_TO, set())

    print(f"\n  Done.")


async def main():
    for cfg in TESTS:
        try:
            await run_test(cfg)
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()


asyncio.run(main())

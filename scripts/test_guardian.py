"""
Quick test: pull articles for a Guardian journalist and print results.
Usage: python3 scripts/test_guardian.py
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from backend.ingestion.article_ingestion import GuardianIngester
from datetime import datetime

JOURNALIST_NAME = "Marina Hyde"
GUARDIAN_TAG = "profile/marinahyde"
DATE_FROM = datetime(2023, 1, 1)
DATE_TO = datetime(2024, 12, 31)


async def main():
    api_key = os.environ.get("GUARDIAN_API_KEY")
    if not api_key:
        print("ERROR: GUARDIAN_API_KEY not found in .env file")
        return

    print(f"Connecting to Guardian API...")
    ingester = GuardianIngester(api_key=api_key)

    print(f"Pulling articles for: {JOURNALIST_NAME}")
    print(f"Date range: {DATE_FROM.date()} to {DATE_TO.date()}")
    print("---")

    articles, result = await ingester.ingest(
        journalist_id="test",
        guardian_tag=GUARDIAN_TAG,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        existing_guardian_ids=set(),
    )

    await ingester.close()

    print(f"Articles ingested:         {result.articles_ingested}")
    print(f"Skipped (duplicate):       {result.articles_skipped_duplicate}")
    print(f"Skipped (too short):       {result.articles_skipped_short}")
    print(f"Skipped (no body):         {result.articles_skipped_no_body}")
    if result.corpus_start:
        print(f"Corpus range:              {result.corpus_start.date()} to {result.corpus_end.date()}")
    print("---")

    print(f"\nFirst 3 articles:\n")
    for a in articles[:3]:
        print(f"  Headline:   {a.headline}")
        print(f"  Published:  {a.published_at.date()}")
        print(f"  Words:      {a.word_count}")
        print(f"  URL:        {a.url}")
        print()

    if result.errors:
        print("Errors:")
        for e in result.errors:
            print(f"  {e}")


asyncio.run(main())

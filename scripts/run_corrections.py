"""
Run corrections ingestion for MVP cohort.
Matches corrections to journalists via Guardian article URL (exact match).
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import asyncpg
from backend.ingestion.corrections_ingestion import GuardianCorrectionsIngester

DATE_FROM = datetime(2023, 1, 1)
DATE_TO   = datetime(2024, 12, 31)

COHORT = [
    "Marina Hyde",
    "Hugo Lowell",
    "Joan E Greve",
    "Ed Pilkington",
    "Lauren Gambino",
]


async def get_journalist_guardian_ids(conn, journalist_name: str) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT a.guardian_id
        FROM articles a
        JOIN journalists j ON a.journalist_id = j.id
        WHERE j.full_name = $1 AND a.guardian_id IS NOT NULL
        """,
        journalist_name,
    )
    return {r["guardian_id"] for r in rows}


async def main():
    api_key = os.environ["GUARDIAN_API_KEY"]
    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)
    ingester = GuardianCorrectionsIngester(api_key=api_key)

    print("Fetching Guardian corrections articles (2023-2024)...")
    corrections_articles = await ingester.fetch_corrections(DATE_FROM, DATE_TO)
    print(f"Found {len(corrections_articles)} corrections articles\n")

    for name in COHORT:
        print(f"{'─' * 50}")
        print(f"  {name}")

        guardian_ids = await get_journalist_guardian_ids(conn, name)
        if not guardian_ids:
            print(f"  No articles in database — skipping")
            continue

        print(f"  Matching against {len(guardian_ids)} stored article IDs...")
        found = ingester.extract_corrections_by_guardian_id(
            corrections_articles, guardian_ids
        )

        if not found:
            print(f"  No corrections matched.")
        else:
            print(f"  Found {len(found)} correction(s) — classifying...")
            found = await ingester.classify_correction_types(found)
            for c in found:
                print(f"\n  [{c.correction_type.upper()}] {c.corrected_at.date()}")
                print(f"  Original: {c.original_headline}")
                print(f"  Text: {c.correction_text[:200]}")
                print(f"  Source: {c.correction_url}")

    await ingester.close()
    await conn.close()
    print("\nDone.")


asyncio.run(main())

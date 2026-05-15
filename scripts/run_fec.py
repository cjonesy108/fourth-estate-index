"""
Run FEC ingestion for all MVP journalists.
Prints auto-ingestable records and flags anything needing manual review.
"""

import asyncio
from dotenv import load_dotenv
load_dotenv()

from backend.ingestion.fec_ingestion import FECIngester

COHORT = [
    {"full_name": "Marina Hyde",   "variations": ["Hyde, Marina"]},
    {"full_name": "Hugo Lowell",   "variations": ["Lowell, Hugo"]},
    {"full_name": "Joan E Greve",  "variations": ["Greve, Joan", "Joan Greve"]},
    {"full_name": "Ed Pilkington", "variations": ["Pilkington, Ed", "Edward Pilkington"]},
    {"full_name": "Lauren Gambino","variations": ["Gambino, Lauren"]},
]


async def main():
    ingester = FECIngester()

    for journalist in COHORT:
        name = journalist["full_name"]
        print(f"\n{'─' * 50}")
        print(f"  {name}")
        print(f"{'─' * 50}")

        result = await ingester.ingest(
            full_name=name,
            known_variations=journalist.get("variations", []),
        )

        if result.records_auto_ingested:
            print(f"  AUTO-INGEST ({len(result.records_auto_ingested)} records):")
            for r in result.records_auto_ingested:
                print(f"    ${r.amount:,.0f} → {r.recipient_name} ({r.recipient_type})")
                print(f"    Date: {r.contribution_date}  Confidence: {r.confidence:.0f}")
                print(f"    Reason: {r.confidence_reason}")
                print(f"    FEC ID: {r.fec_record_id}")
        else:
            print(f"  No contributions found above auto-ingest threshold.")

        if result.records_for_review:
            print(f"\n  NEEDS MANUAL REVIEW ({len(result.records_for_review)} records):")
            for r in result.records_for_review:
                print(f"    ${r.amount:,.0f} → {r.recipient_name}")
                print(f"    Contributor: {r.contributor_name}  Employer: {r.employer}")
                print(f"    Confidence: {r.confidence:.0f}  Reason: {r.confidence_reason}")

        print(f"\n  Rejected (low confidence): {result.records_rejected}")

    await ingester.close()
    print("\nFEC ingestion complete.")


asyncio.run(main())

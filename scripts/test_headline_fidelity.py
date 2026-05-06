"""
Test the headline fidelity analyzer against a live Guardian corpus.
Pulls articles, runs Claude analysis, prints scores and flagged citations.
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from backend.ingestion.article_ingestion import GuardianIngester
from backend.analysis.headline_fidelity import HeadlineFidelityAnalyzer

JOURNALIST_NAME = "Marina Hyde"
GUARDIAN_TAG = "profile/marinahyde"
DATE_FROM = datetime(2023, 1, 1)
DATE_TO = datetime(2024, 12, 31)

# Analyze a sample — 20 articles is enough to see the pattern
SAMPLE_SIZE = 20


async def main():
    api_key = os.environ.get("GUARDIAN_API_KEY")

    print(f"Step 1: Pulling articles for {JOURNALIST_NAME}...")
    ingester = GuardianIngester(api_key=api_key)
    articles, result = await ingester.ingest(
        journalist_id="test",
        guardian_tag=GUARDIAN_TAG,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        existing_guardian_ids=set(),
    )
    await ingester.close()
    print(f"  Got {len(articles)} articles. Using first {SAMPLE_SIZE} for analysis.")
    print()

    # Build corpus for analyzer — just the fields it needs
    sample = articles[:SAMPLE_SIZE]
    corpus = [
        {
            "body": a.body,
            "headline": a.headline,
            "subheadline": a.subheadline,
            "url": a.url,
        }
        for a in sample
    ]

    print(f"Step 2: Running headline fidelity analysis via Claude...")
    print(f"  Model: claude-sonnet-4-6")
    print(f"  Articles: {len(corpus)}")
    print()

    analyzer = HeadlineFidelityAnalyzer()
    analysis = analyzer.run(corpus)

    print("─" * 60)
    print(f"HEADLINE FIDELITY RESULTS — {JOURNALIST_NAME}")
    print("─" * 60)
    print(f"Dimension score:  {analysis.dimensions.get('headline_fidelity')}")
    print(f"Articles flagged: {analysis.dimensions.get('flagged_count')} of {SAMPLE_SIZE}")
    print(f"Summary:          {analysis.dimensions.get('summary')}")
    print()

    if analysis.citations:
        print(f"FLAGGED CITATIONS ({len(analysis.citations)}):")
        print()
        for i, c in enumerate(analysis.citations, 1):
            # Find the matching article for context
            article = sample[i - 1] if i - 1 < len(sample) else None
            print(f"  [{i}] Flag type:  {c.flag_type}")
            print(f"      Flag score: {c.flag_value}")
            if article:
                print(f"      Headline:   {article['headline'][:80]}" if isinstance(article, dict) else f"      Headline:   {article.headline[:80]}")
            print(f"      Cited text: {c.cited_text[:120]}")
            print()
    else:
        print("No citations flagged.")

    # Citation integrity check
    print(f"Citation integrity: {len(analysis.citations)} citations validated against corpus")


asyncio.run(main())

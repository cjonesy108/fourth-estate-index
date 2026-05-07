"""
Run the full pipeline for all MVP journalists in sequence.
Skips Marina Hyde — already in the database.
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from backend.ingestion.article_ingestion import GuardianIngester
from backend.analysis.headline_fidelity import HeadlineFidelityAnalyzer
from backend.analysis.attribution_analysis import AttributionAnalyzer
from backend.scoring.pillar_scorer import build_pillar_scores
from backend.database.db import (
    get_conn,
    save_journalist,
    save_publication,
    save_articles,
    save_analysis_result,
    save_citations,
    save_pillar_scores,
    get_existing_guardian_ids,
    get_article_id_map,
)

DATE_FROM = datetime(2023, 1, 1)
DATE_TO   = datetime(2024, 12, 31)

PUBLICATION = {
    "name":       "The Guardian",
    "domain":     "theguardian.com",
    "api_source": "guardian",
}

COHORT = [
    {
        "full_name":      "Hugo Lowell",
        "slug":           "hugo-lowell",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/hugo-lowell",
    },
    {
        "full_name":      "Joan E Greve",
        "slug":           "joan-e-greve",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/joan-greve",
    },
    {
        "full_name":      "Ed Pilkington",
        "slug":           "ed-pilkington",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/edpilkington",
    },
    {
        "full_name":      "Lauren Gambino",
        "slug":           "lauren-gambino",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/lauren-gambino",
    },
]


async def run_journalist(conn, publication_id: str, journalist: dict):
    name = journalist["full_name"]
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")

    journalist_id = await save_journalist(conn, **journalist)
    print(f"  ID: {journalist_id}")

    # Ingest
    print(f"  Ingesting articles...")
    existing_ids = await get_existing_guardian_ids(conn, journalist_id)
    ingester = GuardianIngester(api_key=os.environ["GUARDIAN_API_KEY"])
    articles, result = await ingester.ingest(
        journalist_id=journalist_id,
        guardian_tag=journalist["guardian_tag"],
        date_from=DATE_FROM,
        date_to=DATE_TO,
        existing_guardian_ids=existing_ids,
    )
    await ingester.close()
    print(f"  Fetched: {result.articles_ingested}  Skipped: {result.articles_skipped_duplicate + result.articles_skipped_short}")

    if articles:
        saved = await save_articles(conn, journalist_id, publication_id, articles)
        print(f"  Saved to DB: {saved}")

    article_id_map = await get_article_id_map(conn, journalist_id)
    corpus_size = len(article_id_map)
    print(f"  Total corpus: {corpus_size} articles")

    if corpus_size < 10:
        print(f"  ⚠️  Corpus too small — skipping analysis")
        return

    # Analyze — use newly fetched articles if available, otherwise sample from DB records
    # We need the article objects to build the corpus; fetch from DB if none were ingested
    if articles:
        sample = articles[:50]
    else:
        print(f"  No new articles fetched — using existing corpus for analysis")
        # Re-fetch from Guardian to get article objects for analysis
        ingester2 = GuardianIngester(api_key=os.environ["GUARDIAN_API_KEY"])
        all_articles, _ = await ingester2.ingest(
            journalist_id=journalist_id,
            guardian_tag=journalist["guardian_tag"],
            date_from=DATE_FROM,
            date_to=DATE_TO,
            existing_guardian_ids=set(),  # fetch all, we just need objects
        )
        await ingester2.close()
        sample = all_articles[:50]

    if not sample:
        print(f"  ⚠️  No articles available for analysis")
        return

    corpus = [
        {
            "body":        a.body,
            "headline":    a.headline,
            "subheadline": a.subheadline,
            "url":         a.url,
            "guardian_id": a.guardian_id,
        }
        for a in sample
    ]

    dimension_results = {}

    # Headline fidelity
    print(f"  Running headline fidelity analysis on {len(corpus)} articles...")
    hl_analyzer = HeadlineFidelityAnalyzer()
    hl_analysis = hl_analyzer.run(corpus)
    hl_score = hl_analysis.dimensions.get("headline_fidelity")
    print(f"  Headline fidelity: {hl_score}  Flagged: {hl_analysis.dimensions.get('flagged_count', 0)}")
    hl_id = await save_analysis_result(conn, journalist_id, hl_analysis)
    if hl_analysis.citations:
        await save_citations(conn, hl_id, hl_analysis.citations, article_id_map)
    dimension_results["headline_fidelity"] = hl_score

    # Attribution patterns — smaller batch, more verbose output per article
    attribution_corpus = corpus[:25]
    print(f"  Running attribution patterns analysis on {len(attribution_corpus)} articles...")
    at_analyzer = AttributionAnalyzer()
    at_analysis = at_analyzer.run(attribution_corpus)
    at_score = at_analysis.dimensions.get("attribution_patterns")
    print(f"  Attribution patterns: {at_score}  Flagged claims: {at_analysis.dimensions.get('flagged_count', 0)}")
    print(f"  Pattern: {at_analysis.dimensions.get('pattern_summary', '')[:100]}")
    at_id = await save_analysis_result(conn, journalist_id, at_analysis)
    if at_analysis.citations:
        await save_citations(conn, at_id, at_analysis.citations, article_id_map)
    dimension_results["attribution_patterns"] = at_score

    # Score all dimensions together
    scores = build_pillar_scores(dimension_results)
    await save_pillar_scores(
        conn, journalist_id, scores,
        corpus_size=corpus_size,
        methodology_version="1.0",
    )
    print(f"  ✅ Done — Pillar 1: {scores['pillar_1_score']}")


async def main():
    print("Fourth Estate Index — MVP Cohort Pipeline")
    print(f"Date range: {DATE_FROM.date()} to {DATE_TO.date()}")
    print(f"Journalists: {len(COHORT)}")

    conn = await get_conn()
    try:
        publication_id = await save_publication(conn, **PUBLICATION)

        for journalist in COHORT:
            try:
                await run_journalist(conn, publication_id, journalist)
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                continue

        print(f"\n{'─' * 60}")
        print(f"  Pipeline complete.")
        print(f"{'─' * 60}\n")

    finally:
        await conn.close()


asyncio.run(main())

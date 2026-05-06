"""
Full pipeline for one journalist: ingest → analyze → store.
Usage: python3 scripts/run_pipeline.py
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from backend.ingestion.article_ingestion import GuardianIngester
from backend.analysis.headline_fidelity import HeadlineFidelityAnalyzer
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

# ── Journalist config ─────────────────────────────────────
JOURNALIST = {
    "full_name":      "Marina Hyde",
    "slug":           "marina-hyde",
    "primary_outlet": "The Guardian",
    "guardian_tag":   "profile/marinahyde",
}

PUBLICATION = {
    "name":       "The Guardian",
    "domain":     "theguardian.com",
    "api_source": "guardian",
}

DATE_FROM = datetime(2023, 1, 1)
DATE_TO   = datetime(2024, 12, 31)
# ─────────────────────────────────────────────────────────


async def main():
    conn = await get_conn()

    try:
        # ── Step 1: Register journalist and publication ───
        print("Step 1: Registering journalist and publication...")
        journalist_id = await save_journalist(conn, **JOURNALIST)
        publication_id = await save_publication(conn, **PUBLICATION)
        print(f"  Journalist ID: {journalist_id}")
        print(f"  Publication ID: {publication_id}")

        # ── Step 2: Ingest articles ───────────────────────
        print(f"\nStep 2: Ingesting articles from Guardian API...")
        existing_ids = await get_existing_guardian_ids(conn, journalist_id)
        print(f"  Already in database: {len(existing_ids)} articles")

        ingester = GuardianIngester(api_key=os.environ["GUARDIAN_API_KEY"])
        articles, ingest_result = await ingester.ingest(
            journalist_id=journalist_id,
            guardian_tag=JOURNALIST["guardian_tag"],
            date_from=DATE_FROM,
            date_to=DATE_TO,
            existing_guardian_ids=existing_ids,
        )
        await ingester.close()

        print(f"  New articles fetched:  {ingest_result.articles_ingested}")
        print(f"  Skipped (duplicate):   {ingest_result.articles_skipped_duplicate}")
        print(f"  Skipped (too short):   {ingest_result.articles_skipped_short}")

        if articles:
            saved = await save_articles(conn, journalist_id, publication_id, articles)
            print(f"  Saved to database:     {saved}")

        # ── Step 3: Load full corpus from database ────────
        print(f"\nStep 3: Loading corpus for analysis...")
        article_id_map = await get_article_id_map(conn, journalist_id)
        print(f"  Total corpus size: {len(article_id_map)} articles")

        if len(article_id_map) < 10:
            print("  ERROR: Corpus too small for analysis (minimum 10 articles)")
            return

        # Build corpus list from the freshly ingested articles
        # (in production this would query from DB; fine for now)
        all_articles = articles if articles else []
        if not all_articles:
            print("  No new articles to analyze — skipping analysis.")
            print("  (Re-run pipeline to analyze existing corpus)")
            return

        corpus = [
            {
                "body":        a.body,
                "headline":    a.headline,
                "subheadline": a.subheadline,
                "url":         a.url,
                "guardian_id": a.guardian_id,
            }
            for a in all_articles[:50]  # cap at 50 for cost during testing
        ]
        print(f"  Analyzing {len(corpus)} articles")

        # ── Step 4: Run headline fidelity analysis ────────
        print(f"\nStep 4: Running headline fidelity analysis...")
        analyzer = HeadlineFidelityAnalyzer()
        analysis = analyzer.run(corpus)

        print(f"  Score:   {analysis.dimensions.get('headline_fidelity')}")
        print(f"  Flagged: {analysis.dimensions.get('flagged_count')} articles")
        print(f"  Summary: {analysis.dimensions.get('summary')}")

        analysis_id = await save_analysis_result(conn, journalist_id, analysis)
        print(f"  Saved analysis: {analysis_id}")

        if analysis.citations:
            await save_citations(conn, analysis_id, analysis.citations, article_id_map)
            print(f"  Saved {len(analysis.citations)} citations")

        # ── Step 5: Score and store ───────────────────────
        print(f"\nStep 5: Calculating pillar scores...")
        dimension_results = {
            "headline_fidelity": analysis.dimensions.get("headline_fidelity"),
        }
        scores = build_pillar_scores(dimension_results)

        print(f"  Pillar 1 (Seek Truth):    {scores['pillar_1_score']}")
        print(f"  Pillar 2 (Minimize Harm): {scores['pillar_2_score']}")
        print(f"  Pillar 3 (Independence):  {scores['pillar_3_score']}")
        print(f"  Pillar 4 (Accountable):   {scores['pillar_4_score']}")
        print(f"  Composite:                {scores['composite_score']}")

        await save_pillar_scores(
            conn, journalist_id, scores,
            corpus_size=len(article_id_map),
            methodology_version="1.0",
        )
        print(f"  Scores saved.")

        print(f"\nDone. Marina Hyde is in the database.")

    finally:
        await conn.close()


asyncio.run(main())

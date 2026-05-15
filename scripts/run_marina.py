"""
Run full analysis for Marina Hyde — headline fidelity + attribution patterns.
Saves results to database.
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


async def main():
    print("Running full analysis for Marina Hyde...")
    conn = await get_conn()

    publication_id = await save_publication(conn,
        name="The Guardian",
        domain="theguardian.com",
        api_source="guardian",
    )

    journalist_id = await save_journalist(conn,
        full_name="Marina Hyde",
        slug="marina-hyde",
        primary_outlet="The Guardian",
        guardian_tag="profile/marinahyde",
    )
    print(f"Journalist ID: {journalist_id}")

    # Fetch articles
    print("Fetching articles...")
    ingester = GuardianIngester(api_key=os.environ["GUARDIAN_API_KEY"])
    articles, result = await ingester.ingest(
        journalist_id=journalist_id,
        guardian_tag="profile/marinahyde",
        date_from=DATE_FROM,
        date_to=DATE_TO,
        existing_guardian_ids=set(),
    )
    await ingester.close()
    print(f"Fetched: {len(articles)}")

    article_id_map = await get_article_id_map(conn, journalist_id)

    # Build corpus
    sample_50 = articles[:50]
    sample_25 = articles[:25]
    corpus_50 = [{"body": a.body, "headline": a.headline, "subheadline": a.subheadline, "url": a.url, "guardian_id": a.guardian_id} for a in sample_50]
    corpus_25 = [{"body": a.body, "headline": a.headline, "subheadline": a.subheadline, "url": a.url, "guardian_id": a.guardian_id} for a in sample_25]

    dimension_results = {}

    # Headline fidelity
    print("Running headline fidelity analysis...")
    hl = HeadlineFidelityAnalyzer().run(corpus_50)
    hl_score = hl.dimensions.get("headline_fidelity")
    print(f"  Score: {hl_score}  Flagged: {hl.dimensions.get('flagged_count', 0)}")
    hl_id = await save_analysis_result(conn, journalist_id, hl)
    if hl.citations:
        await save_citations(conn, hl_id, hl.citations, article_id_map)
    dimension_results["headline_fidelity"] = hl_score

    # Attribution patterns
    print("Running attribution patterns analysis...")
    at = AttributionAnalyzer().run(corpus_25)
    at_score = at.dimensions.get("attribution_patterns")
    print(f"  Score: {at_score}  Flagged claims: {at.dimensions.get('flagged_count', 0)}")
    print(f"  Pattern: {at.dimensions.get('pattern_summary', '')[:120]}")
    at_id = await save_analysis_result(conn, journalist_id, at)
    if at.citations:
        await save_citations(conn, at_id, at.citations, article_id_map)
    dimension_results["attribution_patterns"] = at_score

    # Score
    scores = build_pillar_scores(dimension_results)
    await save_pillar_scores(conn, journalist_id, scores, corpus_size=len(article_id_map), methodology_version="1.0")

    print(f"\nMarina Hyde — Pillar 1: {scores['pillar_1_score']}")
    print("Done.")
    await conn.close()


asyncio.run(main())

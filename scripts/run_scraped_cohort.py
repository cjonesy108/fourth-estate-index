"""
Run the full pipeline for NY Post and Washington Examiner journalists.
Uses Playwright-based scrapers instead of the Guardian API.

Usage:
    PYTHONPATH=. python3 scripts/run_scraped_cohort.py              # all
    PYTHONPATH=. python3 scripts/run_scraped_cohort.py jon-levine   # single slug
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from backend.ingestion.nypost_ingestion import NYPostIngester
from backend.ingestion.washingtonexaminer_ingestion import WashingtonExaminerIngester
from backend.ingestion.corrections_ingestion import GuardianCorrectionsIngester
from backend.analysis.headline_fidelity import HeadlineFidelityAnalyzer
from backend.analysis.attribution_analysis import AttributionAnalyzer
from backend.analysis.language_patterns import LanguagePatternsAnalyzer
from backend.analysis.source_diversity import SourceDiversityAnalyzer
from backend.scoring.pillar_scorer import build_pillar_scores
from backend.scoring.corrections_scorer import score_corrections
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
    get_articles_for_analysis,
)

DATE_FROM = datetime(2023, 1, 1)
DATE_TO   = datetime(2024, 12, 31)

COHORT = [
    {
        "full_name":      "Jon Levine",
        "slug":           "jon-levine",
        "primary_outlet": "New York Post",
        "author_slug":    "jon-levine",
        "publication": {
            "name":       "New York Post",
            "domain":     "nypost.com",
            "api_source": "nypost",
        },
        "ingester_cls": NYPostIngester,
    },
    {
        "full_name":      "Steven Nelson",
        "slug":           "steven-nelson",
        "primary_outlet": "New York Post",
        "author_slug":    "steven-nelson",
        "publication": {
            "name":       "New York Post",
            "domain":     "nypost.com",
            "api_source": "nypost",
        },
        "ingester_cls": NYPostIngester,
    },
    {
        "full_name":      "Mark Moore",
        "slug":           "mark-moore",
        "primary_outlet": "New York Post",
        "author_slug":    "mark-moore",
        "publication": {
            "name":       "New York Post",
            "domain":     "nypost.com",
            "api_source": "nypost",
        },
        "ingester_cls": NYPostIngester,
    },
    {
        "full_name":      "Anna Giaritelli",
        "slug":           "anna-giaritelli",
        "primary_outlet": "Washington Examiner",
        "author_slug":    "anna-giaritelli",
        "publication": {
            "name":       "Washington Examiner",
            "domain":     "washingtonexaminer.com",
            "api_source": "washingtonexaminer",
        },
        "ingester_cls": WashingtonExaminerIngester,
    },
    {
        "full_name":      "Byron York",
        "slug":           "byron-york",
        "primary_outlet": "Washington Examiner",
        "author_slug":    "byron-york",
        "publication": {
            "name":       "Washington Examiner",
            "domain":     "washingtonexaminer.com",
            "api_source": "washingtonexaminer",
        },
        "ingester_cls": WashingtonExaminerIngester,
    },
    {
        "full_name":      "Sarah Westwood",
        "slug":           "sarah-westwood",
        "primary_outlet": "Washington Examiner",
        "author_slug":    "sarah-westwood",
        "publication": {
            "name":       "Washington Examiner",
            "domain":     "washingtonexaminer.com",
            "api_source": "washingtonexaminer",
        },
        "ingester_cls": WashingtonExaminerIngester,
    },
]


async def run_journalist(conn, publication_id: str, journalist: dict):
    name = journalist["full_name"]
    ingester_cls = journalist["ingester_cls"]
    source_api = journalist["publication"]["api_source"]

    print(f"\n{'─' * 60}")
    print(f"  {name} ({journalist['primary_outlet']})")
    print(f"{'─' * 60}")

    journalist_id = await save_journalist(
        conn,
        full_name=journalist["full_name"],
        slug=journalist["slug"],
        primary_outlet=journalist["primary_outlet"],
    )
    print(f"  ID: {journalist_id}")

    # Ingest via scraper
    print(f"  Scraping articles ({DATE_FROM.year}–{DATE_TO.year})...")
    existing_ids = await get_existing_guardian_ids(conn, journalist_id)

    async with ingester_cls() as ingester:
        articles, result = await ingester.ingest(
            journalist_id=journalist_id,
            author_slug=journalist["author_slug"],
            date_from=DATE_FROM,
            date_to=DATE_TO,
            existing_ids=existing_ids,
        )

    print(f"  Fetched: {result.articles_ingested}  "
          f"Skipped dup: {result.articles_skipped_duplicate}  "
          f"Skipped short: {result.articles_skipped_short}  "
          f"No body: {result.articles_skipped_no_body}")

    if articles:
        saved = await save_articles(conn, journalist_id, publication_id, articles, source_api=source_api)
        print(f"  Saved to DB: {saved}")

    article_id_map = await get_article_id_map(conn, journalist_id)
    corpus_size = len(article_id_map)
    print(f"  Total corpus: {corpus_size} articles")

    if corpus_size < 10:
        print(f"  ⚠️  Corpus too small — skipping analysis")
        return

    # Build corpus for analysis
    if articles:
        corpus = [
            {
                "body":        a.body,
                "headline":    a.headline,
                "subheadline": a.subheadline,
                "url":         a.url,
                "guardian_id": a.guardian_id,
            }
            for a in articles[:50]
        ]
    else:
        print(f"  No new articles — fetching from DB for analysis...")
        corpus = await get_articles_for_analysis(conn, journalist_id, limit=50)
        if not corpus:
            print(f"  No articles in DB — skipping analysis")
            return

    dimension_results = {}

    print(f"  Running headline fidelity ({len(corpus)} articles)...")
    hl_analyzer = HeadlineFidelityAnalyzer()
    hl_analysis = hl_analyzer.run(corpus)
    hl_score = hl_analysis.dimensions.get("headline_fidelity")
    print(f"  Headline fidelity: {hl_score}  Flagged: {hl_analysis.dimensions.get('flagged_count', 0)}")
    hl_id = await save_analysis_result(conn, journalist_id, hl_analysis)
    if hl_analysis.citations:
        await save_citations(conn, hl_id, hl_analysis.citations, article_id_map)
    dimension_results["headline_fidelity"] = hl_score

    attribution_corpus = corpus[:25]
    print(f"  Running attribution patterns ({len(attribution_corpus)} articles)...")
    at_analyzer = AttributionAnalyzer()
    at_analysis = at_analyzer.run(attribution_corpus)
    at_score = at_analysis.dimensions.get("attribution_patterns")
    print(f"  Attribution patterns: {at_score}  Flagged: {at_analysis.dimensions.get('flagged_count', 0)}")
    at_id = await save_analysis_result(conn, journalist_id, at_analysis)
    if at_analysis.citations:
        await save_citations(conn, at_id, at_analysis.citations, article_id_map)
    dimension_results["attribution_patterns"] = at_score

    lp_corpus = corpus[:30]
    print(f"  Running language patterns ({len(lp_corpus)} articles)...")
    lp_analyzer = LanguagePatternsAnalyzer()
    lp_analysis = lp_analyzer.run(lp_corpus)
    lp_score = lp_analysis.dimensions.get("language_patterns")
    print(f"  Language patterns: {lp_score}  Flagged: {lp_analysis.dimensions.get('flagged_count', 0)}")
    lp_id = await save_analysis_result(conn, journalist_id, lp_analysis)
    if lp_analysis.citations:
        await save_citations(conn, lp_id, lp_analysis.citations, article_id_map)
    dimension_results["language_patterns"] = lp_score

    sd_corpus = corpus[:15]
    print(f"  Running source diversity ({len(sd_corpus)} articles)...")
    sd_analyzer = SourceDiversityAnalyzer()
    sd_analysis = sd_analyzer.run(sd_corpus)
    sd_score = sd_analysis.dimensions.get("source_diversity")
    print(f"  Source diversity: {sd_score}  Flagged: {sd_analysis.dimensions.get('flagged_count', 0)}")
    sd_id = await save_analysis_result(conn, journalist_id, sd_analysis)
    if sd_analysis.citations:
        await save_citations(conn, sd_id, sd_analysis.citations, article_id_map)
    dimension_results["source_diversity"] = sd_score

    # Corrections — no outlet-specific ingester yet; treat as zero corrections
    correction_scores = score_corrections([], corpus_size=corpus_size)
    dimension_results["corrections_frequency"] = correction_scores["corrections_frequency"]
    dimension_results["corrections_severity"] = correction_scores["corrections_severity"]
    print(f"  Corrections: none ingested (no outlet scraper yet) — "
          f"frequency: {correction_scores['corrections_frequency']}  severity: {correction_scores['corrections_severity']}")

    scores = build_pillar_scores(dimension_results)
    await save_pillar_scores(
        conn, journalist_id, scores,
        corpus_size=corpus_size,
        methodology_version="1.0",
    )
    print(f"  ✅  P1: {scores['pillar_1_score']}  P2: {scores['pillar_2_score']}  "
          f"P3: {scores['pillar_3_score']}  P4: {scores['pillar_4_score']}  "
          f"Composite: {scores['composite_score']}")


async def main():
    slug_filter = sys.argv[1] if len(sys.argv) > 1 else None
    cohort = [j for j in COHORT if slug_filter is None or j["slug"] == slug_filter]

    if not cohort:
        print(f"No journalist found for slug: {slug_filter}")
        sys.exit(1)

    print("Fourth Estate Index — Scraped Outlet Pipeline")
    print(f"Date range: {DATE_FROM.date()} to {DATE_TO.date()}")
    print(f"Journalists: {len(cohort)}")

    conn = await get_conn()
    try:
        # Cache publication IDs (one upsert per outlet)
        pub_ids: dict[str, str] = {}
        for j in cohort:
            domain = j["publication"]["domain"]
            if domain not in pub_ids:
                pub_ids[domain] = await save_publication(conn, **j["publication"])

        for journalist in cohort:
            pub_id = pub_ids[journalist["publication"]["domain"]]
            try:
                await run_journalist(conn, pub_id, journalist)
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n{'─' * 60}")
        print(f"  Pipeline complete.")
        print(f"{'─' * 60}\n")
    finally:
        await conn.close()


asyncio.run(main())

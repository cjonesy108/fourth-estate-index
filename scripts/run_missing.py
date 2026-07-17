"""
Targeted catch-up run for Hugo Lowell and Marina Hyde.

Hugo Lowell: source_diversity failed (JSON truncation) — re-runs all four
  analyzers and saves a fresh pillar_scores row.

Marina Hyde: ran before language_patterns and source_diversity existed —
  runs only the two missing analyzers and saves a fresh pillar_scores row
  with all dimensions included.
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from backend.ingestion.article_ingestion import GuardianIngester
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
    save_analysis_result,
    save_citations,
    save_pillar_scores,
    save_corrections,
    get_article_id_map,
)

DATE_FROM = datetime(2023, 1, 1)
DATE_TO   = datetime(2024, 12, 31)

PUBLICATION = {
    "name":       "The Guardian",
    "domain":     "theguardian.com",
    "api_source": "guardian",
}


def build_corpus(articles, n):
    return [
        {
            "body":        a.body,
            "headline":    a.headline,
            "subheadline": a.subheadline,
            "url":         a.url,
            "guardian_id": a.guardian_id,
        }
        for a in articles[:n]
    ]


async def run_hugo_lowell(conn, publication_id, corrections_articles, corrections_ingester):
    print("\n──────────────────────────────────────────────────────────")
    print("  Hugo Lowell — full re-run (source diversity fix)")
    print("──────────────────────────────────────────────────────────")

    journalist_id = await save_journalist(conn,
        full_name="Hugo Lowell",
        slug="hugo-lowell",
        primary_outlet="The Guardian",
        guardian_tag="profile/hugo-lowell",
    )

    # Re-fetch articles for analysis objects
    ingester = GuardianIngester(api_key=os.environ["GUARDIAN_API_KEY"])
    articles, _ = await ingester.ingest(
        journalist_id=journalist_id,
        guardian_tag="profile/hugo-lowell",
        date_from=DATE_FROM,
        date_to=DATE_TO,
        existing_guardian_ids=set(),
    )
    await ingester.close()
    print(f"  Fetched {len(articles)} articles for analysis")

    article_id_map = await get_article_id_map(conn, journalist_id)
    corpus_size = len(article_id_map)
    dimension_results = {}

    # Headline fidelity
    corpus = build_corpus(articles, 50)
    print(f"  Headline fidelity ({len(corpus)} articles)...")
    hl = HeadlineFidelityAnalyzer().run(corpus)
    hl_score = hl.dimensions.get("headline_fidelity")
    print(f"    Score: {hl_score}  Flagged: {hl.dimensions.get('flagged_count', 0)}")
    hl_id = await save_analysis_result(conn, journalist_id, hl)
    if hl.citations:
        await save_citations(conn, hl_id, hl.citations, article_id_map)
    dimension_results["headline_fidelity"] = hl_score

    # Attribution
    corpus_25 = build_corpus(articles, 25)
    print(f"  Attribution patterns ({len(corpus_25)} articles)...")
    at = AttributionAnalyzer().run(corpus_25)
    at_score = at.dimensions.get("attribution_patterns")
    print(f"    Score: {at_score}  Flagged: {at.dimensions.get('flagged_count', 0)}")
    at_id = await save_analysis_result(conn, journalist_id, at)
    if at.citations:
        await save_citations(conn, at_id, at.citations, article_id_map)
    dimension_results["attribution_patterns"] = at_score

    # Language patterns
    corpus_30 = build_corpus(articles, 30)
    print(f"  Language patterns ({len(corpus_30)} articles)...")
    lp = LanguagePatternsAnalyzer().run(corpus_30)
    lp_score = lp.dimensions.get("language_patterns")
    print(f"    Score: {lp_score}  Flagged: {lp.dimensions.get('flagged_count', 0)}")
    lp_id = await save_analysis_result(conn, journalist_id, lp)
    if lp.citations:
        await save_citations(conn, lp_id, lp.citations, article_id_map)
    dimension_results["language_patterns"] = lp_score

    # Source diversity — 15 articles to avoid truncation
    corpus_15 = build_corpus(articles, 15)
    print(f"  Source diversity ({len(corpus_15)} articles)...")
    sd = SourceDiversityAnalyzer().run(corpus_15)
    sd_score = sd.dimensions.get("source_diversity")
    print(f"    Score: {sd_score}  Flagged: {sd.dimensions.get('flagged_count', 0)}")
    print(f"    Pattern: {sd.dimensions.get('pattern_summary', '')[:100]}")
    sd_id = await save_analysis_result(conn, journalist_id, sd)
    if sd.citations:
        await save_citations(conn, sd_id, sd.citations, article_id_map)
    dimension_results["source_diversity"] = sd_score

    # Corrections
    print(f"  Matching corrections...")
    journalist_guardian_ids = set(article_id_map.keys())
    matched = corrections_ingester.extract_corrections_by_guardian_id(
        corrections_articles, journalist_guardian_ids
    )
    print(f"  Corrections matched: {len(matched)}")
    if matched:
        matched = await corrections_ingester.classify_correction_types(matched)
        await save_corrections(conn, journalist_id, publication_id, matched, article_id_map)

    correction_scores = score_corrections(
        [{"correction_type": c.correction_type} for c in matched],
        corpus_size=corpus_size,
    )
    dimension_results["corrections_frequency"] = correction_scores["corrections_frequency"]
    dimension_results["corrections_severity"] = correction_scores["corrections_severity"]
    print(f"  Corrections: {correction_scores['corrections_count']} ({correction_scores['corrections_per_100']} per 100)")

    scores = build_pillar_scores(dimension_results)
    await save_pillar_scores(conn, journalist_id, scores, corpus_size=corpus_size, methodology_version="1.0")
    print(f"  ✅ Pillar 1: {scores['pillar_1_score']}  Pillar 2: {scores['pillar_2_score']}  "
          f"Pillar 3: {scores['pillar_3_score']}  Pillar 4: {scores['pillar_4_score']}  "
          f"Composite: {scores['composite_score']}")


async def run_marina_missing(conn, corrections_articles, corrections_ingester):
    print("\n──────────────────────────────────────────────────────────")
    print("  Marina Hyde — adding Pillar 2 & 3 (language + source diversity)")
    print("──────────────────────────────────────────────────────────")

    journalist_id = await save_journalist(conn,
        full_name="Marina Hyde",
        slug="marina-hyde",
        primary_outlet="The Guardian",
        guardian_tag="profile/marinahyde",
    )

    ingester = GuardianIngester(api_key=os.environ["GUARDIAN_API_KEY"])
    articles, _ = await ingester.ingest(
        journalist_id=journalist_id,
        guardian_tag="profile/marinahyde",
        date_from=DATE_FROM,
        date_to=DATE_TO,
        existing_guardian_ids=set(),
    )
    await ingester.close()
    print(f"  Fetched {len(articles)} articles for analysis")

    article_id_map = await get_article_id_map(conn, journalist_id)
    corpus_size = len(article_id_map)

    # Use previously scored dimensions as the baseline
    dimension_results = {
        "headline_fidelity":   0.87,
        "attribution_patterns": 0.80,
        "corrections_frequency": 0.85,
        "corrections_severity":  0.75,
    }

    # Language patterns — new
    corpus_30 = build_corpus(articles, 30)
    print(f"  Language patterns ({len(corpus_30)} articles)...")
    lp = LanguagePatternsAnalyzer().run(corpus_30)
    lp_score = lp.dimensions.get("language_patterns")
    print(f"    Score: {lp_score}  Flagged: {lp.dimensions.get('flagged_count', 0)}")
    print(f"    Pattern: {lp.dimensions.get('pattern_summary', '')[:100]}")
    lp_id = await save_analysis_result(conn, journalist_id, lp)
    if lp.citations:
        await save_citations(conn, lp_id, lp.citations, article_id_map)
    dimension_results["language_patterns"] = lp_score

    # Source diversity — new, 15 articles
    corpus_15 = build_corpus(articles, 15)
    print(f"  Source diversity ({len(corpus_15)} articles)...")
    sd = SourceDiversityAnalyzer().run(corpus_15)
    sd_score = sd.dimensions.get("source_diversity")
    print(f"    Score: {sd_score}  Flagged: {sd.dimensions.get('flagged_count', 0)}")
    print(f"    Pattern: {sd.dimensions.get('pattern_summary', '')[:100]}")
    sd_id = await save_analysis_result(conn, journalist_id, sd)
    if sd.citations:
        await save_citations(conn, sd_id, sd.citations, article_id_map)
    dimension_results["source_diversity"] = sd_score

    scores = build_pillar_scores(dimension_results)
    await save_pillar_scores(conn, journalist_id, scores, corpus_size=corpus_size, methodology_version="1.0")
    print(f"  ✅ Pillar 1: {scores['pillar_1_score']}  Pillar 2: {scores['pillar_2_score']}  "
          f"Pillar 3: {scores['pillar_3_score']}  Pillar 4: {scores['pillar_4_score']}  "
          f"Composite: {scores['composite_score']}")


async def main():
    print("Fourth Estate Index — Targeted catch-up (Hugo Lowell + Marina Hyde)")

    corrections_ingester = GuardianCorrectionsIngester(api_key=os.environ["GUARDIAN_API_KEY"])
    print("\nFetching Guardian corrections (2023–2024)...")
    corrections_articles = await corrections_ingester.fetch_corrections(DATE_FROM, DATE_TO)
    print(f"Corrections articles fetched: {len(corrections_articles)}")

    conn = await get_conn()
    try:
        publication_id = await save_publication(conn, **PUBLICATION)
        await run_hugo_lowell(conn, publication_id, corrections_articles, corrections_ingester)
        await run_marina_missing(conn, corrections_articles, corrections_ingester)

        print("\n──────────────────────────────────────────────────────────")
        print("  Done.")
        print("──────────────────────────────────────────────────────────\n")
    finally:
        await conn.close()
        await corrections_ingester.close()


asyncio.run(main())

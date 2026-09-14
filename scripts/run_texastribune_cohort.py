"""
Ingest and score the Texas Tribune directory cohort from public full text.

Usage:
    PYTHONPATH=. python3 scripts/run_texastribune_cohort.py
    PYTHONPATH=. python3 scripts/run_texastribune_cohort.py eleanor-klibanoff
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.analysis.attribution_analysis import AttributionAnalyzer
from backend.analysis.headline_fidelity import HeadlineFidelityAnalyzer
from backend.analysis.language_patterns import LanguagePatternsAnalyzer
from backend.analysis.source_diversity import SourceDiversityAnalyzer
from backend.database.db import (
    get_article_id_map,
    get_articles_for_analysis,
    get_conn,
    get_existing_guardian_ids,
    save_analysis_result,
    save_articles,
    save_citations,
    save_journalist,
    save_pillar_scores,
    save_publication,
)
from backend.ingestion.texastribune_ingestion import TexasTribuneIngester
from backend.scoring.corrections_scorer import score_corrections
from backend.scoring.pillar_scorer import build_pillar_scores

DATE_FROM = datetime(2023, 1, 1)
DATE_TO = datetime(2026, 9, 1)
ROOT = Path(__file__).resolve().parents[1]


def load_cohort() -> list[dict]:
    extra = json.loads((ROOT / "frontend/data/directory-additions.json").read_text())
    return [j for j in extra.get("journalists", []) if j.get("primary_outlet") == "texas-tribune"]


async def run_journalist(conn, publication_id: str, journalist: dict):
    name = journalist["full_name"]
    slug = journalist["slug"]
    print(f"\n{'─' * 60}")
    print(f"  {name} (The Texas Tribune)")
    print(f"{'─' * 60}")

    journalist_id = await save_journalist(
        conn,
        full_name=name,
        slug=slug,
        primary_outlet="The Texas Tribune",
    )
    print(f"  ID: {journalist_id}")

    existing_ids = await get_existing_guardian_ids(conn, journalist_id)
    async with TexasTribuneIngester() as ingester:
        articles, result = await ingester.ingest(
            journalist_id=journalist_id,
            author_slug=journalist.get("author_slug") or slug,
            date_from=DATE_FROM,
            date_to=DATE_TO,
            existing_ids=existing_ids,
        )

    print(
        f"  Fetched: {result.articles_ingested}  "
        f"Skipped dup: {result.articles_skipped_duplicate}  "
        f"Skipped short: {result.articles_skipped_short}  "
        f"No body: {result.articles_skipped_no_body}"
    )
    if result.errors:
        print(f"  Errors: {result.errors}")

    if articles:
        saved = await save_articles(
            conn, journalist_id, publication_id, articles, source_api="texastribune"
        )
        print(f"  Saved to DB: {saved}")

    article_id_map = await get_article_id_map(conn, journalist_id)
    corpus_size = len(article_id_map)
    print(f"  Total corpus: {corpus_size} articles")

    if corpus_size < 10:
        print("  Corpus too small — listed only, no score")
        await conn.execute(
            "UPDATE journalists SET data_status = $1, updated_at = NOW() WHERE id = $2",
            "collecting",
            journalist_id,
        )
        return

    corpus = await get_articles_for_analysis(conn, journalist_id, limit=50)
    if not corpus:
        print("  No full-text articles — skipping analysis")
        return

    dimension_results = {}

    print(f"  Running headline fidelity ({len(corpus)} articles)...")
    hl_analysis = HeadlineFidelityAnalyzer().run(corpus)
    hl_score = hl_analysis.dimensions.get("headline_fidelity")
    hl_id = await save_analysis_result(conn, journalist_id, hl_analysis)
    if hl_analysis.citations:
        await save_citations(conn, hl_id, hl_analysis.citations, article_id_map)
    dimension_results["headline_fidelity"] = hl_score
    print(f"  Headline fidelity: {hl_score}")

    at_corpus = corpus[:25]
    print(f"  Running attribution patterns ({len(at_corpus)} articles)...")
    at_analysis = AttributionAnalyzer().run(at_corpus)
    at_score = at_analysis.dimensions.get("attribution_patterns")
    at_id = await save_analysis_result(conn, journalist_id, at_analysis)
    if at_analysis.citations:
        await save_citations(conn, at_id, at_analysis.citations, article_id_map)
    dimension_results["attribution_patterns"] = at_score
    print(f"  Attribution patterns: {at_score}")

    lp_corpus = corpus[:30]
    print(f"  Running language patterns ({len(lp_corpus)} articles)...")
    lp_analysis = LanguagePatternsAnalyzer().run(lp_corpus)
    lp_score = lp_analysis.dimensions.get("language_patterns")
    lp_id = await save_analysis_result(conn, journalist_id, lp_analysis)
    if lp_analysis.citations:
        await save_citations(conn, lp_id, lp_analysis.citations, article_id_map)
    dimension_results["language_patterns"] = lp_score
    print(f"  Language patterns: {lp_score}")

    sd_corpus = corpus[:15]
    print(f"  Running source diversity ({len(sd_corpus)} articles)...")
    sd_analysis = SourceDiversityAnalyzer().run(sd_corpus)
    sd_score = sd_analysis.dimensions.get("source_diversity")
    sd_id = await save_analysis_result(conn, journalist_id, sd_analysis)
    if sd_analysis.citations:
        await save_citations(conn, sd_id, sd_analysis.citations, article_id_map)
    dimension_results["source_diversity"] = sd_score
    print(f"  Source diversity: {sd_score}")

    correction_scores = score_corrections([], corpus_size=corpus_size)
    dimension_results["corrections_frequency"] = correction_scores["corrections_frequency"]
    dimension_results["corrections_severity"] = correction_scores["corrections_severity"]

    scores = build_pillar_scores(dimension_results)
    await save_pillar_scores(
        conn,
        journalist_id,
        scores,
        corpus_size=corpus_size,
        methodology_version="1.0",
    )
    await conn.execute(
        "UPDATE journalists SET data_status = $1, updated_at = NOW() WHERE id = $2",
        "scored",
        journalist_id,
    )
    print(
        f"  P1: {scores['pillar_1_score']}  P2: {scores['pillar_2_score']}  "
        f"P3: {scores['pillar_3_score']}  P4: {scores['pillar_4_score']}  "
        f"Composite: {scores['composite_score']}"
    )


async def main():
    slug_filter = sys.argv[1] if len(sys.argv) > 1 else None
    cohort = load_cohort()
    if slug_filter:
        cohort = [j for j in cohort if j["slug"] == slug_filter]
    if not cohort:
        print(f"No Texas Tribune journalist found for slug: {slug_filter}")
        sys.exit(1)

    print("Fourth Estate Index — Texas Tribune pipeline")
    print(f"Date range: {DATE_FROM.date()} to {DATE_TO.date()}")
    print(f"Journalists: {len(cohort)}")

    conn = await get_conn()
    try:
        pub_id = await save_publication(
            conn,
            name="The Texas Tribune",
            domain="texastribune.org",
            api_source="texastribune",
        )
        for journalist in cohort:
            try:
                await run_journalist(conn, pub_id, journalist)
            except Exception as e:
                print(f"  Failed: {e}")
                import traceback
                traceback.print_exc()
        print("\nPipeline complete.\n")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
Ingest and score the ProPublica directory cohort from public full text.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.analysis.attribution_analysis import AttributionAnalyzer
from backend.analysis.headline_fidelity import HeadlineFidelityAnalyzer
from backend.analysis.hedging_language import HedgingLanguageAnalyzer
from backend.analysis.language_patterns import LanguagePatternsAnalyzer
from backend.analysis.sentiment_analysis import SentimentDifferentialAnalyzer
from backend.analysis.source_diversity import SourceDiversityAnalyzer
from backend.database.db import (
    get_article_id_map,
    get_articles_for_analysis,
    get_conn,
    get_existing_guardian_ids,
    save_analysis_result,
    save_articles,
    save_citations,
    save_fec_records,
    save_journalist,
    save_pillar_scores,
    save_publication,
)
from backend.ingestion.fec_ingestion import FECIngester
from backend.ingestion.propublica_ingestion import ProPublicaIngester
from backend.scoring.corrections_scorer import score_corrections
from backend.scoring.fec_scorer import score_financial_conflicts
from backend.scoring.pillar_scorer import build_pillar_scores

DATE_FROM = datetime(2023, 1, 1)
DATE_TO = datetime(2026, 8, 31)
ROOT = Path(__file__).resolve().parents[1]
METHODOLOGY = os.environ.get("METHODOLOGY_VERSION", "1.1-partial")


def load_cohort() -> list[dict]:
    extra = json.loads((ROOT / "frontend/data/directory-additions.json").read_text())
    return [j for j in extra.get("journalists", []) if j.get("primary_outlet") == "propublica"]


async def _run_analyzer(conn, journalist_id, article_id_map, analyzer, corpus, key):
    print(f"  Running {key} ({len(corpus)} articles)...")
    analysis = analyzer.run(corpus)
    score = analysis.dimensions.get(key)
    analysis_id = await save_analysis_result(conn, journalist_id, analysis)
    if analysis.citations:
        await save_citations(conn, analysis_id, analysis.citations, article_id_map)
    print(f"  {key}: {score}")
    return score


async def run_journalist(conn, publication_id: str, journalist: dict):
    name = journalist["full_name"]
    slug = journalist["slug"]
    print(f"\n{'─' * 60}")
    print(f"  {name} (ProPublica)")
    print(f"{'─' * 60}")

    journalist_id = await save_journalist(
        conn, full_name=name, slug=slug, primary_outlet="ProPublica"
    )
    print(f"  ID: {journalist_id}")

    existing_ids = await get_existing_guardian_ids(conn, journalist_id)
    async with ProPublicaIngester() as ingester:
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
    if articles:
        saved = await save_articles(conn, journalist_id, publication_id, articles, source_api="propublica")
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
    dimension_results["headline_fidelity"] = await _run_analyzer(
        conn, journalist_id, article_id_map, HeadlineFidelityAnalyzer(), corpus, "headline_fidelity"
    )
    dimension_results["attribution_patterns"] = await _run_analyzer(
        conn, journalist_id, article_id_map, AttributionAnalyzer(), corpus[:25], "attribution_patterns"
    )
    dimension_results["hedging_language"] = await _run_analyzer(
        conn, journalist_id, article_id_map, HedgingLanguageAnalyzer(), corpus[:25], "hedging_language"
    )
    dimension_results["language_patterns"] = await _run_analyzer(
        conn, journalist_id, article_id_map, LanguagePatternsAnalyzer(), corpus[:30], "language_patterns"
    )
    sentiment_score = await _run_analyzer(
        conn, journalist_id, article_id_map, SentimentDifferentialAnalyzer(), corpus[:30], "sentiment_differential"
    )
    dimension_results["sentiment_differential"] = sentiment_score
    dimension_results["source_diversity"] = await _run_analyzer(
        conn, journalist_id, article_id_map, SourceDiversityAnalyzer(), corpus[:15], "source_diversity"
    )

    fec_looked_up = False
    try:
        fec = FECIngester()
        fec_result = await fec.ingest(full_name=name)
        await fec.close()
        fec_looked_up = True
        if fec_result.records_auto_ingested:
            n = await save_fec_records(conn, journalist_id, fec_result.records_auto_ingested)
            print(f"  FEC saved {n} of {len(fec_result.records_auto_ingested)} auto records")
        else:
            print("  FEC lookup complete — no auto-ingest hits")
    except Exception as e:
        print(f"  FEC lookup failed: {e}")

    stored_fec = await conn.fetch(
        "SELECT amount FROM fec_records WHERE journalist_id = $1", journalist_id
    )
    if stored_fec:
        fec_looked_up = True
    fec_scores = score_financial_conflicts([dict(r) for r in stored_fec], looked_up=fec_looked_up)
    dimension_results["financial_conflicts"] = fec_scores["financial_conflicts"]
    print(
        f"  financial_conflicts={fec_scores['financial_conflicts']} "
        f"count={fec_scores['contribution_count']} looked_up={fec_looked_up}"
    )

    stored_corrections = await conn.fetch(
        "SELECT correction_type, days_to_correction FROM corrections WHERE journalist_id = $1",
        journalist_id,
    )
    ingested = len(stored_corrections) > 0
    correction_scores = score_corrections(
        [dict(r) for r in stored_corrections],
        corpus_size=corpus_size,
        ingested=ingested,
    )
    dimension_results["corrections_frequency"] = correction_scores["corrections_frequency"]
    dimension_results["corrections_severity"] = correction_scores["corrections_severity"]
    dimension_results["corrections_velocity"] = correction_scores.get("corrections_velocity")
    print(f"  Corrections ingested={ingested}")

    scores = build_pillar_scores(dimension_results)
    await save_pillar_scores(
        conn, journalist_id, scores, corpus_size=corpus_size, methodology_version=METHODOLOGY
    )
    status = "scored" if scores.get("composite_score") is not None else "insufficient"
    await conn.execute(
        "UPDATE journalists SET data_status = $1, updated_at = NOW() WHERE id = $2",
        status,
        journalist_id,
    )
    print(
        f"  P1: {scores['pillar_1_score']}  P2: {scores['pillar_2_score']}  "
        f"P3: {scores['pillar_3_score']}  P4: {scores['pillar_4_score']}  "
        f"Composite: {scores['composite_score']}  rubric={scores.get('rubric_status')}"
    )


async def main():
    slug_filter = sys.argv[1] if len(sys.argv) > 1 else None
    cohort = load_cohort()
    if slug_filter:
        cohort = [j for j in cohort if j["slug"] == slug_filter]
    if not cohort:
        print(f"No ProPublica journalist found for slug: {slug_filter}")
        sys.exit(1)

    print("Fourth Estate Index — ProPublica pipeline")
    print(f"Date range: {DATE_FROM.date()} to {DATE_TO.date()}")
    print(f"Journalists: {len(cohort)}")

    conn = await get_conn()
    try:
        pub_id = await save_publication(
            conn, name="ProPublica", domain="propublica.org", api_source="propublica"
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

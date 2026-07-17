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
from backend.ingestion.corrections_ingestion import GuardianCorrectionsIngester
from backend.ingestion.x_ingestion import XIngester
from backend.analysis.headline_fidelity import HeadlineFidelityAnalyzer
from backend.analysis.attribution_analysis import AttributionAnalyzer
from backend.analysis.language_patterns import LanguagePatternsAnalyzer
from backend.analysis.source_diversity import SourceDiversityAnalyzer
from backend.analysis.social_analysis import SocialAnalyzer
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
    save_corrections,
    save_social_posts,
    get_existing_guardian_ids,
    get_existing_post_ids,
    get_social_posts,
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
        "x_handle":       None,  # verify before adding
    },
    {
        "full_name":      "Joan E Greve",
        "slug":           "joan-e-greve",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/joan-greve",
        "x_handle":       None,
    },
    {
        "full_name":      "Ed Pilkington",
        "slug":           "ed-pilkington",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/edpilkington",
        "x_handle":       None,
    },
    {
        "full_name":      "Lauren Gambino",
        "slug":           "lauren-gambino",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/lauren-gambino",
        "x_handle":       None,
    },
    {
        "full_name":      "Stephanie Kirchgaessner",
        "slug":           "stephanie-kirchgaessner",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/stephanie-kirchgaessner",
        "x_handle":       None,
    },
    {
        "full_name":      "Chris McGreal",
        "slug":           "chris-mcgreal",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/chrismcgreal",
        "x_handle":       None,
    },
    {
        "full_name":      "Adam Gabbatt",
        "slug":           "adam-gabbatt",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/adam-gabbatt",
        "x_handle":       None,
    },
    {
        "full_name":      "Michael Sainato",
        "slug":           "michael-sainato",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/michael-sainato",
        "x_handle":       None,
    },
    {
        "full_name":      "Oliver Milman",
        "slug":           "oliver-milman",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/oliver-milman",
        "x_handle":       None,
    },
    {
        "full_name":      "Maanvi Singh",
        "slug":           "maanvi-singh",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/maanvi-singh",
        "x_handle":       None,
    },
    {
        "full_name":      "Richard Luscombe",
        "slug":           "richard-luscombe",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/richardluscombe",
        "x_handle":       None,
    },
    {
        "full_name":      "David Smith",
        "slug":           "david-smith",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/davidsmith",
        "x_handle":       None,
    },
    {
        "full_name":      "Peter Beaumont",
        "slug":           "peter-beaumont",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/peterbeaumont",
        "x_handle":       None,
    },
    {
        "full_name":      "Dharna Noor",
        "slug":           "dharna-noor",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/dharna-noor",
        "x_handle":       None,
    },
    {
        "full_name":      "Leonie Chao-Fong",
        "slug":           "leonie-chao-fong",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/leonie-chao-fong",
        "x_handle":       None,
    },
    {
        "full_name":      "Melody Schreiber",
        "slug":           "melody-schreiber",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/melody-schreiber",
        "x_handle":       None,
    },
    {
        "full_name":      "Poppy Noor",
        "slug":           "poppy-noor",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/poppy-noor",
        "x_handle":       None,
    },
    {
        "full_name":      "Ankita Rao",
        "slug":           "ankita-rao",
        "primary_outlet": "The Guardian",
        "guardian_tag":   "profile/ankita-rao",
        "x_handle":       None,
    },
]


async def run_journalist(conn, publication_id: str, journalist: dict, corrections_articles: list, corrections_ingester: GuardianCorrectionsIngester, x_ingester: XIngester = None):
    name = journalist["full_name"]
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")

    journalist_id = await save_journalist(
        conn,
        full_name=journalist["full_name"],
        slug=journalist["slug"],
        primary_outlet=journalist["primary_outlet"],
        guardian_tag=journalist.get("guardian_tag"),
        x_handle=journalist.get("x_handle"),
    )
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

    # Language patterns — Pillar 2
    lp_corpus = corpus[:30]
    print(f"  Running language patterns analysis on {len(lp_corpus)} articles...")
    lp_analyzer = LanguagePatternsAnalyzer()
    lp_analysis = lp_analyzer.run(lp_corpus)
    lp_score = lp_analysis.dimensions.get("language_patterns")
    print(f"  Language patterns: {lp_score}  Flagged: {lp_analysis.dimensions.get('flagged_count', 0)}")
    lp_id = await save_analysis_result(conn, journalist_id, lp_analysis)
    if lp_analysis.citations:
        await save_citations(conn, lp_id, lp_analysis.citations, article_id_map)
    dimension_results["language_patterns"] = lp_score

    # Source diversity — Pillar 3 (15 articles — verbose output, keep under token limit)
    sd_corpus = corpus[:15]
    print(f"  Running source diversity analysis on {len(sd_corpus)} articles...")
    sd_analyzer = SourceDiversityAnalyzer()
    sd_analysis = sd_analyzer.run(sd_corpus)
    sd_score = sd_analysis.dimensions.get("source_diversity")
    print(f"  Source diversity: {sd_score}  Flagged: {sd_analysis.dimensions.get('flagged_count', 0)}")
    print(f"  Pattern: {sd_analysis.dimensions.get('pattern_summary', '')[:100]}")
    sd_id = await save_analysis_result(conn, journalist_id, sd_analysis)
    if sd_analysis.citations:
        await save_citations(conn, sd_id, sd_analysis.citations, article_id_map)
    dimension_results["source_diversity"] = sd_score

    # Corrections — Pillar 4
    print(f"  Matching corrections...")
    journalist_guardian_ids = set(article_id_map.keys())
    matched_corrections = corrections_ingester.extract_corrections_by_guardian_id(
        corrections_articles, journalist_guardian_ids
    )
    print(f"  Corrections matched: {len(matched_corrections)}")

    if matched_corrections:
        print(f"  Classifying correction types...")
        matched_corrections = await corrections_ingester.classify_correction_types(matched_corrections)
        saved_count = await save_corrections(conn, journalist_id, publication_id, matched_corrections, article_id_map)
        print(f"  Corrections saved: {saved_count}")
        for c in matched_corrections:
            print(f"    [{c.correction_type.upper()}] {c.corrected_at.date()} — {c.correction_text[:80]}")
    else:
        print(f"  No corrections found in corpus window")

    correction_scores = score_corrections(
        [{"correction_type": c.correction_type} for c in matched_corrections],
        corpus_size=corpus_size,
    )
    dimension_results["corrections_frequency"] = correction_scores["corrections_frequency"]
    dimension_results["corrections_severity"] = correction_scores["corrections_severity"]
    print(f"  Corrections frequency score: {correction_scores['corrections_frequency']}  "
          f"Severity score: {correction_scores['corrections_severity']}  "
          f"({correction_scores['corrections_count']} corrections / {correction_scores['corrections_per_100']} per 100 articles)")

    # Social media — Pillar 3 dimension
    x_handle = journalist.get("x_handle")
    if x_ingester and x_handle:
        print(f"  Fetching social posts for @{x_handle}...")
        existing_post_ids = await get_existing_post_ids(conn, journalist_id)
        _, new_posts = await x_ingester.ingest(x_handle, existing_post_ids)
        if new_posts:
            saved_posts = await save_social_posts(conn, journalist_id, new_posts)
            print(f"  Social posts saved: {saved_posts}")
        all_posts = await get_social_posts(conn, journalist_id)
        print(f"  Total social corpus: {len(all_posts)} posts")
        if all_posts:
            social_corpus = [
                {"content": p["content"], "is_reply": p["is_reply"],
                 "is_quote": p["is_quote"], "posted_at": str(p["posted_at"])}
                for p in all_posts
            ]
            sm_analyzer = SocialAnalyzer()
            sm_analysis = sm_analyzer.run(social_corpus)
            if sm_analysis:
                sm_score = sm_analysis.dimensions.get("social_media_independence")
                print(f"  Social media independence: {sm_score}  "
                      f"Advocacy: {sm_analysis.dimensions.get('advocacy_signal')}  "
                      f"Amplification: {sm_analysis.dimensions.get('amplification_pattern')}")
                await save_analysis_result(conn, journalist_id, sm_analysis)
                dimension_results["social_media_independence"] = sm_score
            else:
                print(f"  Social corpus below minimum threshold — skipping")
    else:
        print(f"  No X handle configured — skipping social analysis")

    # Score all dimensions together
    scores = build_pillar_scores(dimension_results)
    await save_pillar_scores(
        conn, journalist_id, scores,
        corpus_size=corpus_size,
        methodology_version="1.0",
    )
    print(f"  ✅ Done — Pillar 1: {scores['pillar_1_score']}  Pillar 4: {scores['pillar_4_score']}  Composite: {scores['composite_score']}")


async def main():
    print("Fourth Estate Index — MVP Cohort Pipeline")
    print(f"Date range: {DATE_FROM.date()} to {DATE_TO.date()}")
    print(f"Journalists: {len(COHORT)}")

    # Fetch corrections once — shared across all journalists
    corrections_ingester = GuardianCorrectionsIngester(api_key=os.environ["GUARDIAN_API_KEY"])
    print(f"\nFetching Guardian corrections (2023–2024)...")
    corrections_articles = await corrections_ingester.fetch_corrections(DATE_FROM, DATE_TO)
    print(f"Corrections articles fetched: {len(corrections_articles)}\n")

    # X ingester — optional, skipped if no bearer token configured
    x_bearer = os.environ.get("X_BEARER_TOKEN")
    x_ingester = XIngester(bearer_token=x_bearer) if x_bearer else None
    if not x_ingester:
        print("X_BEARER_TOKEN not set — social analysis will be skipped\n")

    conn = await get_conn()
    try:
        publication_id = await save_publication(conn, **PUBLICATION)

        for journalist in COHORT:
            try:
                await run_journalist(conn, publication_id, journalist, corrections_articles, corrections_ingester, x_ingester)
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"\n{'─' * 60}")
        print(f"  Pipeline complete.")
        print(f"{'─' * 60}\n")

    finally:
        await conn.close()
        await corrections_ingester.close()


asyncio.run(main())

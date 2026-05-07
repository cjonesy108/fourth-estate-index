"""
Attribution patterns analysis — Pillar 1, Dimension 2.

Measures how consistently journalists attribute factual claims to sources.
Scoring reflects:
  - Base attribution rate (what % of factual claims are sourced?)
  - Source quality (named > institutional anonymous > fully anonymous)
  - Pattern (does anonymous sourcing cluster around specific subjects?)
  - Severity (are unattributed claims central facts or minor color?)

One anonymous source in a careful investigation is different from a
pattern of unattributed central assertions across 50 articles.
The score compounds accordingly.
"""

import json
from backend.analysis.base_analyzer import BaseAnalyzer, Citation

PROMPT_TEMPLATE = """You are analyzing attribution patterns for the Fourth Estate Index, which scores journalists against the SPJ Code of Ethics. The SPJ Code requires journalists to "identify sources clearly" and to verify information regardless of source.

For each article, analyze how factual claims are attributed. Apply this framework:

SOURCE QUALITY TIERS:
- Tier 1 (full credit): Named, on-record individual ("Senator Smith said...")
- Tier 2 (light deduction): Named institution, anonymous individual ("a White House official said...")
- Tier 3 (moderate deduction): Fully anonymous ("sources familiar with the matter said...")
- Tier 4 (flag): Unattributed factual claim — a verifiable fact stated with no source at all
- N/A: Opinion, analysis, or argument clearly presented as such — do not penalize

IMPORTANT DISTINCTIONS:
- Anonymous sourcing is sometimes legitimate and necessary. Note the pattern, not just individual instances.
- Columnists and opinion writers operate differently than news reporters — adjust expectations accordingly.
- Flag unattributed central factual claims (the core assertion of the piece) more heavily than unattributed color detail.

For each article provide:
- attribution_score: 0.0 to 1.0 (1.0 = all claims well attributed)
- tier1_count: named on-record sources
- tier2_count: named institution, anonymous individual
- tier3_count: fully anonymous sources
- tier4_count: unattributed factual claims
- pattern_note: one sentence on the attribution pattern in this article
- flagged_claims: list of unattributed central factual assertions (tier 4 only, verbatim from body)

Then provide:
- dimension_score: overall 0.0-1.0 weighted across all articles
  (compound: base rate penalized by pattern frequency and severity)
- pattern_summary: does anonymous sourcing cluster around specific topics or subjects?
- summary: one sentence overall assessment

Respond in this exact JSON format:
{{
  "articles": [
    {{
      "article_index": 0,
      "attribution_score": 0.90,
      "tier1_count": 4,
      "tier2_count": 1,
      "tier3_count": 0,
      "tier4_count": 0,
      "pattern_note": "Well attributed throughout with named sources.",
      "flagged_claims": []
    }}
  ],
  "dimension_score": 0.82,
  "pattern_summary": "Anonymous sourcing clusters around coverage of X topic.",
  "summary": "One sentence overall assessment."
}}

ARTICLES:
{articles}

Respond with JSON only. No preamble."""


class AttributionAnalyzer(BaseAnalyzer):
    analysis_type = "attribution_patterns"
    max_tokens = 8192  # verbose output — one detailed object per article

    def build_prompt(self, corpus: list[dict]) -> str:
        articles_text = ""
        for i, article in enumerate(corpus):
            articles_text += f"\n[{i}] HEADLINE: {article['headline']}\n"
            # Send up to 1200 words — attribution patterns need more context than headline fidelity
            body_preview = " ".join(article["body"].split()[:1200])
            articles_text += f"BODY: {body_preview}\n"
            articles_text += "---"
        return PROMPT_TEMPLATE.format(articles=articles_text)

    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Claude output was not valid JSON: {e}\n{raw[:200]}")

        citations = []
        tier4_total = 0
        tier3_total = 0

        for item in data.get("articles", []):
            tier4_total += item.get("tier4_count", 0)
            tier3_total += item.get("tier3_count", 0)

            for claim in item.get("flagged_claims", []):
                if claim:
                    citations.append(
                        Citation(
                            cited_text=claim,
                            dimension="attribution_patterns",
                            flag_type="unattributed_factual_claim",
                            flag_value=item.get("attribution_score"),
                            article_index=item.get("article_index"),
                        )
                    )

        dimensions = {
            "attribution_patterns": data.get("dimension_score"),
            "tier3_total": tier3_total,
            "tier4_total": tier4_total,
            "pattern_summary": data.get("pattern_summary"),
            "summary": data.get("summary"),
            "flagged_count": len(citations),
        }

        return dimensions, citations

"""
Hedging language — Pillar 1.

Does the journalist mark uncertainty when facts are not established?
Penalize treating contested or unadjudicated claims as settled fact.
Do not penalize plain statements of documented public record.
"""

import json
from backend.analysis.base_analyzer import BaseAnalyzer, Citation

PROMPT_TEMPLATE = """You are scoring hedging language for the Fourth Estate Index against the SPJ Code of Ethics (Seek Truth and Report It).

Look at the journalist's own voice, not quotes from sources.

WHEN HEDGING IS REQUIRED:
- Criminal allegations before conviction
- Claims a source makes that the journalist has not independently established
- Causation that the body treats as possible or disputed
- Unverified numbers, leaks, or second-hand accounts

WHEN HEDGING IS NOT REQUIRED:
- On-record public documents, court filings described as filings, official statistics
- The journalist's clearly labeled analysis or opinion
- Established historical facts

Flag only missing hedges on claims that are not established. cited_text must be a complete verbatim sentence from the body.

Respond in this exact JSON format:
{{
  "hedging_language": 0.82,
  "flagged_count": 1,
  "pattern_summary": "One sentence.",
  "flags": [
    {{
      "article_index": 0,
      "cited_text": "Exact sentence from the body",
      "flag_type": "missing_hedge",
      "note": "Why this claim needed a hedge"
    }}
  ]
}}

ARTICLES:
{articles}

Respond with JSON only. No preamble."""


class HedgingLanguageAnalyzer(BaseAnalyzer):
    analysis_type = "hedging_language"
    max_tokens = 4096

    def build_prompt(self, corpus: list[dict]) -> str:
        articles_text = ""
        for i, article in enumerate(corpus):
            body_preview = " ".join(article["body"].split()[:900])
            articles_text += f"\n[{i}] HEADLINE: {article['headline']}\nBODY: {body_preview}\n---"
        return PROMPT_TEMPLATE.format(articles=articles_text)

    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        data = json.loads(raw)
        citations = []
        for flag in data.get("flags", []):
            if flag.get("cited_text"):
                citations.append(
                    Citation(
                        cited_text=flag["cited_text"],
                        dimension="hedging_language",
                        flag_type=flag.get("flag_type") or "missing_hedge",
                        flag_value=None,
                        article_index=flag.get("article_index"),
                    )
                )
        return {
            "hedging_language": data.get("hedging_language"),
            "flagged_count": data.get("flagged_count", len(citations)),
            "pattern_summary": data.get("pattern_summary"),
        }, citations

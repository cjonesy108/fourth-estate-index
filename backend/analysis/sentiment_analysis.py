"""
Sentiment differential — Pillar 2: Minimize Harm.

A pattern of different tone for similar conduct on opposed sides.
If the corpus has no identifiable opposed pair, score is None (insufficient),
not 1.0.
"""

import json
from backend.analysis.base_analyzer import BaseAnalyzer, Citation

PROMPT_TEMPLATE = """You are scoring sentiment differential for the Fourth Estate Index against the SPJ Minimize Harm principle.

Compare the journalist's own framing of politically or institutionally opposed subjects who are in comparable roles (two campaigns, two agencies, two companies in the same story type).

DO NOT score:
- Different tone because the underlying facts differ in severity
- Quoted language from sources
- A single harsh piece

If you cannot identify at least one opposed pair with enough coverage, set paired_subjects_found to false and sentiment_differential to null.

cited_text must be a complete verbatim sentence from the body.

Respond in this exact JSON format:
{{
  "paired_subjects_found": true,
  "sentiment_differential": 0.74,
  "pair_summary": "Who was compared and how tone differed",
  "flagged_count": 1,
  "flags": [
    {{
      "article_index": 2,
      "cited_text": "Exact sentence from the body",
      "flag_type": "tone_split",
      "note": "Which side this sentence treats more harshly than a comparable case"
    }}
  ]
}}

ARTICLES:
{articles}

Respond with JSON only. No preamble."""


class SentimentDifferentialAnalyzer(BaseAnalyzer):
    analysis_type = "sentiment_differential"
    max_tokens = 4096

    def build_prompt(self, corpus: list[dict]) -> str:
        articles_text = ""
        for i, article in enumerate(corpus):
            body_preview = " ".join(article["body"].split()[:800])
            articles_text += f"\n[{i}] HEADLINE: {article['headline']}\nBODY: {body_preview}\n---"
        return PROMPT_TEMPLATE.format(articles=articles_text)

    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        data = json.loads(raw)
        found = bool(data.get("paired_subjects_found"))
        score = data.get("sentiment_differential") if found else None
        citations = []
        if found:
            for flag in data.get("flags", []):
                if flag.get("cited_text"):
                    citations.append(
                        Citation(
                            cited_text=flag["cited_text"],
                            dimension="sentiment_differential",
                            flag_type=flag.get("flag_type") or "tone_split",
                            flag_value=None,
                            article_index=flag.get("article_index"),
                        )
                    )
        return {
            "sentiment_differential": score,
            "paired_subjects_found": found,
            "pair_summary": data.get("pair_summary"),
            "flagged_count": data.get("flagged_count", len(citations)),
        }, citations

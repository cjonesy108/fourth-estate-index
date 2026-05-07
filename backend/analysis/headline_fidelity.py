"""
Headline fidelity analysis.

Measures whether headlines accurately represent the article body.
Sensationalized, misleading, or overstated headlines are flagged with citations.

This is the highest-confidence dimension — the relationship between a headline
and its body is objectively verifiable and Claude excels at it.
"""

import json
from backend.analysis.base_analyzer import BaseAnalyzer, Citation

PROMPT_TEMPLATE = """You are analyzing journalistic headline accuracy for the Fourth Estate Index, which scores journalists against the SPJ Code of Ethics.

For each article below, evaluate whether the headline accurately represents what the article body actually reports. Focus on:
- Does the headline overstate certainty? (e.g. "X Causes Y" when body says "X may be linked to Y")
- Does the headline omit crucial qualifiers present in the body?
- Is the headline emotionally loaded in a way not supported by the body's tone?
- Does the headline attribute actions or statements not supported by the body?

Score each article: 1.0 (fully accurate) to 0.0 (significantly misleading).
Only flag articles scoring below 0.7.

When flagging an article, cited_text must be copied verbatim from the body — exact words, exact punctuation, no paraphrasing, no ellipsis, no truncation. It must be a complete sentence that appears word-for-word in the text.

Respond in this exact JSON format:
{{
  "articles": [
    {{
      "article_index": 0,
      "headline_score": 0.95,
      "flagged": false,
      "reason": null,
      "cited_text": null
    }},
    {{
      "article_index": 1,
      "headline_score": 0.45,
      "flagged": true,
      "reason": "Headline states X as fact; body uses 'alleged' throughout",
      "cited_text": "Copy the exact sentence verbatim from the body — do not paraphrase or truncate"
    }}
  ],
  "dimension_score": 0.82,
  "summary": "One sentence summary of the overall pattern"
}}

ARTICLES:
{articles}

Respond with JSON only. No preamble."""


class HeadlineFidelityAnalyzer(BaseAnalyzer):
    analysis_type = "headline_fidelity"

    def build_prompt(self, corpus: list[dict]) -> str:
        articles_text = ""
        for i, article in enumerate(corpus):
            articles_text += f"\n[{i}] HEADLINE: {article['headline']}\n"
            if article.get("subheadline"):
                articles_text += f"SUBHEADLINE: {article['subheadline']}\n"
            # Send first 800 words of body — enough for headline fidelity check
            body_preview = " ".join(article["body"].split()[:800])
            articles_text += f"BODY: {body_preview}\n"
            articles_text += "---"

        return PROMPT_TEMPLATE.format(articles=articles_text)

    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Claude output was not valid JSON: {e}\n{raw[:200]}")

        dimension_score = data.get("dimension_score")
        citations = []

        for item in data.get("articles", []):
            if item.get("flagged") and item.get("cited_text"):
                citations.append(
                    Citation(
                        cited_text=item["cited_text"],
                        dimension="headline_fidelity",
                        flag_type="headline_mismatch",
                        flag_value=item.get("headline_score"),
                        article_index=item.get("article_index"),
                    )
                )

        dimensions = {
            "headline_fidelity": dimension_score,
            "summary": data.get("summary"),
            "flagged_count": sum(1 for a in data.get("articles", []) if a.get("flagged")),
        }

        return dimensions, citations

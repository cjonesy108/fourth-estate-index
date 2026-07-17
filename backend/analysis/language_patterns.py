"""
Language patterns analysis — Pillar 2, Minimize Harm.

Scores whether word choice across the corpus dehumanizes, stigmatizes,
or inflames. Single instances don't count — we look for patterns.

This is NOT sentiment analysis of subjects or events. It is analysis
of the journalist's own language choices and framing.

Columnists and opinion writers (like Marina Hyde) will have stronger
voice — that's expected and is NOT penalized unless the language is
genuinely dehumanizing at a pattern level.

Score: 1.0 = no problematic patterns, 0.0 = systematic dehumanizing language.
"""

import json
from backend.analysis.base_analyzer import BaseAnalyzer, Citation

PROMPT_TEMPLATE = """You are analyzing language patterns for the Fourth Estate Index, which scores journalists against the SPJ Code of Ethics. The SPJ Code requires journalists to minimize harm and avoid dehumanizing or stigmatizing language.

You are analyzing the journalist's OWN word choices — not the events they cover, not the people they quote. You are looking at how the journalist themselves frames, describes, and characterizes people, groups, and situations.

WHAT TO LOOK FOR (patterns across the corpus, not isolated instances):
- Dehumanizing language: terms that strip personhood from groups or individuals
- Stigmatizing language: framing that systematically shames, pathologizes, or "others" a group
- Inflammatory language: consistent use of emotionally loaded terms beyond what the facts support
- Othering: language that consistently marks one group as alien, threatening, or less than

CRITICAL DISTINCTIONS:
- Strong opinion writing and satirical voice are NOT violations. Columnists are expected to have a point of view.
- Describing documented wrongdoing in strong terms is NOT dehumanizing. A journalist calling a policy "cruel" based on documented evidence is not a language pattern violation.
- Only flag patterns — recurring choices across multiple articles. A single charged phrase in isolation does not qualify unless it is egregiously dehumanizing.
- Do not flag language that merely quotes others. Flag only the journalist's own framing.

PATTERN TYPES:
- dehumanizing: language that strips personhood ("vermin", "animals", "swarm", "invasion" applied to people)
- stigmatizing: systematic shaming or pathologizing of a group (mental illness framing, criminality framing without basis)
- inflammatory: consistent use of emotionally escalating language that exceeds what the evidence supports
- othering: persistent framing of a group as alien, threatening, or categorically different

For each article, identify any instances of the journalist's own language that fit a pattern type. Only cite language that appears verbatim in the text — exact sentence, no paraphrasing.

Then provide:
- language_patterns_score: 0.0 to 1.0 for the full corpus (1.0 = no problematic patterns)
- flagged_count: total number of flagged instances
- pattern_summary: one sentence describing the overall pattern, or confirming a clean corpus
- flags: list of flagged instances

Respond in this exact JSON format:
{{
  "language_patterns_score": 0.95,
  "flagged_count": 0,
  "pattern_summary": "No dehumanizing or stigmatizing language patterns identified across the corpus.",
  "flags": [
    {{
      "article_index": 2,
      "cited_text": "Exact verbatim sentence from the article body — do not paraphrase or truncate",
      "pattern_type": "dehumanizing",
      "note": "Brief explanation of why this qualifies as a pattern-level concern"
    }}
  ]
}}

ARTICLES:
{articles}

Respond with JSON only. No preamble."""


class LanguagePatternsAnalyzer(BaseAnalyzer):
    analysis_type = "language_patterns"
    max_tokens = 4096

    def build_prompt(self, corpus: list[dict]) -> str:
        articles_text = ""
        for i, article in enumerate(corpus):
            articles_text += f"\n[{i}] HEADLINE: {article['headline']}\n"
            # 1000 words — enough to assess language patterns without overwhelming the context
            body_preview = " ".join(article["body"].split()[:1000])
            articles_text += f"BODY: {body_preview}\n"
            articles_text += "---"
        return PROMPT_TEMPLATE.format(articles=articles_text)

    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Claude output was not valid JSON: {e}\n{raw[:200]}")

        citations = []

        for flag in data.get("flags", []):
            if flag.get("cited_text"):
                citations.append(
                    Citation(
                        cited_text=flag["cited_text"],
                        dimension="language_patterns",
                        flag_type=flag.get("pattern_type"),
                        flag_value=None,
                        article_index=flag.get("article_index"),
                    )
                )

        dimensions = {
            "language_patterns": data.get("language_patterns_score"),
            "flagged_count": data.get("flagged_count", len(citations)),
            "pattern_summary": data.get("pattern_summary"),
        }

        return dimensions, citations

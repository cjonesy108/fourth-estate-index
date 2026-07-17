"""
Source diversity analysis — Pillar 3, Act Independently.

Scores whether the journalist draws from a diverse range of source types,
or overrelies on a narrow institutional set.

Three scoring axes:
  (a) Type diversity — are multiple source categories represented?
  (b) Institutional diversity — is there overreliance on a single org/agency/party?
  (c) Perspective diversity — are opposing viewpoints sourced?

Score: 1.0 = excellent diversity across all three axes,
       0.0 = single-source monoculture.
"""

import json
from backend.analysis.base_analyzer import BaseAnalyzer, Citation

PROMPT_TEMPLATE = """You are analyzing source diversity for the Fourth Estate Index, which scores journalists against the SPJ Code of Ethics. The SPJ Code requires journalists to "act independently" and seek a diversity of perspectives.

For each article, identify and classify all sources the journalist quotes, cites, or attributes claims to. Classify them using these categories:

SOURCE TYPES:
- named_official: Named government official, politician, law enforcement, or institutional spokesperson ("Secretary Smith said...", "NYPD Commissioner Jones stated...")
- named_academic: Named researcher, academic, scientist, or recognized subject-matter expert
- named_advocate: Named representative of an NGO, advocacy group, union, or civil society org
- named_individual: Named private citizen, eyewitness, victim, or non-institutional person
- anonymous_official: Anonymous government or institutional source ("a White House official said...", "sources in the department...")
- anonymous_individual: Anonymous private person ("a witness who asked not to be named...")
- unattributed: Factual claim with no attribution at all

For the full corpus, assess:
1. Type diversity: How many different source categories are used? A journalist who only ever quotes named officials scores lower than one who regularly includes advocates, academics, and individuals.
2. Institutional diversity: Does the journalist overrely on a single institution, party, or agency? (e.g. 80% of all named officials are from one government department)
3. Perspective diversity: Are opposing viewpoints sought and included? A story with only one side of a genuine controversy scores lower.

Flag overreliance patterns with verbatim citations showing the sourcing pattern.

FLAG TYPES:
- overreliance: Heavy concentration on a single source type or institution (cite a representative example sentence)
- single_perspective: Story covers a genuine controversy but only one side is sourced (cite a claim that goes unchallenged)
- anonymous_cluster: Significant cluster of anonymous sourcing in a way that reduces accountability (cite example)

Respond in this exact JSON format:
{{
  "source_diversity_score": 0.78,
  "flagged_count": 2,
  "source_type_breakdown": {{
    "named_official": 42,
    "named_academic": 8,
    "named_advocate": 5,
    "named_individual": 11,
    "anonymous_official": 17,
    "anonymous_individual": 3,
    "unattributed": 9
  }},
  "pattern_summary": "Heavy reliance on named and anonymous government officials; limited academic and civil society sourcing.",
  "flags": [
    {{
      "article_index": 3,
      "cited_text": "Exact verbatim sentence from the article body — do not paraphrase or truncate",
      "flag_type": "overreliance",
      "note": "Brief explanation of the sourcing concern"
    }}
  ]
}}

ARTICLES:
{articles}

Respond with JSON only. No preamble."""


class SourceDiversityAnalyzer(BaseAnalyzer):
    analysis_type = "source_diversity"
    max_tokens = 8192  # source lists can be verbose across 25 articles

    def build_prompt(self, corpus: list[dict]) -> str:
        articles_text = ""
        for i, article in enumerate(corpus):
            articles_text += f"\n[{i}] HEADLINE: {article['headline']}\n"
            # 1200 words — source analysis needs enough article body to identify all sources
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

        for flag in data.get("flags", []):
            if flag.get("cited_text"):
                citations.append(
                    Citation(
                        cited_text=flag["cited_text"],
                        dimension="source_diversity",
                        flag_type=flag.get("flag_type"),
                        flag_value=None,
                        article_index=flag.get("article_index"),
                    )
                )

        breakdown = data.get("source_type_breakdown", {})

        dimensions = {
            "source_diversity": data.get("source_diversity_score"),
            "flagged_count": data.get("flagged_count", len(citations)),
            "source_type_breakdown": breakdown,
            "named_official_count": breakdown.get("named_official", 0),
            "named_academic_count": breakdown.get("named_academic", 0),
            "named_advocate_count": breakdown.get("named_advocate", 0),
            "named_individual_count": breakdown.get("named_individual", 0),
            "anonymous_official_count": breakdown.get("anonymous_official", 0),
            "anonymous_individual_count": breakdown.get("anonymous_individual", 0),
            "unattributed_count": breakdown.get("unattributed", 0),
            "pattern_summary": data.get("pattern_summary"),
        }

        return dimensions, citations

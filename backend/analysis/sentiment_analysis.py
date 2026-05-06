"""
Sentiment differential analysis — Pillar 2: Minimize Harm.

Measures whether a journalist applies meaningfully different tone or
word choice when covering politically or ideologically opposed subjects.

A single harsh article proves nothing. A consistent pattern across the
corpus — where similar events receive different emotional treatment
depending on the subject — is what this analysis surfaces.

TODO: Implement. Requires minimum 20 articles and identifiable
paired subjects (e.g. coverage of two opposing political figures).
"""

from backend.analysis.base_analyzer import BaseAnalyzer, Citation


class SentimentDifferentialAnalyzer(BaseAnalyzer):
    analysis_type = "sentiment_differential"

    def build_prompt(self, corpus: list[dict]) -> str:
        raise NotImplementedError("Sentiment differential analysis not yet implemented")

    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        raise NotImplementedError

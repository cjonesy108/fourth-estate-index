"""
Source diversity and attribution analysis — Pillars 1 & 3.

Two related dimensions:
  attribution_patterns: How consistently are factual claims attributed to named sources?
  source_diversity: How broad is the range of sources cited across the corpus?

TODO: Implement.
"""

from backend.analysis.base_analyzer import BaseAnalyzer, Citation


class SourceAnalyzer(BaseAnalyzer):
    analysis_type = "source_analysis"

    def build_prompt(self, corpus: list[dict]) -> str:
        raise NotImplementedError("Source analysis not yet implemented")

    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        raise NotImplementedError

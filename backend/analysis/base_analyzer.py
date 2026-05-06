"""
Base class for all analysis modules.
Every analyzer accepts a corpus, runs a versioned prompt against Claude,
parses structured output, and returns scored dimensions with citations.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

import anthropic

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    cited_text: str
    dimension: str
    flag_type: Optional[str]
    flag_value: Optional[float]
    article_id: Optional[str] = None
    social_post_id: Optional[str] = None


@dataclass
class AnalysisResult:
    analysis_type: str
    methodology_version: str
    model_id: str
    prompt_version: str
    corpus_size: int
    dimensions: dict[str, Any]  # dimension name → score or None
    citations: list[Citation]
    raw_output: dict


class BaseAnalyzer(ABC):
    analysis_type: str
    prompt_version: str = "1.0"

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = "claude-sonnet-4-6"
        self.methodology_version = os.environ.get("METHODOLOGY_VERSION", "1.0")

    @abstractmethod
    def build_prompt(self, corpus: list[dict]) -> str:
        """Build the analysis prompt for this corpus."""

    @abstractmethod
    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        """
        Parse Claude's structured response into (dimensions, citations).
        Must raise ValueError if output is malformed.
        """

    def run(self, corpus: list[dict]) -> AnalysisResult:
        prompt = self.build_prompt(corpus)
        logger.info(
            f"Running {self.analysis_type} analysis on {len(corpus)} items "
            f"model={self.model} prompt_v={self.prompt_version}"
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = message.content[0].text
        # Extract JSON — find the outermost { } regardless of any wrapping
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        cleaned = raw_text[start:end + 1] if start != -1 and end != -1 else raw_text
        dimensions, citations = self.parse_output(cleaned)

        # Validate citations before returning
        valid_citations = self.validate_citations(citations, corpus)
        dropped = len(citations) - len(valid_citations)
        if dropped:
            logger.warning(f"{dropped} citations dropped — text not found in corpus")

        return AnalysisResult(
            analysis_type=self.analysis_type,
            methodology_version=self.methodology_version,
            model_id=self.model,
            prompt_version=self.prompt_version,
            corpus_size=len(corpus),
            dimensions=dimensions,
            citations=valid_citations,
            raw_output={"text": raw_text},
        )

    def validate_citations(
        self, citations: list[Citation], corpus: list[dict]
    ) -> list[Citation]:
        """
        Every citation must be traceable to the corpus.
        This is the audit trail integrity check — no hallucinated sources.

        We normalize whitespace before matching to account for HTML stripping
        artifacts. We also try a sliding 10-word window match so that minor
        truncation by Claude doesn't drop a legitimate citation.
        """
        corpus_text = self._normalize(
            " ".join(
                item.get("body", "") + " " + item.get("content", "")
                for item in corpus
            )
        )
        valid = []
        for c in citations:
            if not c.cited_text:
                continue
            normalized = self._normalize(c.cited_text)
            if self._is_in_corpus(normalized, corpus_text):
                valid.append(c)
            else:
                logger.warning(f"Citation not found in corpus: {c.cited_text[:80]}...")
        return valid

    def _normalize(self, text: str) -> str:
        import re
        return re.sub(r"\s+", " ", text).strip().lower()

    def _is_in_corpus(self, cited: str, corpus: str) -> bool:
        # Exact match after normalization
        if cited in corpus:
            return True
        # Sliding window: check if any 10 consecutive words from the citation
        # appear in the corpus — catches minor truncation or ellipsis
        words = cited.split()
        if len(words) >= 10:
            for i in range(len(words) - 9):
                window = " ".join(words[i:i + 10])
                if window in corpus:
                    return True
        return False

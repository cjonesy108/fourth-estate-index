"""
Base class for all analysis modules.
Every analyzer accepts a corpus, runs a versioned prompt against Grok,
parses structured output, and returns scored dimensions with citations.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

XAI_BASE = os.environ.get("XAI_API_BASE", "https://api.x.ai/v1")


@dataclass
class Citation:
    cited_text: str
    dimension: str
    flag_type: Optional[str]
    flag_value: Optional[float]
    article_id: Optional[str] = None       # set to guardian_id after parsing
    social_post_id: Optional[str] = None
    article_index: Optional[int] = None    # index into corpus list


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
    max_tokens: int = 4096  # override in subclasses that produce verbose output

    def __init__(self):
        self.api_key = os.environ.get("XAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Missing XAI_API_KEY — add it as a GitHub Actions secret")
        self.model = os.environ.get("SCORER_MODEL", "grok-4.6")
        self.methodology_version = os.environ.get("METHODOLOGY_VERSION", "1.0-grok")

    @abstractmethod
    def build_prompt(self, corpus: list[dict]) -> str:
        """Build the analysis prompt for this corpus."""

    @abstractmethod
    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        """
        Parse the model's structured response into (dimensions, citations).
        Must raise ValueError if output is malformed.
        """

    def _complete(self, prompt: str) -> str:
        resp = httpx.post(
            f"{XAI_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "reasoning_effort": os.environ.get("SCORER_REASONING", "low"),
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=180.0,
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"xAI API {resp.status_code}: {resp.text[:400]}"
            ) from e
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected xAI response shape: {data!r}") from e

    def run(self, corpus: list[dict]) -> AnalysisResult:
        prompt = self.build_prompt(corpus)
        logger.info(
            f"Running {self.analysis_type} analysis on {len(corpus)} items "
            f"model={self.model} prompt_v={self.prompt_version}"
        )

        raw_text = self._complete(prompt)
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        cleaned = raw_text[start:end + 1] if start != -1 and end != -1 else raw_text
        dimensions, citations = self.parse_output(cleaned)

        for c in citations:
            if c.article_index is not None and c.article_index < len(corpus):
                c.article_id = corpus[c.article_index].get("guardian_id")

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
        if cited in corpus:
            return True
        words = cited.split()
        if len(words) >= 10:
            for i in range(len(words) - 9):
                window = " ".join(words[i:i + 10])
                if window in corpus:
                    return True
        return False

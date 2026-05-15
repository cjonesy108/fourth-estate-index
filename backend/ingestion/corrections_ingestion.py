"""
Corrections ingestion — The Guardian corrections page.

The Guardian publishes corrections and clarifications at:
https://www.theguardian.com/theguardian/series/corrections-and-clarifications

Each entry is a dated article containing one or more corrections.
We parse each entry, match corrections to journalists by byline mention,
and classify correction type using Claude.

Guardian corrections format:
- Published as articles in the corrections series
- Each article may contain multiple corrections
- Corrections reference the original article by headline or link
- Byline of the corrected journalist is usually mentioned in the text
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GUARDIAN_BASE = "https://content.guardianapis.com"
CORRECTIONS_TAG = "theguardian/series/corrections-and-clarifications"


@dataclass
class ParsedCorrection:
    correction_text: str
    correction_type: str        # factual | clarification | attribution | omission
    corrected_at: datetime
    correction_url: str
    original_headline: Optional[str]
    journalist_name_mentioned: Optional[str]
    days_to_correction: Optional[int]


class GuardianCorrectionsIngester:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def fetch_corrections(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> list[dict]:
        """Fetch all corrections articles from Guardian API."""
        corrections_articles = []
        page = 1

        while True:
            params = {
                "tag": CORRECTIONS_TAG,
                "from-date": date_from.strftime("%Y-%m-%d"),
                "to-date": date_to.strftime("%Y-%m-%d"),
                "show-fields": "body,headline",
                "page-size": 50,
                "page": page,
                "api-key": self.api_key,
            }

            try:
                resp = await self.client.get(f"{GUARDIAN_BASE}/search", params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"Corrections fetch error page {page}: {e}")
                break

            response = data.get("response", {})
            results = response.get("results", [])
            corrections_articles.extend(results)

            if page >= response.get("pages", 1):
                break
            page += 1
            await asyncio.sleep(0.3)

        logger.info(f"Fetched {len(corrections_articles)} corrections articles")
        return corrections_articles

    def extract_corrections_by_guardian_id(
        self,
        corrections_articles: list[dict],
        journalist_guardian_ids: set[str],
    ) -> list[ParsedCorrection]:
        """
        Match corrections to a journalist's articles by Guardian article URL.

        Each correction embeds a link to the original article. We extract
        those URLs, convert to guardian_id format, and check against the
        journalist's stored article IDs. This is an exact match — no ambiguity.
        """
        found = []
        guardian_base = "https://www.theguardian.com/"

        for article in corrections_articles:
            fields = article.get("fields", {})
            body_html = fields.get("body", "")
            if not body_html:
                continue

            pub_date_str = article.get("webPublicationDate", "")
            try:
                corrected_at = datetime.fromisoformat(
                    pub_date_str.replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except (ValueError, AttributeError):
                corrected_at = datetime.now()

            # Split into paragraph-level correction entries (keep HTML for URL extraction)
            paragraphs = re.split(r'</p>\s*<p>', body_html)

            for para in paragraphs:
                # Extract all guardian.com links from this paragraph
                links = re.findall(
                    r'href="(https://www\.theguardian\.com/[^"]+)"', para
                )

                for link in links:
                    # Convert URL to guardian_id (strip base URL)
                    guardian_id = link.replace(guardian_base, "").rstrip("/")

                    if guardian_id in journalist_guardian_ids:
                        # This correction references one of our journalist's articles
                        correction_text = self._strip_html(para).strip()

                        # Skip the "Other recently amended articles include" list items
                        # (no actual correction text, just article titles)
                        if len(correction_text) < 60:
                            continue

                        # Extract the linked article's anchor text as headline
                        headline_match = re.search(
                            rf'href="{re.escape(link)}">([^<]+)<', para
                        )
                        original_headline = headline_match.group(1) if headline_match else None

                        found.append(ParsedCorrection(
                            correction_text=correction_text,
                            correction_type="clarification",
                            corrected_at=corrected_at,
                            correction_url=article.get("webUrl", ""),
                            original_headline=original_headline,
                            journalist_name_mentioned=None,
                            days_to_correction=None,
                        ))
                        break  # one match per paragraph is enough

        return found

    async def classify_correction_types(
        self, corrections: list[ParsedCorrection]
    ) -> list[ParsedCorrection]:
        """Use Claude to classify each correction type."""
        if not corrections:
            return corrections

        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        for correction in corrections:
            try:
                message = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=100,
                    messages=[{
                        "role": "user",
                        "content": f"""Classify this correction into exactly one category:
- factual: incorrect fact was stated
- clarification: statement was ambiguous or misleading but not factually wrong
- attribution: wrong person credited or quoted
- omission: important information was left out

Correction text: {correction.correction_text[:500]}

Respond with one word only: factual, clarification, attribution, or omission."""
                    }]
                )
                correction.correction_type = message.content[0].text.strip().lower()
                if correction.correction_type not in ["factual", "clarification", "attribution", "omission"]:
                    correction.correction_type = "clarification"
            except Exception as e:
                logger.warning(f"Classification failed: {e}")

            await asyncio.sleep(0.2)

        return corrections

    def _name_in_text(self, name_parts: list[str], text: str) -> bool:
        """Check if enough parts of a name appear in the text."""
        matches = sum(1 for part in name_parts if len(part) > 2 and part in text)
        return matches >= min(2, len(name_parts))

    def _split_corrections(self, body: str) -> list[str]:
        """Split a corrections article into individual correction entries."""
        # Guardian separates corrections with bullets, line breaks, or numbered lists
        entries = re.split(r'\n{2,}|•|\d+\.\s', body)
        return [e.strip() for e in entries if len(e.strip()) > 50]

    def _strip_html(self, html: str) -> str:
        clean = re.sub(r'<[^>]+>', ' ', html)
        return re.sub(r'\s+', ' ', clean).strip()

    def _extract_original_headline(self, text: str) -> Optional[str]:
        """Try to extract the original article headline from the correction text."""
        patterns = [
            r'"([^"]{10,100})"',
            r"'([^']{10,100})'",
            r"article[d\s]+titled?\s+[\"']([^\"']{10,100})[\"']",
            r"headline[d\s]+[\"']([^\"']{10,100})[\"']",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

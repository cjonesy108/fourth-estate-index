"""
FEC contribution record ingestion — api.fec.gov (free, no key required).

Searches FEC individual contribution records by journalist name.
Applies fuzzy matching and employer cross-reference to minimize false positives.

Critical rule: a record is only attached to a journalist profile after
confidence threshold is met OR manual verification is complete.
False positives are a credibility-destroying error.

FEC API docs: https://api.fec.gov/api/v1/
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

import httpx
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

FEC_BASE = "https://api.fec.gov/v1"

# Confidence thresholds
AUTO_INGEST_THRESHOLD = 90   # auto-ingest above this
REVIEW_THRESHOLD = 70        # queue for manual review between 70-90
# Below 70: reject silently

GUARDIAN_EMPLOYER_TERMS = [
    "guardian", "guardian news", "guardian media", "guardian us",
    "guardian news & media", "guardian news and media",
]


@dataclass
class FECRecord:
    contributor_name: str
    recipient_name: str
    recipient_type: str       # candidate | pac | party
    amount: float
    contribution_date: str
    fec_record_id: str
    confidence: float
    confidence_reason: str
    employer: Optional[str]
    occupation: Optional[str]


@dataclass
class FECIngestionResult:
    records_auto_ingested: list[FECRecord]
    records_for_review: list[FECRecord]
    records_rejected: int
    search_names_used: list[str]


class FECIngester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def ingest(
        self,
        full_name: str,
        known_variations: Optional[list[str]] = None,
    ) -> FECIngestionResult:
        """
        Search FEC records for a journalist.
        Returns auto-ingestable records and records needing manual review separately.
        """
        search_names = [full_name] + (known_variations or [])
        all_records: list[FECRecord] = []

        for name in search_names:
            logger.info(f"Searching FEC for: {name}")
            records = await self._search_by_name(name, full_name)
            all_records.extend(records)
            await asyncio.sleep(0.5)

        # Deduplicate by fec_record_id, keep highest confidence
        seen = {}
        for r in all_records:
            if r.fec_record_id not in seen or r.confidence > seen[r.fec_record_id].confidence:
                seen[r.fec_record_id] = r

        deduped = list(seen.values())

        auto = [r for r in deduped if r.confidence >= AUTO_INGEST_THRESHOLD]
        review = [r for r in deduped if REVIEW_THRESHOLD <= r.confidence < AUTO_INGEST_THRESHOLD]
        rejected = len([r for r in deduped if r.confidence < REVIEW_THRESHOLD])

        logger.info(
            f"{full_name}: {len(auto)} auto-ingest, "
            f"{len(review)} for review, {rejected} rejected"
        )

        return FECIngestionResult(
            records_auto_ingested=auto,
            records_for_review=review,
            records_rejected=rejected,
            search_names_used=search_names,
        )

    async def _search_by_name(
        self, search_name: str, canonical_name: str
    ) -> list[FECRecord]:
        """Search FEC schedule A (individual contributions) by contributor name."""
        try:
            resp = await self.client.get(
                f"{FEC_BASE}/schedules/schedule_a/",
                params={
                    "contributor_name": search_name,
                    "per_page": 100,
                    "sort": "-contribution_receipt_date",
                    "api_key": "DEMO_KEY",  # FEC allows DEMO_KEY for low volume
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"FEC API error for '{search_name}': {e}")
            return []

        records = []
        for item in data.get("results", []):
            record = self._evaluate(item, canonical_name)
            if record:
                records.append(record)

        return records

    def _evaluate(self, item: dict, canonical_name: str) -> Optional[FECRecord]:
        """Score a FEC result for likelihood it belongs to our journalist."""
        contributor = item.get("contributor_name", "")
        employer = item.get("contributor_employer", "") or ""
        occupation = item.get("contributor_occupation", "") or ""
        amount = item.get("contribution_receipt_amount", 0) or 0
        receipt_date = item.get("contribution_receipt_date", "")
        transaction_id = item.get("transaction_id", "")

        if not contributor or not transaction_id:
            return None

        # Skip small-dollar contributions unlikely to be journalists
        if abs(amount) < 1:
            return None

        # Name match score
        name_score = max(
            fuzz.token_sort_ratio(canonical_name.lower(), contributor.lower()),
            fuzz.token_set_ratio(canonical_name.lower(), contributor.lower()),
        )

        # Employer match boost
        employer_match = any(
            term in employer.lower() for term in GUARDIAN_EMPLOYER_TERMS
        )
        employer_score = 30 if employer_match else 0

        # Occupation boost — journalists often list "journalist", "reporter", "writer"
        journalist_terms = ["journalist", "reporter", "writer", "editor", "correspondent"]
        occupation_match = any(term in occupation.lower() for term in journalist_terms)
        occupation_score = 10 if occupation_match else 0

        confidence = min(100, name_score + employer_score + occupation_score)

        if confidence < REVIEW_THRESHOLD:
            return None

        # Determine recipient type
        committee_type = item.get("committee", {}).get("committee_type", "")
        if committee_type in ["H", "S", "P"]:
            recipient_type = "candidate"
        elif committee_type in ["N", "Q", "V", "W"]:
            recipient_type = "pac"
        elif committee_type in ["X", "Y", "Z"]:
            recipient_type = "party"
        else:
            recipient_type = "other"

        reason_parts = [f"name={name_score}"]
        if employer_match:
            reason_parts.append(f"employer='{employer}'")
        if occupation_match:
            reason_parts.append(f"occupation='{occupation}'")

        return FECRecord(
            contributor_name=contributor,
            recipient_name=item.get("committee", {}).get("name", "Unknown"),
            recipient_type=recipient_type,
            amount=float(amount),
            contribution_date=receipt_date[:10] if receipt_date else "",
            fec_record_id=transaction_id,
            confidence=confidence,
            confidence_reason=", ".join(reason_parts),
            employer=employer or None,
            occupation=occupation or None,
        )

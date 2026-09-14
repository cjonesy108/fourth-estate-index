"""
FEC contribution record ingestion — api.fec.gov (free, no key required).

Two callers:
  ingest(full_name)         journalist path. Employer/occupation terms
                            are newsroom-shaped. Hits attach to a journalist
                            only after the confidence threshold.
  ingest_owner(slug)        ownership path. Looks up backend.ownership.fec_subjects.
                            Hits attach to the entity slug only — never to an
                            outlet, and never to journalists.fec_records.

False positives are a credibility-destroying error. Common names must
not ingest without an employer hit when the subject requires one.

FEC API docs: https://api.fec.gov/api/v1/
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from rapidfuzz import fuzz

from backend.ownership.fec_subjects import OwnerFecSubject, get_subject

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

JOURNALIST_OCCUPATION_TERMS = [
    "journalist", "reporter", "writer", "editor", "correspondent",
]

OWNER_OCCUPATION_TERMS = [
    "executive", "ceo", "chairman", "chair", "president", "founder",
    "owner", "publisher", "principal",
]


@dataclass
class FECRecord:
    contributor_name: str
    recipient_name: str
    recipient_type: str       # candidate | pac | party | super_pac | other
    amount: float
    contribution_date: str
    fec_record_id: str
    confidence: float
    confidence_reason: str
    employer: Optional[str]
    occupation: Optional[str]
    entity_slug: Optional[str] = None


@dataclass
class FECIngestionResult:
    records_auto_ingested: list[FECRecord]
    records_for_review: list[FECRecord]
    records_rejected: int
    search_names_used: list[str]
    entity_slug: Optional[str] = None


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
        """Search FEC records for a journalist."""
        return await self._run_search(
            canonical_name=full_name,
            search_names=[full_name] + (known_variations or []),
            employer_terms=GUARDIAN_EMPLOYER_TERMS,
            occupation_terms=JOURNALIST_OCCUPATION_TERMS,
            require_employer=False,
            entity_slug=None,
        )

    async def ingest_owner(self, slug: str) -> FECIngestionResult:
        """Search FEC records for an ownership-graph person.

        Results are keyed to the entity slug. Callers must not write
        them onto an outlet page or into journalists.fec_records.
        """
        subject = get_subject(slug)
        if subject is None:
            raise ValueError(f"no FEC subject registered for owner slug {slug!r}")
        search_names = [subject.full_name, *subject.variations]
        return await self._run_search(
            canonical_name=subject.full_name,
            search_names=search_names,
            employer_terms=list(subject.employer_terms),
            occupation_terms=OWNER_OCCUPATION_TERMS,
            require_employer=subject.require_employer,
            entity_slug=subject.slug,
        )

    async def _run_search(
        self,
        *,
        canonical_name: str,
        search_names: list[str],
        employer_terms: list[str],
        occupation_terms: list[str],
        require_employer: bool,
        entity_slug: Optional[str],
    ) -> FECIngestionResult:
        all_records: list[FECRecord] = []

        for name in search_names:
            logger.info(f"Searching FEC for: {name}")
            records = await self._search_by_name(
                name,
                canonical_name,
                employer_terms=employer_terms,
                occupation_terms=occupation_terms,
                require_employer=require_employer,
                entity_slug=entity_slug,
            )
            all_records.extend(records)
            await asyncio.sleep(0.5)

        seen: dict[str, FECRecord] = {}
        for r in all_records:
            if r.fec_record_id not in seen or r.confidence > seen[r.fec_record_id].confidence:
                seen[r.fec_record_id] = r

        deduped = list(seen.values())
        auto = [r for r in deduped if r.confidence >= AUTO_INGEST_THRESHOLD]
        review = [r for r in deduped if REVIEW_THRESHOLD <= r.confidence < AUTO_INGEST_THRESHOLD]
        rejected = len([r for r in deduped if r.confidence < REVIEW_THRESHOLD])

        logger.info(
            f"{canonical_name}: {len(auto)} auto-ingest, "
            f"{len(review)} for review, {rejected} rejected"
        )

        return FECIngestionResult(
            records_auto_ingested=auto,
            records_for_review=review,
            records_rejected=rejected,
            search_names_used=search_names,
            entity_slug=entity_slug,
        )

    async def _search_by_name(
        self,
        search_name: str,
        canonical_name: str,
        *,
        employer_terms: list[str],
        occupation_terms: list[str],
        require_employer: bool,
        entity_slug: Optional[str],
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
            record = self._evaluate(
                item,
                canonical_name,
                employer_terms=employer_terms,
                occupation_terms=occupation_terms,
                require_employer=require_employer,
                entity_slug=entity_slug,
            )
            if record:
                records.append(record)

        return records

    def _evaluate(
        self,
        item: dict,
        canonical_name: str,
        *,
        employer_terms: list[str],
        occupation_terms: list[str],
        require_employer: bool,
        entity_slug: Optional[str],
    ) -> Optional[FECRecord]:
        """Score a FEC result for likelihood it belongs to the subject."""
        contributor = item.get("contributor_name", "")
        employer = item.get("contributor_employer", "") or ""
        occupation = item.get("contributor_occupation", "") or ""
        amount = item.get("contribution_receipt_amount", 0) or 0
        receipt_date = item.get("contribution_receipt_date", "")
        transaction_id = item.get("transaction_id", "")

        if not contributor or not transaction_id:
            return None

        if abs(amount) < 1:
            return None

        name_score = max(
            fuzz.token_sort_ratio(canonical_name.lower(), contributor.lower()),
            fuzz.token_set_ratio(canonical_name.lower(), contributor.lower()),
        )

        employer_match = any(term in employer.lower() for term in employer_terms)
        if require_employer and not employer_match:
            return None

        employer_score = 30 if employer_match else 0
        occupation_match = any(term in occupation.lower() for term in occupation_terms)
        occupation_score = 10 if occupation_match else 0

        confidence = min(100, name_score + employer_score + occupation_score)

        if confidence < REVIEW_THRESHOLD:
            return None

        committee_type = item.get("committee", {}).get("committee_type", "")
        if committee_type in ["H", "S", "P"]:
            recipient_type = "candidate"
        elif committee_type == "O":
            recipient_type = "super_pac"
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
        if entity_slug:
            reason_parts.append(f"slug={entity_slug}")

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
            entity_slug=entity_slug,
        )


def record_to_line_item(record: FECRecord) -> dict:
    """Shape an ingested record like frontend/data/contributions-line-items.json.

    Does not guess party lean. Callers fill party from the committee
    or leave it off the seed until a human checks the row.
    """
    if not record.entity_slug:
        raise ValueError("journalist FEC records are not ownership line items")
    return {
        "entity": record.entity_slug,
        "date": record.contribution_date,
        "amount_usd": record.amount,
        "recipient": record.recipient_name,
        "recipient_type": record.recipient_type if record.recipient_type in {
            "candidate", "pac", "party", "super_pac"
        } else "pac",
        "source_url": f"https://www.fec.gov/data/receipts/?contributor_name={record.contributor_name}",
        "source_label": "FEC schedule A",
        "notes": record.confidence_reason,
    }

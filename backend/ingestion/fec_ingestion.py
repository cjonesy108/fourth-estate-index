"""
FEC contribution record ingestion — api.fec.gov (free, no key required).

Critical rule: a record is only attached to a journalist profile after
confidence threshold is met OR manual verification is complete.
False positives are a credibility-destroying error.

TODO: Implement fuzzy name matching and confidence scoring.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FECRecord:
    contributor_name: str
    recipient_name: str
    recipient_type: str  # candidate | pac | party
    amount: float
    contribution_date: str
    fec_record_id: str
    confidence: str  # auto | manual


class FECIngester:
    FEC_BASE = "https://api.fec.gov/v1"

    async def ingest(
        self,
        journalist_id: str,
        full_name: str,
        known_name_variations: list[str],
        employer: Optional[str] = None,
    ) -> dict:
        # TODO: Implement
        # 1. Query /schedules/schedule_a/ by contributor_name
        # 2. Fuzzy match against known_name_variations
        # 3. Cross-reference employer field
        # 4. Flag high-confidence for auto-ingest, low for manual review
        raise NotImplementedError("FEC ingestion not yet implemented")

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class JournalistBase(BaseModel):
    full_name: str
    slug: str
    primary_outlet: Optional[str] = None
    beat: Optional[str] = None
    data_status: str = "collecting"  # collecting | insufficient | scored


class JournalistSummary(JournalistBase):
    id: UUID
    composite_score: Optional[float] = None  # None until data is sufficient
    scored_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JournalistProfile(JournalistBase):
    id: UUID
    pillar_scores: Optional["PillarScoreOut"] = None
    fec_records: list["FECRecordOut"] = []
    corrections: list["CorrectionOut"] = []
    appeals: list["AppealOut"] = []
    corpus_size: Optional[int] = None
    corpus_start: Optional[datetime] = None
    corpus_end: Optional[datetime] = None
    methodology_version: Optional[str] = None
    scored_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Import here to avoid circular refs
from backend.api.models.score import PillarScoreOut, FECRecordOut, CorrectionOut, AppealOut

JournalistProfile.model_rebuild()

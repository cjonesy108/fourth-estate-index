from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PillarScoreOut(BaseModel):
    pillar_1_score: Optional[float] = None
    pillar_2_score: Optional[float] = None
    pillar_3_score: Optional[float] = None
    pillar_4_score: Optional[float] = None
    composite_score: Optional[float] = None
    dimensions_scored: Optional[dict] = None
    methodology_version: str
    scored_at: datetime

    model_config = {"from_attributes": True}


class FECRecordOut(BaseModel):
    id: UUID
    contributor_name: str
    recipient_name: str
    recipient_type: str
    amount: float
    contribution_date: date
    fec_record_id: str

    model_config = {"from_attributes": True}


class CorrectionOut(BaseModel):
    id: UUID
    correction_text: str
    correction_type: Optional[str]
    original_published_at: Optional[datetime]
    corrected_at: Optional[datetime]
    days_to_correction: Optional[int]
    correction_url: Optional[str]

    model_config = {"from_attributes": True}


class AppealOut(BaseModel):
    id: UUID
    dimension: Optional[str]
    submission_text: str
    submitted_at: datetime
    outcome: Optional[str]
    outcome_notes: Optional[str]
    published: bool

    model_config = {"from_attributes": True}

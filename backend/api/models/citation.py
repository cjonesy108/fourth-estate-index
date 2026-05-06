from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CitationOut(BaseModel):
    id: UUID
    cited_text: str
    dimension: str
    flag_type: Optional[str]
    flag_value: Optional[float]
    article_id: Optional[UUID]
    social_post_id: Optional[UUID]
    article_url: Optional[str] = None
    article_headline: Optional[str] = None

    model_config = {"from_attributes": True}

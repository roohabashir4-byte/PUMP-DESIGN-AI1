from datetime import datetime, timezone
from typing import Optional
from pydantic import Field
from pydantic import BaseModel

class Revision(BaseModel):
    revision_id: Optional[str] = None
    design_id: str
    revision_number: int
    reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    changed_parameters: dict = Field(default_factory=dict)
    snapshot: dict = Field(default_factory=dict)

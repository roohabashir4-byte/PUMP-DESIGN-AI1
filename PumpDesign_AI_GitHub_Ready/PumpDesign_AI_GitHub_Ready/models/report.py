from typing import Optional
from pydantic import BaseModel, Field

class Report(BaseModel):
    report_id: Optional[str] = None
    design_id: str
    title: str
    generated_at: Optional[str] = None
    status: str = 'DRAFT'
    sections: list[dict] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)

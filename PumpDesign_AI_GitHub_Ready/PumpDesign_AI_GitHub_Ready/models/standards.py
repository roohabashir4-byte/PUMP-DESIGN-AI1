from typing import Optional
from pydantic import BaseModel, Field

class Reference(BaseModel):
    reference_id: Optional[str] = None
    title: str
    organization: Optional[str] = None
    edition_year: Optional[str] = None
    section: Optional[str] = None
    page: Optional[str] = None
    url: Optional[str] = None
    document: Optional[str] = None
    applicability: Optional[str] = None
    source_status: Optional[str] = None

class CalculationReference(BaseModel):
    calculation_id: str
    reference_id: str
    relevance: Optional[str] = None

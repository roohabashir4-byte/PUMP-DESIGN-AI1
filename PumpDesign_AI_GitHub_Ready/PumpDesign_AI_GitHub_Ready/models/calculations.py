from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

class CalculationStatus(str, Enum):
    CALCULATED='CALCULATED'; NOT_CALCULABLE='NOT_CALCULABLE'; MISSING_INPUT='MISSING_INPUT'; OVERRIDDEN='OVERRIDDEN'; INVALID='INVALID'
class ValidationStatus(str, Enum):
    PASS='PASS'; FAIL='FAIL'; WARNING='WARNING'; NOT_CHECKED='NOT_CHECKED'
class Severity(str, Enum):
    INFO='INFO'; WARNING='WARNING'; CRITICAL='CRITICAL'

class CalculationDependency(BaseModel):
    calculation_id: str
    depends_on_id: str

class Calculation(BaseModel):
    calculation_id: Optional[str] = None
    name: str
    formula: Optional[str] = None
    substituted_values: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    unit: Optional[str] = None
    method: Optional[str] = None
    assumptions: list[str] = Field(default_factory=list)
    status: CalculationStatus = CalculationStatus.CALCULATED
    notes: Optional[str] = None

class ValidationResult(BaseModel):
    validation_id: Optional[str] = None
    name: str
    status: ValidationStatus
    severity: Severity = Severity.INFO
    criterion: Optional[str] = None
    actual: Any = None
    limit: Any = None
    message: str

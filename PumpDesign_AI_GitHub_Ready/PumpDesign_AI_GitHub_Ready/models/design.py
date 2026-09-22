from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
from .project import PumpApplication, DesignInput
from .calculations import Calculation, ValidationResult

class PumpSelectionStatus(str, Enum):
    DUTY_POINT_ONLY='DUTY_POINT_ONLY'
    COMMERCIAL_PUMP_NOT_SELECTED='COMMERCIAL_PUMP_NOT_SELECTED'
    COMMERCIAL_PUMP_SELECTED='COMMERCIAL_PUMP_SELECTED'

class DesignParameter(BaseModel):
    name: str
    value: Any
    unit: Optional[str] = None
    source: str
    notes: Optional[str] = None

class PumpDuty(BaseModel):
    flow: Optional[float] = None
    flow_unit: Optional[str] = None
    head: Optional[float] = None
    head_unit: Optional[str] = None
    hydraulic_power: Optional[float] = None
    hydraulic_power_unit: Optional[str] = None
    input_power: Optional[float] = None
    input_power_unit: Optional[str] = None
    status: str = "NOT_CALCULABLE"
    validation_status: str = "NOT_CHECKED"
    unresolved_items: list[str] = Field(default_factory=list)
    basis: dict = Field(default_factory=dict)
    selection_status: PumpSelectionStatus = PumpSelectionStatus.DUTY_POINT_ONLY
    efficiency: Optional[float] = None
    npshr: Optional[float] = None
    npshr_unit: Optional[str] = None

class DesignOverride(BaseModel):
    parameter_name: str
    original_value: Any
    override_value: Any
    unit: Optional[str] = None
    reason: str

class Design(BaseModel):
    design_id: Optional[str] = None
    project_id: str
    application: PumpApplication
    scenario: str
    inputs: list[DesignInput] = Field(default_factory=list)
    parameters: list[DesignParameter] = Field(default_factory=list)
    calculations: list[Calculation] = Field(default_factory=list)
    validations: list[ValidationResult] = Field(default_factory=list)
    pump_duty: Optional[PumpDuty] = None
    overrides: list[DesignOverride] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

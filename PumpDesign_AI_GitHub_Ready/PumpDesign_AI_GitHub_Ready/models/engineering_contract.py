"""Contracts between LLM reasoning, RAG criteria, and deterministic tools.

The models in this file contain no engineering constants. They define what
information may cross the reasoning/calculation boundary and how provenance is
carried with it.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class InputSource(str, Enum):
    USER_INPUT = "USER_INPUT"
    DRAWING_EXTRACTED = "DRAWING_EXTRACTED"
    STANDARD_CRITERION = "STANDARD_CRITERION"
    DESIGN_ASSUMPTION = "DESIGN_ASSUMPTION"
    ENGINEER_OVERRIDE = "ENGINEER_OVERRIDE"
    CALCULATED = "CALCULATED"


class CriterionType(str, Enum):
    VELOCITY = "VELOCITY"
    HEAD_LOSS = "HEAD_LOSS"
    PRESSURE = "PRESSURE"
    DEMAND = "DEMAND"
    WATER_PROPERTY = "WATER_PROPERTY"
    MATERIAL = "MATERIAL"
    HYDRAULIC_METHOD = "HYDRAULIC_METHOD"
    PUMP = "PUMP"
    NPSH = "NPSH"
    HOT_WATER = "HOT_WATER"
    CONTROL = "CONTROL"
    OTHER = "OTHER"


class Criterion(BaseModel):
    criterion_id: str
    criterion_type: CriterionType
    parameter: str
    value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None
    application: Optional[str] = None
    service: Optional[str] = None
    jurisdiction: Optional[str] = None
    applicability: str
    method: Optional[str] = None
    source_reference_id: str
    source_status: str = "UNVERIFIED"
    edition_year: Optional[str] = None
    section: Optional[str] = None
    page: Optional[str] = None
    notes: Optional[str] = None


class WaterProperties(BaseModel):
    """Explicit water properties used by a deterministic calculation."""
    temperature_c: float
    density_kg_m3: float
    dynamic_viscosity_pa_s: Optional[float] = None
    kinematic_viscosity_m2_s: Optional[float] = None
    specific_heat_j_kgk: Optional[float] = None
    source_reference_id: Optional[str] = None
    source_status: str = "UNVERIFIED"


class EngineeringMethodDecision(BaseModel):
    application: str
    hydraulic_method: str
    reason: str
    allowed_alternatives: list[str] = Field(default_factory=list)
    criterion_reference_ids: list[str] = Field(default_factory=list)


class DesignInputPacket(BaseModel):
    name: str
    value: Any
    unit: Optional[str] = None
    source: InputSource
    source_reference_ids: list[str] = Field(default_factory=list)
    is_engineering_assumption: bool = False
    notes: Optional[str] = None


class CalculationRequest(BaseModel):
    request_id: str
    application: str
    tool_name: str
    inputs: dict[str, Any]
    input_sources: dict[str, InputSource] = Field(default_factory=dict)
    criterion_ids: list[str] = Field(default_factory=list)
    method_decision: Optional[EngineeringMethodDecision] = None
    water_properties: Optional[WaterProperties] = None
    purpose: str
    allow_assumptions: bool = False


class CalculationResultPacket(BaseModel):
    request_id: str
    tool_name: str
    status: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    formula: Optional[str] = None
    substituted_values: dict[str, Any] = Field(default_factory=dict)
    method: Optional[str] = None
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    criterion_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    authoritative_numeric_source: str = "DETERMINISTIC_TOOL"


class MissingInput(BaseModel):
    name: str
    reason: str
    required_for: str
    can_be_derived: bool = False
    derivation_source: Optional[str] = None


class EngineeringDecisionPacket(BaseModel):
    application: str
    scenario: str
    method_decision: Optional[EngineeringMethodDecision] = None
    criteria: list[Criterion] = Field(default_factory=list)
    inputs: list[DesignInputPacket] = Field(default_factory=list)
    missing_inputs: list[MissingInput] = Field(default_factory=list)
    tool_requests: list[CalculationRequest] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)

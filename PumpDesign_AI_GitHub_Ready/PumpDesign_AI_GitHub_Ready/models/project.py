from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class PumpApplication(str, Enum):
    TRANSFER = 'transfer'
    BOOSTER = 'booster'
    SUBMERSIBLE = 'submersible'
    HOT_WATER_RECIRCULATION = 'hot_water_recirculation'
    CUSTOM = 'custom'

class InputSource(str, Enum):
    USER_INPUT = 'USER_INPUT'
    DRAWING_EXTRACTED = 'DRAWING_EXTRACTED'
    STANDARD_CRITERION = 'STANDARD_CRITERION'
    DESIGN_ASSUMPTION = 'DESIGN_ASSUMPTION'
    ENGINEER_OVERRIDE = 'ENGINEER_OVERRIDE'

class DesignInput(BaseModel):
    name: str
    value: Optional[float | str | bool] = None
    unit: Optional[str] = None
    source: InputSource = InputSource.USER_INPUT
    known: bool = True
    notes: Optional[str] = None

class Project(BaseModel):
    project_id: Optional[str] = None
    project_name: str
    location: str
    jurisdiction: Optional[str] = None
    authority: Optional[str] = None
    building_type: str
    description: Optional[str] = None

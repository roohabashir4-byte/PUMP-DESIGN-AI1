"""Project/design persistence service."""
from __future__ import annotations
from typing import Any
from .database import MemoryDB

class ProjectMemory:
    def __init__(self, db: MemoryDB):
        self.db = db

    def save_project_and_design(self, inputs: dict[str, Any], application: str, result: dict[str, Any], design_id: str | None = None) -> tuple[str, str]:
        project_id = self.db.upsert_project({
            "project_id": inputs.get("project_id"),
            "project_name": inputs.get("project_name", "Unnamed Project"),
            "location": inputs.get("location", ""),
            "jurisdiction": inputs.get("jurisdiction"),
            "authority": inputs.get("authority"),
            "building_type": inputs.get("building_type", ""),
        })
        design_id = self.db.save_design({
            "design_id": design_id,
            "project_id": project_id,
            "application": application,
            "scenario": inputs.get("different_scenario") or application,
            "inputs": inputs,
        }, result=result, status=result.get("status", "UNKNOWN"))
        return project_id, design_id

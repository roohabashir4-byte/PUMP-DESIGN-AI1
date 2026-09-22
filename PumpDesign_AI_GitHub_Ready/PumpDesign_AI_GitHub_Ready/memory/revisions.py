"""Revision comparison and creation helpers."""
from __future__ import annotations
from typing import Any
from .database import MemoryDB

def changed_parameters(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(old) | set(new))
    changes = {}
    for key in keys:
        if old.get(key) != new.get(key):
            changes[key] = {"old": old.get(key), "new": new.get(key)}
    return changes

def create_design_revision(db: MemoryDB, design_id: str, reason: str, old_inputs: dict[str, Any], new_inputs: dict[str, Any], result: dict[str, Any]) -> int:
    changes = changed_parameters(old_inputs, new_inputs)
    if not changes:
        raise ValueError("No design input changes were detected; a new revision is not required.")
    snapshot = {"inputs": new_inputs, "result": result}
    return db.create_revision(design_id, reason, changes, snapshot)

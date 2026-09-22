"""RAG-to-calculation boundary.

This module expects already-retrieved RAG records. It does not invent values,
resolve conflicting sources, or choose engineering criteria silently.
"""
from __future__ import annotations

from models.engineering_contract import Criterion, EngineeringDecisionPacket
from standards.criteria import applicable_criteria, validate_criteria


def build_criteria_packet(
    criteria: list[Criterion],
    *,
    application: str,
    service: str | None = None,
    jurisdiction: str | None = None,
) -> list[Criterion]:
    errors = validate_criteria(criteria)
    if errors:
        raise ValueError("Invalid RAG criteria: " + "; ".join(errors))
    return applicable_criteria(criteria, application=application, service=service, jurisdiction=jurisdiction)


def require_criterion(
    criteria: list[Criterion], *, criterion_type: str, parameter: str
) -> Criterion:
    matches = [
        c for c in criteria
        if c.criterion_type.value == criterion_type and c.parameter.lower() == parameter.lower()
    ]
    if not matches:
        raise LookupError(f"No applicable RAG criterion found for {criterion_type}/{parameter}.")
    if len(matches) > 1:
        raise LookupError(
            f"Multiple criteria found for {criterion_type}/{parameter}; source precedence must be resolved before calculation."
        )
    return matches[0]


def attach_criteria_to_request(request, criteria: list[Criterion]):
    """Return a request carrying only criteria IDs that actually exist."""
    ids = {c.criterion_id for c in criteria}
    unknown = [x for x in request.criterion_ids if x not in ids]
    if unknown:
        raise ValueError(f"Calculation request contains unknown criterion IDs: {unknown}")
    return request

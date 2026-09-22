"""Validation and applicability helpers for RAG-returned engineering criteria."""
from __future__ import annotations

from collections.abc import Iterable
from models.engineering_contract import Criterion


def validate_criteria(criteria: Iterable[Criterion]) -> list[str]:
    """Return validation errors without inventing or modifying criteria."""
    errors: list[str] = []
    for c in criteria:
        if not c.criterion_id.strip():
            errors.append("criterion_id is required")
        if not c.parameter.strip():
            errors.append(f"{c.criterion_id}: parameter is required")
        if not c.applicability.strip():
            errors.append(f"{c.criterion_id}: applicability is required")
        if not c.source_reference_id.strip():
            errors.append(f"{c.criterion_id}: source_reference_id is required")
        if c.min_value is not None and c.max_value is not None and c.min_value > c.max_value:
            errors.append(f"{c.criterion_id}: min_value exceeds max_value")
        if c.value is None and c.min_value is None and c.max_value is None and not (c.notes and c.notes.strip()):
            errors.append(f"{c.criterion_id}: no criterion value/range or qualitative rule supplied")
    return errors


def applicable_criteria(
    criteria: Iterable[Criterion],
    *,
    application: str,
    service: str | None = None,
    jurisdiction: str | None = None,
) -> list[Criterion]:
    """Filter only criteria explicitly matching the supplied context.

    Missing jurisdiction/service does not create a match. This deliberately
    avoids silently applying a generic or unrelated criterion.
    """
    out: list[Criterion] = []
    for c in criteria:
        if c.application:
            apps = {x.strip().lower() for x in c.application.split(",")}
            if "all" not in apps and application.lower() not in apps:
                continue
        if c.service and (service is None or c.service.lower() != service.lower()):
            continue
        if c.jurisdiction and (jurisdiction is None or c.jurisdiction.lower() != jurisdiction.lower()):
            continue
        out.append(c)
    return out

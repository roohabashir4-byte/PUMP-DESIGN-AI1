"""Reference formatting helpers for engineering reports."""
from __future__ import annotations

from typing import Any


def reference_label(ref: Any) -> str:
    if isinstance(ref, str):
        return ref
    if not isinstance(ref, dict):
        return str(ref)
    title = ref.get("title") or ref.get("name") or ref.get("source_id") or "Reference"
    organization = ref.get("organization") or ref.get("publisher")
    year = ref.get("edition_year") or ref.get("year")
    section = ref.get("section")
    page = ref.get("page")
    parts = [str(title)]
    if organization:
        parts.append(str(organization))
    if year:
        parts.append(str(year))
    if section:
        parts.append(f"Section {section}")
    if page:
        parts.append(f"p. {page}")
    return " — ".join(parts)


def unique_references(criteria: list[dict[str, Any]], sources: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    sources_by_id = {str(x.get("source_id")): x for x in (sources or []) if isinstance(x, dict) and x.get("source_id")}
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for criterion in criteria:
        sid = str(criterion.get("source_reference_id") or "").strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        base = dict(sources_by_id.get(sid, {}))
        base.setdefault("source_id", sid)
        result.append(base)
    return result

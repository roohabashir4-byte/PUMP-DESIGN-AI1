from __future__ import annotations

import json
import os
import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import ValidationError

from models.engineering_contract import Criterion, CriterionType

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "standards"
INDEX = DATA / "index"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def _criterion_type(name: str, parameter: str, value: Any) -> CriterionType:
    n = f"{name} {parameter}".lower()
    if "velocity" in n:
        return CriterionType.VELOCITY
    if "pressure" in n or "prv" in n:
        return CriterionType.PRESSURE
    if "hazen" in n or parameter.lower().startswith("hazen"):
        return CriterionType.MATERIAL
    if "demand" in n or "flow" in n:
        return CriterionType.DEMAND
    if "hot" in n or "recirculation" in n or "temperature" in n:
        return CriterionType.HOT_WATER
    if "npsh" in n:
        return CriterionType.NPSH
    if "method" in n or "hydraulic" in n:
        return CriterionType.HYDRAULIC_METHOD
    if isinstance(value, (int, float)):
        return CriterionType.OTHER
    return CriterionType.OTHER


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_criteria() -> list[Criterion]:
    records: list[dict[str, Any]] = []
    for path in [DATA / "criteria" / "engineering_criteria.json", DATA / "criteria" / "extended_criteria.json"]:
        if path.exists():
            obj = _load_json(path)
            if isinstance(obj, list):
                records.extend(obj)

    out: list[Criterion] = []
    seen: set[str] = set()
    for r in records:
        cid = str(r.get("criterion_id", "")).strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        value = r.get("value")
        numeric_value = value if isinstance(value, (int, float)) else None
        min_value = max_value = None
        if isinstance(value, list) and len(value) == 2 and all(isinstance(x, (int, float)) for x in value):
            min_value, max_value = value
        app = r.get("application") or (r.get("scope") if r.get("scope") else "all")
        if isinstance(app, list):
            app = ",".join(str(x).lower() for x in app)
        elif isinstance(app, str):
            app = app.lower()
        source_id = r.get("source_id") or (r.get("source_ids") or [None])[0]
        if not source_id:
            source_id = "UNSPECIFIED"
        note_value = r.get("notes") or r.get("rule") or r.get("value")
        if not isinstance(note_value, str):
            note_value = json.dumps(note_value, sort_keys=True)
        criterion = Criterion(
            criterion_id=cid,
            criterion_type=_criterion_type(str(r.get("name", "")), str(r.get("parameter", "")), value),
            parameter=str(r.get("parameter") or r.get("name") or cid),
            value=numeric_value,
            min_value=min_value,
            max_value=max_value,
            unit=r.get("unit"),
            application=app,
            service=r.get("service"),
            jurisdiction=r.get("jurisdiction"),
            applicability=str(r.get("applicability") or r.get("scope") or "source-defined"),
            method=r.get("method"),
            source_reference_id=source_id,
            source_status=str(r.get("source_status") or r.get("status") or "UNVERIFIED"),
            edition_year=str(r.get("edition_year") or "") or None,
            section=r.get("section") or r.get("reference"),
            page=r.get("page"),
            notes=note_value,
        )
        out.append(criterion)

    # Material/Hazen-Williams records from the verified registry are exposed as
    # criteria so the same agent contract can consume them.
    hw_path = DATA / "pipe_data" / "hazen_williams_c_registry.json"
    if hw_path.exists():
        hw = _load_json(hw_path)
        sources = hw.get("sources", {})
        for rec in hw.get("records", []):
            preferred = rec.get("preferred")
            if preferred is None:
                continue
            source_id = rec.get("source", "UNKNOWN")
            src = sources.get(source_id, {})
            cid = f"HW-C-{_norm(rec.get('material','')).replace(' ','-')}-{_norm(rec.get('condition','')).replace(' ','-')}"
            if any(c.criterion_id == cid for c in out):
                continue
            out.append(Criterion(
                criterion_id=cid,
                criterion_type=CriterionType.MATERIAL,
                parameter="hazen_williams_c",
                value=float(preferred),
                unit="dimensionless",
                application="all",
                applicability=f"{rec.get('material')} / {rec.get('condition')}",
                source_reference_id=source_id,
                source_status=str(rec.get("status", "UNVERIFIED")),
                edition_year=str(src.get("year")) if src.get("year") else None,
                notes="Registry value; governing project/AHJ criterion takes precedence.",
            ))
    return out


def load_chunks() -> list[dict[str, Any]]:
    path = DATA / "corpus" / "chunks.jsonl"
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_sources() -> dict[str, dict[str, Any]]:
    path = DATA / "sources" / "source_registry.json"
    return {x["source_id"]: x for x in _load_json(path)} if path.exists() else {}


class RAGStore:
    """Local RAG store. Uses FAISS when installed; otherwise a deterministic
    TF-IDF cosine fallback is used for local testing. Production deployments
    should install faiss-cpu and build the FAISS index with build_index.py.
    """

    def __init__(self, *, top_k: int = 6):
        self.top_k = top_k
        self.criteria = load_criteria()
        self.chunks = load_chunks()
        self.sources = load_sources()
        self.vectorizer = None
        self.matrix = None
        self.faiss_index = None
        self._load_or_build_index()

    def _load_or_build_index(self):
        pkl = INDEX / "tfidf_vectorizer.pkl"
        npy = INDEX / "tfidf_matrix.npz"
        if pkl.exists() and npy.exists():
            from scipy.sparse import load_npz
            self.vectorizer = pickle.loads(pkl.read_bytes())
            self.matrix = load_npz(npy).tocsr()
        else:
            self._build_tfidf()
        faiss_path = INDEX / "chunks.faiss"
        if faiss_path.exists():
            try:
                import faiss
                self.faiss_index = faiss.read_index(str(faiss_path))
            except Exception:
                self.faiss_index = None

    def _build_tfidf(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from scipy.sparse import save_npz
        texts = [f"{c.get('heading','')} {c.get('text','')} {' '.join(c.get('tags', []))}" for c in self.chunks]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True, norm="l2")
        self.matrix = self.vectorizer.fit_transform(texts).tocsr()
        INDEX.mkdir(parents=True, exist_ok=True)
        pkl = INDEX / "tfidf_vectorizer.pkl"
        pkl.write_bytes(pickle.dumps(self.vectorizer))
        save_npz(INDEX / "tfidf_matrix.npz", self.matrix)

    def _search_chunks(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        k = top_k or self.top_k
        if self.faiss_index is not None:
            q = self.vectorizer.transform([query]).toarray().astype("float32")
            scores, ids = self.faiss_index.search(q, min(k, len(self.chunks)))
            return [{**self.chunks[i], "score": float(scores[0][j])} for j, i in enumerate(ids[0]) if i >= 0]
        q = self.vectorizer.transform([query])
        scores = (self.matrix @ q.T).toarray().ravel()
        order = np.argsort(-scores)[:k]
        return [{**self.chunks[i], "score": float(scores[i])} for i in order if scores[i] > 0]

    def retrieve(self, query: str, *, application: str | None = None, jurisdiction: str | None = None, top_k: int | None = None) -> dict[str, Any]:
        app = (application or "").lower()
        chunks = self._search_chunks(query, top_k)
        criteria = []
        for c in self.criteria:
            capp = (c.application or "all").lower()
            capp_parts = {x.strip() for x in capp.split(",")}
            if app and "all" not in capp_parts and app not in capp_parts and not (app in capp or capp in app):
                continue
            criteria.append(c)
        qnorm = _norm(query)
        tokens = set(qnorm.split())
        ranked = []
        for c in criteria:
            text = _norm(f"{c.criterion_id} {c.parameter} {c.applicability} {c.notes or ''}")
            overlap = len(tokens.intersection(text.split()))
            ranked.append((overlap, c))
        ranked.sort(key=lambda x: (-x[0], x[1].criterion_id))
        limit = max(12, (top_k or self.top_k))
        selected = [c for score, c in ranked if score > 0][:limit]
        # Keep the application-specific baseline criteria even when the text
        # query has weak lexical overlap. Retrieval should not accidentally
        # remove mandatory engineering context merely because wording differs.
        if len(selected) < min(limit, len(criteria)):
            selected_ids = {c.criterion_id for c in selected}
            for c in criteria:
                if c.criterion_id not in selected_ids:
                    selected.append(c)
                if len(selected) >= limit:
                    break
        return {
            "criteria": [c.model_dump(mode="json") for c in selected],
            "chunks": chunks,
            "references": [self.sources[c.source_reference_id] for c in selected if c.source_reference_id in self.sources],
        }

    def retrieve_criteria(self, *, application: str, service: str | None = None, jurisdiction: str | None = None, query: str = "engineering criteria") -> list[Criterion]:
        result = self.retrieve(f"{application} {service or ''} {jurisdiction or ''} {query}", application=application, jurisdiction=jurisdiction)
        return [Criterion.model_validate(x) for x in result["criteria"]]

    def retriever(self, *, application: str, service: str | None = None, jurisdiction: str | None = None, query: str = "engineering criteria") -> list[Criterion]:
        return self.retrieve_criteria(application=application, service=service, jurisdiction=jurisdiction, query=query)

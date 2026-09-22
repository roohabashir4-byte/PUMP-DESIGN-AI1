"""SQLite persistence for structured PumpDesign AI project/design memory."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    location TEXT NOT NULL,
    jurisdiction TEXT,
    authority TEXT,
    building_type TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS designs (
    design_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    application TEXT NOT NULL,
    scenario TEXT NOT NULL,
    status TEXT NOT NULL,
    current_revision INTEGER NOT NULL DEFAULT 0,
    inputs_json TEXT NOT NULL,
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);
CREATE TABLE IF NOT EXISTS revisions (
    revision_id TEXT PRIMARY KEY,
    design_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL,
    reason TEXT NOT NULL,
    changed_parameters_json TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(design_id, revision_number),
    FOREIGN KEY(design_id) REFERENCES designs(design_id)
);
CREATE INDEX IF NOT EXISTS idx_designs_project ON designs(project_id);
CREATE INDEX IF NOT EXISTS idx_revisions_design ON revisions(design_id, revision_number);
"""


class MemoryDB:
    def __init__(self, path: str | Path = "pumpdesign_memory.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @staticmethod
    def _now() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def upsert_project(self, project: dict[str, Any]) -> str:
        import uuid
        project_id = project.get("project_id") or str(uuid.uuid4())
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO projects(project_id,project_name,location,jurisdiction,authority,building_type,description,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(project_id) DO UPDATE SET project_name=excluded.project_name, location=excluded.location,
                   jurisdiction=excluded.jurisdiction, authority=excluded.authority, building_type=excluded.building_type,
                   description=excluded.description, updated_at=excluded.updated_at""",
                (project_id, project.get("project_name", ""), project.get("location", ""),
                 project.get("jurisdiction"), project.get("authority"), project.get("building_type", ""),
                 project.get("description"), now, now),
            )
        return project_id

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        return dict(row) if row else None

    def save_design(self, design: dict[str, Any], *, result: dict[str, Any] | None, status: str) -> str:
        import uuid
        design_id = design.get("design_id") or str(uuid.uuid4())
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO designs(design_id,project_id,application,scenario,status,current_revision,inputs_json,result_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(design_id) DO UPDATE SET project_id=excluded.project_id, application=excluded.application,
                   scenario=excluded.scenario, status=excluded.status, inputs_json=excluded.inputs_json,
                   result_json=excluded.result_json, updated_at=excluded.updated_at""",
                (design_id, design["project_id"], design["application"], design.get("scenario", ""), status,
                 int(design.get("current_revision", 0)), json.dumps(design.get("inputs", {}), default=str),
                 json.dumps(result, default=str) if result is not None else None, now, now),
            )
        return design_id

    def list_designs(self, project_id: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM designs"
        args: tuple[Any, ...] = ()
        if project_id:
            sql += " WHERE project_id=?"
            args = (project_id,)
        sql += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]

    def get_design(self, design_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM designs WHERE design_id=?", (design_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["inputs"] = json.loads(data["inputs_json"])
        data["result"] = json.loads(data["result_json"]) if data["result_json"] else None
        return data

    def create_revision(self, design_id: str, reason: str, changed_parameters: dict[str, Any], snapshot: dict[str, Any]) -> int:
        import uuid
        with self._connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(revision_number),0) FROM revisions WHERE design_id=?", (design_id,)).fetchone()
            number = int(row[0]) + 1
            now = self._now()
            conn.execute(
                "INSERT INTO revisions(revision_id,design_id,revision_number,reason,changed_parameters_json,snapshot_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), design_id, number, reason, json.dumps(changed_parameters, default=str), json.dumps(snapshot, default=str), now),
            )
            conn.execute("UPDATE designs SET current_revision=?, updated_at=? WHERE design_id=?", (number, now, design_id))
        return number

    def list_revisions(self, design_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM revisions WHERE design_id=? ORDER BY revision_number", (design_id,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["changed_parameters"] = json.loads(item.pop("changed_parameters_json"))
            item["snapshot"] = json.loads(item.pop("snapshot_json"))
            result.append(item)
        return result

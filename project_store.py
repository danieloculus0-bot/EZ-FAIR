"""SQLite-backed project persistence for EZ FAIR."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _data_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EZ FAIR"
    base.mkdir(parents=True, exist_ok=True)
    return base


DATABASE_PATH = _data_root() / "ez_fair.db"
BACKUP_ROOT = _data_root() / "Backups"


@dataclass
class ProjectMetadata:
    part_no: str = ""
    part_name: str = ""
    drawing_no: str = ""
    revision: str = ""
    customer: str = ""
    material: str = ""
    scale: str = ""
    units: str = ""
    sheet: str = ""
    drawing_date: str = ""
    inspector: str = ""
    item_no: str = ""
    po_no: str = ""
    order_no: str = ""
    reason_for_fai: str = ""


@dataclass
class ProjectRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Project"
    source_pdf: str = ""
    status: str = "DRAFT"
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    characteristics: list[dict[str, Any]] = field(default_factory=list)
    gdt_controls: list[dict[str, Any]] = field(default_factory=list)
    form_configuration: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectRecord":
        payload = dict(data)
        payload["metadata"] = ProjectMetadata(**payload.get("metadata", {}))
        return cls(**payload)


class ProjectStore:
    def __init__(self, path: Path = DATABASE_PATH, backup_root: Path = BACKUP_ROOT):
        self.path = path
        self.backup_root = backup_root
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_pdf TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'DRAFT',
                    metadata_json TEXT NOT NULL,
                    characteristics_json TEXT NOT NULL,
                    gdt_controls_json TEXT NOT NULL,
                    form_configuration_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(updated_at DESC)")

    def _backup_project(self, project: ProjectRecord, retain: int = 20) -> Path:
        project_dir = self.backup_root / project.id
        project_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        target = project_dir / f"{stamp}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
        temporary.replace(target)
        backups = sorted(project_dir.glob("*.json"), reverse=True)
        for old in backups[retain:]:
            old.unlink(missing_ok=True)
        return target

    def save(self, project: ProjectRecord) -> ProjectRecord:
        project.updated_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                """
                INSERT INTO projects (
                    id, name, source_pdf, status, metadata_json, characteristics_json,
                    gdt_controls_json, form_configuration_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    source_pdf=excluded.source_pdf,
                    status=excluded.status,
                    metadata_json=excluded.metadata_json,
                    characteristics_json=excluded.characteristics_json,
                    gdt_controls_json=excluded.gdt_controls_json,
                    form_configuration_json=excluded.form_configuration_json,
                    updated_at=excluded.updated_at
                """,
                (
                    project.id,
                    project.name,
                    project.source_pdf,
                    project.status,
                    json.dumps(asdict(project.metadata)),
                    json.dumps(project.characteristics),
                    json.dumps(project.gdt_controls),
                    json.dumps(project.form_configuration),
                    project.created_at,
                    project.updated_at,
                ),
            )
        self._backup_project(project)
        return project

    def load(self, project_id: str) -> ProjectRecord:
        with self._connect() as db:
            row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise KeyError(project_id)
        return ProjectRecord(
            id=row["id"],
            name=row["name"],
            source_pdf=row["source_pdf"],
            status=row["status"],
            metadata=ProjectMetadata(**json.loads(row["metadata_json"])),
            characteristics=json.loads(row["characteristics_json"]),
            gdt_controls=json.loads(row["gdt_controls_json"]),
            form_configuration=json.loads(row["form_configuration_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def recover_latest(self, project_id: str) -> ProjectRecord:
        project_dir = self.backup_root / project_id
        backups = sorted(project_dir.glob("*.json"), reverse=True)
        if not backups:
            raise FileNotFoundError(f"No backup exists for project {project_id}.")
        data = json.loads(backups[0].read_text(encoding="utf-8"))
        recovered = ProjectRecord.from_dict(data)
        self.save(recovered)
        return recovered

    def backup_history(self, project_id: str) -> list[Path]:
        return sorted((self.backup_root / project_id).glob("*.json"), reverse=True)

    def recent(self, limit: int = 20) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, name, source_pdf, status, updated_at FROM projects ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, project_id: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM projects WHERE id = ?", (project_id,))

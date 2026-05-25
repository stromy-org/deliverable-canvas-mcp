"""SQLite-backed canvas storage. WAL mode + BEGIN IMMEDIATE for durable writes."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Section:
    id: str
    title: str
    body: str
    revision: int
    updated_ts: float


@dataclass
class Canvas:
    canvas_id: str
    tenant_id: str
    deliverable_type: str
    client_id: str
    title: str
    template_id: str | None
    meta: dict[str, Any]
    finalized: bool
    created_ts: float
    updated_ts: float
    sections: list[Section]


class CanvasNotFound(Exception):
    pass


class SectionNotFound(Exception):
    pass


class CanvasFinalized(Exception):
    pass


SCHEMA = """
CREATE TABLE IF NOT EXISTS canvas (
    canvas_id       TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    deliverable_type TEXT NOT NULL,
    client_id       TEXT NOT NULL,
    title           TEXT NOT NULL,
    template_id     TEXT,
    meta_json       TEXT NOT NULL DEFAULT '{}',
    finalized       INTEGER NOT NULL DEFAULT 0,
    created_ts      REAL NOT NULL,
    updated_ts      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_canvas_tenant_client_type
    ON canvas(tenant_id, client_id, deliverable_type);

CREATE TABLE IF NOT EXISTS section (
    canvas_id   TEXT NOT NULL,
    section_id  TEXT NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    revision    INTEGER NOT NULL DEFAULT 0,
    updated_ts  REAL NOT NULL,
    position    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (canvas_id, section_id),
    FOREIGN KEY (canvas_id) REFERENCES canvas(canvas_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS revision (
    canvas_id    TEXT NOT NULL,
    section_id   TEXT NOT NULL,
    revision     INTEGER NOT NULL,
    body         TEXT NOT NULL,
    summary      TEXT,
    instructed_by_user INTEGER NOT NULL DEFAULT 0,
    body_hash    TEXT NOT NULL,
    ts           REAL NOT NULL,
    PRIMARY KEY (canvas_id, section_id, revision)
);

CREATE TABLE IF NOT EXISTS audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL,
    tool            TEXT NOT NULL,
    canvas_id       TEXT,
    section_id      TEXT,
    instructed_by_user INTEGER NOT NULL DEFAULT 0,
    body_hash       TEXT,
    ts              REAL NOT NULL
);
"""


class CanvasStore:
    """Single-file SQLite store. Safe for the pilot's single-tenant load."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript("PRAGMA journal_mode=WAL;\nPRAGMA foreign_keys=ON;")
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _write_tx(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    # ---- API ----

    def create_canvas(
        self,
        *,
        tenant_id: str,
        deliverable_type: str,
        client_id: str,
        title: str,
        template_id: str | None,
        template_sections: list[dict[str, str]],
        meta: dict[str, Any] | None = None,
    ) -> Canvas:
        canvas_id = uuid.uuid4().hex
        now = time.time()
        with self._write_tx() as conn:
            conn.execute(
                "INSERT INTO canvas("
                "canvas_id,tenant_id,deliverable_type,client_id,title,"
                "template_id,meta_json,finalized,created_ts,updated_ts) "
                "VALUES (?,?,?,?,?,?,?,0,?,?)",
                (
                    canvas_id,
                    tenant_id,
                    deliverable_type,
                    client_id,
                    title,
                    template_id,
                    json.dumps(meta or {}),
                    now,
                    now,
                ),
            )
            for pos, sec in enumerate(template_sections):
                conn.execute(
                    "INSERT INTO section(canvas_id,section_id,title,body,revision,updated_ts,position)"
                    " VALUES (?,?,?,'',0,?,?)",
                    (canvas_id, sec["id"], sec["title"], now, pos),
                )
        return self.get_canvas(tenant_id=tenant_id, canvas_id=canvas_id)

    def get_canvas(self, *, tenant_id: str, canvas_id: str) -> Canvas:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM canvas WHERE canvas_id=? AND tenant_id=?",
                (canvas_id, tenant_id),
            ).fetchone()
            if row is None:
                raise CanvasNotFound(canvas_id)
            sections_rows = conn.execute(
                "SELECT section_id,title,body,revision,updated_ts FROM section"
                " WHERE canvas_id=? ORDER BY position ASC",
                (canvas_id,),
            ).fetchall()
        sections = [
            Section(
                id=s["section_id"],
                title=s["title"],
                body=s["body"],
                revision=s["revision"],
                updated_ts=s["updated_ts"],
            )
            for s in sections_rows
        ]
        return Canvas(
            canvas_id=row["canvas_id"],
            tenant_id=row["tenant_id"],
            deliverable_type=row["deliverable_type"],
            client_id=row["client_id"],
            title=row["title"],
            template_id=row["template_id"],
            meta=json.loads(row["meta_json"]),
            finalized=bool(row["finalized"]),
            created_ts=row["created_ts"],
            updated_ts=row["updated_ts"],
            sections=sections,
        )

    def update_section(
        self,
        *,
        tenant_id: str,
        canvas_id: str,
        section_id: str,
        body: str,
        summary: str | None,
        instructed_by_user: bool,
    ) -> Section:
        now = time.time()
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        with self._write_tx() as conn:
            crow = conn.execute(
                "SELECT finalized FROM canvas WHERE canvas_id=? AND tenant_id=?",
                (canvas_id, tenant_id),
            ).fetchone()
            if crow is None:
                raise CanvasNotFound(canvas_id)
            if crow["finalized"]:
                raise CanvasFinalized(canvas_id)
            srow = conn.execute(
                "SELECT revision FROM section WHERE canvas_id=? AND section_id=?",
                (canvas_id, section_id),
            ).fetchone()
            if srow is None:
                raise SectionNotFound(section_id)
            new_rev = int(srow["revision"]) + 1
            conn.execute(
                "UPDATE section SET body=?, revision=?, updated_ts=? WHERE canvas_id=? AND section_id=?",
                (body, new_rev, now, canvas_id, section_id),
            )
            conn.execute(
                "INSERT INTO revision(canvas_id,section_id,revision,body,summary,instructed_by_user,body_hash,ts)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (
                    canvas_id,
                    section_id,
                    new_rev,
                    body,
                    summary,
                    1 if instructed_by_user else 0,
                    body_hash,
                    now,
                ),
            )
            conn.execute(
                "UPDATE canvas SET updated_ts=? WHERE canvas_id=?", (now, canvas_id)
            )
            conn.execute(
                "INSERT INTO audit(tenant_id,tool,canvas_id,section_id,instructed_by_user,body_hash,ts)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    tenant_id,
                    "canvas_update_section",
                    canvas_id,
                    section_id,
                    1 if instructed_by_user else 0,
                    body_hash,
                    now,
                ),
            )
        return Section(
            id=section_id,
            title="",  # caller can re-fetch full canvas if needed
            body=body,
            revision=new_rev,
            updated_ts=now,
        )

    def list_revisions(
        self,
        *,
        tenant_id: str,
        canvas_id: str,
        section_id: str | None,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            owner = conn.execute(
                "SELECT 1 FROM canvas WHERE canvas_id=? AND tenant_id=?",
                (canvas_id, tenant_id),
            ).fetchone()
            if owner is None:
                raise CanvasNotFound(canvas_id)
            if section_id is None:
                rows = conn.execute(
                    "SELECT section_id,revision,summary,instructed_by_user,body_hash,ts FROM revision"
                    " WHERE canvas_id=? ORDER BY ts ASC",
                    (canvas_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT section_id,revision,summary,instructed_by_user,body_hash,ts FROM revision"
                    " WHERE canvas_id=? AND section_id=? ORDER BY revision ASC",
                    (canvas_id, section_id),
                ).fetchall()
        return [dict(r) for r in rows]

    def finalize(self, *, tenant_id: str, canvas_id: str) -> Canvas:
        now = time.time()
        with self._write_tx() as conn:
            row = conn.execute(
                "SELECT finalized FROM canvas WHERE canvas_id=? AND tenant_id=?",
                (canvas_id, tenant_id),
            ).fetchone()
            if row is None:
                raise CanvasNotFound(canvas_id)
            if not row["finalized"]:
                conn.execute(
                    "UPDATE canvas SET finalized=1, updated_ts=? WHERE canvas_id=?",
                    (now, canvas_id),
                )
                conn.execute(
                    "INSERT INTO audit(tenant_id,tool,canvas_id,instructed_by_user,ts)"
                    " VALUES (?,?,?,0,?)",
                    (tenant_id, "canvas_finalize", canvas_id, now),
                )
        return self.get_canvas(tenant_id=tenant_id, canvas_id=canvas_id)

    def list_canvases(
        self,
        *,
        tenant_id: str,
        client_id: str | None,
        deliverable_type: str | None,
        include_finalized: bool,
    ) -> list[dict[str, Any]]:
        clauses = ["tenant_id=?"]
        params: list[Any] = [tenant_id]
        if client_id is not None:
            clauses.append("client_id=?")
            params.append(client_id)
        if deliverable_type is not None:
            clauses.append("deliverable_type=?")
            params.append(deliverable_type)
        if not include_finalized:
            clauses.append("finalized=0")
        sql = (
            "SELECT canvas_id,title,deliverable_type,client_id,finalized,updated_ts"
            f" FROM canvas WHERE {' AND '.join(clauses)} ORDER BY updated_ts DESC"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            {
                "canvas_id": r["canvas_id"],
                "title": r["title"],
                "deliverable_type": r["deliverable_type"],
                "client_id": r["client_id"],
                "finalized": bool(r["finalized"]),
                "updated_ts": r["updated_ts"],
            }
            for r in rows
        ]

    def backup_to(self, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as src, sqlite3.connect(target) as dst:
            src.backup(dst)

    @classmethod
    def restore_from(cls, *, backup_path: Path, db_path: Path) -> CanvasStore:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(backup_path, db_path)
        return cls(db_path)

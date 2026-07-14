"""Persistence operations: atomic per-repository replace (ADR-014).

storage -> schema, errors only (architecture.md section 2 dependency rule):
this module must never import gitio, config, or aggregate.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from ..errors import StorageError
from ..schema.event import AceEvent, ProvenanceSource


@dataclass
class CommitEvents:
    """One kept commit and the ACE events attributed to it — the unit of
    work scanner.py hands to :func:`replace_repository_scan` per commit."""

    sha: str
    author_email: str
    author_date: str
    events: list[AceEvent]


def replace_repository_scan(
    conn: sqlite3.Connection,
    *,
    repository_uid: str,
    display_name: str,
    local_path: str,
    scanned: list[CommitEvents],
    scanned_at: str | None,
) -> None:
    """Atomically replace one repository's scan-derived rows (ADR-014).

    One transaction: upsert the ``repositories`` row by
    ``repository_uid`` (updating ``display_name``/``local_path``/
    ``last_scanned_at``), delete this repository's prior
    commits/events/provenance rows, and reinsert everything from
    ``scanned``. Any failure — a constraint violation, a corrupt
    connection, or anything else raised while building rows — rolls back
    and is re-raised as :class:`StorageError`, leaving the state from
    before this call intact.
    """
    try:
        conn.execute("BEGIN")
    except sqlite3.Error as exc:
        raise StorageError(
            f"failed to start transaction for {repository_uid!r}: {exc}"
        ) from exc

    try:
        repository_id = _upsert_repository(
            conn,
            repository_uid=repository_uid,
            display_name=display_name,
            local_path=local_path,
            scanned_at=scanned_at,
        )
        _delete_repository_rows(conn, repository_id)
        for commit in scanned:
            commit_id = _insert_commit(conn, repository_id, commit)
            for event in commit.events:
                event_row_id = _insert_event(conn, repository_id, commit_id, event)
                for source in event.sources:
                    _insert_provenance_source(conn, event_row_id, source)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise StorageError(
            f"replace_repository_scan failed for {repository_uid!r}: {exc}"
        ) from exc


def _upsert_repository(
    conn: sqlite3.Connection,
    *,
    repository_uid: str,
    display_name: str,
    local_path: str,
    scanned_at: str | None,
) -> int:
    existing = conn.execute(
        "SELECT id FROM repositories WHERE repository_uid = ?", (repository_uid,)
    ).fetchone()
    if existing is None:
        cur = conn.execute(
            "INSERT INTO repositories"
            " (repository_uid, display_name, local_path, last_scanned_at)"
            " VALUES (?, ?, ?, ?)",
            (repository_uid, display_name, local_path, scanned_at),
        )
        return cur.lastrowid
    repository_id = existing["id"]
    conn.execute(
        "UPDATE repositories"
        " SET display_name = ?, local_path = ?, last_scanned_at = ?"
        " WHERE id = ?",
        (display_name, local_path, scanned_at, repository_id),
    )
    return repository_id


def _delete_repository_rows(conn: sqlite3.Connection, repository_id: int) -> None:
    conn.execute(
        "DELETE FROM provenance_sources WHERE event_id IN"
        " (SELECT id FROM events WHERE repository_id = ?)",
        (repository_id,),
    )
    conn.execute("DELETE FROM events WHERE repository_id = ?", (repository_id,))
    conn.execute("DELETE FROM commits WHERE repository_id = ?", (repository_id,))


def _insert_commit(conn: sqlite3.Connection, repository_id: int, commit: CommitEvents) -> int:
    cur = conn.execute(
        "INSERT INTO commits (repository_id, sha, author_email, author_date)"
        " VALUES (?, ?, ?, ?)",
        (repository_id, commit.sha, commit.author_email, commit.author_date),
    )
    return cur.lastrowid


def _insert_event(
    conn: sqlite3.Connection, repository_id: int, commit_id: int, event: AceEvent
) -> int:
    roles_json = json.dumps([r.value for r in event.roles])
    human_reviewed = None if event.human_reviewed is None else int(event.human_reviewed)
    cur = conn.execute(
        "INSERT INTO events ("
        " event_id, repository_id, commit_id, actor_type, provider, provider_raw,"
        " model, model_raw, tool, tool_raw, roles_json, contribution_mode,"
        " human_reviewed, evidence_level, activity_type, activity_timestamp,"
        " recorded_at, schema_version"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event.event_id,
            repository_id,
            commit_id,
            event.actor_type.value,
            event.provider,
            event.provider_raw,
            event.model,
            event.model_raw,
            event.tool,
            event.tool_raw,
            roles_json,
            event.contribution_mode.value if event.contribution_mode else None,
            human_reviewed,
            event.evidence_level.value,
            event.activity_type.value,
            event.timestamp,
            event.recorded_at,
            event.schema_version,
        ),
    )
    return cur.lastrowid


def _insert_provenance_source(
    conn: sqlite3.Connection, event_row_id: int, source: ProvenanceSource
) -> None:
    conn.execute(
        "INSERT INTO provenance_sources"
        " (event_id, source_type, source_reference, evidence_level)"
        " VALUES (?, ?, ?, ?)",
        (
            event_row_id,
            source.source_type.value,
            source.source_reference,
            source.evidence_level.value,
        ),
    )

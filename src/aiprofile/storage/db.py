"""SQLite connection and migration runner (architecture.md section 6, ADR-004).

One connection per CLI invocation, opened in autocommit mode so callers
(this module and :mod:`storage.store`) manage transactions explicitly with
``BEGIN``/``commit()``/``rollback()`` — the only way stdlib ``sqlite3`` lets
DDL participate in a real atomic transaction (its default legacy mode
opens/closes implicit transactions around DML only, never DDL).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from ..errors import StorageError, diagnostic_text
from .migrations import MIGRATIONS

#: Mirrors config._WARN_ON_CHMOD_FAILURE (duplicated, not imported -
#: storage's dependency graph is pinned at {schema, errors} only): POSIX
#: chmod failures warn, Windows stays quiet; module-level so tests can
#: force the warning branch deterministically on any platform.
_WARN_ON_CHMOD_FAILURE = sys.platform != "win32"


def _restrict_to_owner(path: Path, mode: int) -> None:
    """Best-effort owner-only permissions (ROADMAP "owner-only file
    permissions where supported"), mirroring ``config._restrict_to_owner``.

    Duplicated rather than imported: architecture.md section 2 pins
    ``storage``'s dependency graph at ``{schema, errors}`` only, so this
    module stays git/config-free the same way config.py stays git-free.
    POSIX: sets the exact mode. Windows: ``os.chmod`` cannot express
    owner/group/other bits — it only toggles the read-only attribute,
    which any mode with the owner-write bit set already clears (a
    no-op vs. the default-writable file sqlite3 just created) — so this
    is called unconditionally and is harmless there. Failures are
    swallowed: a permission-restriction problem must never break DB
    access.
    """
    try:
        os.chmod(path, mode)
    except OSError:
        # Mirror config._restrict_to_owner: POSIX failures get a stderr
        # signal; Windows stays quiet (documented no-op there, not a
        # failure).
        if _WARN_ON_CHMOD_FAILURE:
            print(
                diagnostic_text(
                    "warning: could not restrict permissions on a private profile file",
                    f"warning: could not restrict permissions on {path}",
                ),
                file=sys.stderr,
            )


def connect(path: str | Path) -> sqlite3.Connection:
    """Open (creating parent directories as needed) a SQLite connection
    with foreign keys enforced and rows accessible by column name.

    Restricts the database file to owner-only permissions (0o600) on every
    call — cheap and idempotent, and covers the file wherever it is first
    created by sqlite3 (init, scan, aggregate, or render, whichever runs
    first against a fresh AIPROFILE_HOME).

    Wraps any failure in :class:`StorageError`.
    """
    try:
        db_path = Path(path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _restrict_to_owner(db_path, 0o600)
        return conn
    except sqlite3.Error as exc:
        raise StorageError(f"failed to open database at {path}: {exc}") from exc


def applied_versions(conn: sqlite3.Connection) -> list[int]:
    """Migration versions already recorded, ascending.

    Empty before the first :func:`migrate` call, since
    ``schema_migrations`` itself does not exist yet on a fresh database.
    """
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table'"
            " AND name = 'schema_migrations'"
        ).fetchone()
        if exists is None:
            return []
        rows = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        return [row["version"] for row in rows]
    except sqlite3.Error as exc:
        raise StorageError(f"failed to read schema_migrations: {exc}") from exc


def migrate(conn: sqlite3.Connection) -> None:
    """Apply each unapplied version from ``MIGRATIONS``, each inside its
    own atomic transaction, recording ``(version, applied_at UTC ISO)`` in
    ``schema_migrations``. A fresh database and an already-migrated one
    both reach head through this same path (mvp.md test 16); calling this
    again once head is reached is a no-op.
    """
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        already = set(applied_versions(conn))
        for version, sql in MIGRATIONS:
            if version in already:
                continue
            conn.execute("BEGIN")
            try:
                for statement in _statements(sql):
                    conn.execute(statement)
                applied_at = datetime.now(UTC).isoformat()
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, applied_at),
                )
                conn.commit()
            except sqlite3.Error:
                conn.rollback()
                raise
    except sqlite3.Error as exc:
        raise StorageError(f"migration failed: {exc}") from exc


def _statements(sql: str) -> list[str]:
    """Split a migration script into individual statements.

    Migration SQL here is plain DDL with no semicolons inside string
    literals, default expressions, or trigger bodies, so a naive split on
    ``;`` is safe and keeps each statement inside the caller's explicit
    transaction (``executescript`` would instead issue its own implicit
    commit first, breaking atomicity).
    """
    return [s.strip() for s in sql.split(";") if s.strip()]

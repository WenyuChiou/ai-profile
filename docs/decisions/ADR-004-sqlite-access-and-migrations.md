# ADR-004: SQLite access and migrations

Status: accepted (2026-07-14)

## Context

Local storage is SQLite (proposal §13). Candidates: SQLAlchemy+alembic,
raw `sqlite3` with an ad hoc `CREATE TABLE IF NOT EXISTS`, or raw
`sqlite3` with a real migration sequence.

## Decision

- Stdlib `sqlite3`, one connection per CLI invocation,
  `PRAGMA foreign_keys = ON`, explicit transactions (`BEGIN`/`COMMIT`)
  around each scan and each migration.
- Migrations: `storage/migrations.py` holds an ordered list
  `[(version:int, sql:str), ...]`; the runner applies each unapplied
  version atomically and records it in `schema_migrations(version,
  applied_at)`. Startup always runs the runner; a fresh DB reaches head
  the same way an old DB does (tested).
- No ORM, no ad hoc table creation scattered in code.

## Consequences

- Migration discipline from day one; schema changes are reviewable diffs.
- Rollbacks are not supported (forward-only); acceptable for a local
  cache-like DB that can be rebuilt by re-scanning.

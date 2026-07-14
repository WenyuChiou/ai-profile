"""Ordered SQL migrations (architecture.md section 6, ADR-004).

``MIGRATIONS`` is the pinned interface: an ordered ``[(version, sql), ...]``
list. Each ``sql`` string may hold multiple ``;``-separated DDL statements;
the runner in :mod:`storage.db` applies every unapplied version atomically
and records it in ``schema_migrations``.

Version 1 creates the v0.1 tables exactly per architecture.md section 6:
``repositories``, ``commits``, ``events``, ``provenance_sources`` — no
``publication_level`` column anywhere (that lives only in config, never in
this disposable cache — architecture.md section 6 notes). Foreign keys use
surrogate integer primary keys throughout, including
``provenance_sources.event_id``, which references ``events.id`` (not the
textual ``events.event_id`` identity column), following the same
``<table>_id -> <table>.id`` convention as ``repository_id``/``commit_id``.
"""

from __future__ import annotations

_V1 = """
CREATE TABLE repositories (
    id INTEGER PRIMARY KEY,
    repository_uid TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    local_path TEXT NOT NULL,
    last_scanned_at TEXT
);

CREATE TABLE commits (
    id INTEGER PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id),
    sha TEXT NOT NULL,
    author_email TEXT NOT NULL,
    author_date TEXT NOT NULL,
    UNIQUE(repository_id, sha)
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    repository_id INTEGER NOT NULL REFERENCES repositories(id),
    commit_id INTEGER NOT NULL REFERENCES commits(id),
    actor_type TEXT NOT NULL,
    provider TEXT,
    provider_raw TEXT,
    model TEXT,
    model_raw TEXT,
    tool TEXT,
    tool_raw TEXT,
    roles_json TEXT NOT NULL,
    contribution_mode TEXT,
    human_reviewed INTEGER,
    evidence_level TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    activity_timestamp TEXT NOT NULL,
    recorded_at TEXT,
    schema_version TEXT NOT NULL
);

CREATE TABLE provenance_sources (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id),
    source_type TEXT NOT NULL,
    source_reference TEXT,
    evidence_level TEXT NOT NULL,
    UNIQUE(event_id, source_type, source_reference)
);

CREATE INDEX idx_events_repository_id ON events(repository_id);
CREATE INDEX idx_commits_repository_id ON commits(repository_id);
CREATE INDEX idx_provenance_sources_event_id ON provenance_sources(event_id);
"""

MIGRATIONS: list[tuple[int, str]] = [
    (1, _V1),
]

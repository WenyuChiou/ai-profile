"""Unit tests for storage/{db,migrations,store}.py (work package C).

Covers mvp.md required tests 6 and 16, plus ADR-014's per-repository
replace contract: idempotence, amend semantics, cross-repository
isolation, rollback-on-failure, and a full event field roundtrip.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime

import pytest

from aiprofile.errors import StorageError
from aiprofile.schema.event import ProvenanceSource, build_event
from aiprofile.schema.vocab import (
    ActorType,
    ContributionMode,
    EvidenceLevel,
    Role,
    SourceType,
)
from aiprofile.storage import db, migrations, store
from aiprofile.storage.store import CommitEvents

# ---------------------------------------------------------------------------
# Fixtures and small helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "aiprofile.db")
    db.migrate(connection)
    yield connection
    connection.close()


def _sha(n: int) -> str:
    """A distinct, valid 40-lowercase-hex commit sha for test fixtures."""
    return f"{n:040x}"


def _ai_event(
    *,
    repository_uid: str,
    commit_sha: str,
    provider: str = "anthropic",
    tool: str = "claude-code",
    timestamp: str = "2026-07-01T10:00:00+00:00",
    role: Role = Role.IMPLEMENTATION,
    human_reviewed: bool | None = True,
):
    return build_event(
        actor_type=ActorType.AI,
        repository_uid=repository_uid,
        commit_sha=commit_sha,
        timestamp=timestamp,
        provider=provider,
        provider_raw=provider,
        tool=tool,
        tool_raw=tool,
        roles=[role],
        contribution_mode=ContributionMode.AI_ASSISTED,
        human_reviewed=human_reviewed,
        sources=[
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider")
        ],
    )


def _dump_all(connection):
    tables = ("repositories", "commits", "events", "provenance_sources")
    return {
        table: [
            dict(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
        ]
        for table in tables
    }


def _repo_dump(connection, repository_uid: str):
    repo = connection.execute(
        "SELECT * FROM repositories WHERE repository_uid = ?", (repository_uid,)
    ).fetchone()
    repository_id = repo["id"]
    commit_rows = connection.execute(
        "SELECT * FROM commits WHERE repository_id = ? ORDER BY sha", (repository_id,)
    ).fetchall()
    event_rows = connection.execute(
        "SELECT * FROM events WHERE repository_id = ? ORDER BY event_id", (repository_id,)
    ).fetchall()
    provenance_rows = connection.execute(
        "SELECT ps.* FROM provenance_sources ps"
        " JOIN events e ON e.id = ps.event_id"
        " WHERE e.repository_id = ? ORDER BY ps.id",
        (repository_id,),
    ).fetchall()
    return {
        "repository": dict(repo),
        "commits": [dict(r) for r in commit_rows],
        "events": [dict(r) for r in event_rows],
        "provenance_sources": [dict(r) for r in provenance_rows],
    }


# ---------------------------------------------------------------------------
# Migrations (mvp.md test 16)
# ---------------------------------------------------------------------------


def test_migrate_fresh_db_reaches_head_and_records_version(tmp_path):
    connection = db.connect(tmp_path / "aiprofile.db")
    try:
        assert db.applied_versions(connection) == []
        db.migrate(connection)
        assert db.applied_versions(connection) == [v for v, _ in migrations.MIGRATIONS]

        rows = connection.execute(
            "SELECT version, applied_at FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert len(rows) == len(migrations.MIGRATIONS)
        for row in rows:
            # UTC ISO timestamp: must parse and carry a UTC offset.
            parsed = datetime.fromisoformat(row["applied_at"])
            assert parsed.utcoffset() is not None

        tables = {
            r["name"]
            for r in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            "schema_migrations",
            "repositories",
            "commits",
            "events",
            "provenance_sources",
        } <= tables
        columns = {
            r["name"]
            for r in connection.execute("PRAGMA table_info(events)").fetchall()
        }
        assert "publication_level" not in columns
    finally:
        connection.close()


def test_migrate_reopen_is_a_noop(tmp_path):
    path = tmp_path / "aiprofile.db"

    first = db.connect(path)
    db.migrate(first)
    first_rows = [tuple(r) for r in first.execute(
        "SELECT version, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()]
    first.close()

    second = db.connect(path)
    db.migrate(second)  # nothing unapplied left
    second_rows = [tuple(r) for r in second.execute(
        "SELECT version, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()]
    second.close()

    # Same recorded versions with the same applied_at (no re-application).
    assert first_rows == second_rows


# ---------------------------------------------------------------------------
# replace_repository_scan: idempotence, amend, isolation, rollback, roundtrip
# ---------------------------------------------------------------------------


def test_replace_repository_scan_idempotent(conn):
    uid = "repo-a"
    sha = _sha(1)

    def _do_scan():
        store.replace_repository_scan(
            conn,
            repository_uid=uid,
            display_name="repo-a",
            local_path="/tmp/repo-a",
            scanned=[
                CommitEvents(
                    sha=sha,
                    author_email="dev@example.com",
                    author_date="2026-07-01T10:00:00+00:00",
                    events=[_ai_event(repository_uid=uid, commit_sha=sha)],
                )
            ],
            scanned_at="2026-07-01T12:00:00+00:00",
        )

    _do_scan()
    dump1 = _dump_all(conn)
    _do_scan()
    dump2 = _dump_all(conn)

    assert dump1 == dump2
    assert len(dump1["commits"]) == 1
    assert len(dump1["events"]) == 1
    assert len(dump1["provenance_sources"]) == 1


def test_replace_repository_scan_amend_removes_old_sha(conn):
    uid = "repo-b"
    old_sha = _sha(10)
    new_sha = _sha(11)

    old_event = _ai_event(repository_uid=uid, commit_sha=old_sha)
    store.replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name="repo-b",
        local_path="/tmp/repo-b",
        scanned=[
            CommitEvents(old_sha, "dev@example.com", "2026-07-01T10:00:00+00:00", [old_event])
        ],
        scanned_at="2026-07-01T12:00:00+00:00",
    )

    new_event = _ai_event(repository_uid=uid, commit_sha=new_sha)
    store.replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name="repo-b",
        local_path="/tmp/repo-b",
        scanned=[
            CommitEvents(new_sha, "dev@example.com", "2026-07-01T10:00:00+00:00", [new_event])
        ],
        scanned_at="2026-07-01T13:00:00+00:00",
    )

    shas = [r["sha"] for r in conn.execute("SELECT sha FROM commits").fetchall()]
    event_ids = [r["event_id"] for r in conn.execute("SELECT event_id FROM events").fetchall()]

    assert shas == [new_sha]
    assert event_ids == [new_event.event_id]
    assert old_event.event_id not in event_ids


def test_replace_repository_scan_leaves_other_repository_intact(conn):
    uid_a, uid_b = "repo-x", "repo-y"
    sha_a1, sha_b = _sha(20), _sha(21)

    store.replace_repository_scan(
        conn,
        repository_uid=uid_a,
        display_name="x",
        local_path="/tmp/x",
        scanned=[
            CommitEvents(
                sha_a1, "x@example.com", "2026-07-01T10:00:00+00:00",
                [_ai_event(repository_uid=uid_a, commit_sha=sha_a1)],
            )
        ],
        scanned_at="2026-07-01T12:00:00+00:00",
    )
    store.replace_repository_scan(
        conn,
        repository_uid=uid_b,
        display_name="y",
        local_path="/tmp/y",
        scanned=[
            CommitEvents(
                sha_b, "y@example.com", "2026-07-01T10:05:00+00:00",
                [_ai_event(repository_uid=uid_b, commit_sha=sha_b)],
            )
        ],
        scanned_at="2026-07-01T12:05:00+00:00",
    )

    b_before = _repo_dump(conn, uid_b)

    sha_a2 = _sha(22)
    store.replace_repository_scan(
        conn,
        repository_uid=uid_a,
        display_name="x",
        local_path="/tmp/x",
        scanned=[
            CommitEvents(
                sha_a2, "x@example.com", "2026-07-01T11:00:00+00:00",
                [_ai_event(repository_uid=uid_a, commit_sha=sha_a2)],
            )
        ],
        scanned_at="2026-07-01T13:00:00+00:00",
    )

    assert _repo_dump(conn, uid_b) == b_before

    a_shas = [
        r["sha"]
        for r in conn.execute(
            "SELECT c.sha FROM commits c"
            " JOIN repositories r ON r.id = c.repository_id"
            " WHERE r.repository_uid = ?",
            (uid_a,),
        ).fetchall()
    ]
    assert a_shas == [sha_a2]


def test_replace_repository_scan_rolls_back_on_duplicate_event_id(conn):
    uid = "repo-c"
    sha1, sha2 = _sha(40), _sha(41)

    prior_event = _ai_event(repository_uid=uid, commit_sha=sha1)
    store.replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name="c",
        local_path="/tmp/c",
        scanned=[
            CommitEvents(sha1, "c@example.com", "2026-07-01T10:00:00+00:00", [prior_event])
        ],
        scanned_at="2026-07-01T12:00:00+00:00",
    )
    prior_dump = _repo_dump(conn, uid)

    ev1 = _ai_event(repository_uid=uid, commit_sha=sha1)
    ev2 = _ai_event(repository_uid=uid, commit_sha=sha2)
    colliding_ev2 = replace(ev2, event_id=ev1.event_id)  # force a UNIQUE violation

    bad_scan = [
        CommitEvents(sha1, "c@example.com", "2026-07-01T10:00:00+00:00", [ev1]),
        CommitEvents(sha2, "c@example.com", "2026-07-01T10:05:00+00:00", [colliding_ev2]),
    ]

    with pytest.raises(StorageError):
        store.replace_repository_scan(
            conn,
            repository_uid=uid,
            display_name="c-renamed",
            local_path="/tmp/c-renamed",
            scanned=bad_scan,
            scanned_at="2026-07-01T13:00:00+00:00",
        )

    assert _repo_dump(conn, uid) == prior_dump


def test_replace_repository_scan_rolls_back_on_unexpected_error(conn, monkeypatch):
    uid = "repo-d"
    sha = _sha(50)

    prior_event = _ai_event(repository_uid=uid, commit_sha=sha)
    store.replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name="d",
        local_path="/tmp/d",
        scanned=[CommitEvents(sha, "d@example.com", "2026-07-01T10:00:00+00:00", [prior_event])],
        scanned_at="2026-07-01T12:00:00+00:00",
    )
    prior_dump = _repo_dump(conn, uid)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated insert failure")

    monkeypatch.setattr(store, "_insert_provenance_source", _boom)

    new_sha = _sha(51)
    with pytest.raises(StorageError):
        store.replace_repository_scan(
            conn,
            repository_uid=uid,
            display_name="d-renamed",
            local_path="/tmp/d-renamed",
            scanned=[
                CommitEvents(
                    new_sha, "d@example.com", "2026-07-01T11:00:00+00:00",
                    [_ai_event(repository_uid=uid, commit_sha=new_sha)],
                )
            ],
            scanned_at="2026-07-01T13:00:00+00:00",
        )

    assert _repo_dump(conn, uid) == prior_dump


def test_replace_repository_scan_roundtrips_all_event_fields(conn):
    uid = "repo-e"
    sha = _sha(60)

    event = build_event(
        actor_type=ActorType.AI,
        repository_uid=uid,
        commit_sha=sha,
        timestamp="2026-07-01T09:30:00+00:00",
        provider="anthropic",
        provider_raw="Anthropic",
        model="claude-sonnet-5",
        model_raw="Claude Sonnet 5",
        tool="claude-code",
        tool_raw="Claude Code",
        roles=[Role.TESTING, Role.IMPLEMENTATION],  # unsorted input
        contribution_mode=ContributionMode.AI_ASSISTED,
        human_reviewed=True,
        sources=[
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"),
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.VERIFIED, "co-authored-by"
            ),
        ],
        recorded_at="2026-07-01T09:35:00+00:00",
    )
    # Sanity: build_event sorts roles (schema.md 8.2) — the DB must preserve this order.
    assert event.roles == (Role.IMPLEMENTATION, Role.TESTING)
    assert event.evidence_level is EvidenceLevel.VERIFIED  # max across sources

    store.replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name="e",
        local_path="/tmp/e",
        scanned=[
            CommitEvents(sha, "e@example.com", "2026-07-01T09:30:00+00:00", [event])
        ],
        scanned_at="2026-07-01T12:00:00+00:00",
    )

    row = conn.execute("SELECT * FROM events WHERE event_id = ?", (event.event_id,)).fetchone()
    assert row is not None
    assert row["actor_type"] == "ai"
    assert row["provider"] == "anthropic"
    assert row["provider_raw"] == "Anthropic"
    assert row["model"] == "claude-sonnet-5"
    assert row["model_raw"] == "Claude Sonnet 5"
    assert row["tool"] == "claude-code"
    assert row["tool_raw"] == "Claude Code"
    assert json.loads(row["roles_json"]) == ["implementation", "testing"]
    assert row["contribution_mode"] == "ai_assisted"
    assert row["human_reviewed"] == 1
    assert row["evidence_level"] == "verified"
    assert row["activity_type"] == "commit"
    assert row["activity_timestamp"] == "2026-07-01T09:30:00+00:00"
    assert row["recorded_at"] == "2026-07-01T09:35:00+00:00"
    assert row["schema_version"] == event.schema_version

    sources = conn.execute(
        "SELECT source_type, source_reference, evidence_level FROM provenance_sources"
        " WHERE event_id = ? ORDER BY id",
        (row["id"],),
    ).fetchall()
    assert [dict(s) for s in sources] == [
        {
            "source_type": "git_trailer",
            "source_reference": "ai-provider",
            "evidence_level": "declared",
        },
        {
            "source_type": "git_trailer_coauthor",
            "source_reference": "co-authored-by",
            "evidence_level": "verified",
        },
    ]

    commit_row = conn.execute(
        "SELECT sha, author_email, author_date FROM commits WHERE sha = ?", (sha,)
    ).fetchone()
    assert dict(commit_row) == {
        "sha": sha,
        "author_email": "e@example.com",
        "author_date": "2026-07-01T09:30:00+00:00",
    }


def test_human_reviewed_stored_as_int_or_null(conn):
    uid = "repo-f"
    sha_true, sha_false, sha_unknown = _sha(70), _sha(71), _sha(72)

    ev_true = _ai_event(repository_uid=uid, commit_sha=sha_true, human_reviewed=True)
    ev_false = _ai_event(repository_uid=uid, commit_sha=sha_false, human_reviewed=False)
    ev_unknown = build_event(
        actor_type=ActorType.UNKNOWN,
        repository_uid=uid,
        commit_sha=sha_unknown,
        timestamp="2026-07-01T10:10:00+00:00",
        sources=[ProvenanceSource(SourceType.NONE, EvidenceLevel.UNKNOWN)],
    )

    store.replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name="f",
        local_path="/tmp/f",
        scanned=[
            CommitEvents(sha_true, "f@example.com", "2026-07-01T10:00:00+00:00", [ev_true]),
            CommitEvents(sha_false, "f@example.com", "2026-07-01T10:05:00+00:00", [ev_false]),
            CommitEvents(sha_unknown, "f@example.com", "2026-07-01T10:10:00+00:00", [ev_unknown]),
        ],
        scanned_at="2026-07-01T12:00:00+00:00",
    )

    rows = {
        r["event_id"]: r["human_reviewed"]
        for r in conn.execute("SELECT event_id, human_reviewed FROM events").fetchall()
    }
    assert rows[ev_true.event_id] == 1
    assert rows[ev_false.event_id] == 0
    assert rows[ev_unknown.event_id] is None


def test_repository_upsert_updates_display_name_local_path_and_last_scanned(conn):
    uid = "repo-g"
    sha = _sha(80)

    store.replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name="old-name",
        local_path="/tmp/old-path",
        scanned=[
            CommitEvents(
                sha, "g@example.com", "2026-07-01T10:00:00+00:00",
                [_ai_event(repository_uid=uid, commit_sha=sha)],
            )
        ],
        scanned_at="2026-07-01T12:00:00+00:00",
    )
    store.replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name="new-name",
        local_path="/tmp/new-path",
        scanned=[
            CommitEvents(
                sha, "g@example.com", "2026-07-01T10:00:00+00:00",
                [_ai_event(repository_uid=uid, commit_sha=sha)],
            )
        ],
        scanned_at="2026-07-02T12:00:00+00:00",
    )

    rows = conn.execute("SELECT * FROM repositories WHERE repository_uid = ?", (uid,)).fetchall()
    assert len(rows) == 1  # upsert, not a second row
    row = rows[0]
    assert row["display_name"] == "new-name"
    assert row["local_path"] == "/tmp/new-path"
    assert row["last_scanned_at"] == "2026-07-02T12:00:00+00:00"

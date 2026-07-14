"""Unit tests for aggregate.py (work package D).

Metric definitions under test: docs/schema.md section 15. Fixtures are
built through the real storage layer (db.connect + migrate +
store.replace_repository_scan with schema.build_event) rather than by
poking raw SQL, so these tests exercise the same path production code
takes.
"""

from __future__ import annotations

import pytest

from aiprofile.aggregate import compute_repo_aggregates
from aiprofile.errors import StorageError
from aiprofile.schema.event import ProvenanceSource, build_event
from aiprofile.schema.vocab import ActorType, EvidenceLevel, SourceType
from aiprofile.storage import db, store
from aiprofile.storage.store import CommitEvents

# ---------------------------------------------------------------------------
# Fixtures and small helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "t.db")
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
    provider: str | None = "anthropic",
    provider_raw: str | None = "Anthropic",
    tool: str | None = "claude-code",
    tool_raw: str | None = "Claude Code",
    timestamp: str = "2026-07-01T10:00:00+00:00",
):
    return build_event(
        actor_type=ActorType.AI,
        repository_uid=repository_uid,
        commit_sha=commit_sha,
        timestamp=timestamp,
        provider=provider,
        provider_raw=provider_raw,
        tool=tool,
        tool_raw=tool_raw,
        sources=[
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "AI-Provider")
        ],
    )


def _human_event(
    *, repository_uid: str, commit_sha: str, timestamp: str = "2026-07-01T10:00:00+00:00"
):
    return build_event(
        actor_type=ActorType.HUMAN,
        repository_uid=repository_uid,
        commit_sha=commit_sha,
        timestamp=timestamp,
        sources=[
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "AI-Mode")
        ],
    )


def _unknown_event(
    *, repository_uid: str, commit_sha: str, timestamp: str = "2026-07-01T10:00:00+00:00"
):
    return build_event(
        actor_type=ActorType.UNKNOWN,
        repository_uid=repository_uid,
        commit_sha=commit_sha,
        timestamp=timestamp,
        sources=[ProvenanceSource(SourceType.NONE, EvidenceLevel.UNKNOWN)],
    )


def _scan(conn, *, repository_uid: str, commits: list[CommitEvents]):
    store.replace_repository_scan(
        conn,
        repository_uid=repository_uid,
        display_name=repository_uid,
        local_path=f"/tmp/{repository_uid}",
        scanned=commits,
        scanned_at="2026-07-01T12:00:00+00:00",
    )


def _one(results, repository_uid: str):
    matches = [r for r in results if r.repository_uid == repository_uid]
    assert len(matches) == 1, f"expected exactly one aggregate for {repository_uid!r}"
    return matches[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_multi_ai_commit_never_double_counts(conn):
    """One commit, two providers -> ai_attributed_commits stays 1, but
    ai_participation_events and each provider's attributed_commits count
    the participation, not the commit, twice."""
    uid = "repo-multi"
    sha = _sha(1)
    ev_anthropic = _ai_event(
        repository_uid=uid, commit_sha=sha, provider="anthropic", tool="claude-code"
    )
    ev_openai = _ai_event(
        repository_uid=uid,
        commit_sha=sha,
        provider="openai",
        provider_raw="OpenAI",
        tool="codex-cli",
        tool_raw="Codex CLI",
    )
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(
            sha, "dev@example.com", "2026-07-01T10:00:00+00:00", [ev_anthropic, ev_openai]
        ),
    ])

    agg = _one(compute_repo_aggregates(conn), uid)

    assert agg.commits_scanned == 1
    assert agg.ai_attributed_commits == 1
    assert agg.ai_participation_events == 2
    assert agg.providers["anthropic"].attributed_commits == 1
    assert agg.providers["anthropic"].participation_events == 1
    assert agg.providers["openai"].attributed_commits == 1
    assert agg.providers["openai"].participation_events == 1


def test_unknown_vs_human_separation(conn):
    """A no-evidence commit and a human-declared commit stay in disjoint
    buckets — neither counted as the other."""
    uid = "repo-sep"
    sha_unknown = _sha(2)
    sha_human = _sha(3)
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(
            sha_unknown, "dev@example.com", "2026-07-01T10:00:00+00:00",
            [_unknown_event(repository_uid=uid, commit_sha=sha_unknown)],
        ),
        CommitEvents(
            sha_human, "dev@example.com", "2026-07-01T11:00:00+00:00",
            [_human_event(repository_uid=uid, commit_sha=sha_human)],
        ),
    ])

    agg = _one(compute_repo_aggregates(conn), uid)

    assert agg.commits_scanned == 2
    assert agg.unknown_commits == 1
    assert agg.human_declared_commits == 1
    assert agg.ai_attributed_commits == 0
    assert agg.ai_participation_events == 0


def test_evidence_events_counts_across_all_actor_types(conn):
    """evidence_events sums events (not commits) across every actor type."""
    uid = "repo-evidence"
    sha_ai = _sha(4)
    sha_human = _sha(5)
    sha_unknown = _sha(6)
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(
            sha_ai, "dev@example.com", "2026-07-01T10:00:00+00:00",
            [_ai_event(repository_uid=uid, commit_sha=sha_ai)],
        ),
        CommitEvents(
            sha_human, "dev@example.com", "2026-07-01T11:00:00+00:00",
            [_human_event(repository_uid=uid, commit_sha=sha_human)],
        ),
        CommitEvents(
            sha_unknown, "dev@example.com", "2026-07-01T12:00:00+00:00",
            [_unknown_event(repository_uid=uid, commit_sha=sha_unknown)],
        ),
    ])

    agg = _one(compute_repo_aggregates(conn), uid)

    # ai event + human event both carry evidence_level=declared (schema.md
    # section 2: human is only ever produced by explicit declaration).
    assert agg.evidence_events["declared"] == 2
    assert agg.evidence_events["unknown"] == 1


def test_active_dates_use_author_local_iso_prefix(conn):
    """Active dates take the first 10 characters of the stored timestamp
    verbatim -- no timezone conversion, even across an offset that would
    shift the UTC calendar day."""
    uid = "repo-dates"
    sha = _sha(7)
    ts = "2026-01-05T23:30:00+08:00"  # UTC would be 2026-01-05T15:30:00Z; still same day here
    ev = _ai_event(repository_uid=uid, commit_sha=sha, timestamp=ts)
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(sha, "dev@example.com", ts, [ev]),
    ])

    agg = _one(compute_repo_aggregates(conn), uid)

    assert agg.active_ai_dates == {"2026-01-05"}
    assert agg.providers["anthropic"].active_dates == {"2026-01-05"}


def test_unrecognized_provider_collects_raw_values_under_none(conn):
    """A canonical-null AI participation groups under providers[None], and
    its raw provider string is retained (local-only visibility)."""
    uid = "repo-unrecognized"
    sha = _sha(8)
    ev = _ai_event(
        repository_uid=uid,
        commit_sha=sha,
        provider=None,
        provider_raw="WeirdAI-99",
        tool=None,
        tool_raw=None,
    )
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(sha, "dev@example.com", "2026-07-01T10:00:00+00:00", [ev]),
    ])

    agg = _one(compute_repo_aggregates(conn), uid)

    assert None in agg.providers
    none_agg = agg.providers[None]
    assert none_agg.attributed_commits == 1
    assert none_agg.participation_events == 1
    assert "WeirdAI-99" in none_agg.raw_values


def test_two_repositories_isolated_and_sorted_by_uid(conn):
    uid_b = "repo-b"
    uid_a = "repo-a"
    sha_b = _sha(9)
    sha_a = _sha(10)
    # Insert repo-b first so a naive insertion-order return would fail sort.
    ev_b = _ai_event(repository_uid=uid_b, commit_sha=sha_b)
    _scan(conn, repository_uid=uid_b, commits=[
        CommitEvents(sha_b, "dev@example.com", "2026-07-01T10:00:00+00:00", [ev_b]),
    ])
    ev_a = _human_event(repository_uid=uid_a, commit_sha=sha_a)
    _scan(conn, repository_uid=uid_a, commits=[
        CommitEvents(sha_a, "dev@example.com", "2026-07-01T10:00:00+00:00", [ev_a]),
    ])

    results = compute_repo_aggregates(conn)

    assert [r.repository_uid for r in results] == [uid_a, uid_b]
    agg_a = _one(results, uid_a)
    agg_b = _one(results, uid_b)
    assert agg_a.human_declared_commits == 1
    assert agg_a.ai_attributed_commits == 0
    assert agg_b.ai_attributed_commits == 1
    assert agg_b.human_declared_commits == 0


def test_unsupported_schema_version_raises_storage_error(conn):
    uid = "repo-version"
    sha = _sha(11)
    ev = _ai_event(repository_uid=uid, commit_sha=sha)
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(sha, "dev@example.com", "2026-07-01T10:00:00+00:00", [ev]),
    ])
    conn.execute("UPDATE events SET schema_version = '0.9.0'")

    with pytest.raises(StorageError) as exc_info:
        compute_repo_aggregates(conn)

    assert "0.9" in str(exc_info.value)


def test_unparseable_schema_version_raises_storage_error(conn):
    uid = "repo-badversion"
    sha = _sha(12)
    ev = _ai_event(repository_uid=uid, commit_sha=sha)
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(sha, "dev@example.com", "2026-07-01T10:00:00+00:00", [ev]),
    ])
    conn.execute("UPDATE events SET schema_version = 'not-a-version'")

    with pytest.raises(StorageError):
        compute_repo_aggregates(conn)


def test_empty_database_returns_empty_list(conn):
    assert compute_repo_aggregates(conn) == []


def test_repository_with_zero_commits_yields_zero_filled_row(conn):
    uid = "repo-empty"
    _scan(conn, repository_uid=uid, commits=[])

    results = compute_repo_aggregates(conn)

    agg = _one(results, uid)
    assert agg.commits_scanned == 0
    assert agg.ai_attributed_commits == 0
    assert agg.ai_participation_events == 0
    assert agg.human_declared_commits == 0
    assert agg.unknown_commits == 0
    assert agg.active_ai_dates == set()
    assert agg.evidence_events == {}
    assert agg.providers == {}

"""Unit tests for aggregate.py (work package D).

Metric definitions under test: docs/schema.md section 15. Fixtures are
built through the real storage layer (db.connect + migrate +
store.replace_repository_scan with schema.build_event) rather than by
poking raw SQL, so these tests exercise the same path production code
takes.
"""

from __future__ import annotations

import pytest

from aiprofile.aggregate import (
    DailyProviderRow,
    compute_daily_provider_counts,
    compute_repo_aggregates,
)
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
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider")
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
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-mode")
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
    ai_actor_presences and each provider's attributed_commits count
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
    assert agg.ai_actor_presences == 2
    assert agg.providers["anthropic"].attributed_commits == 1
    assert agg.providers["anthropic"].actor_presences == 1
    assert agg.providers["openai"].attributed_commits == 1
    assert agg.providers["openai"].actor_presences == 1


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
    assert agg.ai_actor_presences == 0


def test_evidence_records_counts_across_all_actor_types(conn):
    """evidence_records sums events (not commits) across every actor type."""
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
    assert agg.evidence_records["declared"] == 2
    assert agg.evidence_records["unknown"] == 1


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
    assert none_agg.actor_presences == 1
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
    assert agg.ai_actor_presences == 0
    assert agg.human_declared_commits == 0
    assert agg.unknown_commits == 0
    assert agg.active_ai_dates == set()
    assert agg.evidence_records == {}
    assert agg.providers == {}


# ---------------------------------------------------------------------------
# compute_daily_provider_counts (round D2 isometric calendar, lane A)
#
# Interface pinned by the orchestrator:
#   aggregate.compute_daily_provider_counts(conn) -> tuple[DailyProviderRow, ...]
# Population: actor_type in {ai, mixed} - the same schema.md section 15
# AI definition the rest of this module uses (maintainer ruling during
# D2; test_daily_mixed_actor_type_counts_as_ai pins it).
# ---------------------------------------------------------------------------


def _daily_rows(conn, uid: str) -> list[DailyProviderRow]:
    return [r for r in compute_daily_provider_counts(conn) if r.repository_uid == uid]


def test_daily_multi_repo_separation(conn):
    """Same date, same provider, two different repositories -> two rows,
    each scoped to its own repository_uid and each counting only its own
    commit. Would fail if the query grouped by (date, provider) alone and
    merged repositories together (e.g. a JOIN/GROUP BY missing
    repository_uid), which would collapse this into a single row with
    attributed_commits == 2."""
    uid_a, uid_b = "repo-daily-a", "repo-daily-b"
    sha_a, sha_b = _sha(20), _sha(21)
    ts = "2026-06-01T09:00:00+00:00"
    ev_a = _ai_event(repository_uid=uid_a, commit_sha=sha_a, provider="anthropic", timestamp=ts)
    ev_b = _ai_event(repository_uid=uid_b, commit_sha=sha_b, provider="anthropic", timestamp=ts)
    _scan(conn, repository_uid=uid_a, commits=[CommitEvents(sha_a, "d@e.com", ts, [ev_a])])
    _scan(conn, repository_uid=uid_b, commits=[CommitEvents(sha_b, "d@e.com", ts, [ev_b])])

    rows = compute_daily_provider_counts(conn)

    matching = [r for r in rows if r.date == "2026-06-01" and r.provider == "anthropic"]
    assert {r.repository_uid for r in matching} == {uid_a, uid_b}
    for row in matching:
        assert row.attributed_commits == 1


def test_daily_multi_provider_same_day(conn):
    """Two different commits, different providers, same repo and day ->
    two distinct provider rows for that day. Would fail if provider were
    dropped from the GROUP BY (all AI activity for the day collapsing
    into one row), losing the per-provider breakdown the isometric
    stacked columns need."""
    uid = "repo-daily-multiprov"
    sha_1, sha_2 = _sha(22), _sha(23)
    ts = "2026-06-02T08:00:00+00:00"
    ev_anthropic = _ai_event(
        repository_uid=uid, commit_sha=sha_1, provider="anthropic", timestamp=ts
    )
    ev_openai = _ai_event(
        repository_uid=uid, commit_sha=sha_2, provider="openai",
        provider_raw="OpenAI", tool="codex-cli", tool_raw="Codex CLI", timestamp=ts,
    )
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(sha_1, "d@e.com", ts, [ev_anthropic]),
        CommitEvents(sha_2, "d@e.com", ts, [ev_openai]),
    ])

    rows = _daily_rows(conn, uid)

    by_provider = {r.provider: r for r in rows}
    assert by_provider.keys() == {"anthropic", "openai"}
    assert by_provider["anthropic"].attributed_commits == 1
    assert by_provider["openai"].attributed_commits == 1


def test_daily_multi_commit_same_provider_same_day_counted_distinctly(conn):
    """Two commits carrying the same provider on the same day count as 2
    attributed commits, not merged into 1 -- and a commit with a
    DUPLICATE same-provider event (two actions, one presence per G2-02)
    must still count that commit only once. Would fail if COUNT() lacked
    DISTINCT on commit_id: the duplicate-event commit would then
    contribute 2 to the total instead of 1, yielding 3 instead of 2."""
    uid = "repo-daily-multicommit"
    sha_1, sha_2 = _sha(24), _sha(25)
    ts = "2026-06-03T08:00:00+00:00"
    ev_1a = _ai_event(repository_uid=uid, commit_sha=sha_1, provider="anthropic", timestamp=ts)
    ev_1b = _ai_event(
        repository_uid=uid, commit_sha=sha_1, provider="anthropic",
        tool="cursor", tool_raw="Cursor", timestamp=ts,
    )
    ev_2 = _ai_event(repository_uid=uid, commit_sha=sha_2, provider="anthropic", timestamp=ts)
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(sha_1, "d@e.com", ts, [ev_1a, ev_1b]),
        CommitEvents(sha_2, "d@e.com", ts, [ev_2]),
    ])

    rows = _daily_rows(conn, uid)

    assert len(rows) == 1
    assert rows[0].provider == "anthropic"
    assert rows[0].attributed_commits == 2


def test_daily_single_commit_two_providers_appears_in_both_provider_rows(conn):
    """One commit carrying two providers appears in BOTH provider rows for
    that day (attributed-commit semantic, matching ProviderAgg above) --
    not split, not deduplicated away. Would fail if the query only kept
    one provider per commit (e.g. a non-GROUP-BY provider pick)."""
    uid = "repo-daily-twoprov-onecommit"
    sha = _sha(26)
    ts = "2026-06-04T08:00:00+00:00"
    ev_anthropic = _ai_event(repository_uid=uid, commit_sha=sha, provider="anthropic", timestamp=ts)
    ev_openai = _ai_event(
        repository_uid=uid, commit_sha=sha, provider="openai",
        provider_raw="OpenAI", tool="codex-cli", tool_raw="Codex CLI", timestamp=ts,
    )
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(sha, "d@e.com", ts, [ev_anthropic, ev_openai]),
    ])

    rows = _daily_rows(conn, uid)

    by_provider = {r.provider: r for r in rows}
    assert by_provider.keys() == {"anthropic", "openai"}
    assert by_provider["anthropic"].attributed_commits == 1
    assert by_provider["openai"].attributed_commits == 1


def test_daily_date_from_commit_author_date_not_event_timestamp(conn):
    """date comes from commits.author_date, not events.activity_timestamp
    -- the spec's join is events -> commits keyed on author_date. Would
    fail if the query (or a future refactor) read activity_timestamp
    instead, since this fixture gives the event a timestamp on a
    different day than the commit's own author_date."""
    uid = "repo-daily-authordate"
    sha = _sha(27)
    commit_author_date = "2026-06-05T08:00:00+00:00"
    event_timestamp = "2026-06-09T08:00:00+00:00"  # deliberately a different day
    ev = _ai_event(
        repository_uid=uid, commit_sha=sha, provider="anthropic", timestamp=event_timestamp
    )
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(sha, "d@e.com", commit_author_date, [ev]),
    ])

    rows = _daily_rows(conn, uid)

    assert len(rows) == 1
    assert rows[0].date == "2026-06-05"


def test_daily_timestamps_with_times_collapse_to_one_date_no_tz_conversion(conn):
    """Two commits on the same author-local calendar day but different
    times of day (and a UTC offset that WOULD shift the calendar day
    under UTC conversion) collapse into one date row with
    attributed_commits == 2. Empirically verified against SQLite's own
    date() function before writing this: date('2026-06-05T23:30:00+08:00')
    returns '2026-06-05' here, but date('2026-06-06T01:00:00+09:00')
    returns '2026-06-05' (converts to UTC) where the verbatim-prefix rule
    this function uses must return '2026-06-06'. This test's second
    fixture uses exactly that shape, so it would fail if substr() were
    swapped for SQLite's date()."""
    uid = "repo-daily-tzsafe"
    sha_1, sha_2 = _sha(28), _sha(29)
    ts_1 = "2026-06-06T01:00:00+09:00"  # UTC would be 2026-06-05 -- must stay 2026-06-06
    ts_2 = "2026-06-06T23:00:00+09:00"
    ev_1 = _ai_event(repository_uid=uid, commit_sha=sha_1, provider="anthropic", timestamp=ts_1)
    ev_2 = _ai_event(repository_uid=uid, commit_sha=sha_2, provider="anthropic", timestamp=ts_2)
    _scan(conn, repository_uid=uid, commits=[
        CommitEvents(sha_1, "d@e.com", ts_1, [ev_1]),
        CommitEvents(sha_2, "d@e.com", ts_2, [ev_2]),
    ])

    rows = _daily_rows(conn, uid)

    assert len(rows) == 1
    assert rows[0].date == "2026-06-06"
    assert rows[0].attributed_commits == 2


def test_daily_null_provider_preserved_as_none(conn):
    """A canonical-null AI participation groups under provider=None (not
    collapsed to the 'unrecognized' display bucket -- that is privacy.py's
    job). Would fail if the row construction coerced NULL to a sentinel
    string, or if the query's WHERE/GROUP BY silently excluded NULL
    providers (SQLite groups NULLs together, but a naive equality filter
    elsewhere could drop them)."""
    uid = "repo-daily-nullprovider"
    sha = _sha(30)
    ts = "2026-06-07T08:00:00+00:00"
    ev = _ai_event(
        repository_uid=uid, commit_sha=sha, provider=None,
        provider_raw="WeirdAI-99", tool=None, tool_raw=None, timestamp=ts,
    )
    _scan(conn, repository_uid=uid, commits=[CommitEvents(sha, "d@e.com", ts, [ev])])

    rows = _daily_rows(conn, uid)

    assert len(rows) == 1
    assert rows[0].provider is None
    assert rows[0].attributed_commits == 1


def test_daily_deterministic_ordering(conn):
    """Rows come back strictly ordered by (date, provider, repository_uid)
    regardless of insertion order, with None providers sorting before any
    named slug within a date. Would fail if the query had no ORDER BY (SQL
    engines do not guarantee GROUP BY output order) or ordered on the
    wrong column set."""
    ts_early, ts_late = "2026-06-08T08:00:00+00:00", "2026-06-09T08:00:00+00:00"
    uid_z, uid_a = "repo-z", "repo-a"
    sha_1, sha_2, sha_3, sha_4 = _sha(31), _sha(32), _sha(33), _sha(34)
    # Insert deliberately out of every natural order: late date first,
    # 'repo-z' before 'repo-a', named provider before None.
    ev_late = _ai_event(
        repository_uid=uid_a, commit_sha=sha_1, provider="openai", timestamp=ts_late
    )
    ev_early_z = _ai_event(
        repository_uid=uid_z, commit_sha=sha_2, provider="anthropic", timestamp=ts_early
    )
    ev_early_a = _ai_event(
        repository_uid=uid_a, commit_sha=sha_3, provider="anthropic", timestamp=ts_early
    )
    ev_early_null = _ai_event(
        repository_uid=uid_a, commit_sha=sha_4, provider=None,
        provider_raw="Mystery", tool=None, tool_raw=None, timestamp=ts_early,
    )
    _scan(conn, repository_uid=uid_a, commits=[
        CommitEvents(sha_1, "d@e.com", ts_late, [ev_late]),
        CommitEvents(sha_3, "d@e.com", ts_early, [ev_early_a]),
        CommitEvents(sha_4, "d@e.com", ts_early, [ev_early_null]),
    ])
    _scan(conn, repository_uid=uid_z, commits=[
        CommitEvents(sha_2, "d@e.com", ts_early, [ev_early_z]),
    ])

    rows = compute_daily_provider_counts(conn)

    keys = [(r.date, r.provider, r.repository_uid) for r in rows]
    assert keys == sorted(keys, key=lambda k: (k[0], k[1] is not None, k[1] or "", k[2]))
    # And explicitly: the early date's None-provider row precedes its
    # named-provider rows.
    early_rows = [k for k in keys if k[0] == "2026-06-08"]
    assert early_rows[0][1] is None


def test_daily_mixed_actor_type_counts_as_ai(conn):
    """MAINTAINER RULING (round D2): the daily series follows schema.md
    section 15's AI definition - actor_type in {ai, mixed} - exactly like
    compute_repo_aggregates and the provider rows. The lane originally
    delivered a literal 'ai'-only filter per its pinned brief and flagged
    the divergence; ruling aligns the calendar with the provider-row
    semantic so the two can never drift apart the moment a 'mixed'
    producer ships. This test would fail if the filter silently narrowed
    back to 'ai'-only."""
    uid = "repo-daily-mixed"
    sha = _sha(35)
    ts = "2026-06-10T08:00:00+00:00"
    ev_mixed = build_event(
        actor_type=ActorType.MIXED,
        repository_uid=uid,
        commit_sha=sha,
        timestamp=ts,
        provider="anthropic",
        provider_raw="Anthropic",
        tool="claude-code",
        tool_raw="Claude Code",
        sources=[ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider")],
    )
    _scan(conn, repository_uid=uid, commits=[CommitEvents(sha, "d@e.com", ts, [ev_mixed])])

    # Sanity: compute_repo_aggregates counts this as AI (the {ai, mixed}
    # definition); the daily series must agree.
    agg = _one(compute_repo_aggregates(conn), uid)
    assert agg.ai_attributed_commits == 1

    rows = _daily_rows(conn, uid)

    assert len(rows) == 1
    assert rows[0].provider == "anthropic"
    assert rows[0].attributed_commits == 1


def test_daily_unsupported_schema_version_raises_storage_error(conn):
    uid = "repo-daily-version"
    sha = _sha(36)
    ts = "2026-06-11T08:00:00+00:00"
    ev = _ai_event(repository_uid=uid, commit_sha=sha, timestamp=ts)
    _scan(conn, repository_uid=uid, commits=[CommitEvents(sha, "d@e.com", ts, [ev])])
    conn.execute("UPDATE events SET schema_version = '0.9.0'")

    with pytest.raises(StorageError) as exc_info:
        compute_daily_provider_counts(conn)

    assert "0.9" in str(exc_info.value)


def test_daily_empty_database_returns_empty_tuple(conn):
    assert compute_daily_provider_counts(conn) == ()

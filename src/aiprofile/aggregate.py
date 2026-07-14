"""Aggregation: SQL over stored events → RepoAggregates (internal).

INTERFACE PINNED BY THE ORCHESTRATOR — work package D implements
compute_repo_aggregates without changing the dataclasses. RepoAggregates
is internal to the pipeline: only privacy.py may consume it; it never
reaches renderers, exports, or stdout (architecture.md section 7).
Metric definitions: docs/schema.md section 15 (units are normative).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from .errors import StorageError

#: major.minor ACE schema versions this aggregator knows how to read
#: (ADR-012). Bump alongside a real migration, never to silence this guard.
_SUPPORTED_SCHEMA_VERSIONS = {"0.1"}


@dataclass
class ProviderAgg:
    """Per-provider counts within one repository. Key context: the owning
    RepoAggregates.providers dict is keyed by canonical provider slug, or
    None for unrecognized (canonical-null) participations."""

    attributed_commits: int = 0        # distinct commits with >=1 event of this provider
    actor_presences: int = 0           # AI actor presences (G2-02)
    active_dates: set[str] = field(default_factory=set)   # YYYY-MM-DD, author-local
    raw_values: set[str] = field(default_factory=set)     # raw provider strings;
                                                          # local-only (-v), never public


@dataclass
class RepoAggregates:
    repository_uid: str
    commits_scanned: int = 0           # unique commits stored for this repo
    ai_attributed_commits: int = 0     # commits with >=1 ai/mixed event
    ai_actor_presences: int = 0        # ai/mixed records (presences)
    human_declared_commits: int = 0    # commits with human event(s) and no ai
    unknown_commits: int = 0           # commits with only unknown events
    active_ai_dates: set[str] = field(default_factory=set)  # dates with >=1 ai event
    evidence_records: dict[str, int] = field(default_factory=dict)  # level -> records
    providers: dict[str | None, ProviderAgg] = field(default_factory=dict)


def compute_repo_aggregates(conn: sqlite3.Connection) -> list[RepoAggregates]:
    """One RepoAggregates per stored repository (implemented by work
    package D).

    Contract:
    - Metric definitions and units exactly per schema.md section 15;
      active dates are the date part of the stored ISO author timestamp
      (the author's own local day — no timezone conversion).
    - actor_type 'mixed' counts as AI (schema.md section 15).
    - Provider key = events.provider (canonical slug) or None when null;
      raw_values collects events.provider_raw for canonical-null events.
    - Refuse to aggregate unsupported schema versions: if any stored
      events.schema_version has major.minor above the supported set
      ({"0.1"}), raise StorageError naming the version (ADR-012) — never
      silently skip rows.
    - Read-only: plain SELECTs, no writes, no config access (publication
      policy is privacy.py's job, not aggregation's).
    """
    _check_schema_versions(conn)

    repo_rows = conn.execute(
        "SELECT id, repository_uid FROM repositories ORDER BY repository_uid"
    ).fetchall()

    results = [
        _aggregate_repository(conn, repo_row["id"], repo_row["repository_uid"])
        for repo_row in repo_rows
    ]
    results.sort(key=lambda agg: agg.repository_uid)
    return results


def _check_schema_versions(conn: sqlite3.Connection) -> None:
    """Refuse to aggregate if any stored event carries an unsupported ACE
    schema version (ADR-012). Runs first, over the whole database — never
    silently skips rows from an offending version."""
    rows = conn.execute("SELECT DISTINCT schema_version FROM events").fetchall()
    for row in rows:
        version = row["schema_version"]
        major_minor = _major_minor(version)
        if major_minor is None or major_minor not in _SUPPORTED_SCHEMA_VERSIONS:
            raise StorageError(
                f"unsupported ACE schema_version {version!r} found in stored"
                f" events (supported: {sorted(_SUPPORTED_SCHEMA_VERSIONS)});"
                " upgrade aiprofile before aggregating this database (ADR-012)"
            )


def _major_minor(version: str | None) -> str | None:
    """``"0.1.0"`` -> ``"0.1"``; ``None`` for anything unparseable."""
    parts = (version or "").split(".")
    if len(parts) < 2:
        return None
    major, minor = parts[0], parts[1]
    if not (major.isdigit() and minor.isdigit()):
        return None
    return f"{major}.{minor}"


def _aggregate_repository(
    conn: sqlite3.Connection, repository_id: int, repository_uid: str
) -> RepoAggregates:
    """One repository's counts (schema.md section 15 definitions)."""
    commits_scanned = conn.execute(
        "SELECT COUNT(*) AS n FROM commits WHERE repository_id = ?",
        (repository_id,),
    ).fetchone()["n"]

    agg = RepoAggregates(repository_uid=repository_uid, commits_scanned=commits_scanned)

    event_rows = conn.execute(
        "SELECT commit_id, actor_type, provider, provider_raw, tool_raw,"
        " evidence_level, activity_timestamp"
        " FROM events WHERE repository_id = ?",
        (repository_id,),
    ).fetchall()

    ai_commits: set[int] = set()
    human_commits: set[int] = set()
    unknown_commits: set[int] = set()
    provider_commits: dict[str | None, set[int]] = {}

    for row in event_rows:
        actor_type = row["actor_type"]
        commit_id = row["commit_id"]

        evidence_level = row["evidence_level"]
        agg.evidence_records[evidence_level] = agg.evidence_records.get(evidence_level, 0) + 1

        if actor_type in ("ai", "mixed"):
            ai_commits.add(commit_id)
            agg.ai_actor_presences += 1
            date = row["activity_timestamp"][:10]
            agg.active_ai_dates.add(date)

            provider_key = row["provider"]
            provider_agg = agg.providers.setdefault(provider_key, ProviderAgg())
            provider_agg.actor_presences += 1
            provider_agg.active_dates.add(date)
            provider_commits.setdefault(provider_key, set()).add(commit_id)

            if provider_key is None:
                raw = row["provider_raw"] if row["provider_raw"] is not None else row["tool_raw"]
                if raw is not None:
                    provider_agg.raw_values.add(raw)
        elif actor_type == "human":
            human_commits.add(commit_id)
        elif actor_type == "unknown":
            unknown_commits.add(commit_id)

    for provider_key, commit_ids in provider_commits.items():
        agg.providers[provider_key].attributed_commits = len(commit_ids)

    agg.ai_attributed_commits = len(ai_commits)
    agg.human_declared_commits = len(human_commits - ai_commits)
    agg.unknown_commits = len(unknown_commits - ai_commits - human_commits)

    return agg

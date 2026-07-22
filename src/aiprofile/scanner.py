"""Repository scanner: gitio → adapters → schema → storage (one repo).

Owns two schema invariants: the identity filter (ADR-015: author email must
match a configured identity) and unknown handling (schema.md section 11: a
kept commit with zero ACE records gets exactly one unknown record).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import gitio
from .adapters.trailers import ParseWarning, ParticipationSpec, parse_commit_trailers
from .config import Config, effective_level, save_config, upsert_repository
from .errors import AiProfileError, ConfigError, GitError
from .schema.event import AceEvent, ProvenanceSource, build_event, merge_event_group
from .schema.vocab import ActorType, EvidenceLevel, PublicationLevel, SourceType
from .storage.store import CommitEvents, replace_repository_scan


@dataclass
class ScanSummary:
    repository_uid: str
    display_name: str
    excluded: bool = False
    commits_seen: int = 0            # all HEAD-reachable commits
    commits_kept: int = 0            # authored by a configured identity
    commits_skipped_identity: int = 0
    events_stored: int = 0
    #: (scan-local ordinal over commits seen, sha, warning). Default output
    #: prints the ordinal only — SHAs are stable cross-system correlators
    #: and appear only under --verbose (architecture.md section 10, G2-08).
    warnings: list[tuple[int, str, ParseWarning]] = field(default_factory=list)


def scan_repository(
    home: Path,
    cfg: Config,
    conn,
    repo_path: str,
    *,
    make_full: bool = False,
    recorded_at: str | None = None,
) -> ScanSummary:
    """Register (config) and scan (storage) one local repository.

    Commit ordering (gate C-04): every mutation is staged in memory —
    preflight, enumeration, parsing, and the atomic database replacement
    all complete BEFORE the config file is persisted. A failure at any
    earlier step leaves the on-disk config byte-identical (so a failed
    `scan --full` can never elevate policy over stale cached data); if the
    database commit succeeds but the config write fails, the new uid is
    unconfigured and therefore excluded — the fail-closed direction.
    """
    path = Path(repo_path)
    gitio.assert_repository(path)
    fmt = gitio.object_format(path)
    if fmt != "sha1":
        # Path-free by design (gate H-04).
        raise GitError(
            f"this repository uses the {fmt} object format, which v0.1 does"
            " not support (SHA-1 repositories only - ADR-005); no data was"
            " imported and no configuration was changed"
        )
    if not cfg.identities:
        raise ConfigError(
            "no identities configured - add your git author email(s) to"
            " config.json (identities)"
        )

    uid = gitio.repository_uid(path, cfg.salt)
    resolved = str(path.resolve())
    prev_entry = next((e for e in cfg.repositories if e.path == resolved), None)
    old_uid = prev_entry.repository_uid if prev_entry else None
    entry = upsert_repository(cfg, path=resolved, repository_uid=uid, make_full=make_full)
    purge_uids: tuple[str, ...] = ()
    if old_uid and old_uid != uid:
        purge_uids = _migrate_alias_uids(cfg, entry, old_uid)

    display_name = path.resolve().name
    summary = ScanSummary(repository_uid=uid, display_name=display_name)

    if effective_level(cfg, uid) is PublicationLevel.EXCLUDED:
        # Scan-time skip (schema.md section 9). Nothing was scanned, so
        # nothing is persisted — the in-memory registration is discarded
        # (fail-closed: config changes only ride a successful scan).
        summary.excluded = True
        return summary

    records = gitio.enumerate_commits(path)
    summary.commits_seen = len(records)
    identities = {i.strip().lower() for i in cfg.identities}

    scanned: list[CommitEvents] = []
    for ordinal, rec in enumerate(records, start=1):
        if rec.author_email.strip().lower() not in identities:
            summary.commits_skipped_identity += 1
            continue

        specs, warns = parse_commit_trailers(rec.trailer_lines)
        summary.warnings.extend((ordinal, rec.sha, w) for w in warns)

        # Collect ALL leaf productions per identity first, then reduce each
        # group in one canonical batch — an incremental pairwise fold is not
        # ingestion-order-free (schema.md 8.3, gate round-2 P1).
        productions: dict[str, list[AceEvent]] = {}
        for spec in specs:
            ev = _event_from_spec(spec, rec, uid, recorded_at)
            productions.setdefault(ev.event_id, []).append(ev)
        events: dict[str, AceEvent] = {
            event_id: merge_event_group(leaves)
            for event_id, leaves in productions.items()
        }

        if not events:
            unknown = build_event(
                actor_type=ActorType.UNKNOWN,
                repository_uid=uid,
                commit_sha=rec.sha,
                timestamp=rec.author_date,
                sources=[
                    ProvenanceSource(SourceType.NONE, EvidenceLevel.UNKNOWN)
                ],
                recorded_at=recorded_at,
            )
            events[unknown.event_id] = unknown

        scanned.append(
            CommitEvents(
                sha=rec.sha,
                author_email=rec.author_email,
                author_date=rec.author_date,
                events=list(events.values()),
            )
        )
        summary.events_stored += len(events)

    summary.commits_kept = len(scanned)
    replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name=display_name,
        local_path=resolved,
        scanned=scanned,
        scanned_at=recorded_at,
        purge_uids=purge_uids,
    )
    save_config(home, cfg)  # LAST — see the commit-ordering note above
    return summary


def _migrate_alias_uids(cfg: Config, scanned_entry, old_uid: str) -> tuple[str, ...]:
    """uid-algorithm migration for a whole alias group (gate C-03): when a
    rescanned entry's uid changes, every OTHER config entry still holding
    the old uid is re-derived in the same operation, so clones that aliased
    under the old algorithm keep aliasing (and most-restrictive policy
    resolution keeps seeing them together). If a sibling cannot be
    re-derived, the scan halts BEFORE anything is persisted."""
    stale = [
        e
        for e in cfg.repositories
        if e is not scanned_entry and e.repository_uid == old_uid
    ]
    for sibling in stale:
        sibling_path = Path(sibling.path)
        try:
            gitio.assert_repository(sibling_path)
            sibling.repository_uid = gitio.repository_uid(sibling_path, cfg.salt)
        except AiProfileError as exc:
            raise ConfigError(
                "uid-algorithm migration halted fail-closed (gate C-03): the"
                f" config entry for {sibling.path!r} shares the rescanned"
                " repository's previous identity but cannot be re-derived"
                f" ({exc}); fix or remove that entry, then rescan - no"
                " configuration or cache was changed"
            ) from exc
    return (old_uid,)


def _event_from_spec(
    spec: ParticipationSpec,
    rec: gitio.CommitRecord,
    repository_uid: str,
    recorded_at: str | None,
) -> AceEvent:
    return build_event(
        actor_type=spec.actor_type,
        provider=spec.provider,
        provider_raw=spec.provider_raw,
        model=spec.model,
        model_raw=spec.model_raw,
        tool=spec.tool,
        tool_raw=spec.tool_raw,
        roles=spec.roles,
        contribution_mode=spec.contribution_mode,
        human_reviewed=spec.human_reviewed,
        timestamp=rec.author_date,
        repository_uid=repository_uid,
        commit_sha=rec.sha,
        sources=[spec.source],
        recorded_at=recorded_at,
    )

"""Repository scanner: gitio → adapters → schema → storage (one repo).

Owns two schema invariants: the identity filter (ADR-015: author email must
match a configured identity) and unknown handling (schema.md section 11: a
kept commit with zero participations gets exactly one unknown event).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import gitio
from .adapters.trailers import ParseWarning, ParticipationSpec, parse_commit_trailers
from .config import Config, effective_level, save_config, upsert_repository
from .errors import ConfigError
from .schema.event import AceEvent, ProvenanceSource, build_event, merge_events
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
    warnings: list[tuple[str, ParseWarning]] = field(default_factory=list)  # (sha, warning)


def scan_repository(
    home: Path,
    cfg: Config,
    conn,
    repo_path: str,
    *,
    make_full: bool = False,
    recorded_at: str | None = None,
) -> ScanSummary:
    """Register (config) and scan (storage) one local repository."""
    path = Path(repo_path)
    gitio.assert_repository(path)
    if not cfg.identities:
        raise ConfigError(
            "no identities configured — add your git author email(s) to"
            " config.json (identities)"
        )

    uid = gitio.repository_uid(path, cfg.salt)
    resolved = str(path.resolve())
    upsert_repository(cfg, path=resolved, repository_uid=uid, make_full=make_full)
    save_config(home, cfg)

    display_name = path.resolve().name
    summary = ScanSummary(repository_uid=uid, display_name=display_name)

    if effective_level(cfg, uid) is PublicationLevel.EXCLUDED:
        summary.excluded = True
        return summary  # scan-time skip (schema.md section 9)

    records = gitio.enumerate_commits(path)
    summary.commits_seen = len(records)
    identities = {i.strip().lower() for i in cfg.identities}

    scanned: list[CommitEvents] = []
    for rec in records:
        if rec.author_email.strip().lower() not in identities:
            summary.commits_skipped_identity += 1
            continue

        specs, warns = parse_commit_trailers(rec.trailer_lines)
        summary.warnings.extend((rec.sha, w) for w in warns)

        events: dict[str, AceEvent] = {}
        for spec in specs:
            ev = _event_from_spec(spec, rec, uid, recorded_at)
            if ev.event_id in events:
                events[ev.event_id] = merge_events(events[ev.event_id], ev)
            else:
                events[ev.event_id] = ev

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
    )
    return summary


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

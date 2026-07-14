"""ACE v0.1 event model: validation, deterministic identity, merge rules.

Normative spec: docs/schema.md (sections 1, 8). Where this code and that
document disagree, the document wins and this code is a bug.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime

from .. import ACE_SCHEMA_VERSION
from ..errors import SchemaValidationError
from .vocab import (
    EVIDENCE_PRECEDENCE,
    ActivityType,
    ActorType,
    ContributionMode,
    EvidenceLevel,
    Role,
    SourceType,
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_IDENTITY_PREFIX = "ace-identity-v1"


@dataclass(frozen=True)
class ProvenanceSource:
    """One piece of evidence behind an event (schema.md section 6.2)."""

    source_type: SourceType
    evidence_level: EvidenceLevel
    source_reference: str | None = None

    def key(self) -> tuple[str, str | None]:
        return (self.source_type.value, self.source_reference)


@dataclass(frozen=True)
class AceEvent:
    """A validated ACE v0.1 event. Construct via :func:`build_event` only —
    the raw constructor performs no validation."""

    event_id: str
    actor_type: ActorType
    provider: str | None
    provider_raw: str | None
    model: str | None
    model_raw: str | None
    tool: str | None
    tool_raw: str | None
    activity_type: ActivityType
    roles: tuple[Role, ...]
    contribution_mode: ContributionMode | None
    human_reviewed: bool | None
    timestamp: str
    repository_uid: str
    commit_sha: str
    evidence_level: EvidenceLevel
    sources: tuple[ProvenanceSource, ...]
    recorded_at: str | None = None
    schema_version: str = ACE_SCHEMA_VERSION


def _identity_key(value: str | None, raw: str | None) -> str:
    """Canonical-if-known, else lowercase raw, else empty (schema.md 8.1)."""
    if value:
        return value
    if raw:
        return raw.lower()
    return ""


def compute_event_id(
    repository_uid: str,
    commit_sha: str,
    actor_type: ActorType,
    provider: str | None,
    provider_raw: str | None,
    tool: str | None,
    tool_raw: str | None,
    activity_type: ActivityType,
) -> str:
    """Deterministic identity (schema.md section 8.1). Model and roles are
    deliberately excluded (section 8.2)."""
    identity = "\n".join(
        [
            _IDENTITY_PREFIX,
            repository_uid,
            commit_sha,
            actor_type.value,
            _identity_key(provider, provider_raw),
            _identity_key(tool, tool_raw),
            activity_type.value,
        ]
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return "ace_" + digest[:24]


def build_event(
    *,
    actor_type: ActorType | str,
    repository_uid: str,
    commit_sha: str,
    timestamp: str,
    sources: list[ProvenanceSource] | tuple[ProvenanceSource, ...],
    provider: str | None = None,
    provider_raw: str | None = None,
    model: str | None = None,
    model_raw: str | None = None,
    tool: str | None = None,
    tool_raw: str | None = None,
    activity_type: ActivityType | str = ActivityType.COMMIT,
    roles: list[Role | str] | tuple[Role | str, ...] = (),
    contribution_mode: ContributionMode | str | None = None,
    human_reviewed: bool | None = None,
    recorded_at: str | None = None,
) -> AceEvent:
    """Validate inputs against docs/schema.md section 1 and return an event.

    Raises SchemaValidationError with a field-specific message; never
    coerces an unknown vocabulary value.
    """
    actor = _coerce(ActorType, actor_type, "actor.type")
    activity = _coerce(ActivityType, activity_type, "activity.type")
    mode = None if contribution_mode is None else _coerce(
        ContributionMode, contribution_mode, "activity.contribution_mode"
    )
    role_set = {_coerce(Role, r, "activity.roles") for r in roles}
    sorted_roles = tuple(sorted(role_set, key=lambda r: r.value))

    if not repository_uid:
        raise SchemaValidationError("source.repository_uid is required")
    if not _SHA40.match(commit_sha or ""):
        raise SchemaValidationError(
            "source.commit_sha must be 40 lowercase hex characters"
        )
    _require_iso(timestamp, "activity.timestamp")
    if recorded_at is not None:
        _require_iso(recorded_at, "recorded_at")

    if not sources:
        raise SchemaValidationError("provenance.sources requires at least one entry")
    src_tuple = tuple(sources)
    evidence = max(
        (s.evidence_level for s in src_tuple),
        key=lambda lv: EVIDENCE_PRECEDENCE[lv],
    )

    identity_fields = (provider, provider_raw, model, model_raw, tool, tool_raw)
    if actor is ActorType.AI:
        if not (provider or provider_raw or tool or tool_raw):
            raise SchemaValidationError(
                "actor.type=ai requires provider, provider_raw, tool, or tool_raw"
            )
    elif actor in (ActorType.HUMAN, ActorType.UNKNOWN):
        if any(f is not None for f in identity_fields):
            raise SchemaValidationError(
                f"actor.type={actor.value} requires provider/model/tool (and raw"
                " forms) to be null"
            )
        if actor is ActorType.UNKNOWN and evidence is not EvidenceLevel.UNKNOWN:
            raise SchemaValidationError(
                "actor.type=unknown requires evidence_level=unknown"
            )

    event_id = compute_event_id(
        repository_uid, commit_sha, actor, provider, provider_raw, tool, tool_raw, activity
    )
    return AceEvent(
        event_id=event_id,
        actor_type=actor,
        provider=provider,
        provider_raw=provider_raw,
        model=model,
        model_raw=model_raw,
        tool=tool,
        tool_raw=tool_raw,
        activity_type=activity,
        roles=sorted_roles,
        contribution_mode=mode,
        human_reviewed=human_reviewed,
        timestamp=timestamp,
        repository_uid=repository_uid,
        commit_sha=commit_sha,
        evidence_level=evidence,
        sources=src_tuple,
        recorded_at=recorded_at,
    )


def merge_events(existing: AceEvent, new: AceEvent) -> AceEvent:
    """Merge two productions of the same identity (schema.md section 8.3).

    Sources set-union; evidence max; roles union; scalars from the
    higher-precedence side, first-write-wins on ties.
    """
    if existing.event_id != new.event_id:
        raise SchemaValidationError(
            "merge_events requires identical identity"
            f" ({existing.event_id} != {new.event_id})"
        )
    seen = {s.key() for s in existing.sources}
    merged_sources = existing.sources + tuple(
        s for s in new.sources if s.key() not in seen
    )
    evidence = max(
        (s.evidence_level for s in merged_sources),
        key=lambda lv: EVIDENCE_PRECEDENCE[lv],
    )
    roles = tuple(sorted(set(existing.roles) | set(new.roles), key=lambda r: r.value))

    new_wins = (
        EVIDENCE_PRECEDENCE[new.evidence_level]
        > EVIDENCE_PRECEDENCE[existing.evidence_level]
    )

    def pick(a, b):
        # a = existing value, b = new value
        if new_wins:
            return b if b is not None else a
        return a if a is not None else b

    return AceEvent(
        event_id=existing.event_id,
        actor_type=existing.actor_type,
        provider=existing.provider or new.provider,
        provider_raw=pick(existing.provider_raw, new.provider_raw),
        model=pick(existing.model, new.model),
        model_raw=pick(existing.model_raw, new.model_raw),
        tool=existing.tool or new.tool,
        tool_raw=pick(existing.tool_raw, new.tool_raw),
        activity_type=existing.activity_type,
        roles=roles,
        contribution_mode=pick(existing.contribution_mode, new.contribution_mode),
        human_reviewed=pick(existing.human_reviewed, new.human_reviewed),
        timestamp=existing.timestamp,
        repository_uid=existing.repository_uid,
        commit_sha=existing.commit_sha,
        evidence_level=evidence,
        sources=merged_sources,
        recorded_at=existing.recorded_at,
        schema_version=existing.schema_version,
    )


def to_dict(event: AceEvent) -> dict:
    """Nested canonical dict per schema.md section 1 (tests/debug + future
    raw-event export; no v0.1 CLI emits it)."""
    return {
        "schema_version": event.schema_version,
        "event_id": event.event_id,
        "actor": {
            "type": event.actor_type.value,
            "provider": event.provider,
            "provider_raw": event.provider_raw,
            "model": event.model,
            "model_raw": event.model_raw,
            "tool": event.tool,
            "tool_raw": event.tool_raw,
        },
        "activity": {
            "type": event.activity_type.value,
            "roles": [r.value for r in event.roles],
            "contribution_mode": (
                event.contribution_mode.value if event.contribution_mode else None
            ),
            "human_reviewed": event.human_reviewed,
            "timestamp": event.timestamp,
        },
        "source": {
            "repository_uid": event.repository_uid,
            "commit_sha": event.commit_sha,
        },
        "provenance": {
            "evidence_level": event.evidence_level.value,
            "sources": [
                {
                    "source_type": s.source_type.value,
                    "evidence_level": s.evidence_level.value,
                    "source_reference": s.source_reference,
                }
                for s in event.sources
            ],
        },
        "recorded_at": event.recorded_at,
    }


def canonical_json(event: AceEvent) -> str:
    """Deterministic serialization: equal events serialize byte-identically."""
    return json.dumps(
        to_dict(event), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def _coerce(enum_cls, value, field: str):
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except ValueError:
        allowed = ", ".join(m.value for m in enum_cls)
        raise SchemaValidationError(
            f"{field}: {value!r} is not one of [{allowed}]"
        ) from None


def _require_iso(value: str, field: str) -> None:
    try:
        datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise SchemaValidationError(
            f"{field}: {value!r} is not an ISO 8601 timestamp"
        ) from None

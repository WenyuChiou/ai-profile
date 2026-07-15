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
    ALLOWED_SOURCE_REFERENCES,
    CANONICAL_PROVIDERS,
    CANONICAL_TOOLS,
    EVIDENCE_PRECEDENCE,
    SOURCE_TYPE_PRIORITY,
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
    #: Derivation marker (gate-4 High): True iff this event is the product
    #: of a multi-input merge_event_group reduction. Envelope metadata like
    #: recorded_at — excluded from the canonical payload and from identity.
    #: The source-count heuristic it replaces was bypassable: leaves
    #: sharing one provenance key merged into a single-source result, and
    #: it wrongly rejected schema-valid multi-source leaf productions.
    #: Like every raw-constructor field it is honored, not re-derived:
    #: rebuilding a merged result with merged=False (dataclasses.replace
    #: or a raw AceEvent(...) call) forges derivation and is
    #: out-of-contract — build_event and merge_event_group are the only
    #: sanctioned constructors.
    merged: bool = False


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
    # Per-source enum coercion (gate H-05: raw strings must yield the
    # schema's own error, never AttributeError/KeyError downstream), then
    # dedup by (type, reference) keeping the HIGHEST evidence (gate H-03:
    # a stable sort alone left duplicate keys caller-ordered, giving one
    # evidence multiset two canonical serializations), then canonical order
    # (G2-06: serialization must not depend on ingestion order).
    coerced: list[ProvenanceSource] = []
    for raw_src in sources:
        st = _coerce(SourceType, raw_src.source_type, "provenance.sources[].source_type")
        lv = _coerce(
            EvidenceLevel, raw_src.evidence_level, "provenance.sources[].evidence_level"
        )
        coerced.append(ProvenanceSource(st, lv, raw_src.source_reference))
    by_key: dict[tuple[str, str | None], ProvenanceSource] = {}
    for src in coerced:
        held = by_key.get(src.key())
        if held is None or (
            EVIDENCE_PRECEDENCE[src.evidence_level]
            > EVIDENCE_PRECEDENCE[held.evidence_level]
        ):
            by_key[src.key()] = src
    src_tuple = tuple(sorted(by_key.values(), key=_source_sort_key))
    for src in src_tuple:
        allowed = ALLOWED_SOURCE_REFERENCES.get(src.source_type)
        if allowed is None:
            # A SourceType added without a locator set is a schema bug, not
            # a KeyError (gate round-2 P3): fail with the schema's own error.
            raise SchemaValidationError(
                f"source type {src.source_type.value!r} has no allowed-locator"
                " set defined (schema.md 6.2) — define it before shipping"
            )
        if src.source_reference not in allowed:
            names = ", ".join(sorted(str(a) for a in allowed))
            raise SchemaValidationError(
                "provenance.sources[].source_reference"
                f" {src.source_reference!r} is not an allowed locator for"
                f" {src.source_type.value} (allowed: [{names}]) — locators are"
                " enum-constrained (schema.md 6.2, G2-07)"
            )
    evidence = max(
        (s.evidence_level for s in src_tuple),
        key=lambda lv: EVIDENCE_PRECEDENCE[lv],
    )

    if human_reviewed is not None and not isinstance(human_reviewed, bool):
        raise SchemaValidationError(
            f"activity.human_reviewed must be true, false, or null — got"
            f" {human_reviewed!r} (gate H-05)"
        )
    if provider is not None and provider not in CANONICAL_PROVIDERS:
        raise SchemaValidationError(
            f"actor.provider {provider!r} is not a canonical provider slug"
            " (schema.md 10, gate H-02) — unrecognized values belong in"
            " provider_raw with provider=null"
        )
    if tool is not None and tool not in CANONICAL_TOOLS:
        raise SchemaValidationError(
            f"actor.tool {tool!r} is not a canonical tool slug (schema.md 10,"
            " gate H-02) — unrecognized values belong in tool_raw with"
            " tool=null"
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
        if actor is ActorType.HUMAN and (
            evidence is not EvidenceLevel.DECLARED
            or any(s.source_type is SourceType.NONE for s in src_tuple)
        ):
            raise SchemaValidationError(
                "actor.type=human requires declared evidence from an explicit"
                " declaration source — a human record never arises from"
                " absence of evidence (schema.md 2, gate H-05)"
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


def _source_sort_key(s: ProvenanceSource) -> tuple[str, str]:
    return (s.source_type.value, s.source_reference or "")


def _event_rank(event: AceEvent) -> tuple[int, int, str]:
    """Canonical strength of an event for scalar conflict resolution
    (ADR-008, G2-06): evidence precedence (higher wins), best source-type
    priority (higher wins), lexicographically smallest locator (smaller
    wins). Ingestion-order-free by construction."""
    best_priority = max(SOURCE_TYPE_PRIORITY[s.source_type] for s in event.sources)
    min_locator = min((s.source_reference or "") for s in event.sources)
    return (EVIDENCE_PRECEDENCE[event.evidence_level], best_priority, min_locator)


def merge_event_group(events: list[AceEvent] | tuple[AceEvent, ...]) -> AceEvent:
    """Canonical N-ary reduction of ALL productions of one identity
    (schema.md section 8.3, ADR-008; gate round-2 P1 fix).

    A pure function of the multiset of LEAF events: every scalar resolves
    against the rank of the leaf production that carries it — never against
    a merged pool, where a weak-origin value could borrow a stronger
    sibling's rank and make the outcome fold-order dependent. All
    permutations of the input reduce to a byte-identical canonical event
    (exhaustively tested).
    """
    if not events:
        raise SchemaValidationError("merge_event_group requires at least one event")
    first = events[0]
    for e in events[1:]:
        if e.event_id != first.event_id:
            raise SchemaValidationError(
                "merge_event_group requires identical identity"
                f" ({first.event_id} != {e.event_id})"
            )
    if len(events) == 1:
        # Deliberately exempt from the leaf-only check below: with a single
        # input there is no second candidate to re-rank against, so no
        # order-dependence can arise regardless of leaf/merged status — the
        # input is returned unchanged (independently verified in review).
        return first
    # LEAF-ONLY boundary, enforced via the explicit derivation marker
    # (gate-4 High replaced the bypassable source-count heuristic): a
    # previously merged event smuggled back in would have its values
    # re-ranked against POOLED provenance, so nested composition could
    # differ from the flat N-ary reduction over the same leaves — the
    # exact order-dependence this API exists to prevent. Schema-valid
    # multi-source LEAF productions (future notes/git-ai/manual imports)
    # remain accepted. Callers must pass ALL leaves in one call.
    for e in events:
        if e.merged:
            raise SchemaValidationError(
                "merge_event_group accepts leaf productions only — this"
                " input is itself a merged result, and nested/incremental"
                " composition is not ingestion-order-free; pass every leaf"
                " of the identity in a single call"
            )

    # Union by (source_type, source_reference); on key collision the HIGHER
    # evidence level survives — first-seen-wins would make the union (and
    # the event's max evidence) ingestion-order dependent.
    by_key: dict[tuple[str, str | None], ProvenanceSource] = {}
    for e in events:
        for s in e.sources:
            held = by_key.get(s.key())
            if held is None or (
                EVIDENCE_PRECEDENCE[s.evidence_level]
                > EVIDENCE_PRECEDENCE[held.evidence_level]
            ):
                by_key[s.key()] = s
    merged_sources = tuple(sorted(by_key.values(), key=_source_sort_key))
    evidence = max(
        (s.evidence_level for s in merged_sources),
        key=lambda lv: EVIDENCE_PRECEDENCE[lv],
    )
    roles = tuple(
        sorted({r for e in events for r in e.roles}, key=lambda r: r.value)
    )

    def resolve(field: str):
        """Strongest-leaf value: max (evidence precedence, source-type
        priority), then smallest locator, then smallest value — computed
        per ORIGINAL leaf, so the result is order-free by construction."""
        candidates = [
            (e, getattr(e, field)) for e in events if getattr(e, field) is not None
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda pair: (
                -_event_rank(pair[0])[0],
                -_event_rank(pair[0])[1],
                _event_rank(pair[0])[2],
                str(pair[1]),
            )
        )
        return candidates[0][1]

    def resolve_pair(canonical_field: str, raw_field: str):
        """(canonical, raw) pairs resolve atomically from ONE winning leaf
        (gate M-10): independent per-scalar resolution could pair a
        canonical value from one source with a raw value from another — a
        provenance statement no source ever made."""
        candidates = [
            e
            for e in events
            if getattr(e, canonical_field) is not None
            or getattr(e, raw_field) is not None
        ]
        if not candidates:
            return None, None
        candidates.sort(
            key=lambda e: (
                -_event_rank(e)[0],
                -_event_rank(e)[1],
                _event_rank(e)[2],
                str((getattr(e, canonical_field), getattr(e, raw_field))),
            )
        )
        winner = candidates[0]
        return getattr(winner, canonical_field), getattr(winner, raw_field)

    provider, provider_raw = resolve_pair("provider", "provider_raw")
    model, model_raw = resolve_pair("model", "model_raw")
    tool, tool_raw = resolve_pair("tool", "tool_raw")

    recorded = sorted(e.recorded_at for e in events if e.recorded_at is not None)
    return AceEvent(
        event_id=first.event_id,
        actor_type=first.actor_type,
        provider=provider,
        provider_raw=provider_raw,
        model=model,
        model_raw=model_raw,
        tool=tool,
        tool_raw=tool_raw,
        activity_type=first.activity_type,
        roles=roles,
        contribution_mode=resolve("contribution_mode"),
        human_reviewed=resolve("human_reviewed"),
        timestamp=first.timestamp,
        repository_uid=first.repository_uid,
        commit_sha=first.commit_sha,
        evidence_level=evidence,
        sources=merged_sources,
        recorded_at=recorded[0] if recorded else None,
        schema_version=first.schema_version,
        merged=True,
    )


# NOTE (gate M-12): there is deliberately NO exported pairwise merge —
# an incremental pairwise fold of three or more productions re-ranks values
# against the merged pool and is not ingestion-order-free. All callers pass
# every leaf production of one identity to merge_event_group in one call.


def to_dict(event: AceEvent) -> dict:
    """Canonical SEMANTIC PAYLOAD per schema.md section 1 (tests/debug +
    future raw-event export; no v0.1 CLI emits it).

    Deliberately excludes `recorded_at`: it is audit-envelope metadata that
    varies per scan, and canonical serialization must stay byte-identical
    for equal events across rescans (G2-14)."""
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
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise SchemaValidationError(
            f"{field}: {value!r} is not an ISO 8601 timestamp"
        ) from None
    if parsed.tzinfo is None:
        # Date-only and naive forms parse but carry no offset; author-local
        # day semantics depend on the offset being present (gate H-05).
        raise SchemaValidationError(
            f"{field}: {value!r} must be an offset-aware ISO 8601 timestamp"
        )

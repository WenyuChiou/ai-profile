"""Unit tests for the ACE v0.1 event model (docs/schema.md sections 1, 8).

Covers: valid construction + role normalization, validation rejections,
actor/evidence invariants, deterministic event_id derivation, canonical
JSON serialization, and merge_events semantics.
"""

from __future__ import annotations

import json
import re

import pytest

from aiprofile.errors import SchemaValidationError
from aiprofile.schema.event import (
    ProvenanceSource,
    build_event,
    canonical_json,
    compute_event_id,
    merge_events,
    to_dict,
)
from aiprofile.schema.vocab import (
    ActivityType,
    ActorType,
    ContributionMode,
    EvidenceLevel,
    Role,
    SourceType,
)

VALID_REPO_UID = "remote:github.com/owner/repo"
VALID_SHA = "a" * 40
VALID_TIMESTAMP = "2026-07-14T08:22:12-04:00"


def _base_kwargs(**overrides):
    """A minimal valid actor=ai event's kwargs; override to probe one field."""
    kwargs = dict(
        actor_type=ActorType.AI,
        repository_uid=VALID_REPO_UID,
        commit_sha=VALID_SHA,
        timestamp=VALID_TIMESTAMP,
        sources=(ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED),),
        provider="anthropic",
        tool="claude-code",
    )
    kwargs.update(overrides)
    return kwargs


def _make_ai_event(**overrides):
    return build_event(**_base_kwargs(**overrides))


# --- 1. valid event accepted; roles sorted+deduped; schema_version ---------


def test_valid_ai_event_accepted():
    event = _make_ai_event()
    assert event.actor_type is ActorType.AI
    assert event.schema_version == "0.1.0"


def test_roles_stored_sorted_and_deduplicated():
    event = _make_ai_event(roles=["testing", "implementation", "testing"])
    assert event.roles == (Role.IMPLEMENTATION, Role.TESTING)


def test_schema_version_constant():
    assert _make_ai_event().schema_version == "0.1.0"


# --- 2. SchemaValidationError for malformed/unknown fields ------------------


def test_unknown_actor_type_rejected():
    with pytest.raises(SchemaValidationError):
        build_event(**_base_kwargs(actor_type="alien"))


def test_unknown_activity_type_rejected():
    with pytest.raises(SchemaValidationError):
        build_event(**_base_kwargs(activity_type="pull_request"))


def test_unknown_contribution_mode_rejected():
    with pytest.raises(SchemaValidationError):
        build_event(**_base_kwargs(contribution_mode="banana"))


def test_unknown_role_rejected():
    with pytest.raises(SchemaValidationError):
        build_event(**_base_kwargs(roles=["banana"]))


def test_empty_repository_uid_rejected():
    with pytest.raises(SchemaValidationError):
        build_event(**_base_kwargs(repository_uid=""))


@pytest.mark.parametrize(
    "bad_sha",
    [
        "a" * 39,  # too short
        "A" * 40,  # uppercase
        "g" * 40,  # non-hex character
    ],
    ids=["short", "uppercase", "non-hex"],
)
def test_bad_commit_sha_rejected(bad_sha):
    with pytest.raises(SchemaValidationError):
        build_event(**_base_kwargs(commit_sha=bad_sha))


def test_non_iso_timestamp_rejected():
    with pytest.raises(SchemaValidationError):
        build_event(**_base_kwargs(timestamp="not-a-timestamp"))


def test_empty_sources_list_rejected():
    with pytest.raises(SchemaValidationError):
        build_event(**_base_kwargs(sources=()))


# --- 3. actor-type / identity-field / evidence invariants ------------------


def test_ai_actor_without_any_identity_field_rejected():
    with pytest.raises(SchemaValidationError):
        build_event(**_base_kwargs(provider=None, tool=None))


@pytest.mark.parametrize("actor", [ActorType.HUMAN, ActorType.UNKNOWN])
@pytest.mark.parametrize(
    "field,value",
    [
        ("provider", "anthropic"),
        ("provider_raw", "Anthropic"),
        ("model", "claude-sonnet"),
        ("model_raw", "Claude-Sonnet"),
        ("tool", "claude-code"),
        ("tool_raw", "Claude-Code"),
    ],
)
def test_human_or_unknown_actor_with_identity_field_rejected(actor, field, value):
    kwargs = _base_kwargs(actor_type=actor, provider=None, tool=None)
    if actor is ActorType.UNKNOWN:
        # otherwise this would independently fail the evidence check below;
        # keep evidence valid so the identity-field check is what's probed.
        kwargs["sources"] = (ProvenanceSource(SourceType.NONE, EvidenceLevel.UNKNOWN),)
    kwargs[field] = value
    with pytest.raises(SchemaValidationError):
        build_event(**kwargs)


def test_unknown_actor_with_declared_source_rejected():
    with pytest.raises(SchemaValidationError):
        build_event(
            **_base_kwargs(
                actor_type=ActorType.UNKNOWN,
                provider=None,
                tool=None,
                sources=(ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED),),
            )
        )


def test_unknown_actor_with_unknown_evidence_accepted():
    event = build_event(
        **_base_kwargs(
            actor_type=ActorType.UNKNOWN,
            provider=None,
            tool=None,
            sources=(ProvenanceSource(SourceType.NONE, EvidenceLevel.UNKNOWN),),
        )
    )
    assert event.actor_type is ActorType.UNKNOWN
    assert event.evidence_level is EvidenceLevel.UNKNOWN


def test_human_actor_without_identity_fields_accepted():
    event = build_event(**_base_kwargs(actor_type=ActorType.HUMAN, provider=None, tool=None))
    assert event.actor_type is ActorType.HUMAN


# --- 4. event_id determinism ------------------------------------------------


def test_event_id_shape():
    event = _make_ai_event()
    assert re.match(r"^ace_[0-9a-f]{24}$", event.event_id)


def test_event_id_equal_for_equal_identity():
    a = _make_ai_event()
    b = _make_ai_event()
    assert a.event_id == b.event_id


def test_event_id_matches_compute_event_id_directly():
    event = _make_ai_event()
    expected = compute_event_id(
        event.repository_uid,
        event.commit_sha,
        event.actor_type,
        event.provider,
        event.provider_raw,
        event.tool,
        event.tool_raw,
        event.activity_type,
    )
    assert event.event_id == expected


def test_event_id_unaffected_by_model():
    a = _make_ai_event(model="claude-sonnet", model_raw="Claude-Sonnet")
    b = _make_ai_event(model=None, model_raw=None)
    assert a.event_id == b.event_id


def test_event_id_unaffected_by_roles():
    a = _make_ai_event(roles=[Role.IMPLEMENTATION])
    b = _make_ai_event(roles=[Role.REVIEW, Role.TESTING])
    assert a.event_id == b.event_id


def test_event_id_same_for_canonical_provider_vs_raw_only():
    # canonical "anthropic" vs raw-only "Anthropic" (canonical None): the
    # identity key lowercases the raw value, so these collide (schema.md 8.1).
    a = _make_ai_event(provider="anthropic", provider_raw=None)
    b = _make_ai_event(provider=None, provider_raw="Anthropic")
    assert a.event_id == b.event_id


def test_event_id_differs_when_actor_type_changes():
    a = _make_ai_event()
    b = build_event(**_base_kwargs(actor_type=ActorType.HUMAN, provider=None, tool=None))
    assert a.event_id != b.event_id


def test_event_id_differs_when_provider_changes():
    a = _make_ai_event(provider="anthropic", provider_raw=None)
    b = _make_ai_event(provider="openai", provider_raw=None)
    assert a.event_id != b.event_id


def test_event_id_differs_when_tool_changes():
    a = _make_ai_event(tool="claude-code")
    b = _make_ai_event(tool="codex-cli")
    assert a.event_id != b.event_id


def test_event_id_differs_when_repository_uid_changes():
    a = _make_ai_event(repository_uid=VALID_REPO_UID)
    b = _make_ai_event(repository_uid="remote:github.com/owner/other")
    assert a.event_id != b.event_id


def test_event_id_differs_when_commit_sha_changes():
    a = _make_ai_event(commit_sha="a" * 40)
    b = _make_ai_event(commit_sha="b" * 40)
    assert a.event_id != b.event_id


# --- 5. canonical_json ------------------------------------------------------


def test_canonical_json_byte_identical_for_equal_events():
    a = _make_ai_event()
    b = _make_ai_event()
    assert canonical_json(a) == canonical_json(b)


def test_canonical_json_matches_sorted_dump_of_to_dict():
    event = _make_ai_event()
    assert canonical_json(event) == json.dumps(
        to_dict(event), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def test_canonical_json_differs_for_different_events():
    a = _make_ai_event(provider="anthropic", provider_raw=None)
    b = _make_ai_event(provider="openai", provider_raw=None)
    assert canonical_json(a) != canonical_json(b)


# --- 6. merge_events ---------------------------------------------------------


def test_merge_events_mismatched_identity_raises():
    a = _make_ai_event()
    b = _make_ai_event(repository_uid="remote:github.com/owner/other")
    with pytest.raises(SchemaValidationError):
        merge_events(a, b)


def test_merge_sources_set_union_deduped_by_type_and_reference():
    shared = ProvenanceSource(
        SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, source_reference="AI-Provider"
    )
    existing = _make_ai_event(sources=(shared,))
    new = _make_ai_event(
        sources=(
            shared,  # duplicate of an existing (source_type, source_reference)
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR,
                EvidenceLevel.DECLARED,
                source_reference="Co-authored-by",
            ),
        )
    )
    merged = merge_events(existing, new)
    assert len(merged.sources) == 2
    assert {s.key() for s in merged.sources} == {
        (SourceType.GIT_TRAILER.value, "AI-Provider"),
        (SourceType.GIT_TRAILER_COAUTHOR.value, "Co-authored-by"),
    }


def test_merge_evidence_level_is_max_over_sources():
    existing = _make_ai_event(
        sources=(ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED),)
    )
    new = _make_ai_event(
        sources=(ProvenanceSource(SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.VERIFIED),)
    )
    merged = merge_events(existing, new)
    assert merged.evidence_level is EvidenceLevel.VERIFIED


def test_merge_roles_are_sorted_union():
    existing = _make_ai_event(roles=[Role.IMPLEMENTATION])
    new = _make_ai_event(roles=[Role.TESTING, Role.DOCUMENTATION])
    merged = merge_events(existing, new)
    assert merged.roles == (Role.DOCUMENTATION, Role.IMPLEMENTATION, Role.TESTING)


def test_merge_scalar_tie_keeps_existing_and_fills_null_from_new():
    existing = _make_ai_event(
        model="claude-sonnet-existing",
        model_raw=None,
        sources=(ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED),),
    )
    new = _make_ai_event(
        model="claude-sonnet-new",
        model_raw="Claude-Sonnet-New",
        sources=(ProvenanceSource(SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.DECLARED),),
    )
    merged = merge_events(existing, new)
    # both DECLARED (a tie): existing non-null scalar is kept...
    assert merged.model == "claude-sonnet-existing"
    # ...and existing's null scalar is filled from new.
    assert merged.model_raw == "Claude-Sonnet-New"


def test_merge_new_side_with_higher_evidence_wins_non_null_scalars():
    existing = _make_ai_event(
        model="claude-sonnet-existing",
        model_raw="Claude-Sonnet-Existing",
        contribution_mode=ContributionMode.AI_ASSISTED,
        human_reviewed=False,
        sources=(ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED),),
    )
    new = _make_ai_event(
        model="claude-sonnet-new",
        model_raw="Claude-Sonnet-New",
        contribution_mode=ContributionMode.AI_REVIEWED,
        human_reviewed=True,
        sources=(ProvenanceSource(SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.VERIFIED),),
    )
    merged = merge_events(existing, new)
    assert merged.model == "claude-sonnet-new"
    assert merged.model_raw == "Claude-Sonnet-New"
    assert merged.contribution_mode is ContributionMode.AI_REVIEWED
    assert merged.human_reviewed is True


def test_merge_preserves_activity_type():
    existing = _make_ai_event()
    new = _make_ai_event()
    merged = merge_events(existing, new)
    assert merged.activity_type is ActivityType.COMMIT

"""Unit tests for the ACE v0.1 event model (docs/schema.md sections 1, 8).

Covers: valid construction + role normalization, validation rejections,
actor/evidence invariants, deterministic event_id derivation, canonical
JSON serialization, and merge_event_group semantics.
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
    merge_event_group,
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
        sources=(
                    ProvenanceSource(
                        SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"
                    ),
                ),
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
                sources=(
                    ProvenanceSource(
                        SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"
                    ),
                ),
            )
        )


def test_unknown_actor_with_unknown_evidence_accepted():
    event = build_event(
        **_base_kwargs(
            actor_type=ActorType.UNKNOWN,
            provider=None,
            tool=None,
            sources=(
                ProvenanceSource(
                    SourceType.NONE, EvidenceLevel.UNKNOWN
                ),
            ),
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


# --- 6. merge_event_group ---------------------------------------------------------


def test_merge_events_mismatched_identity_raises():
    a = _make_ai_event()
    b = _make_ai_event(repository_uid="remote:github.com/owner/other")
    with pytest.raises(SchemaValidationError):
        merge_event_group([a, b])


def test_merge_sources_set_union_deduped_by_type_and_reference():
    shared = ProvenanceSource(
        SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, source_reference="ai-provider"
    )
    a = _make_ai_event(sources=(shared,))
    b = _make_ai_event(sources=(shared,))  # duplicate key across leaves
    c = _make_ai_event(
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR,
                EvidenceLevel.DECLARED,
                source_reference="co-authored-by",
            ),
        )
    )
    merged = merge_event_group([a, b, c])
    assert len(merged.sources) == 2
    assert {s.key() for s in merged.sources} == {
        (SourceType.GIT_TRAILER.value, "ai-provider"),
        (SourceType.GIT_TRAILER_COAUTHOR.value, "co-authored-by"),
    }


def test_merge_evidence_level_is_max_over_sources():
    existing = _make_ai_event(
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"
            ),
        )
    )
    new = _make_ai_event(
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.VERIFIED, "co-authored-by"
            ),
        )
    )
    merged = merge_event_group([existing, new])
    assert merged.evidence_level is EvidenceLevel.VERIFIED


def test_merge_roles_are_sorted_union():
    existing = _make_ai_event(roles=[Role.IMPLEMENTATION])
    new = _make_ai_event(roles=[Role.TESTING, Role.DOCUMENTATION])
    merged = merge_event_group([existing, new])
    assert merged.roles == (Role.DOCUMENTATION, Role.IMPLEMENTATION, Role.TESTING)


def test_merge_scalar_tie_keeps_existing_and_fills_null_from_new():
    existing = _make_ai_event(
        model="claude-sonnet-existing",
        model_raw=None,
        sources=(
                    ProvenanceSource(
                        SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"
                    ),
                ),
    )
    new = _make_ai_event(
        model="claude-sonnet-new",
        model_raw="Claude-Sonnet-New",
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.DECLARED, "co-authored-by"
            ),
        ),
    )
    merged = merge_event_group([existing, new])
    # Trailer (priority 3) outranks coauthor (2): the trailer leaf wins the
    # (model, model_raw) PAIR atomically (gate M-10) — its null model_raw is
    # NOT back-filled from the weaker leaf, because that would assert a
    # canonical/raw pairing no single source ever made.
    assert merged.model == "claude-sonnet-existing"
    assert merged.model_raw is None


def test_merge_new_side_with_higher_evidence_wins_non_null_scalars():
    existing = _make_ai_event(
        model="claude-sonnet-existing",
        model_raw="Claude-Sonnet-Existing",
        contribution_mode=ContributionMode.AI_ASSISTED,
        human_reviewed=False,
        sources=(
                    ProvenanceSource(
                        SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"
                    ),
                ),
    )
    new = _make_ai_event(
        model="claude-sonnet-new",
        model_raw="Claude-Sonnet-New",
        contribution_mode=ContributionMode.AI_REVIEWED,
        human_reviewed=True,
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.VERIFIED, "co-authored-by"
            ),
        ),
    )
    merged = merge_event_group([existing, new])
    assert merged.model == "claude-sonnet-new"
    assert merged.model_raw == "Claude-Sonnet-New"
    assert merged.contribution_mode is ContributionMode.AI_REVIEWED
    assert merged.human_reviewed is True


def test_merge_preserves_activity_type():
    existing = _make_ai_event()
    new = _make_ai_event()
    merged = merge_event_group([existing, new])
    assert merged.activity_type is ActivityType.COMMIT


# ---------------------------------------------------------------------------
# Gate 2 conformance additions (G2-06, G2-07, G2-14).
# ---------------------------------------------------------------------------


def test_source_reference_locators_are_enum_constrained():
    # G2-07: free text structurally cannot enter provenance.
    for bad in ("AI-Provider", "C:/secret/path", "prompt text", None):
        with pytest.raises(SchemaValidationError):
            _make_ai_event(
                sources=(
                    ProvenanceSource(
                        SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, bad
                    ),
                )
            )
    with pytest.raises(SchemaValidationError):
        build_event(
            actor_type="unknown",
            repository_uid="u",
            commit_sha="a" * 40,
            timestamp="2026-01-01T00:00:00+00:00",
            sources=[
                ProvenanceSource(SourceType.NONE, EvidenceLevel.UNKNOWN, "none-ref")
            ],
        )


def test_canonical_json_excludes_recorded_at_envelope():
    # G2-14: recorded_at is audit envelope, not canonical payload.
    a = _make_ai_event(recorded_at="2026-07-14T10:00:00+00:00")
    b = _make_ai_event(recorded_at="2026-07-15T22:33:44+00:00")
    assert canonical_json(a) == canonical_json(b)
    assert "recorded_at" not in to_dict(a)


def test_merge_scalar_true_tie_breaks_by_lexicographic_value():
    # Same evidence, same source type, same locator -> canonical value wins.
    src = (ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"),)
    a = _make_ai_event(model="zeta-model", model_raw="Zeta-Model", sources=src)
    b = _make_ai_event(model="alpha-model", model_raw="Alpha-Model", sources=src)
    assert merge_event_group([a, b]).model == "alpha-model"
    assert merge_event_group([b, a]).model == "alpha-model"


def test_merge_is_permutation_invariant():
    # G2-06: the same evidence set in ANY order yields identical canonical
    # data — via ONE flat N-ary reduction per permutation (the leaf-only
    # boundary rejects incremental composition; see
    # test_merge_event_group_rejects_non_leaf_inputs).
    e1 = _make_ai_event(
        model="mid-model",
        contribution_mode="ai_assisted",
        sources=(
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"),
        ),
    )
    e2 = _make_ai_event(
        model=None,
        model_raw=None,
        human_reviewed=True,
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.DECLARED, "co-authored-by"
            ),
        ),
    )
    e3 = _make_ai_event(
        model="aaa-model",
        sources=(
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-tool"),
        ),
    )
    import itertools

    results = {
        canonical_json(merge_event_group(list(perm)))
        for perm in itertools.permutations([e1, e2, e3])
    }
    assert len(results) == 1


def _leaf_from_spec(spec, sha="f" * 40):
    """Build a leaf AceEvent from a ParticipationSpec the way scanner does."""
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
        timestamp="2026-01-05T10:00:00+08:00",
        repository_uid="remote:v2:github.com/x/y",
        commit_sha=sha,
        sources=[spec.source],
    )


def test_group_merge_reviewer_trailer_counterexample():
    """Gate round-2 P1 regression: two ordinary Co-authored-by lines naming
    the same AI identity with different display text, plus an AI-Tool
    trailer — swapping the co-author line order must NOT change any
    persisted field (pre-fix: provider_raw depended on fold order)."""
    from aiprofile.adapters.trailers import parse_commit_trailers
    from aiprofile.schema.event import merge_event_group

    order_a = [
        "Co-authored-by: Claude <noreply@anthropic.com>",
        "AI-Tool: claude-code",
        "Co-authored-by: Claude Assistant <noreply@anthropic.com>",
    ]
    order_b = [
        "Co-authored-by: Claude Assistant <noreply@anthropic.com>",
        "AI-Tool: claude-code",
        "Co-authored-by: Claude <noreply@anthropic.com>",
    ]
    merged = []
    for lines in (order_a, order_b):
        specs, warnings = parse_commit_trailers(lines)
        assert not warnings
        leaves = [_leaf_from_spec(s) for s in specs]
        assert len({e.event_id for e in leaves}) == 1
        merged.append(merge_event_group(leaves))
    assert canonical_json(merged[0]) == canonical_json(merged[1])
    assert merged[0].provider_raw == merged[1].provider_raw


def test_group_merge_exhaustive_permutations_of_four_leaves():
    """G2-06 closure test: ALL 24 orders of four adversarial leaves (mixed
    source types, locators, values, evidence) reduce to byte-identical
    canonical events."""
    from aiprofile.schema.event import merge_event_group

    leaves = [
        _make_ai_event(
            model="mid-model",
            contribution_mode="ai_assisted",
            sources=(
                ProvenanceSource(
                    SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"
                ),
            ),
        ),
        _make_ai_event(
            model=None,
            model_raw=None,
            human_reviewed=True,
            sources=(
                ProvenanceSource(
                    SourceType.GIT_TRAILER_COAUTHOR,
                    EvidenceLevel.DECLARED,
                    "co-authored-by",
                ),
            ),
        ),
        _make_ai_event(
            model="aaa-model",
            sources=(
                ProvenanceSource(
                    SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-tool"
                ),
            ),
        ),
        _make_ai_event(
            model="zzz-model",
            contribution_mode="ai_generated",
            human_reviewed=False,
            sources=(
                ProvenanceSource(
                    SourceType.GIT_TRAILER_COAUTHOR,
                    EvidenceLevel.VERIFIED,
                    "co-authored-by",
                ),
            ),
        ),
    ]
    import itertools

    results = {
        canonical_json(merge_event_group(list(perm)))
        for perm in itertools.permutations(leaves)
    }
    assert len(results) == 1, len(results)


# ---------------------------------------------------------------------------
# Gate-3 regressions (docs/reviews/gate-review.md): each test below was
# confirmed FAILING against the pre-fix code (H-02, H-03, H-05, M-10).
# ---------------------------------------------------------------------------


def test_h05_date_only_timestamp_rejected():
    with pytest.raises(SchemaValidationError, match="offset-aware"):
        _make_ai_event(timestamp="2026-07-14")


def test_h05_naive_datetime_rejected():
    with pytest.raises(SchemaValidationError, match="offset-aware"):
        _make_ai_event(timestamp="2026-07-14T10:00:00")


def test_h05_human_requires_declared_non_none_evidence():
    with pytest.raises(SchemaValidationError, match="human"):
        build_event(
            actor_type="human",
            repository_uid="u",
            commit_sha="a" * 40,
            timestamp="2026-01-01T00:00:00+00:00",
            sources=[ProvenanceSource(SourceType.NONE, EvidenceLevel.UNKNOWN)],
        )


def test_h05_raw_string_provenance_enums_coerced_or_schema_error():
    # Valid strings coerce (never AttributeError/KeyError)...
    ev = _make_ai_event(
        sources=(ProvenanceSource("git_trailer", "declared", "ai-provider"),)
    )
    assert ev.sources[0].source_type is SourceType.GIT_TRAILER
    assert ev.sources[0].evidence_level is EvidenceLevel.DECLARED
    # ...and invalid strings raise the schema's own error type.
    with pytest.raises(SchemaValidationError):
        _make_ai_event(
            sources=(ProvenanceSource("git_trailerz", "declared", "ai-provider"),)
        )
    with pytest.raises(SchemaValidationError):
        _make_ai_event(
            sources=(ProvenanceSource("git_trailer", "very-sure", "ai-provider"),)
        )


def test_h05_human_reviewed_must_be_bool_or_none():
    with pytest.raises(SchemaValidationError, match="human_reviewed"):
        _make_ai_event(human_reviewed="yes")


def test_h03_duplicate_source_keys_dedupe_to_highest_evidence_any_order():
    lo = ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider")
    hi = ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.VERIFIED, "ai-provider")
    a = _make_ai_event(sources=(lo, hi))
    b = _make_ai_event(sources=(hi, lo))
    assert canonical_json(a) == canonical_json(b)
    assert len(a.sources) == 1
    assert a.sources[0].evidence_level is EvidenceLevel.VERIFIED


def test_h02_non_canonical_provider_and_tool_rejected_at_schema_boundary():
    with pytest.raises(SchemaValidationError, match="canonical"):
        _make_ai_event(provider="private-org-secret")
    with pytest.raises(SchemaValidationError, match="canonical"):
        _make_ai_event(tool="secret-internal-tool")
    # Canonical slugs still pass; raw fields stay free-form (local-only).
    ok = _make_ai_event(provider="anthropic", provider_raw="Anything At All")
    assert ok.provider == "anthropic"


def test_m10_canonical_raw_pairs_resolve_from_one_leaf():
    from aiprofile.schema.event import merge_event_group

    src = (ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"),)
    a = _make_ai_event(model="alpha", model_raw="alpha", sources=src)
    b = _make_ai_event(model="beta", model_raw="Beta", sources=src)
    for order in ([a, b], [b, a]):
        merged = merge_event_group(order)
        assert (merged.model, merged.model_raw) in {("alpha", "alpha"), ("beta", "Beta")}, (
            merged.model,
            merged.model_raw,
        )


def test_merge_event_group_rejects_non_leaf_inputs():
    """Verification-review round: the exported merge API enforces its
    documented leaf-only boundary — a previously merged event (multiple
    provenance sources) is rejected, because nested composition re-ranks
    values against pooled provenance and can differ from the flat N-ary
    reduction. Confirmed failing pre-fix (nested call silently succeeded
    with divergent canonical output)."""
    from aiprofile.schema.event import merge_event_group

    a = _make_ai_event(
        model="mid-model",
        sources=(
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"),
        ),
    )
    b = _make_ai_event(
        model=None,
        model_raw=None,
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.DECLARED, "co-authored-by"
            ),
        ),
    )
    c = _make_ai_event(
        model="aaa-model",
        sources=(
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-tool"),
        ),
    )
    merged_ab = merge_event_group([a, b])
    assert len(merged_ab.sources) == 2
    with pytest.raises(SchemaValidationError, match="leaf"):
        merge_event_group([merged_ab, c])
    # The flat reduction over all leaves remains the supported path.
    flat = merge_event_group([a, b, c])
    assert flat.model == "mid-model"


def test_leaf_guard_not_bypassable_via_source_dedup():
    """Gate-4 High regression: two leaves sharing one provenance key merge
    into a result whose deduplicated source set has cardinality 1 — the
    old source-count heuristic accepted it for nested composition. The
    merged marker must reject it regardless. Confirmed failing pre-fix
    (nested selected a different model than the flat reduction)."""
    from aiprofile.schema.event import merge_event_group

    l1 = _make_ai_event(
        model=None,
        model_raw=None,
        sources=(
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"),
        ),
    )
    l2 = _make_ai_event(
        model="zeta",
        model_raw="Zeta",
        sources=(
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.IMPORTED, "ai-provider"),
        ),
    )
    merged = merge_event_group([l1, l2])
    assert len(merged.sources) == 1  # dedup collapsed the shared key
    coauthor = _make_ai_event(
        model="alpha",
        model_raw="Alpha",
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.DECLARED, "co-authored-by"
            ),
        ),
    )
    with pytest.raises(SchemaValidationError, match="merged"):
        merge_event_group([merged, coauthor])
    flat = merge_event_group([l1, l2, coauthor])
    assert flat.model == "alpha"  # declared coauthor outranks imported-only zeta


def test_valid_multi_source_leaf_productions_are_mergeable():
    """Gate-4 M-2 regression: the schema permits one-or-more sources per
    production (future notes/git-ai/manual imports); a schema-valid
    multi-source LEAF must be accepted by multi-event reductions.
    Confirmed failing pre-fix (SchemaValidationError on valid input)."""
    from aiprofile.schema.event import merge_event_group

    multi_source_leaf = _make_ai_event(
        sources=(
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider"),
            ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-tool"),
        ),
    )
    other = _make_ai_event(
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER_COAUTHOR, EvidenceLevel.DECLARED, "co-authored-by"
            ),
        ),
    )
    merged = merge_event_group([multi_source_leaf, other])
    assert len(merged.sources) == 3


def test_operational_equality_audit_excluded_derivation_included():
    """Gate-5 L-03 + gate-6 L-01 (operational equality): `recorded_at`
    is pure audit metadata — excluded from equality/hash, so rescan
    stamps never split value-identical events. `merged` however decides
    merge ADMISSIBILITY: a leaf and a reduced event are NOT
    substitutable in the API, so equality must keep them distinct or
    set/cache dedup makes merge behavior depend on insertion order
    (gate-6 reviewer probe). Confirmed failing pre-fix (leaf and
    reduced event compared equal)."""
    src = ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider")
    kwargs = dict(
        actor_type=ActorType.AI,
        repository_uid="remote:v4:github.com/o/r",
        commit_sha="a" * 40,
        timestamp="2026-07-14T12:00:00+00:00",
        sources=[src],
        provider="anthropic",
    )
    l1 = build_event(**kwargs)
    l2 = build_event(**kwargs)
    reduced = merge_event_group([l1, l2])

    # audit metadata: excluded (canonical payload agreement)
    stamped = build_event(**kwargs, recorded_at="2026-07-15T00:00:00+00:00")
    assert canonical_json(stamped) == canonical_json(l1)
    assert stamped == l1
    assert hash(stamped) == hash(l1)

    # derivation state: INCLUDED (operational distinction)
    assert reduced.merged and not l1.merged
    assert canonical_json(reduced) == canonical_json(l1)
    assert reduced != l1
    assert len({l1, reduced}) == 2

    # substitutability: dedup through a set can never flip merge
    # admissibility — both orders keep the leaf AND the reduced event
    # distinct, so behavior cannot depend on insertion order.
    for pair in ({l1, reduced}, {reduced, l1}):
        leaves = [e for e in pair if not e.merged]
        assert len(leaves) == 1
        assert merge_event_group([leaves[0], build_event(**kwargs)]).merged


def test_m01_derivation_state_is_envelope_only_never_persisted():
    """Gate-5 M-01 (pin, not a fix): the approved boundary is that
    derivation state lives on the in-memory scan path only — it never
    enters the canonical payload nor the SQLite representation, so
    rehydrated events are NOT re-mergeable and schema.md documents that
    contract."""
    src = ProvenanceSource(SourceType.GIT_TRAILER, EvidenceLevel.DECLARED, "ai-provider")
    event = build_event(
        actor_type=ActorType.AI,
        repository_uid="remote:v4:github.com/o/r",
        commit_sha="a" * 40,
        timestamp="2026-07-14T12:00:00+00:00",
        sources=[src],
        provider="anthropic",
    )
    payload = to_dict(event)
    assert "merged" not in json.dumps(payload)
    assert "recorded_at" not in json.dumps(payload)
    # The persisted-schema half of this contract (no `merged` column)
    # lives with the storage/migration tests (gate-6 L-03).

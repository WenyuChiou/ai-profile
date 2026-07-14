"""Unit tests for the git trailer adapter (ADR-005; docs/schema.md sections
5 and 10; work package B)."""

from __future__ import annotations

from aiprofile.adapters.trailers import ParseWarning, parse_commit_trailers
from aiprofile.schema.event import ProvenanceSource
from aiprofile.schema.vocab import ActorType, ContributionMode, EvidenceLevel, Role, SourceType

#: The exact warning-code vocabulary documented on ParseWarning.code.
DOCUMENTED_WARNING_CODES = {
    "unknown-role",
    "malformed-mode",
    "malformed-reviewed-by",
    "incomplete-group",
    "contradictory-group",
}


# --- no evidence --------------------------------------------------------


def test_no_trailer_input_returns_empty():
    assert parse_commit_trailers([]) == ([], [])


def test_unrelated_trailers_return_empty():
    lines = ["Signed-off-by: Someone <someone@example.com>", "Fixes: #123"]
    assert parse_commit_trailers(lines) == ([], [])


def test_lines_without_colon_are_ignored():
    lines = ["AI-Provider Anthropic (no colon)", "AI-Model: claude-sonnet"]
    specs, warnings = parse_commit_trailers(lines)
    # AI-Model alone (no anchor) -> incomplete-group, not a spec.
    assert specs == []
    assert [w.code for w in warnings] == ["incomplete-group"]


# --- full single group ---------------------------------------------------


def test_full_single_group_all_seven_keys():
    lines = [
        "AI-Provider: Anthropic",
        "AI-Model: Claude-Sonnet",
        "AI-Tool: Claude Code",
        "AI-Role: implementation, testing",
        "AI-Mode: AI-Assisted",
        "AI-Reviewed-By: human",
        "AI-Schema: 0.1.0",
    ]
    specs, warnings = parse_commit_trailers(lines)
    assert warnings == []
    assert len(specs) == 1
    spec = specs[0]
    assert spec.actor_type == ActorType.AI
    assert spec.provider == "anthropic"
    assert spec.provider_raw == "Anthropic"
    assert spec.model == "claude-sonnet"
    assert spec.model_raw == "Claude-Sonnet"
    assert spec.tool == "claude-code"
    assert spec.tool_raw == "Claude Code"
    assert spec.roles == (Role.IMPLEMENTATION, Role.TESTING)
    assert spec.contribution_mode == ContributionMode.AI_ASSISTED
    assert spec.human_reviewed is True
    assert spec.source == ProvenanceSource(
        source_type=SourceType.GIT_TRAILER,
        evidence_level=EvidenceLevel.DECLARED,
        source_reference="ai-provider",
    )


# --- repeated-key grouping -------------------------------------------------


def test_repeated_provider_key_splits_into_two_groups():
    lines = [
        "AI-Provider: Anthropic",
        "AI-Model: claude-sonnet",
        "AI-Provider: OpenAI",
        "AI-Model: gpt-5",
    ]
    specs, warnings = parse_commit_trailers(lines)
    assert warnings == []
    assert len(specs) == 2
    assert specs[0].provider == "anthropic"
    assert specs[0].model == "claude-sonnet"
    assert specs[1].provider == "openai"
    assert specs[1].model == "gpt-5"


# --- tool-only group resolving provider via registry ------------------------


def test_tool_only_group_resolves_provider_via_registry():
    specs, warnings = parse_commit_trailers(["AI-Tool: Claude Code"])
    assert warnings == []
    assert len(specs) == 1
    spec = specs[0]
    assert spec.tool == "claude-code"
    assert spec.tool_raw == "Claude Code"
    assert spec.provider == "anthropic"
    assert spec.provider_raw is None
    assert spec.source.source_reference == "ai-tool"


def test_unrecognized_tool_alone_is_incomplete_group():
    specs, warnings = parse_commit_trailers(["AI-Tool: NotARealTool"])
    assert specs == []
    assert len(warnings) == 1
    assert warnings[0].code == "incomplete-group"
    assert warnings[0].trailer_key == "ai-tool"


# --- unrecognized provider ------------------------------------------------


def test_unrecognized_provider_group_keeps_raw_with_null_canonical():
    specs, warnings = parse_commit_trailers(["AI-Provider: SomeUnlistedVendor"])
    assert warnings == []
    assert len(specs) == 1
    spec = specs[0]
    assert spec.provider is None
    assert spec.provider_raw == "SomeUnlistedVendor"
    assert spec.actor_type == ActorType.AI


def test_explicit_provider_wins_over_conflicting_tool_owner():
    # AI-Tool implies anthropic; AI-Provider explicitly says openai — the
    # explicit AI-Provider wins (docstring contract), even though it's
    # unrecognized (still None, not silently backfilled from the tool).
    specs, warnings = parse_commit_trailers(
        ["AI-Provider: NotAKnownVendor", "AI-Tool: Claude Code"]
    )
    assert warnings == []
    assert len(specs) == 1
    spec = specs[0]
    assert spec.provider is None
    assert spec.provider_raw == "NotAKnownVendor"
    assert spec.tool == "claude-code"


# --- incomplete group (AI-Model only) ---------------------------------------


def test_model_only_group_is_incomplete_group_no_spec():
    specs, warnings = parse_commit_trailers(["AI-Model: claude-sonnet"])
    assert specs == []
    assert len(warnings) == 1
    assert warnings[0] == ParseWarning("incomplete-group", "ai-model")


# --- human-only ------------------------------------------------------------


def test_human_only_alone_yields_human_spec():
    specs, warnings = parse_commit_trailers(["AI-Mode: Human-Only"])
    assert warnings == []
    assert len(specs) == 1
    spec = specs[0]
    assert spec.actor_type == ActorType.HUMAN
    assert spec.provider is None
    assert spec.provider_raw is None
    assert spec.model is None
    assert spec.model_raw is None
    assert spec.tool is None
    assert spec.tool_raw is None
    assert spec.roles == ()
    assert spec.contribution_mode == ContributionMode.HUMAN_ONLY
    assert spec.human_reviewed is None
    assert spec.source == ProvenanceSource(
        source_type=SourceType.GIT_TRAILER,
        evidence_level=EvidenceLevel.DECLARED,
        source_reference="ai-mode",
    )


def test_human_only_keeps_roles_and_reviewed_by():
    specs, warnings = parse_commit_trailers(
        ["AI-Mode: Human-Only", "AI-Role: review", "AI-Reviewed-By: human"]
    )
    assert warnings == []
    assert len(specs) == 1
    spec = specs[0]
    assert spec.actor_type == ActorType.HUMAN
    assert spec.roles == (Role.REVIEW,)
    assert spec.human_reviewed is True


def test_human_only_with_ai_provider_is_contradictory_group():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Mode: Human-Only"])
    assert specs == []
    assert warnings == [ParseWarning("contradictory-group", "ai-mode")]


def test_human_only_with_ai_tool_is_contradictory_group():
    specs, warnings = parse_commit_trailers(["AI-Tool: Claude Code", "AI-Mode: Human-Only"])
    assert specs == []
    assert warnings == [ParseWarning("contradictory-group", "ai-mode")]


# --- AI-Role -----------------------------------------------------------


def test_unknown_role_token_dropped_others_kept():
    specs, warnings = parse_commit_trailers(
        ["AI-Provider: Anthropic", "AI-Role: implementation, bogus, testing"]
    )
    assert len(specs) == 1
    assert specs[0].roles == (Role.IMPLEMENTATION, Role.TESTING)
    assert len(warnings) == 1
    assert warnings[0].code == "unknown-role"
    assert warnings[0].trailer_key == "ai-role"
    assert warnings[0].local_detail == "bogus"


def test_all_unknown_roles_yields_empty_roles_tuple():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Role: bogus, nonsense"])
    assert len(specs) == 1
    assert specs[0].roles == ()
    assert [w.code for w in warnings] == ["unknown-role", "unknown-role"]


# --- AI-Mode -----------------------------------------------------------


def test_malformed_mode_yields_none_mode_and_warning():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Mode: not-a-real-mode"])
    assert len(specs) == 1
    assert specs[0].contribution_mode is None
    assert warnings == [
        ParseWarning("malformed-mode", "ai-mode", local_detail="not-a-real-mode")
    ]


def test_missing_mode_on_ai_group_is_none_with_no_warning():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic"])
    assert warnings == []
    assert len(specs) == 1
    assert specs[0].contribution_mode is None


def test_mode_hyphen_and_space_equivalence():
    specs_hyphen, _ = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Mode: ai-assisted"])
    specs_space, _ = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Mode: ai assisted"])
    assert specs_hyphen[0].contribution_mode == ContributionMode.AI_ASSISTED
    assert specs_space[0].contribution_mode == ContributionMode.AI_ASSISTED


# --- AI-Reviewed-By -------------------------------------------------------


def test_reviewed_by_human_is_true():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Reviewed-By: human"])
    assert warnings == []
    assert specs[0].human_reviewed is True


def test_reviewed_by_none_is_false():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Reviewed-By: none"])
    assert warnings == []
    assert specs[0].human_reviewed is False


def test_reviewed_by_garbage_is_null_with_warning():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Reviewed-By: maybe"])
    assert specs[0].human_reviewed is None
    assert warnings == [
        ParseWarning("malformed-reviewed-by", "ai-reviewed-by", local_detail="maybe")
    ]


def test_reviewed_by_missing_is_null_with_no_warning():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic"])
    assert warnings == []
    assert specs[0].human_reviewed is None


# --- Co-authored-by ------------------------------------------------------


def test_coauthor_registry_hit_claude_code():
    specs, warnings = parse_commit_trailers(["Co-authored-by: Claude <noreply@anthropic.com>"])
    assert warnings == []
    assert len(specs) == 1
    spec = specs[0]
    assert spec.actor_type == ActorType.AI
    assert spec.provider == "anthropic"
    assert spec.provider_raw == "Claude"
    assert spec.tool == "claude-code"
    assert spec.tool_raw is None
    assert spec.model is None
    assert spec.model_raw is None
    assert spec.roles == ()
    assert spec.contribution_mode is None
    assert spec.human_reviewed is None
    assert spec.source == ProvenanceSource(
        source_type=SourceType.GIT_TRAILER_COAUTHOR,
        evidence_level=EvidenceLevel.DECLARED,
        source_reference="co-authored-by",
    )


def test_coauthor_name_prefix_matches_when_present():
    specs, warnings = parse_commit_trailers(["Co-authored-by: Gemini X <noreply@google.com>"])
    assert warnings == []
    assert len(specs) == 1
    assert specs[0].provider == "google"
    assert specs[0].provider_raw == "Gemini X"


def test_coauthor_name_prefix_rejects_when_absent():
    specs, warnings = parse_commit_trailers(["Co-authored-by: Someone <noreply@google.com>"])
    assert specs == []
    assert warnings == []


def test_coauthor_unmatched_human_is_silently_ignored():
    specs, warnings = parse_commit_trailers(["Co-authored-by: John Doe <john@example.com>"])
    assert specs == []
    assert warnings == []


def test_coauthor_malformed_no_email_is_ignored():
    specs, warnings = parse_commit_trailers(["Co-authored-by: Claude Anthropic Bot"])
    assert specs == []
    assert warnings == []


def test_coauthor_tolerates_extra_spaces():
    specs, warnings = parse_commit_trailers(
        ["Co-authored-by:   Claude   <  noreply@anthropic.com  >"]
    )
    assert warnings == []
    assert len(specs) == 1
    assert specs[0].provider == "anthropic"


# --- AI-Schema ----------------------------------------------------------


def test_ai_schema_alongside_provider_is_ignored():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Schema: 0.1.0"])
    assert warnings == []
    assert len(specs) == 1
    assert specs[0].provider == "anthropic"


def test_ai_schema_alone_is_incomplete_group():
    specs, warnings = parse_commit_trailers(["AI-Schema: 0.1.0"])
    assert specs == []
    assert warnings == [ParseWarning("incomplete-group", "ai-schema")]


# --- empty-value keys treated as absent -------------------------------------


def test_empty_value_key_is_treated_as_absent_and_does_not_split_group():
    lines = [
        "AI-Provider: Anthropic",
        "AI-Provider: ",
        "AI-Model: gpt-5",
    ]
    specs, warnings = parse_commit_trailers(lines)
    assert warnings == []
    # The empty-valued repeat of AI-Provider is absent, so it neither
    # overwrites the first value nor splits the group.
    assert len(specs) == 1
    assert specs[0].provider == "anthropic"
    assert specs[0].model == "gpt-5"


def test_empty_value_ai_model_treated_as_absent():
    specs, warnings = parse_commit_trailers(["AI-Provider: Anthropic", "AI-Model:   "])
    assert warnings == []
    assert len(specs) == 1
    assert specs[0].model is None
    assert specs[0].model_raw is None


def test_empty_value_coauthor_ignored():
    specs, warnings = parse_commit_trailers(["Co-authored-by: "])
    assert specs == []
    assert warnings == []


# --- warning codes exactly as documented ------------------------------------


def test_warning_codes_match_documented_vocabulary():
    scenarios = [
        ["AI-Model: claude-sonnet"],  # incomplete-group
        ["AI-Provider: Anthropic", "AI-Mode: Human-Only"],  # contradictory-group
        ["AI-Provider: Anthropic", "AI-Role: bogus"],  # unknown-role
        ["AI-Provider: Anthropic", "AI-Mode: bogus"],  # malformed-mode
        ["AI-Provider: Anthropic", "AI-Reviewed-By: bogus"],  # malformed-reviewed-by
    ]
    seen_codes: set[str] = set()
    for lines in scenarios:
        _, warnings = parse_commit_trailers(lines)
        for warning in warnings:
            assert warning.code in DOCUMENTED_WARNING_CODES
            seen_codes.add(warning.code)
    assert seen_codes == DOCUMENTED_WARNING_CODES


# --- source_reference never contains a trailer value ------------------------


def test_source_reference_never_contains_a_trailer_value():
    lines = [
        "AI-Provider: Anthropic",
        "AI-Model: claude-sonnet",
        "AI-Tool: Claude Code",
        "AI-Provider: SomeUnlistedVendor",
        "AI-Tool: Claude Code",
        "Co-authored-by: Claude <noreply@anthropic.com>",
        "AI-Mode: Ai-Assisted",
        "AI-Mode: Human-Only",
    ]
    specs, _ = parse_commit_trailers(lines)
    # group1 (anthropic), coauthor (anthropic), group2 (unlisted vendor +
    # tool), group3 (isolated Human-Only, forced by the repeated AI-Mode key).
    assert len(specs) == 4
    raw_values = {
        "Anthropic",
        "claude-sonnet",
        "Claude Code",
        "SomeUnlistedVendor",
        "Claude",
        "noreply@anthropic.com",
        "Ai-Assisted",
        "Human-Only",
    }
    allowed_source_references = {"ai-provider", "ai-tool", "ai-mode", "co-authored-by"}
    for spec in specs:
        ref = spec.source.source_reference
        assert ref in allowed_source_references
        assert ref not in raw_values


# --- deterministic ordering across mixed groups and co-authors --------------


def test_deterministic_order_across_mixed_groups_and_coauthor():
    lines = [
        "AI-Provider: Anthropic",
        "Co-authored-by: Gemini Assistant <noreply@google.com>",
        "AI-Provider: OpenAI",
    ]
    specs, warnings = parse_commit_trailers(lines)
    assert warnings == []
    assert [s.provider for s in specs] == ["anthropic", "google", "openai"]


def test_human_only_with_unrecognized_tool_is_contradictory():
    """Orchestrator regression (review round): declaring ANY AI-Provider or
    AI-Tool key alongside AI-Mode: Human-Only is a contradiction even when
    the tool is not registry-resolvable — the tool string must not be
    silently dropped into a clean human declaration."""
    specs, warnings = parse_commit_trailers(
        ["AI-Tool: SomeUnknownTool", "AI-Mode: Human-Only"]
    )
    assert specs == []
    assert [w.code for w in warnings] == ["contradictory-group"]

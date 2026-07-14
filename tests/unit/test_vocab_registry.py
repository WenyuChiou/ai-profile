"""Unit tests for the controlled vocabularies (docs/schema.md sections 2-6, 9)
and the provider/tool/co-author registry (docs/schema.md section 10; ADR-013).
"""

from __future__ import annotations

from aiprofile.registry import (
    PROVIDER_ALIASES,
    PROVIDER_DISPLAY,
    TOOL_ALIASES,
    match_coauthor,
    normalize_provider,
    provider_display,
    resolve_tool,
)
from aiprofile.schema.vocab import (
    EVIDENCE_PRECEDENCE,
    PUBLICATION_RESTRICTIVENESS,
    UNRECOGNIZED_PROVIDER,
    EvidenceLevel,
    PublicationLevel,
)

# --- registry: reserved slug must never leak into alias/display tables -----


def test_unrecognized_provider_absent_from_provider_aliases():
    assert UNRECOGNIZED_PROVIDER not in PROVIDER_ALIASES


def test_unrecognized_provider_absent_from_provider_display():
    assert UNRECOGNIZED_PROVIDER not in PROVIDER_DISPLAY


def test_unrecognized_provider_absent_from_tool_aliases():
    assert UNRECOGNIZED_PROVIDER not in TOOL_ALIASES


# --- normalize_provider ------------------------------------------------------


def test_normalize_provider_case_insensitive():
    assert normalize_provider("anthropic") == "anthropic"
    assert normalize_provider("Anthropic") == "anthropic"
    assert normalize_provider("ANTHROPIC") == "anthropic"


def test_normalize_provider_unknown_returns_none():
    assert normalize_provider("some-unlisted-vendor") is None


# --- resolve_tool -------------------------------------------------------------


def test_resolve_tool_claude_code():
    assert resolve_tool("Claude Code") == ("claude-code", "anthropic")


def test_resolve_tool_unknown_returns_none():
    assert resolve_tool("not-a-real-tool") is None


# --- match_coauthor -----------------------------------------------------------


def test_match_coauthor_exact_email_case_insensitive():
    identity = match_coauthor("Claude", "noreply@anthropic.com")
    upper = match_coauthor("Claude", "NOREPLY@ANTHROPIC.COM")
    assert identity is not None
    assert identity.provider == "anthropic"
    assert identity.tool == "claude-code"
    assert upper == identity


def test_match_coauthor_google_noreply_matches_with_gemini_name_prefix():
    identity = match_coauthor("Gemini Code Assist", "noreply@google.com")
    assert identity is not None
    assert identity.provider == "google"


def test_match_coauthor_google_noreply_rejects_without_gemini_name_prefix():
    assert match_coauthor("Some Other Bot", "noreply@google.com") is None


def test_match_coauthor_unknown_email_returns_none():
    assert match_coauthor("Whoever", "unknown@example.com") is None


# --- provider_display -----------------------------------------------------


def test_provider_display_known_slug():
    assert provider_display("anthropic") == "Claude"


def test_provider_display_unknown_slug_falls_back_to_slug():
    assert provider_display("some-unlisted-vendor") == "some-unlisted-vendor"


# --- vocab: precedence orderings --------------------------------------------


def test_evidence_precedence_ordering():
    assert (
        EVIDENCE_PRECEDENCE[EvidenceLevel.VERIFIED]
        > EVIDENCE_PRECEDENCE[EvidenceLevel.DECLARED]
        > EVIDENCE_PRECEDENCE[EvidenceLevel.IMPORTED]
        > EVIDENCE_PRECEDENCE[EvidenceLevel.INFERRED]
        > EVIDENCE_PRECEDENCE[EvidenceLevel.UNKNOWN]
    )


def test_publication_restrictiveness_ordering():
    assert (
        PUBLICATION_RESTRICTIVENESS[PublicationLevel.EXCLUDED]
        > PUBLICATION_RESTRICTIVENESS[PublicationLevel.AGGREGATE_ONLY]
        > PUBLICATION_RESTRICTIVENESS[PublicationLevel.REPOSITORY_ANONYMOUS]
        > PUBLICATION_RESTRICTIVENESS[PublicationLevel.FULL]
    )

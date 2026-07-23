"""Unit tests for the controlled vocabularies (docs/schema.md sections 2-6, 9)
and the provider/tool/co-author registry (docs/schema.md section 10; ADR-013).
"""

from __future__ import annotations

from aiprofile.registry import (
    COAUTHOR_IDENTITIES,
    PROVIDER_ALIASES,
    PROVIDER_DISPLAY,
    TOOL_ALIASES,
    match_coauthor,
    normalize_provider,
    provider_display,
    resolve_tool,
)
from aiprofile.schema.vocab import (
    CANONICAL_PROVIDERS,
    CANONICAL_TOOLS,
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


# --- round D3: two-tier provider vocabulary (ADR-019) -----------------------

#: canonical slug -> expected PUBLIC display name for the ten round-D3
#: declaration-tier providers (owner ruling 4: product identity, matching
#: the pre-existing google->Gemini precedent).
_D3_DECLARATION_TIER_DISPLAY: dict[str, str] = {
    "amp": "Amp",
    "replit": "Replit",
    "moonshot": "Kimi",
    "deepseek": "DeepSeek",
    "alibaba": "Qwen",
    "mistral": "Mistral",
    "xai": "Grok",
    "zhipu": "GLM",
    "ollama": "Ollama",
    "meta": "Llama",
}


def test_d3_declaration_tier_slugs_are_canonical():
    assert set(_D3_DECLARATION_TIER_DISPLAY) <= CANONICAL_PROVIDERS


def test_d3_every_new_slug_resolves_display_name():
    for slug, expected_display in _D3_DECLARATION_TIER_DISPLAY.items():
        assert provider_display(slug) == expected_display


def test_d3_every_new_slug_normalizes_from_its_raw_trailer_form():
    # Declaration tier means a hand-written AI-Provider trailer resolves,
    # not just that the slug exists in the display map (schema.md section
    # 10, ADR-019).
    for slug in _D3_DECLARATION_TIER_DISPLAY:
        assert normalize_provider(slug) == slug
        assert normalize_provider(slug.upper()) == slug


def test_d3_new_tool_slugs_resolve_and_are_canonical():
    expected = {
        "amp": ("amp", "amp"),
        "replit-agent": ("replit-agent", "replit"),
        "kimi-code": ("kimi-code", "moonshot"),
        "qwen-code": ("qwen-code", "alibaba"),
        "vibe-code": ("vibe-code", "mistral"),
        "ollama": ("ollama", "ollama"),
    }
    for raw, resolved in expected.items():
        assert resolve_tool(raw) == resolved
    assert {tool for tool, _ in expected.values()} <= CANONICAL_TOOLS


def test_d3_amp_coauthor_matches_via_registry():
    identity = match_coauthor("Amp", "amp@ampcode.com")
    assert identity is not None
    assert identity.provider == "amp"
    assert identity.tool == "amp"
    # case-insensitive on email, consistent with every other identity
    assert match_coauthor("Amp", "AMP@AMPCODE.COM") == identity


def test_d3_declaration_tier_slug_without_identity_does_not_auto_match():
    # deepseek is declaration-tier only (owner ruling 1: no auto-match for
    # backend-model providers) - no email should resolve to it, including
    # the most plausible noreply-style guesses.
    assert "deepseek" not in {i.provider for i in COAUTHOR_IDENTITIES.values()}
    for candidate_email in ("noreply@deepseek.com", "deepseek@deepseek.com"):
        identity = match_coauthor("DeepSeek", candidate_email)
        assert identity is None


def test_d3_only_amp_gained_a_new_auto_match_identity():
    # Every round-D3 slug except amp stays out of COAUTHOR_IDENTITIES
    # entirely (ADR-019: declaration tier != auto-match tier).
    new_auto_match_providers = {
        i.provider for i in COAUTHOR_IDENTITIES.values()
    } & set(_D3_DECLARATION_TIER_DISPLAY)
    assert new_auto_match_providers == {"amp"}


def test_d3_vocab_and_tool_subset_asserts_still_hold():
    # Mirrors the module-level asserts in registry.py (belt and suspenders:
    # a future edit that broke one of these would fail at import time
    # already, but pinning it here gives a readable failure).
    assert set(PROVIDER_ALIASES.values()) <= CANONICAL_PROVIDERS
    assert set(PROVIDER_DISPLAY.keys()) <= CANONICAL_PROVIDERS
    assert {slug for slug, _ in TOOL_ALIASES.values()} <= CANONICAL_TOOLS
    assert {owner for _, owner in TOOL_ALIASES.values()} <= CANONICAL_PROVIDERS
    assert {i.provider for i in COAUTHOR_IDENTITIES.values()} <= CANONICAL_PROVIDERS
    assert {
        i.tool for i in COAUTHOR_IDENTITIES.values() if i.tool
    } <= CANONICAL_TOOLS

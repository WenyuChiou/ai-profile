"""Provider / tool normalization and known-AI co-author identities (ADR-013).

Seed policy: every co-author identity and slug below was CONFIRMED by the
adversarially verified landscape research (docs/landscape.md section 2.1).
Unverified candidate strings live in landscape.md section 7, not here.
Matching is case-insensitive; raw strings are always preserved by callers.
Models deliberately do not use this registry (lowercase+trim only).
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema.vocab import CANONICAL_PROVIDERS, CANONICAL_TOOLS, UNRECOGNIZED_PROVIDER

#: raw (lowercased) AI-Provider trailer value -> canonical provider slug
PROVIDER_ALIASES: dict[str, str] = {
    "anthropic": "anthropic",
    "openai": "openai",
    "google": "google",
    "github": "github",
    "amazon": "amazon",
    "cursor": "cursor",
    "aider": "aider",
    "roo code": "roo-code",
    "roo-code": "roo-code",
    "roocode": "roo-code",
    "openhands": "openhands",
    "windsurf": "windsurf",
    "cognition": "cognition",
}

#: canonical provider slug -> display name for cards/exports
PROVIDER_DISPLAY: dict[str, str] = {
    "anthropic": "Claude",
    "openai": "OpenAI",
    "google": "Gemini",
    "github": "Copilot",
    "amazon": "Amazon Q",
    "cursor": "Cursor",
    "aider": "Aider",
    "roo-code": "Roo Code",
    "openhands": "OpenHands",
    "windsurf": "Windsurf",
    "cognition": "Devin",
}

#: raw (lowercased) AI-Tool trailer value -> (tool slug, owning provider slug)
TOOL_ALIASES: dict[str, tuple[str, str]] = {
    "claude-code": ("claude-code", "anthropic"),
    "claude code": ("claude-code", "anthropic"),
    "claudecode": ("claude-code", "anthropic"),
    "codex-cli": ("codex-cli", "openai"),
    "codex cli": ("codex-cli", "openai"),
    "codex": ("codex-cli", "openai"),
    "gemini-cli": ("gemini-cli", "google"),
    "gemini cli": ("gemini-cli", "google"),
    "gemini-code-assist": ("gemini-code-assist", "google"),
    "jules": ("jules", "google"),
    "copilot": ("copilot", "github"),
    "github-copilot": ("copilot", "github"),
    "github copilot": ("copilot", "github"),
    "cursor": ("cursor", "cursor"),
    "aider": ("aider", "aider"),
    "roo-code": ("roo-code", "roo-code"),
    "roo code": ("roo-code", "roo-code"),
    "openhands": ("openhands", "openhands"),
    "devin": ("devin", "cognition"),
    "windsurf": ("windsurf", "windsurf"),
    "cascade": ("windsurf", "windsurf"),
    "amazon-q": ("amazon-q", "amazon"),
    "amazon q": ("amazon-q", "amazon"),
}


@dataclass(frozen=True)
class CoauthorIdentity:
    provider: str
    tool: str | None
    #: required lowercase display-name prefix; None = email alone suffices
    name_prefix: str | None = None


#: exact (lowercased) co-author email -> identity (landscape.md section 2.1)
COAUTHOR_IDENTITIES: dict[str, CoauthorIdentity] = {
    "noreply@anthropic.com": CoauthorIdentity("anthropic", "claude-code"),
    "noreply@openai.com": CoauthorIdentity("openai", "codex-cli"),
    "cursoragent@cursor.com": CoauthorIdentity("cursor", "cursor"),
    "copilot@github.com": CoauthorIdentity("github", "copilot"),
    "223556219+copilot@users.noreply.github.com": CoauthorIdentity("github", "copilot"),
    "198982749+copilot@users.noreply.github.com": CoauthorIdentity("github", "copilot"),
    "aider@aider.chat": CoauthorIdentity("aider", "aider"),
    "roomote@roocode.com": CoauthorIdentity("roo-code", "roo-code"),
    "openhands@all-hands.dev": CoauthorIdentity("openhands", "openhands"),
    "158243242+devin-ai-integration[bot]@users.noreply.github.com": CoauthorIdentity(
        "cognition", "devin"
    ),
    "161369871+google-labs-jules[bot]@users.noreply.github.com": CoauthorIdentity(
        "google", "jules"
    ),
    "176961590+gemini-code-assist[bot]@users.noreply.github.com": CoauthorIdentity(
        "google", "gemini-code-assist"
    ),
    "gemini-cli@google.com": CoauthorIdentity("google", "gemini-cli"),
    "cascade@windsurf.ai": CoauthorIdentity("windsurf", "windsurf"),
    "cascade@windsurf.com": CoauthorIdentity("windsurf", "windsurf"),
    "amazon-q@amazon.com": CoauthorIdentity("amazon", "amazon-q"),
    # Generic Google noreply: only with a "Gemini..." display name (ADR-013
    # name-prefix condition); tool not attributable from the email alone.
    "noreply@google.com": CoauthorIdentity("google", None, name_prefix="gemini"),
}


def normalize_provider(raw: str) -> str | None:
    """Canonical provider slug for a raw AI-Provider value, else None."""
    return PROVIDER_ALIASES.get(raw.strip().lower())


def resolve_tool(raw: str) -> tuple[str, str] | None:
    """(tool slug, owning provider slug) for a raw AI-Tool value, else None."""
    return TOOL_ALIASES.get(raw.strip().lower())


def match_coauthor(name: str, email: str) -> CoauthorIdentity | None:
    """Registry match for a Co-authored-by identity: exact email, plus the
    entry's display-name-prefix condition when it has one."""
    identity = COAUTHOR_IDENTITIES.get(email.strip().lower())
    if identity is None:
        return None
    if identity.name_prefix is not None and not name.strip().lower().startswith(
        identity.name_prefix
    ):
        return None
    return identity


def provider_display(slug: str) -> str:
    return PROVIDER_DISPLAY.get(slug, slug)


# The reserved public-output bucket may never be a registry value (schema.md
# section 10); guarded here and pinned by a unit test.
assert UNRECOGNIZED_PROVIDER not in PROVIDER_ALIASES
assert UNRECOGNIZED_PROVIDER not in PROVIDER_DISPLAY

# The registry maps INTO the schema-owned canonical vocabulary and may never
# emit anything outside it (gate H-02); guarded here and pinned by tests.
assert set(PROVIDER_ALIASES.values()) <= CANONICAL_PROVIDERS
assert set(PROVIDER_DISPLAY.keys()) <= CANONICAL_PROVIDERS
assert {slug for slug, _ in TOOL_ALIASES.values()} <= CANONICAL_TOOLS
assert {owner for _, owner in TOOL_ALIASES.values()} <= CANONICAL_PROVIDERS
assert {i.provider for i in COAUTHOR_IDENTITIES.values()} <= CANONICAL_PROVIDERS
assert {i.tool for i in COAUTHOR_IDENTITIES.values() if i.tool} <= CANONICAL_TOOLS

"""Controlled vocabularies for ACE v0.1 (docs/schema.md sections 2-6, 9).

These enums are the schema: validation rejects anything not listed here.
Adding a value is a schema change and requires a docs/schema.md revision
plus a version bump per ADR-012.
"""

from __future__ import annotations

import re
from enum import StrEnum


class ActorType(StrEnum):
    HUMAN = "human"
    AI = "ai"
    MIXED = "mixed"  # no v0.1 producer; legal input (schema.md section 2)
    UNKNOWN = "unknown"


class ActivityType(StrEnum):
    COMMIT = "commit"  # v0.1: the only activity type (schema.md section 3)


class Role(StrEnum):
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    OTHER = "other"


class ContributionMode(StrEnum):
    AI_GENERATED = "ai_generated"
    AI_ASSISTED = "ai_assisted"
    AI_REVIEWED = "ai_reviewed"
    HUMAN_REVIEWED_AI = "human_reviewed_ai"
    HUMAN_ONLY = "human_only"
    UNKNOWN = "unknown"  # explicit "source asserts mode unknown"; parser emits None, not this


class EvidenceLevel(StrEnum):
    VERIFIED = "verified"
    DECLARED = "declared"
    IMPORTED = "imported"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


#: Precedence for merges (schema.md section 6.1): higher wins.
EVIDENCE_PRECEDENCE: dict[EvidenceLevel, int] = {
    EvidenceLevel.VERIFIED: 4,
    EvidenceLevel.DECLARED: 3,
    EvidenceLevel.IMPORTED: 2,
    EvidenceLevel.INFERRED: 1,
    EvidenceLevel.UNKNOWN: 0,
}


class SourceType(StrEnum):
    GIT_TRAILER = "git_trailer"
    GIT_TRAILER_COAUTHOR = "git_trailer_coauthor"
    MANUAL_DECLARATION = "manual_declaration"  # reserved, post-v0.1 (schema.md section 14)
    NONE = "none"  # the no-evidence marker used by unknown events


#: Merge tie-break priority (ADR-008 canonical rule, G2-06): higher wins
#: after evidence precedence; then lexicographic locator, then value.
SOURCE_TYPE_PRIORITY: dict[SourceType, int] = {
    SourceType.GIT_TRAILER: 3,
    SourceType.GIT_TRAILER_COAUTHOR: 2,
    SourceType.MANUAL_DECLARATION: 1,
    SourceType.NONE: 0,
}

#: Allowed source_reference locators per source type (schema.md section 6.2,
#: G2-07): enum-constrained so sensitive free text structurally cannot enter
#: provenance. Future source types must define their sets before shipping.
ALLOWED_SOURCE_REFERENCES: dict[SourceType, frozenset[str | None]] = {
    SourceType.GIT_TRAILER: frozenset({"ai-provider", "ai-tool", "ai-mode"}),
    SourceType.GIT_TRAILER_COAUTHOR: frozenset({"co-authored-by"}),
    SourceType.MANUAL_DECLARATION: frozenset({None}),  # reserved
    SourceType.NONE: frozenset({None}),
}


class PublicationLevel(StrEnum):
    FULL = "full"
    REPOSITORY_ANONYMOUS = "repository_anonymous"
    AGGREGATE_ONLY = "aggregate_only"
    EXCLUDED = "excluded"


#: Restrictiveness for duplicate-uid resolution (schema.md section 9): higher wins.
PUBLICATION_RESTRICTIVENESS: dict[PublicationLevel, int] = {
    PublicationLevel.EXCLUDED: 3,
    PublicationLevel.AGGREGATE_ONLY: 2,
    PublicationLevel.REPOSITORY_ANONYMOUS: 1,
    PublicationLevel.FULL: 0,
}

#: Reserved provider slug for the public-output bucket of canonical-null
#: presences (schema.md section 10). May not be used as a registry alias.
UNRECOGNIZED_PROVIDER = "unrecognized"
UNRECOGNIZED_DISPLAY = "Unrecognized"

#: Canonical provider slug -> PUBLIC display name (gate-7 H-01: the schema
#: owns the public display vocabulary, exactly as it owns the slugs — the
#: VizStats boundary validates display text against THIS map, so an
#: arbitrary string cannot pose as a display name; the registry maps
#: aliases into the slugs and reads displays from here).
#:
#: ADR-019 two-tier note: the ten entries below `cognition` are
#: DECLARATION-tier only (round D3) — display names follow PRODUCT
#: identity per the google->Gemini precedent (owner ruling 4):
#: moonshot->Kimi, alibaba->Qwen, xai->Grok, zhipu->GLM.
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

#: Closed public model-family vocabulary (ADR-027).  Model categories are
#: intentionally separate from providers: an explicit canonical ``model``
#: value is the only input to this normalizer.  Provider, tool, author,
#: commit-message, and source-style values are never consulted.
MODEL_DISPLAY: dict[str, str] = {
    "claude": "Claude",
    "gpt": "GPT",
    "gemini": "Gemini",
    "llama": "Llama",
    "mistral": "Mistral",
    "deepseek": "DeepSeek",
    "qwen": "Qwen",
    "grok": "Grok",
    "kimi": "Kimi",
    "other": "Other",
    "unknown": "Unknown",
}
MODEL_CATEGORIES = frozenset(MODEL_DISPLAY)

# Prefixes are matched only at a token boundary (exact value, or a separator
#/version character after the family token).  Keeping the table schema-owned
# makes normalization deterministic and auditable rather than a loose keyword
# search.  Exact aliases cover product names that do not carry the family as
# their first token.
MODEL_CATEGORY_PREFIXES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "anthropic/claude", "anthropic.claude", "anthropic-claude"),
    "gpt": (
        "gpt",
        "openai/gpt",
        "openai.gpt",
        "openai-gpt",
        "chatgpt",
        "o1",
        "o3",
        "o4",
    ),
    "gemini": ("gemini", "google/gemini", "google.gemini", "google-gemini"),
    "llama": ("llama", "meta/llama", "meta.llama", "meta-llama"),
    "mistral": ("mistral", "mixtral", "mistralai"),
    "deepseek": ("deepseek",),
    "qwen": ("qwen", "alibaba/qwen", "alibaba.qwen", "alibaba-qwen"),
    "grok": ("grok", "xai/grok", "xai.grok", "xai-grok"),
    "kimi": ("kimi", "moonshot/kimi", "moonshot.kimi", "moonshot-kimi"),
}
MODEL_CATEGORY_ALIASES: dict[str, str] = {
    "chatgpt": "gpt",
    "o1": "gpt",
    "o3": "gpt",
    "o4": "gpt",
    "mixtral": "mistral",
    "mistral-ai": "mistral",
    "meta-ai": "llama",
}
_MODEL_BOUNDARY_RE = re.compile(r"[-_.:/\s0-9]")


def normalize_model_category(model: str | None) -> str:
    """Map one explicit canonical ACE model to a public family slug.

    ``None``/blank values are ``unknown``.  A non-empty value that is not in
    the closed alias/prefix table is deliberately ``other``.  The function
    never falls back to provider/tool values or to ``model_raw``.
    """
    if model is None:
        return "unknown"
    if type(model) is not str:
        return "other"
    value = model.strip().lower()
    if not value:
        return "unknown"
    alias = MODEL_CATEGORY_ALIASES.get(value)
    if alias is not None:
        return alias
    for category, prefixes in MODEL_CATEGORY_PREFIXES.items():
        for prefix in prefixes:
            if value == prefix:
                return category
            if value.startswith(prefix) and len(value) > len(prefix):
                remainder = value[len(prefix) :]
                if _MODEL_BOUNDARY_RE.match(remainder):
                    return category
    return "other"

#: Canonical slug vocabularies (schema.md section 10; gate finding H-02).
#: The schema OWNS these sets: `build_event` rejects any canonical
#: provider/tool value outside them, so an arbitrary string (e.g. a private
#: org name smuggled into a "canonical" field by malformed cache/library
#: input) is structurally unable to pose as canonical. The registry maps
#: aliases INTO these sets and asserts it never emits anything else. Raw
#: (`*_raw`) fields stay free-form and local-only.
#: ADR-019 two-tier note (round D3): the ten slugs below `cognition` are
#: DECLARATION-tier only — accepted so a hand-written `AI-Provider:`
#: trailer resolves and gets its brand mark, with NO auto-match co-author
#: identity (only `amp` also has one, in registry.COAUTHOR_IDENTITIES).
CANONICAL_PROVIDERS = frozenset(
    {
        "anthropic",
        "openai",
        "google",
        "github",
        "amazon",
        "cursor",
        "aider",
        "roo-code",
        "openhands",
        "windsurf",
        "cognition",
        "amp",
        "replit",
        "moonshot",
        "deepseek",
        "alibaba",
        "mistral",
        "xai",
        "zhipu",
        "ollama",
        "meta",
    }
)
CANONICAL_TOOLS = frozenset(
    {
        "claude-code",
        "codex-cli",
        "copilot",
        "cursor",
        "aider",
        "roo-code",
        "openhands",
        "devin",
        "jules",
        "gemini-cli",
        "gemini-code-assist",
        "windsurf",
        "amazon-q",
        "amp",
        "replit-agent",
        "kimi-code",
        "qwen-code",
        "vibe-code",
        "ollama",
    }
)

#: Modes that imply an AI actor (schema.md section 5 mapping table).
AI_IMPLYING_MODES = frozenset(
    {
        ContributionMode.AI_GENERATED,
        ContributionMode.AI_ASSISTED,
        ContributionMode.AI_REVIEWED,
        ContributionMode.HUMAN_REVIEWED_AI,
    }
)

"""Controlled vocabularies for ACE v0.1 (docs/schema.md sections 2-6, 9).

These enums are the schema: validation rejects anything not listed here.
Adding a value is a schema change and requires a docs/schema.md revision
plus a version bump per ADR-012.
"""

from __future__ import annotations

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

#: Canonical slug vocabularies (schema.md section 10; gate finding H-02).
#: The schema OWNS these sets: `build_event` rejects any canonical
#: provider/tool value outside them, so an arbitrary string (e.g. a private
#: org name smuggled into a "canonical" field by malformed cache/library
#: input) is structurally unable to pose as canonical. The registry maps
#: aliases INTO these sets and asserts it never emits anything else. Raw
#: (`*_raw`) fields stay free-form and local-only.
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

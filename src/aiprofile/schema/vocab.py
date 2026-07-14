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
#: participations (schema.md section 10). May not be used as a registry alias.
UNRECOGNIZED_PROVIDER = "unrecognized"
UNRECOGNIZED_DISPLAY = "Unrecognized"

#: Modes that imply an AI actor (schema.md section 5 mapping table).
AI_IMPLYING_MODES = frozenset(
    {
        ContributionMode.AI_GENERATED,
        ContributionMode.AI_ASSISTED,
        ContributionMode.AI_REVIEWED,
        ContributionMode.HUMAN_REVIEWED_AI,
    }
)

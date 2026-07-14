"""VizStats — the visualization data contract and privacy redaction boundary
(architecture.md sections 3 and 8).

Renderers and exporters accept only this type. Its fields are counts,
canonical slugs/display names, evidence totals, period, flags, and a UTC
date: repository identity, emails, shas, paths, and raw trailer strings are
structurally unrepresentable. Only privacy.build_viz_stats constructs it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .errors import RenderError
from .schema.vocab import UNRECOGNIZED_PROVIDER

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Period:
    from_date: str | None
    to_date: str | None
    label: str


@dataclass(frozen=True)
class Totals:
    commits_scanned: int
    ai_attributed_commits: int
    ai_participation_events: int
    human_declared_commits: int
    unknown_commits: int
    active_ai_days: int


@dataclass(frozen=True)
class ProviderRow:
    provider: str
    display_name: str
    attributed_commits: int   # unit: commits (schema.md section 15)
    participation_events: int  # unit: events
    active_days: int           # unit: days


@dataclass(frozen=True)
class EvidenceTotals:
    # unit: events (schema.md section 15)
    verified: int
    declared: int
    imported: int
    inferred: int
    unknown: int


@dataclass(frozen=True)
class PrivacySplit:
    public_commits: int              # commits from `full` repositories
    private_aggregate_commits: int   # commits from aggregate_only/repository_anonymous
    includes_private: bool


@dataclass(frozen=True)
class VizStats:
    schema_version: str
    period: Period
    totals: Totals
    providers: tuple[ProviderRow, ...]
    provider_count: int   # distinct providers excluding the unrecognized bucket
    evidence: EvidenceTotals
    privacy: PrivacySplit
    generated_on: str     # UTC date, YYYY-MM-DD — never a full timestamp

    def __post_init__(self) -> None:
        _validate(self)


def _validate(s: VizStats) -> None:
    counts = [
        s.totals.commits_scanned,
        s.totals.ai_attributed_commits,
        s.totals.ai_participation_events,
        s.totals.human_declared_commits,
        s.totals.unknown_commits,
        s.totals.active_ai_days,
        s.evidence.verified,
        s.evidence.declared,
        s.evidence.imported,
        s.evidence.inferred,
        s.evidence.unknown,
        s.privacy.public_commits,
        s.privacy.private_aggregate_commits,
        s.provider_count,
    ]
    if any((not isinstance(c, int)) or c < 0 for c in counts):
        raise RenderError("VizStats: all counts must be non-negative integers")
    if not _DATE_RE.match(s.generated_on):
        raise RenderError(
            "VizStats.generated_on must be a date (YYYY-MM-DD), never a timestamp"
        )
    if (
        s.privacy.public_commits + s.privacy.private_aggregate_commits
        != s.totals.commits_scanned
    ):
        raise RenderError(
            "VizStats: public + private commits must equal commits_scanned"
        )
    if s.privacy.includes_private != (s.privacy.private_aggregate_commits > 0):
        raise RenderError("VizStats: includes_private flag inconsistent with counts")
    expected_rank = sorted(
        s.providers, key=lambda p: (-p.attributed_commits, p.provider)
    )
    if list(s.providers) != expected_rank:
        raise RenderError(
            "VizStats.providers must be ranked by attributed_commits desc, slug asc"
        )
    real = [p for p in s.providers if p.provider != UNRECOGNIZED_PROVIDER]
    if s.provider_count != len(real):
        raise RenderError(
            "VizStats.provider_count must equal providers excluding the"
            " unrecognized bucket"
        )
    if not s.period.label:
        raise RenderError("VizStats.period.label is required")


def to_json_dict(s: VizStats) -> dict:
    return {
        "schema_version": s.schema_version,
        "generated_on": s.generated_on,
        "period": {
            "from": s.period.from_date,
            "to": s.period.to_date,
            "label": s.period.label,
        },
        "totals": {
            "commits_scanned": s.totals.commits_scanned,
            "ai_attributed_commits": s.totals.ai_attributed_commits,
            "ai_participation_events": s.totals.ai_participation_events,
            "human_declared_commits": s.totals.human_declared_commits,
            "unknown_commits": s.totals.unknown_commits,
            "active_ai_days": s.totals.active_ai_days,
        },
        "providers": [
            {
                "provider": p.provider,
                "display_name": p.display_name,
                "attributed_commits": p.attributed_commits,
                "participation_events": p.participation_events,
                "active_days": p.active_days,
            }
            for p in s.providers
        ],
        "provider_count": s.provider_count,
        "evidence_events": {
            "verified": s.evidence.verified,
            "declared": s.evidence.declared,
            "imported": s.evidence.imported,
            "inferred": s.evidence.inferred,
            "unknown": s.evidence.unknown,
        },
        "privacy": {
            "public_commits": s.privacy.public_commits,
            "private_aggregate_commits": s.privacy.private_aggregate_commits,
            "includes_private": s.privacy.includes_private,
        },
    }


def dumps_stats(s: VizStats) -> str:
    """Deterministic profile.json body (mvp.md section 7 test 17)."""
    return json.dumps(to_json_dict(s), sort_keys=True, indent=2, ensure_ascii=False) + "\n"

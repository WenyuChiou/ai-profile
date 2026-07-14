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
    ai_actor_presences: int   # one provider/tool tuple per commit (G2-02)
    human_declared_commits: int
    unknown_commits: int
    active_ai_days: int       # commit author dates (G2-18)


@dataclass(frozen=True)
class ProviderRow:
    provider: str
    display_name: str
    attributed_commits: int   # unit: commits (schema.md section 15)
    actor_presences: int       # unit: presences (G2-02)
    active_days: int           # unit: days (author dates)


@dataclass(frozen=True)
class EvidenceTotals:
    # unit: records; population = ALL ACE records, every actor type
    # (schema.md section 15, G2-05). Categories must sum to total_records.
    verified: int
    declared: int
    imported: int
    inferred: int
    unknown: int
    total_records: int


@dataclass(frozen=True)
class PrivacySplit:
    # Policy-based labels, never visibility claims (G2-04): "publishable"
    # records the user's `full` decision, not verified GitHub visibility.
    explicitly_publishable_commits: int
    anonymous_aggregate_commits: int
    includes_anonymous_aggregate: bool


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
        s.totals.ai_actor_presences,
        s.totals.human_declared_commits,
        s.totals.unknown_commits,
        s.totals.active_ai_days,
        s.evidence.verified,
        s.evidence.declared,
        s.evidence.imported,
        s.evidence.inferred,
        s.evidence.unknown,
        s.evidence.total_records,
        s.privacy.explicitly_publishable_commits,
        s.privacy.anonymous_aggregate_commits,
        s.provider_count,
        # provider-row numerics (gate M-01): rows are part of the validated
        # contract too, not just the top-level totals.
        *(p.attributed_commits for p in s.providers),
        *(p.actor_presences for p in s.providers),
        *(p.active_days for p in s.providers),
    ]
    if any((not isinstance(c, int)) or c < 0 for c in counts):
        raise RenderError("VizStats: all counts must be non-negative integers")
    if not _DATE_RE.match(s.generated_on):
        raise RenderError(
            "VizStats.generated_on must be a date (YYYY-MM-DD), never a timestamp"
        )
    if (
        s.privacy.explicitly_publishable_commits
        + s.privacy.anonymous_aggregate_commits
        != s.totals.commits_scanned
    ):
        raise RenderError(
            "VizStats: publishable + anonymous-aggregate commits must equal"
            " commits_scanned"
        )
    if s.privacy.includes_anonymous_aggregate != (
        s.privacy.anonymous_aggregate_commits > 0
    ):
        raise RenderError(
            "VizStats: includes_anonymous_aggregate flag inconsistent with counts"
        )
    evidence_sum = (
        s.evidence.verified
        + s.evidence.declared
        + s.evidence.imported
        + s.evidence.inferred
        + s.evidence.unknown
    )
    if evidence_sum != s.evidence.total_records:
        raise RenderError(
            "VizStats: evidence categories must sum to total_records (G2-05)"
        )
    if sum(p.actor_presences for p in s.providers) != s.totals.ai_actor_presences:
        raise RenderError(
            "VizStats: provider actor_presences rows must sum to"
            " totals.ai_actor_presences"
        )
    if s.totals.ai_attributed_commits > s.totals.commits_scanned:
        raise RenderError(
            "VizStats: ai_attributed_commits cannot exceed commits_scanned"
        )
    if any(
        p.attributed_commits > s.totals.ai_attributed_commits for p in s.providers
    ):
        raise RenderError(
            "VizStats: a provider attributed_commits value cannot exceed the"
            " AI-attributed total"
        )
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
            "ai_actor_presences": s.totals.ai_actor_presences,
            "human_declared_commits": s.totals.human_declared_commits,
            "unknown_commits": s.totals.unknown_commits,
            "active_ai_days": s.totals.active_ai_days,
        },
        "providers": [
            {
                "provider": p.provider,
                "display_name": p.display_name,
                "attributed_commits": p.attributed_commits,
                "actor_presences": p.actor_presences,
                "active_days": p.active_days,
            }
            for p in s.providers
        ],
        "provider_count": s.provider_count,
        "evidence_records": {
            "verified": s.evidence.verified,
            "declared": s.evidence.declared,
            "imported": s.evidence.imported,
            "inferred": s.evidence.inferred,
            "unknown": s.evidence.unknown,
            "total_records": s.evidence.total_records,
        },
        "privacy": {
            "explicitly_publishable_commits": s.privacy.explicitly_publishable_commits,
            "anonymous_aggregate_commits": s.privacy.anonymous_aggregate_commits,
            "includes_anonymous_aggregate": s.privacy.includes_anonymous_aggregate,
        },
    }


def dumps_stats(s: VizStats) -> str:
    """Deterministic profile.json body (mvp.md section 7 test 17)."""
    return json.dumps(to_json_dict(s), sort_keys=True, indent=2, ensure_ascii=False) + "\n"

"""Privacy layer: RepoAggregates + config policy → VizStats.

THE redaction boundary (architecture.md section 3). This module is the only
constructor of VizStats; every rule that keeps private data out of public
artifacts is applied here, and the two leak tests (mvp.md section 7 tests
9-10) pin its behavior.
"""

from __future__ import annotations

import datetime

from . import ACE_SCHEMA_VERSION
from .aggregate import DailyProviderRow, RepoAggregates
from .config import Config, resolve_publication_levels
from .registry import provider_display
from .schema.vocab import (
    CANONICAL_PROVIDERS,
    UNRECOGNIZED_DISPLAY,
    UNRECOGNIZED_PROVIDER,
    EvidenceLevel,
    PublicationLevel,
)
from .viz import (
    DAILY_WINDOW_DAYS,
    V01_PERIOD_LABEL,
    DayCell,
    DayCount,
    EvidenceTotals,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
)

_PRIVATE_LEVELS = (
    PublicationLevel.AGGREGATE_ONLY,
    PublicationLevel.REPOSITORY_ANONYMOUS,
)


def _build_daily(
    daily_rows: tuple[DailyProviderRow, ...],
    levels: dict[str, PublicationLevel],
) -> tuple[DayCell, ...]:
    """Publishable-only daily series (round D2, ADR-018).

    Policy applied HERE, at the single chokepoint: only repositories whose
    effective level is FULL ("explicitly publishable") contribute -
    aggregate-only and anonymous repositories NEVER surface their activity
    dates. Non-canonical/None providers collapse into the reserved bucket
    (same defense-in-depth as the provider rows), per-(date, slug) counts
    merge across repositories, and the series is trimmed to the contract
    window (the last DAILY_WINDOW_DAYS ending at the newest publishable
    date - never "today"; the builder stays clock-free).
    """
    merged: dict[str, dict[str, int]] = {}
    for row in daily_rows:
        if levels.get(row.repository_uid, PublicationLevel.EXCLUDED) is not (
            PublicationLevel.FULL
        ):
            continue
        slug = (
            row.provider
            if row.provider in CANONICAL_PROVIDERS
            else UNRECOGNIZED_PROVIDER
        )
        per_day = merged.setdefault(row.date, {})
        per_day[slug] = per_day.get(slug, 0) + row.attributed_commits

    if not merged:
        return ()

    newest = max(datetime.date.fromisoformat(d) for d in merged)
    cutoff = (newest - datetime.timedelta(days=DAILY_WINDOW_DAYS - 1)).isoformat()
    return tuple(
        DayCell(
            date=day,
            counts=tuple(
                DayCount(provider=slug, attributed_commits=count)
                for slug, count in sorted(merged[day].items())
            ),
        )
        for day in sorted(merged)
        if day >= cutoff
    )


def build_viz_stats(
    repo_aggs: list[RepoAggregates],
    cfg: Config,
    generated_on: str,
    daily_rows: tuple[DailyProviderRow, ...] = (),
) -> VizStats:
    """Apply publication policy and strip identity (architecture.md section 3):

    1. levels resolved from current config only; unconfigured uid → excluded
       (fail-closed); most-restrictive wins for duplicate uids;
    2. excluded rows dropped, and no excluded count is emitted;
    3. public/private split in commits;
    4. canonical-null providers collapse into the reserved bucket;
    5. nothing uid-keyed survives.
    """
    levels = resolve_publication_levels(cfg)

    included: list[tuple[RepoAggregates, PublicationLevel]] = []
    for agg in repo_aggs:
        level = levels.get(agg.repository_uid, PublicationLevel.EXCLUDED)
        if level is PublicationLevel.EXCLUDED:
            continue
        included.append((agg, level))

    commits_scanned = sum(a.commits_scanned for a, _ in included)
    publishable_commits = sum(
        a.commits_scanned for a, lv in included if lv is PublicationLevel.FULL
    )
    private_commits = sum(
        a.commits_scanned for a, lv in included if lv in _PRIVATE_LEVELS
    )

    ai_days: set[str] = set()
    evidence = dict.fromkeys((lv.value for lv in EvidenceLevel), 0)
    merged: dict[str, dict] = {}
    for agg, _ in included:
        ai_days |= agg.active_ai_dates
        for level_value, count in agg.evidence_records.items():
            evidence[level_value] = evidence.get(level_value, 0) + count
        for key, pagg in agg.providers.items():
            # Defense in depth (gate H-02): the schema already rejects
            # non-canonical provider values, but this boundary must not
            # TRUST that — any key outside the canonical vocabulary
            # (malformed cache rows, future adapters, library misuse)
            # collapses into the reserved bucket before display lookup.
            slug = key if key in CANONICAL_PROVIDERS else UNRECOGNIZED_PROVIDER
            row = merged.setdefault(
                slug,
                {"attributed_commits": 0, "actor_presences": 0, "dates": set()},
            )
            row["attributed_commits"] += pagg.attributed_commits
            row["actor_presences"] += pagg.actor_presences
            row["dates"] |= pagg.active_dates

    provider_rows = tuple(
        sorted(
            (
                ProviderRow(
                    provider=slug,
                    display_name=(
                        UNRECOGNIZED_DISPLAY
                        if slug == UNRECOGNIZED_PROVIDER
                        else provider_display(slug)
                    ),
                    attributed_commits=row["attributed_commits"],
                    actor_presences=row["actor_presences"],
                    active_days=len(row["dates"]),
                )
                for slug, row in merged.items()
            ),
            key=lambda p: (-p.attributed_commits, p.provider),
        )
    )

    return VizStats(
        schema_version=ACE_SCHEMA_VERSION,
        period=Period(from_date=None, to_date=None, label=V01_PERIOD_LABEL),
        totals=Totals(
            commits_scanned=commits_scanned,
            ai_attributed_commits=sum(a.ai_attributed_commits for a, _ in included),
            ai_actor_presences=sum(
                a.ai_actor_presences for a, _ in included
            ),
            human_declared_commits=sum(
                a.human_declared_commits for a, _ in included
            ),
            unknown_commits=sum(a.unknown_commits for a, _ in included),
            active_ai_days=len(ai_days),
        ),
        providers=provider_rows,
        provider_count=sum(
            1 for p in provider_rows if p.provider != UNRECOGNIZED_PROVIDER
        ),
        evidence=EvidenceTotals(
            verified=evidence[EvidenceLevel.VERIFIED.value],
            declared=evidence[EvidenceLevel.DECLARED.value],
            imported=evidence[EvidenceLevel.IMPORTED.value],
            inferred=evidence[EvidenceLevel.INFERRED.value],
            unknown=evidence[EvidenceLevel.UNKNOWN.value],
            total_records=sum(evidence.values()),
        ),
        privacy=PrivacySplit(
            explicitly_publishable_commits=publishable_commits,
            anonymous_aggregate_commits=private_commits,
            includes_anonymous_aggregate=private_commits > 0,
        ),
        generated_on=generated_on,
        daily=_build_daily(daily_rows, levels),
    )


def local_only_details(repo_aggs: list[RepoAggregates], cfg: Config) -> dict:
    """Local terminal detail for `aggregate -v` (mvp.md section 3). May
    contain raw trailer values and excluded counts — MUST NOT be written
    into dist/ or any published artifact."""
    levels = resolve_publication_levels(cfg)
    excluded = sum(
        1
        for agg in repo_aggs
        if levels.get(agg.repository_uid, PublicationLevel.EXCLUDED)
        is PublicationLevel.EXCLUDED
    )
    unrecognized_raws: set[str] = set()
    for agg in repo_aggs:
        if (
            levels.get(agg.repository_uid, PublicationLevel.EXCLUDED)
            is PublicationLevel.EXCLUDED
        ):
            continue
        none_agg = agg.providers.get(None)
        if none_agg:
            unrecognized_raws |= none_agg.raw_values
    return {
        "excluded_repositories": excluded,
        "unrecognized_provider_values": sorted(unrecognized_raws),
    }

"""Gate-3 privacy-boundary regressions (gate-review.md H-02, M-01):
non-canonical provider keys collapse inside the boundary, and provider-row
numerics are validated. Confirmed failing pre-fix."""

from __future__ import annotations

import pytest

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.aggregate import ProviderAgg, RepoAggregates
from aiprofile.config import Config, RepoEntry
from aiprofile.errors import RenderError
from aiprofile.privacy import build_viz_stats
from aiprofile.schema.vocab import UNRECOGNIZED_PROVIDER, PublicationLevel
from aiprofile.viz import (
    EvidenceTotals,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
)


def test_h02_non_canonical_provider_key_collapses_to_unrecognized():
    # Malformed cache/library input: a provider KEY that is not canonical
    # vocabulary must never survive into VizStats verbatim.
    agg = RepoAggregates(repository_uid="u1", commits_scanned=1)
    agg.ai_attributed_commits = 1
    agg.ai_actor_presences = 1
    agg.active_ai_dates = {"2026-03-01"}
    agg.evidence_records = {"declared": 1}
    agg.providers = {
        "private-org-secret": ProviderAgg(
            attributed_commits=1, actor_presences=1, active_dates={"2026-03-01"}
        )
    }
    cfg = Config(
        identities=["a@example.com"],
        salt="s" * 64,
        repositories=[RepoEntry("/p", "u1", PublicationLevel.AGGREGATE_ONLY)],
    )
    stats = build_viz_stats([agg], cfg, generated_on="2026-07-14")
    slugs = {p.provider for p in stats.providers}
    names = {p.display_name for p in stats.providers}
    assert "private-org-secret" not in slugs
    assert "private-org-secret" not in names
    assert UNRECOGNIZED_PROVIDER in slugs


def test_m01_provider_row_numerics_validated():
    with pytest.raises(RenderError):
        VizStats(
            schema_version=ACE_SCHEMA_VERSION,
            period=Period(None, None, "All time"),
            totals=Totals(
                commits_scanned=1,
                ai_attributed_commits=1,
                ai_actor_presences=1,
                human_declared_commits=0,
                unknown_commits=0,
                active_ai_days=1,
            ),
            providers=(
                ProviderRow(
                    provider="anthropic",
                    display_name="Claude",
                    attributed_commits=-1,
                    actor_presences=1,
                    active_days=-2,
                ),
            ),
            provider_count=1,
            evidence=EvidenceTotals(
                verified=0, declared=1, imported=0, inferred=0, unknown=0, total_records=1
            ),
            privacy=PrivacySplit(
                explicitly_publishable_commits=0,
                anonymous_aggregate_commits=1,
                includes_anonymous_aggregate=True,
            ),
            generated_on="2026-07-14",
        )


# ---------------------------------------------------------------------------
# Round D2 (ADR-018): the daily series is PUBLISHABLE-ONLY. These are the
# canary-date regressions - the single most important property of the
# calendar feature. REVIEW LESSON (D2 internal round): the first canary
# used a far-past date (2019-03-07) that the 84-day window trim excluded
# on its own, so the test could not fail even with the levels filter
# deleted - a confounded proof. The canary is now IN-WINDOW (2026-06-15,
# vs newest publishable date 2026-07-02), re-proven by sabotage: with the
# levels filter disabled the in-window canary leaks, with it restored the
# canary is excluded. Window-trim behavior has its own separate test.
# ---------------------------------------------------------------------------

from aiprofile.aggregate import DailyProviderRow, DailyTotalsRow  # noqa: E402


def _two_repo_setup():
    full = RepoAggregates(repository_uid="u-full", commits_scanned=3)
    full.ai_attributed_commits = 3
    full.ai_actor_presences = 3
    full.active_ai_dates = {"2026-07-01", "2026-07-02"}
    full.evidence_records = {"declared": 3}
    full.providers = {
        "anthropic": ProviderAgg(
            attributed_commits=3,
            actor_presences=3,
            active_dates={"2026-07-01", "2026-07-02"},
        )
    }
    agg_only = RepoAggregates(repository_uid="u-private", commits_scanned=2)
    agg_only.ai_attributed_commits = 2
    agg_only.ai_actor_presences = 2
    agg_only.active_ai_dates = {"2026-06-15"}
    agg_only.evidence_records = {"declared": 2}
    agg_only.providers = {
        "anthropic": ProviderAgg(
            attributed_commits=2, actor_presences=2, active_dates={"2026-06-15"}
        )
    }
    cfg = Config(
        identities=["a@example.com"],
        salt="s" * 64,
        repositories=[
            RepoEntry("/f", "u-full", PublicationLevel.FULL),
            RepoEntry("/p", "u-private", PublicationLevel.AGGREGATE_ONLY),
        ],
    )
    daily_rows = (
        DailyProviderRow("u-full", "2026-07-01", "anthropic", 2),
        DailyProviderRow("u-full", "2026-07-02", "anthropic", 1),
        # The canary: a distinctive date that exists ONLY in the
        # aggregate-only repo and must never surface.
        DailyProviderRow("u-private", "2026-06-15", "anthropic", 2),
    )
    totals_rows = (
        DailyTotalsRow("u-full", "2026-07-01", 3, 2),
        DailyTotalsRow("u-full", "2026-07-02", 1, 1),
        DailyTotalsRow("u-private", "2026-06-15", 2, 2),
    )
    return [full, agg_only], cfg, daily_rows, totals_rows


def test_daily_aggregate_only_dates_never_surface():
    aggs, cfg, daily_rows, totals_rows = _two_repo_setup()
    stats = build_viz_stats(
        aggs, cfg, "2026-07-14", daily_rows=daily_rows, totals_rows=totals_rows
    )
    dates = {c.date for c in stats.daily}
    assert "2026-06-15" not in dates
    assert dates == {"2026-07-01", "2026-07-02"}
    from aiprofile.viz import dumps_stats

    assert "2026-06-15" not in dumps_stats(stats)


def test_daily_publishable_dates_surface_with_counts():
    aggs, cfg, daily_rows, totals_rows = _two_repo_setup()
    stats = build_viz_stats(
        aggs, cfg, "2026-07-14", daily_rows=daily_rows, totals_rows=totals_rows
    )
    assert stats.daily[0].date == "2026-07-01"
    assert stats.daily[0].counts[0].provider == "anthropic"
    assert stats.daily[0].counts[0].attributed_commits == 2
    assert stats.daily[1].counts[0].attributed_commits == 1


def test_daily_noncanonical_provider_collapses_to_unrecognized():
    aggs, cfg, _, _ = _two_repo_setup()
    # Give the FULL repo an unrecognized provider so the bucket exists in
    # the provider rows (subset invariant), then feed a raw daily key.
    aggs[0].providers["zzz-secret-vendor"] = ProviderAgg(
        attributed_commits=2, actor_presences=2, active_dates={"2026-07-02"}
    )
    aggs[0].ai_actor_presences += 2
    daily_rows = (
        DailyProviderRow("u-full", "2026-07-02", "zzz-secret-vendor", 1),
        DailyProviderRow("u-full", "2026-07-02", None, 1),
    )
    totals_rows = (DailyTotalsRow("u-full", "2026-07-02", 2, 2),)
    stats = build_viz_stats(
        aggs, cfg, "2026-07-14", daily_rows=daily_rows, totals_rows=totals_rows
    )
    (cell,) = stats.daily
    (count,) = cell.counts
    assert count.provider == UNRECOGNIZED_PROVIDER
    assert count.attributed_commits == 2
    assert "zzz-secret-vendor" not in str(stats.daily)


def test_daily_window_trims_to_365_days_from_newest():
    # D2 pinned 84; the D4 addendum widened to 365 - a date older than
    # the year window is trimmed, clock-free (anchored on the newest
    # publishable date, not "today").
    aggs, cfg, _, _ = _two_repo_setup()
    aggs[0].providers["anthropic"].attributed_commits = 3
    daily_rows = (
        DailyProviderRow("u-full", "2024-01-01", "anthropic", 1),
        DailyProviderRow("u-full", "2026-07-01", "anthropic", 1),
        DailyProviderRow("u-full", "2026-07-02", "anthropic", 1),
    )
    totals_rows = (
        DailyTotalsRow("u-full", "2024-01-01", 1, 1),
        DailyTotalsRow("u-full", "2026-07-01", 1, 1),
        DailyTotalsRow("u-full", "2026-07-02", 1, 1),
    )
    stats = build_viz_stats(
        aggs, cfg, "2026-07-14", daily_rows=daily_rows, totals_rows=totals_rows
    )
    dates = {c.date for c in stats.daily}
    assert "2024-01-01" not in dates
    assert dates == {"2026-07-01", "2026-07-02"}


def test_daily_empty_rows_yield_empty_series():
    aggs, cfg, _, _ = _two_repo_setup()
    stats = build_viz_stats(aggs, cfg, "2026-07-14", daily_rows=(), totals_rows=())
    assert stats.daily == ()


# ---------------------------------------------------------------------------
# Round D4 (.ai/round_d4_heatmap_spec.md): whole-rhythm totals join the
# chokepoint. Written RED-FIRST against _build_daily consuming totals.
# ---------------------------------------------------------------------------


def test_d4_daily_cells_carry_totals_and_human_only_days():
    aggs, cfg, daily_rows, totals_rows = _two_repo_setup()
    # A publishable human-only day: totals row with zero AI, no provider row.
    totals_rows = totals_rows + (DailyTotalsRow("u-full", "2026-07-03", 4, 0),)
    stats = build_viz_stats(
        aggs, cfg, "2026-07-14", daily_rows=daily_rows, totals_rows=totals_rows
    )
    by_date = {c.date: c for c in stats.daily}
    assert by_date["2026-07-01"].total_commits == 3
    assert by_date["2026-07-01"].ai_commits == 2
    human_day = by_date["2026-07-03"]
    assert human_day.total_commits == 4
    assert human_day.ai_commits == 0
    assert human_day.counts == ()


def test_d4_daily_private_totals_never_surface():
    aggs, cfg, daily_rows, totals_rows = _two_repo_setup()
    # Canary: a human-only day that exists ONLY in the aggregate-only repo.
    totals_rows = totals_rows + (DailyTotalsRow("u-private", "2026-06-20", 9, 0),)
    stats = build_viz_stats(
        aggs, cfg, "2026-07-14", daily_rows=daily_rows, totals_rows=totals_rows
    )
    dates = {c.date for c in stats.daily}
    assert "2026-06-20" not in dates and "2026-06-15" not in dates
    from aiprofile.viz import dumps_stats

    assert "2026-06-20" not in dumps_stats(stats)


def test_d4_daily_multi_repo_same_date_totals_merge():
    aggs, cfg, daily_rows, totals_rows = _two_repo_setup()
    # Second FULL repo active on 2026-07-01: totals sum across repos.
    full2 = RepoAggregates(repository_uid="u-full2", commits_scanned=2)
    full2.ai_attributed_commits = 1
    full2.ai_actor_presences = 1
    full2.active_ai_dates = {"2026-07-01"}
    full2.evidence_records = {"declared": 1}
    full2.providers = {
        "anthropic": ProviderAgg(
            attributed_commits=1, actor_presences=1, active_dates={"2026-07-01"}
        )
    }
    cfg = Config(
        identities=cfg.identities,
        salt=cfg.salt,
        repositories=cfg.repositories
        + [RepoEntry("/f2", "u-full2", PublicationLevel.FULL)],
    )
    daily_rows = daily_rows + (DailyProviderRow("u-full2", "2026-07-01", "anthropic", 1),)
    totals_rows = totals_rows + (DailyTotalsRow("u-full2", "2026-07-01", 2, 1),)
    stats = build_viz_stats(
        aggs + [full2], cfg, "2026-07-14", daily_rows=daily_rows, totals_rows=totals_rows
    )
    by_date = {c.date: c for c in stats.daily}
    assert by_date["2026-07-01"].total_commits == 5  # 3 + 2
    assert by_date["2026-07-01"].ai_commits == 3  # 2 + 1
    assert by_date["2026-07-01"].counts[0].attributed_commits == 3


def test_d4_daily_provider_rows_without_totals_fail_loud():
    # A date with provider counts but no totals row is structurally
    # impossible from one DB - never fabricate, never silently drop.
    aggs, cfg, daily_rows, totals_rows = _two_repo_setup()
    totals_rows = tuple(t for t in totals_rows if t.date != "2026-07-02")
    with pytest.raises(ValueError, match="totals"):
        build_viz_stats(
            aggs, cfg, "2026-07-14", daily_rows=daily_rows, totals_rows=totals_rows
        )

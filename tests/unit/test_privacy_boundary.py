"""Gate-3 privacy-boundary regressions (gate-review.md H-02, M-01):
non-canonical provider keys collapse inside the boundary, and provider-row
numerics are validated. Confirmed failing pre-fix."""

from __future__ import annotations

import pytest

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
            schema_version="0.1.0",
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

"""Gate-7 H-01: VizStats must BE the structural privacy boundary the
architecture claims — a validated instance must be unable to carry
arbitrary strings into SVG/JSON. Every rejection case below was a
reproduced leak pre-fix (canaries appeared verbatim in render_summary
and dumps_stats output)."""

from __future__ import annotations

import pytest

from aiprofile.errors import RenderError
from aiprofile.viz import (
    EvidenceTotals,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
)


def _stats(**overrides):
    base = dict(
        schema_version="0.1.0",
        period=Period(None, None, "All time"),
        totals=Totals(10, 5, 6, 0, 2, 3),
        providers=(ProviderRow("anthropic", "Claude", 5, 6, 3),),
        provider_count=1,
        evidence=EvidenceTotals(0, 6, 0, 0, 0, 6),
        privacy=PrivacySplit(10, 0, False),
        generated_on="2026-07-15",
    )
    base.update(overrides)
    return VizStats(**base)


def test_valid_public_vocabulary_constructs():
    s = _stats()
    assert s.providers[0].display_name == "Claude"


def test_arbitrary_period_label_rejected():
    with pytest.raises(RenderError, match="period"):
        _stats(period=Period(None, None, "SecretPeriod-Repo"))


def test_period_bounds_rejected_in_v01():
    with pytest.raises(RenderError, match="period"):
        _stats(period=Period("2001-01-01", "2002-02-02", "All time"))


def test_foreign_schema_version_rejected():
    with pytest.raises(RenderError, match="schema_version"):
        _stats(schema_version="EVIL-SCHEMA-9.9")


def test_noncanonical_provider_slug_rejected():
    with pytest.raises(RenderError, match="provider"):
        _stats(providers=(ProviderRow("totally-fake-provider", "X", 5, 6, 3),))


def test_arbitrary_display_name_rejected():
    # Canonical slug smuggling an arbitrary display string — the exact
    # H-01 reproduction ("SecretOrg-PrivateRepo" reached SVG and JSON).
    with pytest.raises(RenderError, match="display"):
        _stats(providers=(ProviderRow("anthropic", "SecretOrg-PrivateRepo", 5, 6, 3),))


def test_unrecognized_bucket_display_pinned():
    with pytest.raises(RenderError, match="display"):
        _stats(
            providers=(ProviderRow("unrecognized", "MyPrivateOrg", 5, 6, 3),),
            provider_count=0,
        )


def test_unrecognized_bucket_valid_display_constructs():
    s = _stats(
        providers=(ProviderRow("unrecognized", "Unrecognized", 5, 6, 3),),
        provider_count=0,
    )
    assert s.provider_count == 0

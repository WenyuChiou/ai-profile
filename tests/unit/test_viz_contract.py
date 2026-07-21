"""Gate-7 H-01: VizStats must BE the structural privacy boundary the
architecture claims — a validated instance must be unable to carry
arbitrary strings into SVG/JSON. Every rejection case below was a
reproduced leak pre-fix (canaries appeared verbatim in render_summary
and dumps_stats output)."""

from __future__ import annotations

from dataclasses import dataclass as _dataclass

import pytest

from aiprofile.errors import RenderError
from aiprofile.render.summary_svg import render_summary
from aiprofile.render.themes import THEMES
from aiprofile.viz import (
    EvidenceTotals,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
    dumps_stats,
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


# ---------------------------------------------------------------------------
# Gate-8 H-01: the validated graph must be structurally IMMUTABLE — exact
# frozen contract types only, enforced before any duck-typed access. Each
# rejection below was a reproduced pre-fix bypass (post-construction
# mutation of a duck-typed nested object published private strings via
# BOTH render_summary and dumps_stats).
# ---------------------------------------------------------------------------


@_dataclass
class _MutableRow:
    provider: str = "anthropic"
    display_name: str = "Claude"
    attributed_commits: int = 5
    actor_presences: int = 6
    active_days: int = 3


@_dataclass
class _MutablePeriod:
    from_date: object = None
    to_date: object = None
    label: str = "All time"


def test_mutable_provider_list_rejected():
    with pytest.raises(RenderError, match="tuple"):
        _stats(providers=[ProviderRow("anthropic", "Claude", 5, 6, 3)])


def test_tuple_containing_mutable_row_rejected():
    with pytest.raises(RenderError, match="ProviderRow"):
        _stats(providers=(_MutableRow(),))


def test_mutable_period_rejected():
    with pytest.raises(RenderError, match="Period"):
        _stats(period=_MutablePeriod())


def test_ducktyped_totals_evidence_privacy_rejected():
    @_dataclass
    class FakeTotals:
        commits_scanned: int = 10
        ai_attributed_commits: int = 5
        ai_actor_presences: int = 6
        human_declared_commits: int = 0
        unknown_commits: int = 2
        active_ai_days: int = 3

    @_dataclass
    class FakeEvidence:
        verified: int = 0
        declared: int = 6
        imported: int = 0
        inferred: int = 0
        unknown: int = 0
        total_records: int = 6

    @_dataclass
    class FakePrivacy:
        explicitly_publishable_commits: int = 10
        anonymous_aggregate_commits: int = 0
        includes_anonymous_aggregate: bool = False

    with pytest.raises(RenderError, match="Totals"):
        _stats(totals=FakeTotals())
    with pytest.raises(RenderError, match="EvidenceTotals"):
        _stats(evidence=FakeEvidence())
    with pytest.raises(RenderError, match="PrivacySplit"):
        _stats(privacy=FakePrivacy())


def test_str_subclass_leaves_rejected():
    # A str subclass can override __str__/__format__ to emit DIFFERENT
    # text at render time than what validation saw — same leak class as
    # the mutable duck types, so string leaves require exact str.
    class EvilStr(str):
        def __str__(self):
            return "SecretOrg-PrivateRepo"

    with pytest.raises(RenderError, match="exact str"):
        _stats(period=Period(None, None, EvilStr("All time")))
    with pytest.raises(RenderError, match="exact str"):
        _stats(generated_on=EvilStr("2026-07-15"))


def test_valid_exact_contract_graph_still_constructs():
    s = _stats()
    assert isinstance(s.providers, tuple)
    assert type(s.providers[0]) is ProviderRow


def test_post_construction_mutation_structurally_impossible():
    """The original leak probes are closed STRUCTURALLY: every nested
    object is an exact frozen dataclass, so mutation raises and the
    rendered/exported bytes cannot change."""
    s = _stats()
    theme = THEMES["github-light"]
    before_svg = render_summary(s, theme)
    before_json = dumps_stats(s)
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        s.providers[0].display_name = "SecretOrg-PrivateRepo"
    with pytest.raises(FrozenInstanceError):
        s.period.label = "SecretPeriod-Repo"
    assert render_summary(s, theme) == before_svg
    assert dumps_stats(s) == before_json


# ---------------------------------------------------------------------------
# Gate-8 L-01: generated_on must be a canonical ASCII calendar date.
# Every rejection below was accepted pre-fix.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "２０２６-０７-１５",  # full-width digits
        "٢٠٢٦-٠٧-١٥",  # arabic-indic digits
        "2026-07-15\n",  # trailing newline ($ artifact)
        "2026-99-99",  # impossible month/day
        "2026-13-01",  # invalid month
        "2026-02-30",  # invalid day
        "2025-02-29",  # invalid leap day
    ],
)
def test_generated_on_noncanonical_dates_rejected(bad):
    with pytest.raises(RenderError, match="generated_on"):
        _stats(generated_on=bad)


def test_generated_on_valid_dates_accepted():
    assert _stats(generated_on="2024-02-29").generated_on == "2024-02-29"
    assert _stats(generated_on="2026-07-15").generated_on == "2026-07-15"


def test_int_subclass_leaves_rejected():
    """Same leak class as the str subclass (found by the gate-8
    code-review pass, reproduced: svg_leak=True): an int subclass can
    override __str__ and emit render-time text validation never saw —
    every count leaf requires exact int (which also rejects bool), and
    the privacy flag requires exact bool."""

    class EvilInt(int):
        def __str__(self):
            return "SecretOrg-PrivateRepo"

    with pytest.raises(RenderError, match="exact int"):
        _stats(totals=Totals(10, EvilInt(5), 6, 0, 2, 3))
    with pytest.raises(RenderError, match="exact int"):
        _stats(providers=(ProviderRow("anthropic", "Claude", EvilInt(5), 6, 3),))
    with pytest.raises(RenderError, match="exact int"):
        _stats(totals=Totals(True, 5, 6, 0, 2, 3))  # bool is an int subclass
    with pytest.raises(RenderError, match="exact bool"):
        _stats(privacy=PrivacySplit(10, 0, 0))  # falsy int posing as the flag


def test_vizstats_cannot_be_subclassed():
    """Gate-9 H-01: VizStats is SEALED against subclassing at
    class-definition time. A subclass is an ordinary Python construct
    that defeats every in-method guard — it can override __getattribute__
    to substitute a private-canary ProviderRow at render/export time
    (gate-9 first PoC), OR simply override __post_init__ to skip
    validation entirely (gate-9 review PoC: the malicious row is present
    from construction, no class flag needed). Both leak into SVG and
    JSON. Guarding inside _validate is whack-a-mole; __init_subclass__
    closes the whole family at definition. Confirmed failing pre-fix
    (subclass definition succeeded)."""
    # The class statement itself must raise — before any instance exists.
    with pytest.raises(TypeError, match="subclass"):
        type("GetattrEvil", (VizStats,), {})

    with pytest.raises(TypeError, match="subclass"):

        class SkipValidationEvil(VizStats):
            def __post_init__(self):  # never calls _validate
                pass

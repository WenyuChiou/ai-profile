"""Gate-7 H-01: VizStats must BE the structural privacy boundary the
architecture claims — a validated instance must be unable to carry
arbitrary strings into SVG/JSON. Every rejection case below was a
reproduced leak pre-fix (canaries appeared verbatim in render_summary
and dumps_stats output)."""

from __future__ import annotations

from dataclasses import dataclass as _dataclass

import pytest

from aiprofile import ACE_SCHEMA_VERSION
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
        schema_version=ACE_SCHEMA_VERSION,
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


# ---------------------------------------------------------------------------
# Round D2 (ADR-018): the publishable-only daily series joins the validated
# contract. Every rejection below written RED-FIRST against the field
# landing without its validation battery.
# ---------------------------------------------------------------------------

from aiprofile.viz import DayCell, DayCount  # noqa: E402


def _daily_ok():
    return (
        DayCell("2026-07-14", (DayCount("anthropic", 2),), 3, 2),
        DayCell("2026-07-15", (DayCount("anthropic", 3),), 3, 3),
    )


def test_daily_valid_series_accepted():
    s = _stats(daily=_daily_ok())
    assert len(s.daily) == 2


def test_daily_default_empty_accepted():
    assert _stats().daily == ()


def test_daily_container_must_be_exact_tuple():
    with pytest.raises(RenderError):
        _stats(daily=list(_daily_ok()))


def test_daily_cell_must_be_exact_daycell():
    @_dataclass(frozen=True)
    class FakeCell:
        date: str
        counts: tuple
        total_commits: int
        ai_commits: int

    with pytest.raises(RenderError):
        _stats(daily=(FakeCell("2026-07-15", (DayCount("anthropic", 1),), 1, 1),))


def test_daily_count_must_be_exact_daycount():
    @_dataclass(frozen=True)
    class FakeCount:
        provider: str
        attributed_commits: int

    with pytest.raises(RenderError):
        _stats(daily=(DayCell("2026-07-15", (FakeCount("anthropic", 1),), 1, 1),))


def test_daily_date_rejects_noncanonical_and_invalid():
    for bad in ("2026-7-15", "2026-99-99", "2026-07-15\n", "２026-07-15"):
        with pytest.raises(RenderError):
            _stats(daily=(DayCell(bad, (DayCount("anthropic", 1),), 1, 1),))


def test_daily_dates_must_ascend_without_duplicates():
    cells = (
        DayCell("2026-07-15", (DayCount("anthropic", 1),), 1, 1),
        DayCell("2026-07-14", (DayCount("anthropic", 1),), 1, 1),
    )
    with pytest.raises(RenderError):
        _stats(daily=cells)
    dup = (
        DayCell("2026-07-15", (DayCount("anthropic", 1),), 1, 1),
        DayCell("2026-07-15", (DayCount("anthropic", 1),), 1, 1),
    )
    with pytest.raises(RenderError):
        _stats(daily=dup)


def test_daily_counts_must_be_nonempty_sorted_unique():
    with pytest.raises(RenderError):
        _stats(daily=(DayCell("2026-07-15", (), 1, 1),))
    with pytest.raises(RenderError):
        _stats(
            providers=(
                ProviderRow("anthropic", "Claude", 3, 4, 3),
                ProviderRow("openai", "OpenAI", 2, 2, 2),
            ),
            provider_count=2,
            daily=(
                DayCell(
                    "2026-07-15",
                    (DayCount("openai", 1), DayCount("anthropic", 1)),
                    2,
                    2,
                ),
            ),
        )
    with pytest.raises(RenderError):
        _stats(
            daily=(
                DayCell(
                    "2026-07-15",
                    (DayCount("anthropic", 1), DayCount("anthropic", 2)),
                    3,
                    3,
                ),
            ),
        )


def test_daily_count_must_be_positive_exact_int():
    with pytest.raises(RenderError):
        _stats(daily=(DayCell("2026-07-15", (DayCount("anthropic", 0),), 1, 1),))
    with pytest.raises(RenderError):
        _stats(daily=(DayCell("2026-07-15", (DayCount("anthropic", True),), 1, 1),))


def test_daily_slug_must_be_public_vocabulary():
    with pytest.raises(RenderError):
        _stats(
            daily=(DayCell("2026-07-15", (DayCount("secret-org-name", 1),), 1, 1),)
        )


def test_daily_provider_must_appear_in_provider_rows():
    # A slug in daily that has no provider row cannot be a publishable
    # subset of anything - reject.
    with pytest.raises(RenderError):
        _stats(daily=(DayCell("2026-07-15", (DayCount("cursor", 1),), 1, 1),))


def test_daily_per_provider_sum_cannot_exceed_provider_total():
    # anthropic row has attributed_commits=5; daily sums to 6 -> reject.
    cells = (
        DayCell("2026-07-14", (DayCount("anthropic", 3),), 3, 3),
        DayCell("2026-07-15", (DayCount("anthropic", 3),), 3, 3),
    )
    with pytest.raises(RenderError):
        _stats(daily=cells)


def test_daily_window_bounded():
    # D2 pinned 84 days; the D4 addendum widened the bound to 365 - a
    # >=365-day span is still rejected (see test_d4_window_widens_to_365_days
    # for the exact boundary pair).
    cells = (
        DayCell("2024-01-01", (DayCount("anthropic", 1),), 1, 1),
        DayCell("2026-07-15", (DayCount("anthropic", 1),), 1, 1),
    )
    with pytest.raises(RenderError):
        _stats(daily=cells)


def test_daily_appears_in_json_dump():
    s = _stats(daily=_daily_ok())
    out = dumps_stats(s)
    assert '"daily"' in out and '"2026-07-14"' in out


# ---------------------------------------------------------------------------
# Round D4 (.ai/round_d4_heatmap_spec.md): DayCell carries the day's WHOLE
# rhythm - total_commits (all actors, the owner's own commits included)
# and ai_commits (distinct AI/mixed commits) - and the window widens to
# 365 days. Every rejection below written RED-FIRST against the fields
# landing without their validation battery.
# ---------------------------------------------------------------------------


_D4_DEFAULT_COUNTS = (DayCount("anthropic", 2),)


def _d4_cell(date="2026-07-15", counts=_D4_DEFAULT_COUNTS, total=3, ai=2):
    return DayCell(date, counts, total, ai)


def test_d4_valid_cell_with_totals_accepted():
    s = _stats(daily=(_d4_cell(),))
    assert s.daily[0].total_commits == 3
    assert s.daily[0].ai_commits == 2


def test_d4_human_only_day_accepted():
    # The owner's explicit requirement: days with ONLY the user's own
    # commits are real cells (neutral hue, nonzero intensity).
    s = _stats(daily=(_d4_cell(counts=(), total=4, ai=0),))
    assert s.daily[0].total_commits == 4
    assert s.daily[0].ai_commits == 0
    assert s.daily[0].counts == ()


def test_d4_total_commits_must_be_positive_exact_int():
    for bad in (0, -1, True, "3", 3.0, None):
        with pytest.raises((RenderError, TypeError)):
            _stats(daily=(_d4_cell(total=bad, ai=0, counts=()),))


def test_d4_ai_commits_must_be_exact_nonnegative_int():
    for bad in (-1, True, "2", 2.0, None):
        with pytest.raises((RenderError, TypeError)):
            _stats(daily=(_d4_cell(ai=bad),))


def test_d4_ai_commits_cannot_exceed_total_commits():
    with pytest.raises(RenderError, match="total"):
        _stats(daily=(_d4_cell(total=2, ai=3, counts=(DayCount("anthropic", 3),)),))


def test_d4_empty_counts_require_zero_ai():
    # ai_commits > 0 with no provider breakdown would publish an AI count
    # that cannot be cross-checked against the rows - reject.
    with pytest.raises(RenderError, match="counts"):
        _stats(daily=(_d4_cell(counts=(), total=2, ai=1),))


def test_d4_nonempty_counts_require_positive_ai():
    # A provider count on a day claimed to have zero AI commits is
    # internally contradictory - reject.
    with pytest.raises(RenderError, match="counts"):
        _stats(daily=(_d4_cell(counts=(DayCount("anthropic", 1),), total=2, ai=0),))


def test_d4_provider_count_cannot_exceed_ai_commits():
    # Each provider's distinct-commit count is a subset of the day's
    # distinct AI commits.
    with pytest.raises(RenderError, match="ai_commits"):
        _stats(daily=(_d4_cell(counts=(DayCount("anthropic", 3),), total=5, ai=2),))


def test_d4_ai_commits_cannot_exceed_sum_of_counts():
    # Every AI commit surfaces in >=1 provider count (unrecognized
    # bucket included), so ai_commits > sum(counts) is impossible data.
    with pytest.raises(RenderError, match="ai_commits"):
        _stats(daily=(_d4_cell(counts=(DayCount("anthropic", 1),), total=5, ai=2),))


def test_d4_multi_provider_day_with_overlap_accepted():
    # "Claude implements, Gemini reviews the same commit": counts sum (3)
    # exceeds ai_commits (2); each count <= ai_commits; accepted.
    s = _stats(
        totals=Totals(10, 5, 8, 0, 2, 3),
        providers=(
            ProviderRow("anthropic", "Claude", 5, 6, 3),
            ProviderRow("google", "Gemini", 2, 2, 1),
        ),
        provider_count=2,
        daily=(
            _d4_cell(
                counts=(DayCount("anthropic", 2), DayCount("google", 1)),
                total=4,
                ai=2,
            ),
        ),
    )
    assert s.daily[0].ai_commits == 2


def test_d4_window_widens_to_365_days():
    ok = _stats(
        daily=(
            _d4_cell(date="2025-07-17", counts=(DayCount("anthropic", 1),), total=1, ai=1),
            _d4_cell(date="2026-07-16", counts=(DayCount("anthropic", 1),), total=1, ai=1),
        )
    )
    assert len(ok.daily) == 2  # 364-day span: inside the D4 window
    with pytest.raises(RenderError, match="365"):
        _stats(
            daily=(
                _d4_cell(date="2025-07-16", counts=(DayCount("anthropic", 1),), total=1, ai=1),
                _d4_cell(date="2026-07-16", counts=(DayCount("anthropic", 1),), total=1, ai=1),
            )
        )


def test_d4_daily_json_serialization_carries_totals():
    from aiprofile.viz import dumps_stats

    s = _stats(daily=(_d4_cell(),))
    import json as _json

    payload = _json.loads(dumps_stats(s))
    cell = payload["daily"][0]
    assert cell["total_commits"] == 3
    assert cell["ai_commits"] == 2

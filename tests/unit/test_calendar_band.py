"""Unit tests for the Collaboration Pulse (ADR-032; semantics from ADR-022).

Fixtures here are built inline from `aiprofile.viz` dataclasses, same
discipline as `test_render_summary.py` (never round-tripped through
storage/aggregate) — constructing them exercises the REAL VizStats
validators (subset-of-provider-rows, window bound, slug-ascending unique
counts, date-ascending unique cells): an invalid series fails at module
import time, not just in a targeted assertion.

The pulse's ENCODING contract (mark height = total-commit bins, accent
fill height = AI-share bins, provider independence) is pinned in
tests/unit/test_recruiter_card.py; this module keeps the geometry
regressions: the 84 chronological positions, 12x7 grouping rhythm, month
labels, legend, painter determinism, integer hygiene, the SMIL ban, and
the honest empty states.
"""

from __future__ import annotations

import dataclasses
import datetime
import re
import xml.etree.ElementTree as ET

import pytest

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.errors import RenderError
from aiprofile.render._bins import _share_bin, _volume_bin
from aiprofile.render.summary_svg import (
    CAL_GAP_BELOW,
    CAL_NOTICE_HEIGHT,
    CAL_TOP,
    CAL_UNPUBLISHED_TEXT,
    CAL_WINDOW_DAYS,
    PADDING,
    PULSE_BASELINE_Y,
    PULSE_BLOCK_HEIGHT,
    PULSE_GROUP_DAYS,
    PULSE_GROUP_GAP,
    PULSE_GROUP_PITCH,
    PULSE_GROUP_W,
    PULSE_GROUPS,
    PULSE_HEIGHTS,
    PULSE_LABEL_TEXT,
    PULSE_LEGEND_TEXT,
    PULSE_MARK_GAP,
    PULSE_MARK_W,
    PULSE_TICK_H,
    PULSE_WIDTH,
    PULSE_X,
    WIDTH,
    _calendar_desc_suffix,
    _dedupe_colliding_month_labels,
    _month_boundaries,
    _month_label_columns,
    _panel_top,
    _pulse_day_cells,
    _pulse_legend_svg,
    _pulse_mark_svg,
    _pulse_mark_x,
    _pulse_month_labels_svg,
    card_height,
    render_summary,
)
from aiprofile.render.themes import THEMES
from aiprofile.schema.vocab import UNRECOGNIZED_DISPLAY, UNRECOGNIZED_PROVIDER
from aiprofile.viz import (
    DayCell,
    DayCount,
    EvidenceTotals,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
)

SVG_NS = "{http://www.w3.org/2000/svg}"
CAL_GENERATED_ON = "2026-07-14"


def _period() -> Period:
    return Period(from_date=None, to_date=None, label="All time")


# ---------------------------------------------------------------------------
# Main fixture: mirrors test_render_summary.FIXTURE_POPULATED's daily shape
# (same dates/counts, deliberately duplicated rather than cross-imported —
# each test module owns its fixtures, matching this repo's convention).
# Newest date 2026-07-14, oldest 2026-04-22 (exactly the 84-day window's
# own left edge). Offsets (see the module docstring of `_pulse_day_cells`
# for the oldest-to-newest indexing) are pinned here so the geometry tests
# below can address specific marks directly.
# ---------------------------------------------------------------------------

OFFSET_OLDEST = 0  # 2026-04-22 -- total 3, ai 2
OFFSET_LOW = 23  # 2026-05-15 -- total 3, ai 3
OFFSET_MIXED = 43  # 2026-06-04 -- total 8, ai 7 (multi-provider day)
OFFSET_BUSY = 73  # 2026-07-04 -- total 12, ai 10 (top volume bin)
OFFSET_NEWEST = 83  # 2026-07-14 -- total 8, ai 8

_MAIN_PROVIDERS = (
    ProviderRow(provider="anthropic", display_name="Claude", attributed_commits=30,
                actor_presences=32, active_days=10),
    ProviderRow(provider="openai", display_name="OpenAI", attributed_commits=10,
                actor_presences=10, active_days=4),
    ProviderRow(provider="google", display_name="Gemini", attributed_commits=6,
                actor_presences=6, active_days=2),
    ProviderRow(provider="amazon", display_name="Amazon Q", attributed_commits=5,
                actor_presences=5, active_days=2),
    ProviderRow(provider=UNRECOGNIZED_PROVIDER, display_name=UNRECOGNIZED_DISPLAY,
                attributed_commits=3, actor_presences=3, active_days=1),
)

_MAIN_DAILY = (
    DayCell(date="2026-04-22", counts=(DayCount(provider="amazon", attributed_commits=2),),
            total_commits=3, ai_commits=2),
    DayCell(date="2026-05-15", counts=(DayCount(provider="anthropic", attributed_commits=3),),
            total_commits=3, ai_commits=3),
    DayCell(
        date="2026-06-04",
        counts=(
            DayCount(provider="anthropic", attributed_commits=4),
            DayCount(provider="google", attributed_commits=2),
            DayCount(provider=UNRECOGNIZED_PROVIDER, attributed_commits=1),
        ),
        total_commits=8,
        ai_commits=7,
    ),
    DayCell(date="2026-07-04", counts=(DayCount(provider="anthropic", attributed_commits=10),),
            total_commits=12, ai_commits=10),
    DayCell(
        date="2026-07-14",
        counts=(
            DayCount(provider="amazon", attributed_commits=3),
            DayCount(provider="anthropic", attributed_commits=5),
        ),
        total_commits=8,
        ai_commits=8,
    ),
)

FIXTURE_MAIN = VizStats(
    schema_version=ACE_SCHEMA_VERSION,
    period=_period(),
    totals=Totals(
        commits_scanned=80,
        ai_attributed_commits=54,
        ai_actor_presences=56,
        human_declared_commits=2,
        unknown_commits=24,
        active_ai_days=15,
    ),
    providers=_MAIN_PROVIDERS,
    provider_count=4,  # excludes the unrecognized bucket
    evidence=EvidenceTotals(
        verified=0, declared=54, imported=0, inferred=0, unknown=26, total_records=80
    ),
    privacy=PrivacySplit(
        explicitly_publishable_commits=80,
        anonymous_aggregate_commits=0,
        includes_anonymous_aggregate=False,
    ),
    generated_on=CAL_GENERATED_ON,
    daily=_MAIN_DAILY,
)

_SINGLE_PROVIDERS = (
    ProviderRow(provider="anthropic", display_name="Claude", attributed_commits=5,
                actor_presences=5, active_days=1),
)
_SINGLE_KWARGS = dict(
    schema_version=ACE_SCHEMA_VERSION,
    period=_period(),
    totals=Totals(
        commits_scanned=5,
        ai_attributed_commits=5,
        ai_actor_presences=5,
        human_declared_commits=0,
        unknown_commits=0,
        active_ai_days=1,
    ),
    providers=_SINGLE_PROVIDERS,
    provider_count=1,
    evidence=EvidenceTotals(
        verified=0, declared=5, imported=0, inferred=0, unknown=0, total_records=5
    ),
    privacy=PrivacySplit(
        explicitly_publishable_commits=5,
        anonymous_aggregate_commits=0,
        includes_anonymous_aggregate=False,
    ),
    generated_on=CAL_GENERATED_ON,
)

FIXTURE_SINGLE_DAY = VizStats(
    **_SINGLE_KWARGS,
    daily=(
        DayCell(date="2026-07-14", counts=(DayCount(provider="anthropic", attributed_commits=5),),
            total_commits=5, ai_commits=5),
    ),
)


# ---------------------------------------------------------------------------
# 1. Empty daily with nonzero totals = the exact honest notice (ADR-022).
# ---------------------------------------------------------------------------


def test_omitted_daily_equals_explicit_empty_tuple():
    """`daily` is additive with a `()` default (viz.py): constructing
    without it must be indistinguishable from passing `daily=()`
    explicitly — proven by rendering both and comparing bytes, not just
    asserting the dataclass values are equal."""
    implicit = VizStats(**_SINGLE_KWARGS)
    explicit = VizStats(**_SINGLE_KWARGS, daily=())
    for theme in THEMES.values():
        assert render_summary(implicit, theme).encode("utf-8") == render_summary(
            explicit, theme
        ).encode("utf-8")


def test_empty_daily_renders_notice_not_pulse_and_shrinks_the_card():
    """An unpublished daily series renders the exact CAL_UNPUBLISHED_TEXT
    notice in the pulse slot (no marks, no legend, no month labels) and
    the card shrinks by the pulse-vs-notice height difference."""
    no_daily = dataclasses.replace(FIXTURE_MAIN, daily=())
    assert card_height(FIXTURE_MAIN) - card_height(no_daily) == (
        PULSE_BLOCK_HEIGHT - CAL_NOTICE_HEIGHT
    )
    assert _panel_top(FIXTURE_MAIN) - _panel_top(no_daily) == (
        PULSE_BLOCK_HEIGHT - CAL_NOTICE_HEIGHT
    )
    for theme in THEMES.values():
        svg = render_summary(no_daily, theme)
        assert CAL_UNPUBLISHED_TEXT in svg
        assert PULSE_LABEL_TEXT in svg  # the section label stays honest
        assert PULSE_LEGEND_TEXT not in svg
        assert "<polygon" not in svg
        assert "<animate" not in svg
        assert "Jan" not in svg and "Feb" not in svg  # no stray month labels
        root = ET.fromstring(svg)  # still well-formed
        del root


# ---------------------------------------------------------------------------
# 2. The 84 chronological positions and the 12x7 grouping rhythm.
# ---------------------------------------------------------------------------


def test_pulse_geometry_constants_are_the_approved_design():
    assert PULSE_GROUPS == 12
    assert PULSE_GROUP_DAYS == 7
    assert CAL_WINDOW_DAYS == 84
    assert PULSE_MARK_W == 6
    assert PULSE_MARK_GAP == 2
    assert PULSE_GROUP_GAP > PULSE_MARK_GAP  # structural 7-day rhythm
    assert PULSE_HEIGHTS == (12, 24, 36, 48)
    assert PULSE_TICK_H == 2
    # Left-aligned on the card margin; fits inside the content width.
    assert PULSE_X == PADDING
    assert PULSE_X + PULSE_WIDTH <= WIDTH - PADDING


def test_all_84_mark_positions_are_exact_integers_in_chronological_order():
    xs = [_pulse_mark_x(offset) for offset in range(CAL_WINDOW_DAYS)]
    assert len(xs) == 84
    assert all(isinstance(x, int) for x in xs)
    assert xs == sorted(xs)
    assert len(set(xs)) == 84
    for offset, x in enumerate(xs):
        group, member = divmod(offset, PULSE_GROUP_DAYS)
        assert x == PULSE_X + group * PULSE_GROUP_PITCH + member * (
            PULSE_MARK_W + PULSE_MARK_GAP
        )
    assert xs[0] == PULSE_X
    assert xs[-1] + PULSE_MARK_W == PULSE_X + PULSE_WIDTH


def test_group_gap_is_wider_than_the_mark_gap():
    """The 12 groups of seven read as a structural rhythm: consecutive
    marks inside a group sit PULSE_MARK_GAP apart, while the seam between
    group N's last mark and group N+1's first mark is PULSE_GROUP_GAP."""
    for offset in range(CAL_WINDOW_DAYS - 1):
        gap = _pulse_mark_x(offset + 1) - (_pulse_mark_x(offset) + PULSE_MARK_W)
        if offset % PULSE_GROUP_DAYS == PULSE_GROUP_DAYS - 1:
            assert gap == PULSE_GROUP_GAP
        else:
            assert gap == PULSE_MARK_GAP
    assert PULSE_GROUP_W == PULSE_GROUP_DAYS * PULSE_MARK_W + (
        PULSE_GROUP_DAYS - 1
    ) * PULSE_MARK_GAP


def test_pulse_renders_exactly_84_marks_and_no_background_cells():
    """Every date renders exactly one mark anchored on the shared
    baseline: a data pulse for an active day, a 2px tick otherwise —
    and there is no 84-cell background heatmap grid behind them. All
    mark rectangles (ticks, neutral pulses, accent fills) bottom-anchor
    on the shared baseline."""
    theme = THEMES["github-light"]
    svg = render_summary(FIXTURE_MAIN, theme)
    baseline = CAL_TOP + PULSE_BASELINE_Y
    root = ET.fromstring(svg)
    marks = [
        node
        for node in root
        if node.tag == f"{SVG_NS}rect"
        and node.attrib.get("width") == str(PULSE_MARK_W)
        and int(node.attrib["y"]) + int(node.attrib["height"]) == baseline
    ]
    # 84 base marks + one accent overlay per active day with a nonzero
    # AI-share fill (all 5 fixture days have ai_commits > 0).
    assert len(marks) == CAL_WINDOW_DAYS + 5
    ticks = [node for node in marks if node.attrib.get("height") == str(PULSE_TICK_H)]
    assert len(ticks) == CAL_WINDOW_DAYS - 5
    fills = {node.attrib["fill"] for node in marks}
    assert fills == {theme.border, theme.muted, theme.accent}
    assert theme.bar_track not in fills


def test_chronology_oldest_first_newest_last():
    cells = _pulse_day_cells(FIXTURE_MAIN)
    assert len(cells) == CAL_WINDOW_DAYS
    assert cells[OFFSET_OLDEST] is not None and cells[OFFSET_OLDEST].date == "2026-04-22"
    assert cells[OFFSET_NEWEST] is not None and cells[OFFSET_NEWEST].date == "2026-07-14"
    assert _pulse_mark_x(OFFSET_OLDEST) < _pulse_mark_x(OFFSET_NEWEST)


def test_single_day_series_populates_exactly_one_mark():
    cells = _pulse_day_cells(FIXTURE_SINGLE_DAY)
    assert len(cells) == CAL_WINDOW_DAYS
    populated = [c for c in cells if c is not None]
    assert len(populated) == 1
    assert populated[0].date == "2026-07-14"
    # Card height is IDENTICAL to any other non-empty daily series: the
    # pulse's footprint is a fixed constant, independent of how sparse
    # the data is (only presence/absence of `daily` changes the layout).
    assert card_height(FIXTURE_SINGLE_DAY) - card_height(
        dataclasses.replace(FIXTURE_SINGLE_DAY, daily=())
    ) == PULSE_BLOCK_HEIGHT - CAL_NOTICE_HEIGHT
    svg = render_summary(FIXTURE_SINGLE_DAY, THEMES["github-light"])
    assert "<rect" in svg
    assert "<polygon" not in svg
    ET.fromstring(svg)  # well-formed


# ---------------------------------------------------------------------------
# 3. Height bins, fill levels, and the no-activity baseline tick.
# ---------------------------------------------------------------------------


def test_top_volume_bin_saturates_at_max_height():
    """A 12-commit day and an 8-commit day share the top volume bin, so
    both pulses render at exactly PULSE_HEIGHTS[-1] — never a taller,
    proportionally-scaled column that would blow the fixed geometry
    budget."""
    cells = _pulse_day_cells(FIXTURE_MAIN)
    theme = THEMES["github-light"]
    for offset, total in ((OFFSET_BUSY, 12), (OFFSET_NEWEST, 8)):
        cell = cells[offset]
        assert cell is not None and cell.total_commits == total
        svg = _pulse_mark_svg(cell, _pulse_mark_x(offset), 100, theme)
        assert f'height="{PULSE_HEIGHTS[-1]}"' in svg
    # An under-cap day (3 commits -> bin 1) renders at its own fixed bin
    # height, strictly lower than the top bin.
    low_cell = cells[OFFSET_LOW]
    assert low_cell is not None
    svg_low = _pulse_mark_svg(low_cell, _pulse_mark_x(OFFSET_LOW), 100, theme)
    expected_h = PULSE_HEIGHTS[_volume_bin(3)]
    assert 0 < expected_h < PULSE_HEIGHTS[-1]
    assert f'height="{expected_h}"' in svg_low


def test_accent_fill_rises_from_the_baseline_in_exact_quarters():
    """The accent fill spatially maps `_share_bin` levels to
    0/25/50/75/100% of the pulse height, always growing up from the
    shared baseline (its bottom edge equals the pulse's bottom edge)."""
    theme = THEMES["github-light"]
    baseline = 100
    for total, ai, bin_index in ((3, 0, 0), (8, 2, 1), (6, 3, 2), (3, 2, 3), (5, 5, 4)):
        cell = DayCell(date="2026-07-14", counts=(), total_commits=total, ai_commits=ai) \
            if ai == 0 else DayCell(
                date="2026-07-14",
                counts=(DayCount(provider="anthropic", attributed_commits=ai),),
                total_commits=total, ai_commits=ai,
            )
        assert _share_bin(ai, total) == bin_index
        height = PULSE_HEIGHTS[_volume_bin(total)]
        expected_fill = height * bin_index // 4
        svg = _pulse_mark_svg(cell, 100, baseline, theme)
        rects = [
            node.attrib
            for node in ET.fromstring(
                f'<svg xmlns="http://www.w3.org/2000/svg">{svg}</svg>'
            )
        ]
        outer = rects[0]
        assert outer["fill"] == theme.muted
        assert int(outer["height"]) == height
        assert int(outer["y"]) + int(outer["height"]) == baseline
        if bin_index == 0:
            # Zero AI attribution: neutral pulse only — never a Human claim.
            assert len(rects) == 1
            assert theme.accent not in svg
        else:
            fill = rects[1]
            assert fill["fill"] == theme.accent
            assert int(fill["height"]) == expected_fill
            assert int(fill["y"]) + int(fill["height"]) == baseline
            assert expected_fill * 4 == height * bin_index  # exact integer quarters


def test_no_activity_date_renders_only_a_2px_baseline_tick():
    for theme in THEMES.values():
        tick_svg = _pulse_mark_svg(None, 100, 200, theme)
        assert tick_svg.count("<rect") == 1
        assert f'height="{PULSE_TICK_H}"' in tick_svg
        assert f'y="{200 - PULSE_TICK_H}"' in tick_svg
        assert f'width="{PULSE_MARK_W}"' in tick_svg
        assert theme.accent not in tick_svg
        assert "fill-opacity" not in tick_svg


def test_zero_ai_day_differs_from_no_activity_and_never_reads_human():
    """A 3-commit day with zero attributed AI commits (not provably
    human — unattributed history sits in that bin too) is a full-height
    neutral pulse, visibly different from both a no-activity tick and an
    AI-share day, and never labelled human."""
    theme = THEMES["github-light"]
    zero_ai = DayCell("2026-07-14", (), 3, 0)
    assert _pulse_mark_svg(zero_ai, 100, 200, theme) != _pulse_mark_svg(None, 100, 200, theme)
    svg = render_summary(FIXTURE_MAIN, theme)
    assert "Human commits" not in svg


# ---------------------------------------------------------------------------
# 4. Geometry determinism and integer hygiene.
# ---------------------------------------------------------------------------


def test_pulse_lookup_and_positions_are_deterministic():
    assert _pulse_day_cells(FIXTURE_MAIN) == _pulse_day_cells(FIXTURE_MAIN)
    for offset in range(CAL_WINDOW_DAYS):
        assert _pulse_mark_x(offset) == _pulse_mark_x(offset)


def test_same_input_renders_byte_identical_pulse_markup():
    for theme in THEMES.values():
        first = render_summary(FIXTURE_MAIN, theme)
        second = render_summary(FIXTURE_MAIN, theme)
        assert first == second
        assert first.encode("utf-8") == second.encode("utf-8")


def test_pulse_coordinates_carry_no_float_noise():
    """Every coordinate the pulse emits is an exact integer, by
    construction: every geometry constant is int and the quarter fills
    divide exactly (all PULSE_HEIGHTS are multiples of 4)."""
    assert all(height % 4 == 0 for height in PULSE_HEIGHTS)
    coord_attr_re = re.compile(r' (?:x|y|width|height)="(-?\d+)"')
    coord_re = re.compile(r"-?\d+")
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_MAIN, theme)
        matches = coord_attr_re.findall(svg)
        assert len(matches) > 80  # 84 marks plus card and section rectangles
        assert all(coord_re.fullmatch(value) for value in matches)


def test_pulse_is_provider_independent_geometry():
    """Provider rows and counts never reach mark geometry: a one-commit
    multi-provider day renders byte-identically to a one-commit
    single-provider day."""
    single = DayCell(
        date="2026-07-14",
        counts=(DayCount(provider="anthropic", attributed_commits=1),),
        total_commits=1, ai_commits=1,
    )
    multi = DayCell(
        date="2026-07-14",
        counts=(
            DayCount(provider="anthropic", attributed_commits=1),
            DayCount(provider="google", attributed_commits=1),
        ),
        total_commits=1, ai_commits=1,
    )
    for theme in THEMES.values():
        assert _pulse_mark_svg(single, 100, 200, theme) == _pulse_mark_svg(
            multi, 100, 200, theme
        )


# ---------------------------------------------------------------------------
# 5. <desc> summary (window span + peak day + both encodings) and ASCII sweep.
# ---------------------------------------------------------------------------


def test_desc_suffix_states_window_span_peak_and_encodings():
    suffix = _calendar_desc_suffix(FIXTURE_MAIN)
    assert suffix != ""
    assert suffix.isascii()
    assert "2026-04-22 to 2026-07-14" in suffix
    peak = max(cell.total_commits for cell in _MAIN_DAILY)
    assert peak == 12  # the 2026-07-04 day
    assert f"peak day {peak} commits" in suffix
    assert "pulse height encodes total commits" in suffix
    assert "accent fill height encodes the day's AI-attributed share" in suffix
    assert "publishable dates only" in suffix


def test_desc_suffix_repeats_the_notice_when_no_daily_series():
    suffix = _calendar_desc_suffix(dataclasses.replace(FIXTURE_MAIN, daily=()))
    assert suffix == f" {CAL_UNPUBLISHED_TEXT}."


def test_notice_text_and_desc_addition_are_ascii():
    assert CAL_UNPUBLISHED_TEXT.isascii()
    svg = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    root = ET.fromstring(svg)
    desc_text = root.find(f"{SVG_NS}desc").text
    assert "2026-04-22 to 2026-07-14" in desc_text
    assert desc_text.isascii()


# ---------------------------------------------------------------------------
# 6. Allowed-tags sweep still passes with the pulse elements present.
# ---------------------------------------------------------------------------


def test_pulse_svg_elements_are_allowlisted_and_carry_no_active_content():
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_MAIN, theme)
        root = ET.fromstring(svg)
        tags = {el.tag for el in root.iter()}
        assert f"{SVG_NS}rect" in tags
        assert f"{SVG_NS}polygon" not in tags
        # No <g>/<animate>: the pulse ships fully static (see
        # test_pulse_is_fully_static_no_animation).
        assert f"{SVG_NS}animate" not in tags
        for el in root.iter():
            for attr in el.attrib:
                assert not attr.lower().startswith("on"), attr
                assert "href" not in attr.lower(), attr
        lowered = svg.lower()
        assert "<script" not in lowered
        assert "foreignobject" not in lowered
        assert "gradient" not in lowered


def test_pulse_is_fully_static_no_animation():
    """No entrance animation, PERMANENTLY (two failed attempts, both
    caught only by visual PDF-print inspection): a from-nothing SMIL
    entrance leaves the band invisible in every static capture - either
    because the renderer ignores SMIL (static opacity 0 = empty) or
    because a SMIL-aware print pipeline snapshots the timeline at t=0
    where the animated value (0) overrides the static value (1). The
    pulse ships static; this test fails if anyone reintroduces an
    animation without first proving a t=0-visible capture."""
    svg1 = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    svg2 = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    assert svg1 == svg2  # byte-stable
    assert "<animate" not in svg1
    assert 'opacity="0"' not in svg1


# ---------------------------------------------------------------------------
# 7. The VizStats contract is actually enforced, not just documented.
# ---------------------------------------------------------------------------


def test_daily_exceeding_provider_row_total_is_rejected_by_vizstats():
    with pytest.raises(RenderError):
        dataclasses.replace(
            FIXTURE_MAIN,
            daily=(
                DayCell(
                    date="2026-07-14",
                    counts=(DayCount(provider="openai", attributed_commits=999),),
                    total_commits=999,
                    ai_commits=999,
                ),
            ),
        )


# ---------------------------------------------------------------------------
# 8. Section label and the direct one-line legend.
# ---------------------------------------------------------------------------


def test_section_label_names_the_pulse_and_the_published_window():
    assert PULSE_LABEL_TEXT == "Daily collaboration pulse · 12-week published window"
    svg = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    assert PULSE_LABEL_TEXT in svg
    # The groups are a structural 7-day rhythm, never falsely labelled
    # as calendar weeks.
    assert "calendar week" not in svg.lower()


def test_legend_is_the_direct_one_line_statement_of_both_encodings():
    assert PULSE_LEGEND_TEXT == (
        "height = total commits · fill = AI-attributed share · publishable dates only"
    )
    for theme in THEMES.values():
        svg = _pulse_legend_svg(theme, top=0)
        assert PULSE_LEGEND_TEXT in svg
        assert f'fill="{theme.muted}"' in svg
        assert 'font-size="12"' in svg
    full = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    assert PULSE_LEGEND_TEXT in full


def test_legend_absent_when_daily_empty():
    no_daily = dataclasses.replace(FIXTURE_MAIN, daily=())
    for theme in THEMES.values():
        svg = render_summary(no_daily, theme)
        assert PULSE_LEGEND_TEXT not in svg


def test_weekday_labels_and_quarter_rails_are_gone():
    """ADR-032 removes the weekday rail and the quarter-window rails:
    no left-gutter single-letter weekday labels, no 0.35-opacity
    structural rails — the wider group gaps carry the rhythm instead."""
    svg = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    assert 'stroke-opacity="0.35"' not in svg
    root = ET.fromstring(svg)
    for node in root:
        if node.tag != f"{SVG_NS}text":
            continue
        if node.attrib.get("text-anchor") == "end" and int(node.attrib["x"]) < PADDING + 24:
            raise AssertionError(f"unexpected left-gutter label: {node.text!r}")


# ---------------------------------------------------------------------------
# 9. Month-boundary labels (derived only from stats.daily; mechanics kept).
# ---------------------------------------------------------------------------


def test_month_boundaries_empty_for_a_single_month_window():
    """Falsifiable directly (no need to build a real 84-day window): a
    contiguous date sequence that never leaves its own first month yields
    NO boundaries -- the sequence's own first month is never itself a
    'boundary'."""
    dates = tuple(datetime.date(2026, 3, 1) + datetime.timedelta(days=i) for i in range(10))
    assert _month_boundaries(dates) == ()


def test_month_boundaries_span_three_to_four_months():
    """FIXTURE_MAIN's own 84-day window (2026-04-22 to 2026-07-14)
    crosses 4 calendar months (Apr partial, May, Jun, Jul partial) --
    exactly 3 boundaries (May 1, Jun 1, Jul 1), April itself unlabeled
    since it is the window's own first, partial month."""
    labels = _month_label_columns(FIXTURE_MAIN)
    assert [label for _, label in labels] == ["May", "Jun", "Jul"]
    # Columns strictly increase (each later month starts in a later
    # group than the one before it).
    cols = [col for col, _ in labels]
    assert cols == sorted(cols)
    assert len(set(cols)) == len(cols)


def test_month_labels_empty_when_daily_empty():
    assert _month_label_columns(dataclasses.replace(FIXTURE_MAIN, daily=())) == ()


def test_month_label_collision_rule_drops_same_column_boundaries():
    """Collision rule (documented in `_dedupe_colliding_month_labels`):
    a later boundary in the SAME group column as the immediately
    preceding KEPT label is dropped outright. Exercised directly with
    synthetic input since real calendar months (>= 28 days == >= 4
    columns apart) never actually trigger it on a real 84-day window."""
    boundaries = ((2, "Jan"), (2, "Feb"), (2, "Mar"), (5, "Apr"))
    assert _dedupe_colliding_month_labels(boundaries) == ((2, "Jan"), (5, "Apr"))


def test_month_label_collision_rule_no_collision_passes_through():
    boundaries = ((1, "Jan"), (5, "Feb"), (9, "Mar"))
    assert _dedupe_colliding_month_labels(boundaries) == boundaries


def test_month_labels_render_ascii_muted_and_group_aligned():
    for theme in THEMES.values():
        svg = _pulse_month_labels_svg(FIXTURE_MAIN, theme, top=0)
        assert svg.isascii()
        assert f'fill="{theme.muted}"' in svg
        for label in ("May", "Jun", "Jul"):
            assert f">{label}<" in svg
    root = ET.fromstring(
        f'<svg xmlns="http://www.w3.org/2000/svg">'
        f'{_pulse_month_labels_svg(FIXTURE_MAIN, THEMES["github-light"], 0)}</svg>'
    )
    expected_cols = [col for col, _ in _month_label_columns(FIXTURE_MAIN)]
    xs = [int(node.attrib["x"]) for node in root]
    assert xs == [
        PULSE_X + col * PULSE_GROUP_PITCH + PULSE_GROUP_W // 2 for col in expected_cols
    ]


# ---------------------------------------------------------------------------
# 10. D4 whole-rhythm days and the 84-day window slice.
# ---------------------------------------------------------------------------


def test_d4_wider_series_band_shows_only_its_own_84_day_slice():
    # A 300-day-old AI day is valid under the D4 365-day contract but
    # must not surface anywhere in the pulse (marks, desc, months).
    old_date = "2025-09-17"  # 300 days before 2026-07-14
    daily = (
        DayCell(old_date, (DayCount(provider="anthropic", attributed_commits=5),), 5, 5),
    ) + _MAIN_DAILY
    stats = dataclasses.replace(FIXTURE_MAIN, daily=daily)
    svg = render_summary(stats, THEMES["github-light"])
    assert old_date not in svg
    assert "2026-04-22 to 2026-07-14" in svg  # window still newest-anchored


def test_out_of_window_day_does_not_leak_into_the_peak_claim():
    # A 40-commit day outside the 84-day window must not become the
    # desc's window-scoped "peak day" claim.
    old_date = "2025-09-17"
    daily = (
        DayCell(old_date, (DayCount(provider="anthropic", attributed_commits=5),), 40, 5),
    ) + _MAIN_DAILY
    stats = dataclasses.replace(FIXTURE_MAIN, daily=daily)
    suffix = _calendar_desc_suffix(stats)
    assert "peak day 12 commits" in suffix
    assert "peak day 40 commits" not in suffix


def test_pulse_moves_the_provider_table_not_the_other_way_round():
    """Layout regression: the pulse block sits between the ledger and
    the provider table, so an unpublished series shifts the table UP by
    the pulse/notice difference while the table's internal geometry
    stays fixed."""
    with_daily = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    without_daily = render_summary(
        dataclasses.replace(FIXTURE_MAIN, daily=()), THEMES["github-light"]
    )
    assert with_daily.index(PULSE_LABEL_TEXT) < with_daily.index(
        "Attributed commits by provider"
    )
    assert without_daily.index(CAL_UNPUBLISHED_TEXT) < without_daily.index(
        "Attributed commits by provider"
    )
    assert CAL_GAP_BELOW > 0


def test_marks_sit_between_month_labels_and_legend_without_dead_space():
    """The band's internal layout is contiguous: month labels above the
    marks, the shared baseline at PULSE_BASELINE_Y, the legend below,
    and the block height derived from those constants — no dead band."""
    assert PULSE_BASELINE_Y > 0
    assert PULSE_BLOCK_HEIGHT > PULSE_BASELINE_Y
    assert PULSE_BLOCK_HEIGHT < 200  # tighter than the old 84-cell grid (238)

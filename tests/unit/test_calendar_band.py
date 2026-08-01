"""Unit tests for the isometric collaboration terrain (grid geometry from
round D2/ADR-018, whole-rhythm semantics from ADR-022).

Fixtures here are built inline from `aiprofile.viz` dataclasses, same
discipline as `test_render_summary.py` (never round-tripped through
storage/aggregate) — constructing them exercises the REAL VizStats
validators (subset-of-provider-rows, window bound, slug-ascending unique
counts, date-ascending unique cells): an invalid series fails at module
import time, not just in a targeted assertion.

The terrain's ENCODING contract (height = total-commit bins, hue =
AI-share bins, provider independence) is pinned in
tests/unit/test_recruiter_card.py; this module keeps the grid-mechanics
regressions: window slicing, month labels, legend derivation, painter
determinism, float hygiene, the SMIL ban, and the honest empty states.
"""

from __future__ import annotations

import dataclasses
import datetime
import re
import xml.etree.ElementTree as ET

import pytest

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.errors import RenderError
from aiprofile.render._bins import _share_bin, _share_colors, _volume_bin
from aiprofile.render.summary_svg import (
    CAL_CAP_COMMITS,
    CAL_GAP_BELOW,
    CAL_HEIGHT,
    CAL_LABEL_TEXT,
    CAL_LEGEND_CUE_TEXT,
    CAL_NOTICE_HEIGHT,
    CAL_TILE_HH,
    CAL_UNPUBLISHED_TEXT,
    CAL_WINDOW_DAYS,
    TERRAIN_HEIGHTS,
    _calendar_cell_position,
    _calendar_desc_suffix,
    _calendar_grid_cells,
    _calendar_legend_svg,
    _calendar_month_labels_svg,
    _day_cell_svg,
    _dedupe_colliding_month_labels,
    _legend_bins,
    _month_boundaries,
    _month_label_columns,
    _panel_top,
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
# own left edge). Offsets (see the module docstring of
# `_calendar_grid_cells` for the oldest-to-newest indexing) are pinned
# here so the geometry tests below can address specific cells directly.
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


def test_empty_daily_renders_notice_not_grid_and_shrinks_the_card():
    """An unpublished daily series renders the exact CAL_UNPUBLISHED_TEXT
    notice in the terrain slot (no polygons, no legend, no month labels)
    and the card shrinks by the grid-vs-notice height difference."""
    no_daily = dataclasses.replace(FIXTURE_MAIN, daily=())
    assert card_height(FIXTURE_MAIN) - card_height(no_daily) == CAL_HEIGHT - CAL_NOTICE_HEIGHT
    assert _panel_top(FIXTURE_MAIN) - _panel_top(no_daily) == CAL_HEIGHT - CAL_NOTICE_HEIGHT
    for theme in THEMES.values():
        svg = render_summary(no_daily, theme)
        assert CAL_UNPUBLISHED_TEXT in svg
        assert CAL_LABEL_TEXT in svg  # the section label stays honest
        assert "<polygon" not in svg
        assert "<animate" not in svg
        assert CAL_LEGEND_CUE_TEXT not in svg
        assert "Jan" not in svg and "Feb" not in svg  # no stray month labels
        root = ET.fromstring(svg)  # still well-formed
        del root


# ---------------------------------------------------------------------------
# 2. Single-day series.
# ---------------------------------------------------------------------------


def test_single_day_series_populates_exactly_one_cell():
    cells = _calendar_grid_cells(FIXTURE_SINGLE_DAY)
    assert len(cells) == CAL_WINDOW_DAYS
    populated = [c for c in cells if c is not None]
    assert len(populated) == 1
    assert populated[0].date == "2026-07-14"
    # Card height is IDENTICAL to any other non-empty daily series: the
    # terrain's footprint is a fixed constant, independent of how sparse
    # the data is (only presence/absence of `daily` changes the layout).
    assert card_height(FIXTURE_SINGLE_DAY) - card_height(
        dataclasses.replace(FIXTURE_SINGLE_DAY, daily=())
    ) == CAL_HEIGHT - CAL_NOTICE_HEIGHT
    svg = render_summary(FIXTURE_SINGLE_DAY, THEMES["github-light"])
    assert "<polygon" in svg
    ET.fromstring(svg)  # well-formed


# ---------------------------------------------------------------------------
# 3. Volume-bin saturation and the flat no-data diamond.
# ---------------------------------------------------------------------------


def test_top_volume_bin_saturates_at_max_height():
    """A 12-commit day and an 8-commit day share the top volume bin, so
    both prisms render at exactly TERRAIN_HEIGHTS[-1] — never a taller,
    proportionally-scaled column that would blow the fixed geometry
    budget."""
    cells = _calendar_grid_cells(FIXTURE_MAIN)
    theme = THEMES["github-light"]
    for offset, total in ((OFFSET_BUSY, 12), (OFFSET_NEWEST, 8)):
        cell = cells[offset]
        assert cell is not None and cell.total_commits == total
        _, _, cx, cy = _calendar_cell_position(offset)
        svg = _day_cell_svg(cell, cx, cy, theme)
        top_y = cy - CAL_TILE_HH - TERRAIN_HEIGHTS[-1]
        assert f"{cx},{top_y}" in svg
    # An under-cap day (3 commits -> bin 1) renders at its own fixed bin
    # height, strictly lower than the top bin.
    low_cell = cells[OFFSET_LOW]
    assert low_cell is not None
    _, _, cx_low, cy_low = _calendar_cell_position(OFFSET_LOW)
    svg_low = _day_cell_svg(low_cell, cx_low, cy_low, theme)
    expected_h = TERRAIN_HEIGHTS[_volume_bin(3)]
    assert 0 < expected_h < TERRAIN_HEIGHTS[-1]
    assert f"{cx_low},{cy_low - CAL_TILE_HH - expected_h}" in svg_low


def test_zero_day_renders_flat_base_diamond_in_bar_track():
    """A date with no DayCell (whether it predates the series or is a
    genuine zero-activity day inside the window — both are simply absent
    from stats.daily) draws a single flat diamond in theme.bar_track, not
    a degenerate zero-height prism."""
    for theme in THEMES.values():
        empty_cell_svg = _day_cell_svg(None, 100, 100, theme)
        assert empty_cell_svg.count("<polygon") == 1
        assert f'fill="{theme.bar_track}"' in empty_cell_svg
        assert "fill-opacity" not in empty_cell_svg


def test_rendered_card_uses_share_bin_hues_not_provider_colors():
    """The terrain's hue axis is the AI-share ramp (ADR-022) — provider
    brand colors never reach the grid. The mixed 2026-06-04 day (7 AI of
    8) sits in share bin 4 despite spanning three providers."""
    theme = THEMES["github-light"]
    svg = render_summary(FIXTURE_MAIN, theme)
    colors = _share_colors(theme)
    assert _share_bin(7, 8) == 4
    cells = _calendar_grid_cells(FIXTURE_MAIN)
    mixed_svg = _day_cell_svg(cells[OFFSET_MIXED], 100, 100, theme)
    assert f'fill="{colors[4]}"' in mixed_svg
    assert mixed_svg.count("<polygon") == 3  # one prism, never a provider stack
    # The partial-share oldest day (2 AI of 3 -> bin 3) uses a mid-ramp hue.
    oldest_svg = _day_cell_svg(cells[OFFSET_OLDEST], 100, 100, theme)
    assert f'fill="{colors[_share_bin(2, 3)]}"' in oldest_svg
    del svg


# ---------------------------------------------------------------------------
# 4. Grid math determinism.
# ---------------------------------------------------------------------------


def test_grid_cell_lookup_and_positions_are_deterministic():
    assert _calendar_grid_cells(FIXTURE_MAIN) == _calendar_grid_cells(FIXTURE_MAIN)
    for offset in range(CAL_WINDOW_DAYS):
        assert _calendar_cell_position(offset) == _calendar_cell_position(offset)


def test_same_input_renders_byte_identical_calendar_markup():
    for theme in THEMES.values():
        first = render_summary(FIXTURE_MAIN, theme)
        second = render_summary(FIXTURE_MAIN, theme)
        assert first == second
        assert first.encode("utf-8") == second.encode("utf-8")


def test_polygon_points_carry_no_float_noise():
    """The coordinate-hygiene regex in test_render_summary.py does not
    reach the polygon "points" attribute (it only matches x/y/x1/y1/x2/
    y2/width/height) — this test pins the same "no float noise" invariant
    for it directly: every coordinate the terrain emits is an exact
    integer, by construction (every geometry constant is int, and the
    fixed TERRAIN_HEIGHTS bins remove the last division)."""
    pt_re = re.compile(r'<polygon points="([^"]+)"')
    coord_re = re.compile(r"-?\d+,-?\d+")
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_MAIN, theme)
        matches = pt_re.findall(svg)
        assert len(matches) > 80  # 84 cells, most with >=1 polygon
        for points_attr in matches:
            for pair in points_attr.split(" "):
                assert coord_re.fullmatch(pair), pair


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
    assert "height is total commits" in suffix
    assert "hue is the day's AI share" in suffix
    assert "publishable repositories only" in suffix


def test_desc_suffix_repeats_the_notice_when_no_daily_series():
    suffix = _calendar_desc_suffix(dataclasses.replace(FIXTURE_MAIN, daily=()))
    assert suffix == f" {CAL_UNPUBLISHED_TEXT}."


def test_calendar_label_and_desc_addition_are_ascii():
    assert CAL_LABEL_TEXT.isascii()
    assert CAL_UNPUBLISHED_TEXT.isascii()
    svg = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    root = ET.fromstring(svg)
    desc_text = root.find(f"{SVG_NS}desc").text
    assert "2026-04-22 to 2026-07-14" in desc_text
    assert desc_text.isascii()


# ---------------------------------------------------------------------------
# 6. Allowed-tags sweep still passes with the terrain elements present.
# ---------------------------------------------------------------------------


def test_new_svg_elements_are_allowlisted_and_carry_no_active_content():
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_MAIN, theme)
        root = ET.fromstring(svg)
        tags = {el.tag for el in root.iter()}
        assert f"{SVG_NS}polygon" in tags
        # No <g>/<animate>: the terrain ships fully static (see
        # test_calendar_band_is_fully_static_no_animation).
        assert f"{SVG_NS}animate" not in tags
        for el in root.iter():
            for attr in el.attrib:
                assert not attr.lower().startswith("on"), attr
                assert "href" not in attr.lower(), attr
        lowered = svg.lower()
        assert "<script" not in lowered
        assert "foreignobject" not in lowered


def test_calendar_band_is_fully_static_no_animation():
    """No entrance animation, PERMANENTLY (two failed attempts, both
    caught only by visual PDF-print inspection): a from-nothing SMIL
    entrance leaves the band invisible in every static capture - either
    because the renderer ignores SMIL (static opacity 0 = empty) or
    because a SMIL-aware print pipeline snapshots the timeline at t=0
    where the animated value (0) overrides the static value (1). The
    terrain ships static; this test fails if anyone reintroduces an
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
# 8. Legend: volume bins + share ramp (ADR-022).
# ---------------------------------------------------------------------------


def test_legend_bins_math_for_the_current_cap():
    """Falsifiable: with CAL_CAP_COMMITS == 8 today, `_legend_bins` must
    produce EXACTLY the four bins the terrain heights encode
    ("1", "2-4", "5-7", "8+") -- fails if the derivation drifts from
    `_bins._volume_bin`'s worked thresholds."""
    assert _legend_bins(8) == ((1, "1"), (4, "2-4"), (7, "5-7"), (8, "8+"))
    # The derivation and the binning function agree bin-for-bin.
    for representative, _label in _legend_bins(CAL_CAP_COMMITS):
        assert 0 <= _volume_bin(representative) <= len(TERRAIN_HEIGHTS) - 1


def test_legend_bins_resilient_to_a_cap_change():
    """Falsifiable: recomputing bins for OTHER cap values must still
    satisfy the general contract (first bin "1", last bin "{cap}+", every
    label's own numbers ASCII, no bin with low > high ever emitted) --
    proves the derivation is a real function of ``cap``, not a hand-typed
    table that happens to match cap=8."""
    for cap in (2, 3, 4, 6, 8, 12, 15):
        bins = _legend_bins(cap)
        assert bins[0] == (1, "1")
        assert bins[-1] == (cap, f"{cap}+")
        assert len(bins) <= 4
        for _, label in bins:
            assert label.isascii()
            if "-" in label:
                low, high = (int(n) for n in label.split("-"))
                assert low <= high


def test_legend_absent_when_daily_empty():
    no_daily = dataclasses.replace(FIXTURE_MAIN, daily=())
    for theme in THEMES.values():
        svg = render_summary(no_daily, theme)
        assert CAL_LEGEND_CUE_TEXT not in svg
        assert "8+" not in svg


def test_legend_states_both_encodings_ascii():
    for theme in THEMES.values():
        svg = _calendar_legend_svg(theme, top=0)
        assert svg.isascii()
        assert CAL_LEGEND_CUE_TEXT in svg
        assert "Commits" in svg
        assert "AI share" in svg
        assert "0%" in svg and "100%" in svg
        # Every share-ramp hex appears exactly as a real day prism would
        # use it (the ramp swatches carry the bin colors verbatim).
        for color in _share_colors(theme):
            assert f'fill="{color}"' in svg


def test_legend_diamonds_carry_no_float_noise():
    coord_re = re.compile(r"-?\d+,-?\d+")
    pt_re = re.compile(r'<polygon points="([^"]+)"')
    for theme in THEMES.values():
        svg = _calendar_legend_svg(theme, top=0)
        for points_attr in pt_re.findall(svg):
            for pair in points_attr.split(" "):
                assert coord_re.fullmatch(pair), pair


# ---------------------------------------------------------------------------
# 9. P2: month-boundary labels (round D3, unchanged mechanics).
# ---------------------------------------------------------------------------


def test_month_boundaries_empty_for_a_single_month_window():
    """Falsifiable directly (no need to build a real 84-day window): a
    contiguous date sequence that never leaves its own first month yields
    NO boundaries -- the sequence's own first month is never itself a
    'boundary'."""
    dates = tuple(datetime.date(2026, 3, 1) + datetime.timedelta(days=i) for i in range(10))
    assert _month_boundaries(dates) == ()


def test_month_boundaries_span_three_to_four_months():
    """FIXTURE_MAIN's own 84-day window (2026-04-22 to 2026-07-14, the D2
    fixture's documented span) crosses 4 calendar months (Apr partial,
    May, Jun, Jul partial) -- exactly 3 boundaries (May 1, Jun 1, Jul 1),
    April itself unlabeled since it is the window's own first, partial
    month."""
    labels = _month_label_columns(FIXTURE_MAIN)
    assert [label for _, label in labels] == ["May", "Jun", "Jul"]
    # Columns strictly increase (each later month starts in a later
    # column than the one before it).
    cols = [col for col, _ in labels]
    assert cols == sorted(cols)
    assert len(set(cols)) == len(cols)


def test_month_labels_empty_when_daily_empty():
    assert _month_label_columns(dataclasses.replace(FIXTURE_MAIN, daily=())) == ()


def test_month_label_collision_rule_drops_same_column_boundaries():
    """Collision rule (documented in `_dedupe_colliding_month_labels`):
    a later boundary in the SAME column as the immediately preceding KEPT
    label is dropped outright. Exercised directly with synthetic input
    since real calendar months (>= 28 days == >= 4 columns apart) never
    actually trigger it on a real 84-day window."""
    # Two boundaries collide with column 2 (a run of 3) then a genuinely
    # later one in column 5.
    boundaries = ((2, "Jan"), (2, "Feb"), (2, "Mar"), (5, "Apr"))
    assert _dedupe_colliding_month_labels(boundaries) == ((2, "Jan"), (5, "Apr"))


def test_month_label_collision_rule_no_collision_passes_through():
    boundaries = ((1, "Jan"), (5, "Feb"), (9, "Mar"))
    assert _dedupe_colliding_month_labels(boundaries) == boundaries


def test_month_labels_render_ascii_and_muted():
    for theme in THEMES.values():
        svg = _calendar_month_labels_svg(FIXTURE_MAIN, theme, top=0)
        assert svg.isascii()
        assert f'fill="{theme.muted}"' in svg
        for label in ("May", "Jun", "Jul"):
            assert f">{label}<" in svg


# ---------------------------------------------------------------------------
# 10. D4 whole-rhythm days and the 84-day window slice.
# ---------------------------------------------------------------------------


def test_d4_zero_attributed_ai_day_renders_a_neutral_prism_not_a_flat_diamond():
    """ADR-022 supersedes the D4 rule that a zero-attributed-AI day
    renders like a no-data day: the terrain charts the WHOLE rhythm, so a
    3-commit day with zero attributed AI (not provably human — the day's
    total includes unattributed commits) is a bin-1 prism in the neutral
    share-0 hue — visibly different from both a no-data day (flat track
    diamond) and an AI-share day (ramp hue)."""
    theme = THEMES["github-light"]
    zero_ai = DayCell("2026-07-14", (), 3, 0)
    none_svg = _day_cell_svg(None, 100, 100, theme)
    zero_ai_svg = _day_cell_svg(zero_ai, 100, 100, theme)
    assert zero_ai_svg != none_svg
    assert zero_ai_svg.count("<polygon") == 3
    assert f'fill="{_share_colors(theme)[0]}"' in zero_ai_svg
    assert theme.bar_track not in zero_ai_svg


def test_d4_wider_series_band_shows_only_its_own_84_day_slice():
    # A 300-day-old AI day is valid under the D4 365-day contract but
    # must not surface anywhere in the terrain (grid, desc, months).
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


def test_terrain_moves_the_provider_table_not_the_other_way_round():
    """Layout regression: the terrain block sits between the ledger and
    the provider table, so an unpublished series shifts the table UP by
    the grid/notice difference while the table's internal geometry stays
    fixed."""
    with_daily = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    without_daily = render_summary(
        dataclasses.replace(FIXTURE_MAIN, daily=()), THEMES["github-light"]
    )
    assert with_daily.index(CAL_LABEL_TEXT) < with_daily.index("Attributed commits by provider")
    assert without_daily.index(CAL_UNPUBLISHED_TEXT) < without_daily.index(
        "Attributed commits by provider"
    )
    assert CAL_GAP_BELOW > 0

"""Unit tests for the round D2 isometric daily-activity calendar band
(ADR-018, `.ai/round_d2_isometric_calendar_spec.md` "Renderer" section).

Fixtures here are built inline from `aiprofile.viz` dataclasses, same
discipline as `test_render_summary.py` (never round-tripped through
storage/aggregate) — constructing them exercises the REAL VizStats
validators (subset-of-provider-rows, window < 84 days, slug-ascending
unique counts, date-ascending unique cells): an invalid series fails at
module import time, not just in a targeted assertion.
"""

from __future__ import annotations

import dataclasses
import datetime
import re
import xml.etree.ElementTree as ET

import pytest

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.errors import RenderError
from aiprofile.render.brand import BRAND
from aiprofile.render.summary_svg import (
    CAL_CAP_COMMITS,
    CAL_GAP_ABOVE,
    CAL_GAP_BELOW,
    CAL_HEIGHT,
    CAL_LABEL_TEXT,
    CAL_LEGEND_CUE_TEXT,
    CAL_LEGEND_OPACITIES,
    CAL_MAX_STACK_PX,
    CAL_TILE_HH,
    CAL_WINDOW_DAYS,
    PANEL_GAP_ABOVE,
    _brand_fg_tint,
    _calendar_cell_position,
    _calendar_color,
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
    _rows_bottom,
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

OFFSET_OLDEST = 0  # 2026-04-22 -- amazon only (fallback-tile color; was
#   openai until round D5 gave openai a BrandSpec)
OFFSET_LOW = 23  # 2026-05-15 -- anthropic only, under cap
OFFSET_STACK = 43  # 2026-06-04 -- anthropic + google + unrecognized (3-way stack)
OFFSET_OVER_CAP = 73  # 2026-07-04 -- anthropic=10, total > CAL_CAP_COMMITS
OFFSET_NEWEST = 83  # 2026-07-14 -- amazon + anthropic, total == CAL_CAP_COMMITS exactly

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
# 1. Empty daily = byte-identical to the pre-D2 layout.
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


def test_empty_daily_omits_band_and_matches_pre_d2_geometry():
    """Confirmed failing pre-fix by construction: before `_panel_top` grew
    its `if stats.daily:` branch, ANY card (populated or not) used the
    single `_rows_bottom(stats) + PANEL_GAP_ABOVE` expression asserted
    here. Also pins that no calendar markup (polygon/label/SMIL) leaks
    into a no-daily card."""
    no_daily = dataclasses.replace(FIXTURE_MAIN, daily=())
    assert _panel_top(no_daily) == _rows_bottom(no_daily) + PANEL_GAP_ABOVE
    # The daily branch replaces the plain PANEL_GAP_ABOVE term with
    # CAL_GAP_ABOVE + CAL_HEIGHT + CAL_GAP_BELOW (see _panel_top) -- the
    # card grows by that difference, not by the raw band height alone.
    assert card_height(FIXTURE_MAIN) - card_height(no_daily) == (
        CAL_GAP_ABOVE + CAL_HEIGHT + CAL_GAP_BELOW - PANEL_GAP_ABOVE
    )
    for theme in THEMES.values():
        svg = render_summary(no_daily, theme)
        assert "<polygon" not in svg
        assert "<animate" not in svg
        assert CAL_LABEL_TEXT not in svg
        # Round D3 additions (P1 legend, P2 month labels) live entirely
        # inside the same `if stats.daily:` branch -- they must vanish
        # together with the rest of the band, not leak into a no-daily
        # card.
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
    # band's footprint is a fixed constant, independent of how sparse the
    # data is (only presence/absence of `daily` changes the layout).
    assert card_height(FIXTURE_SINGLE_DAY) - card_height(
        dataclasses.replace(FIXTURE_SINGLE_DAY, daily=())
    ) == (CAL_GAP_ABOVE + CAL_HEIGHT + CAL_GAP_BELOW - PANEL_GAP_ABOVE)
    svg = render_summary(FIXTURE_SINGLE_DAY, THEMES["github-light"])
    assert "<polygon" in svg
    ET.fromstring(svg)  # well-formed


# ---------------------------------------------------------------------------
# 3. Cap behavior.
# ---------------------------------------------------------------------------


def test_cap_behavior_saturates_at_max_stack_height():
    """A day whose total (10) exceeds CAL_CAP_COMMITS (8) renders at the
    SAME height as a day exactly at the cap (8) — proportional scaling
    stops at the cap rather than silently continuing past the card's
    fixed geometry budget. Confirmed by asserting the capped column's own
    top-face corner lands at the documented CAL_MAX_STACK_PX elevation,
    not at a taller, proportionally-scaled elevation (10/8 * 32 = 40,
    which would overflow CAL_GRID_TOP_Y and is asserted absent)."""
    cells = _calendar_grid_cells(FIXTURE_MAIN)
    over_cap_cell = cells[OFFSET_OVER_CAP]
    at_cap_cell = cells[OFFSET_NEWEST]
    assert over_cap_cell is not None and at_cap_cell is not None
    assert sum(dc.attributed_commits for dc in over_cap_cell.counts) == 10
    assert sum(dc.attributed_commits for dc in at_cap_cell.counts) == CAL_CAP_COMMITS

    theme = THEMES["github-light"]
    _, _, cx, cy = _calendar_cell_position(OFFSET_OVER_CAP)
    svg = _day_cell_svg(over_cap_cell, cx, cy, theme)
    capped_top_y = cy - CAL_TILE_HH - CAL_MAX_STACK_PX
    uncapped_proportional_top_y = cy - CAL_TILE_HH - round(CAL_MAX_STACK_PX * 10 / CAL_CAP_COMMITS)
    assert f"{cx},{capped_top_y}" in svg
    assert capped_top_y != uncapped_proportional_top_y
    assert f"{cx},{uncapped_proportional_top_y}" not in svg

    # An uncapped day (3 commits, under CAL_CAP_COMMITS) scales linearly.
    low_cell = cells[OFFSET_LOW]
    assert low_cell is not None
    _, _, cx_low, cy_low = _calendar_cell_position(OFFSET_LOW)
    svg_low = _day_cell_svg(low_cell, cx_low, cy_low, theme)
    expected_h = round(CAL_MAX_STACK_PX * 3 / CAL_CAP_COMMITS)
    assert 0 < expected_h < CAL_MAX_STACK_PX
    assert f"{cx_low},{cy_low - CAL_TILE_HH - expected_h}" in svg_low


def test_zero_day_renders_flat_base_diamond_in_bar_track():
    """A date with no DayCell (whether it predates the series or is a
    genuine zero-activity day inside the window — the spec treats both
    identically) draws a single flat diamond in theme.bar_track, not a
    degenerate zero-height column."""
    for theme in THEMES.values():
        empty_cell_svg = _day_cell_svg(None, 100, 100, theme)
        assert empty_cell_svg.count("<polygon") == 1
        assert f'fill="{theme.bar_track}"' in empty_cell_svg
        assert "fill-opacity" not in empty_cell_svg


# ---------------------------------------------------------------------------
# 4. Per-provider color mapping (branded / fallback / unrecognized).
# ---------------------------------------------------------------------------


def test_calendar_color_matches_branded_fallback_and_unrecognized_rules():
    for theme in THEMES.values():
        assert _calendar_color("anthropic", theme) == _brand_fg_tint(BRAND["anthropic"], theme)[0]
        assert _calendar_color("google", theme) == _brand_fg_tint(BRAND["google"], theme)[0]
        # amazon/aider: no BrandSpec entry -> the same fallback color the
        # provider table uses for a non-branded row. (openai moved to the
        # branded branch in round D5.)
        assert _calendar_color("openai", theme) == _brand_fg_tint(BRAND["openai"], theme)[0]
        assert _calendar_color("amazon", theme) == theme.bar_fill
        assert _calendar_color("aider", theme) == theme.bar_fill
        assert _calendar_color(UNRECOGNIZED_PROVIDER, theme) == theme.evidence_unknown
        # Branded colors are theme-specific and never equal the fallback.
        assert _calendar_color("anthropic", theme) != theme.bar_fill


def test_rendered_card_uses_the_mapped_colors_for_each_daily_provider():
    svg = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    theme = THEMES["github-light"]
    anthropic_fg = _brand_fg_tint(BRAND["anthropic"], theme)[0]
    google_fg = _brand_fg_tint(BRAND["google"], theme)[0]
    assert f'fill="{anthropic_fg}"' in svg
    assert f'fill="{google_fg}"' in svg
    assert f'fill="{theme.bar_fill}"' in svg  # amazon fallback
    assert f'fill="{theme.evidence_unknown}"' in svg  # unrecognized bucket


# ---------------------------------------------------------------------------
# 5. Grid math determinism.
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
    for it directly: every coordinate the calendar emits is an exact
    integer, by construction (every geometry constant is int, and the
    only division — the height-scaling `round()` calls — always returns
    an int)."""
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
# 6. <desc> summary (window span + peak summed provider count) and ASCII sweep.
# ---------------------------------------------------------------------------


def test_desc_suffix_states_window_span_and_peak_provider_total():
    suffix = _calendar_desc_suffix(FIXTURE_MAIN)
    assert suffix != ""
    assert suffix.isascii()
    assert "2026-04-22 to 2026-07-14" in suffix
    peak = max(sum(dc.attributed_commits for dc in cell.counts) for cell in _MAIN_DAILY)
    assert peak == 10  # the 2026-07-04 anthropic=10 day
    assert f"peak day summed provider-attributed count {peak}" in suffix
    assert "provider counts may overlap" in suffix


def test_desc_suffix_does_not_present_overlapping_provider_counts_as_unique_commits():
    overlap = dataclasses.replace(
        FIXTURE_MAIN,
        daily=(
            DayCell(
                date="2026-07-14",
                counts=(
                    DayCount(provider="anthropic", attributed_commits=1),
                    DayCount(provider="openai", attributed_commits=1),
                ),
                total_commits=1,
                ai_commits=1,
            ),
        ),
    )

    suffix = _calendar_desc_suffix(overlap)

    assert "peak day summed provider-attributed count 2" in suffix
    assert "provider counts may overlap" in suffix
    assert "peak day 2 attributed commits" not in suffix


def test_desc_suffix_empty_when_no_daily_series():
    assert _calendar_desc_suffix(dataclasses.replace(FIXTURE_MAIN, daily=())) == ""


def test_calendar_label_and_desc_addition_are_ascii():
    assert CAL_LABEL_TEXT.isascii()
    svg = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    root = ET.fromstring(svg)
    desc_text = root.find(f"{SVG_NS}desc").text
    assert "2026-04-22 to 2026-07-14" in desc_text
    assert desc_text.isascii()


# ---------------------------------------------------------------------------
# 7. Allowed-tags sweep still passes with the new elements present.
# ---------------------------------------------------------------------------


def test_new_svg_elements_are_allowlisted_and_carry_no_active_content():
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_MAIN, theme)
        root = ET.fromstring(svg)
        tags = {el.tag for el in root.iter()}
        assert f"{SVG_NS}polygon" in tags
        # No <g>/<animate>: the band ships fully static (see
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
    band ships static; this test fails if anyone reintroduces an
    animation without first proving a t=0-visible capture."""
    svg1 = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    svg2 = render_summary(FIXTURE_MAIN, THEMES["github-light"])
    assert svg1 == svg2  # byte-stable
    assert "<animate" not in svg1
    assert 'opacity="0"' not in svg1


# ---------------------------------------------------------------------------
# 8. The VizStats contract is actually enforced, not just documented.
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
# 9. P1: compact intensity legend (round D3).
# ---------------------------------------------------------------------------


def test_legend_bins_math_for_the_current_cap():
    """Falsifiable: with CAL_CAP_COMMITS == 8 today, `_legend_bins` must
    produce EXACTLY the 4 bins the round D3 spec worked through by hand
    ("1", "2-4", "5-7", "8+") -- fails if the derivation drifts from that
    worked example."""
    assert _legend_bins(8) == ((1, "1"), (4, "2-4"), (7, "5-7"), (8, "8+"))


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
    """Confirmed failing pre-fix by construction: before the `if
    stats.daily:` guard around `_calendar_svg` (round D2, still governing
    the legend since it lives inside the same band), any card would carry
    the legend markup unconditionally."""
    no_daily = dataclasses.replace(FIXTURE_MAIN, daily=())
    for theme in THEMES.values():
        svg = render_summary(no_daily, theme)
        assert CAL_LEGEND_CUE_TEXT not in svg
        assert "8+" not in svg


def test_legend_renders_with_the_band_ascii_and_muted():
    for theme in THEMES.values():
        svg = _calendar_legend_svg(theme, top=0)
        assert svg.isascii()
        assert CAL_LEGEND_CUE_TEXT in svg
        assert f'fill="{theme.muted}"' in svg
        # Every non-final bin's opacity literal appears at least once
        # (the final bin, opacity 1, is rendered with NO fill-opacity
        # attribute at all -- `_polygon`'s own has_opacity rule).
        for opacity in CAL_LEGEND_OPACITIES[:-1]:
            assert f'fill-opacity="{opacity}"' in svg


def test_legend_diamonds_carry_no_float_noise():
    coord_re = re.compile(r"-?\d+,-?\d+")
    pt_re = re.compile(r'<polygon points="([^"]+)"')
    for theme in THEMES.values():
        svg = _calendar_legend_svg(theme, top=0)
        for points_attr in pt_re.findall(svg):
            for pair in points_attr.split(" "):
                assert coord_re.fullmatch(pair), pair


# ---------------------------------------------------------------------------
# 10. P2: month-boundary labels (round D3).
# ---------------------------------------------------------------------------


def test_month_boundaries_empty_for_a_single_month_window():
    """Falsifiable directly (no need to build a real 84-day window): a
    contiguous date sequence that never leaves its own first month yields
    NO boundaries -- the sequence's own first month is never itself a
    'boundary'."""
    dates = tuple(datetime.date(2026, 3, 1) + datetime.timedelta(days=i) for i in range(10))
    assert _month_boundaries(dates) == ()


def test_month_boundaries_span_three_to_four_months():
    """FIXTURE_MAIN/FIXTURE_POPULATED's own 84-day window (2026-04-22 to
    2026-07-14, the D2 fixture's documented span) crosses 4 calendar
    months (Apr partial, May, Jun, Jul partial) -- exactly 3 boundaries
    (May 1, Jun 1, Jul 1), April itself unlabeled since it is the
    window's own first, partial month."""
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
# Round D4: the series now carries human-only days (ai_commits == 0,
# empty counts). The BAND charts AI collaboration, so such a day renders
# as the flat base diamond - byte-identical to a no-data day - and must
# never crash the stack builder. Written RED-FIRST (pre-fix:
# cell.counts[-1] IndexError).
# ---------------------------------------------------------------------------


def test_d4_human_only_day_renders_as_flat_base_diamond():
    theme = THEMES["github-light"]
    human_only = DayCell("2026-07-14", (), 3, 0)
    none_svg = _day_cell_svg(None, 100, 100, theme)
    human_svg = _day_cell_svg(human_only, 100, 100, theme)
    assert human_svg == none_svg


def test_d4_wider_series_band_shows_only_its_own_84_day_slice():
    # A 300-day-old AI day is valid under the D4 365-day contract but
    # must not surface anywhere in the band (grid, desc, months).
    old_date = "2025-09-17"  # 300 days before 2026-07-14
    daily = (
        DayCell(old_date, (DayCount(provider="anthropic", attributed_commits=5),), 5, 5),
    ) + _MAIN_DAILY
    stats = dataclasses.replace(FIXTURE_MAIN, daily=daily)
    svg = render_summary(stats, THEMES["github-light"])
    assert old_date not in svg
    assert "2026-04-22 to 2026-07-14" in svg  # window still newest-anchored

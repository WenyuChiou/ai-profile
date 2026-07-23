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
    CAL_MAX_STACK_PX,
    CAL_TILE_HH,
    CAL_WINDOW_DAYS,
    PANEL_GAP_ABOVE,
    _brand_fg_tint,
    _calendar_cell_position,
    _calendar_color,
    _calendar_desc_suffix,
    _calendar_grid_cells,
    _day_cell_svg,
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

OFFSET_OLDEST = 0  # 2026-04-22 -- openai only (fallback-tile color)
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
    DayCell(date="2026-04-22", counts=(DayCount(provider="openai", attributed_commits=2),)),
    DayCell(date="2026-05-15", counts=(DayCount(provider="anthropic", attributed_commits=3),)),
    DayCell(
        date="2026-06-04",
        counts=(
            DayCount(provider="anthropic", attributed_commits=4),
            DayCount(provider="google", attributed_commits=2),
            DayCount(provider=UNRECOGNIZED_PROVIDER, attributed_commits=1),
        ),
    ),
    DayCell(date="2026-07-04", counts=(DayCount(provider="anthropic", attributed_commits=10),)),
    DayCell(
        date="2026-07-14",
        counts=(
            DayCount(provider="amazon", attributed_commits=3),
            DayCount(provider="anthropic", attributed_commits=5),
        ),
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
        DayCell(date="2026-07-14", counts=(DayCount(provider="anthropic", attributed_commits=5),)),
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
        # openai/amazon: no BrandSpec entry -> the same fallback color the
        # provider table uses for a non-branded row.
        assert _calendar_color("openai", theme) == theme.bar_fill
        assert _calendar_color("amazon", theme) == theme.bar_fill
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
    assert f'fill="{theme.bar_fill}"' in svg  # openai / amazon fallback
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
# 6. <desc> summary (window span + peak day total) and ASCII sweep.
# ---------------------------------------------------------------------------


def test_desc_suffix_states_window_span_and_peak_day_total():
    suffix = _calendar_desc_suffix(FIXTURE_MAIN)
    assert suffix != ""
    assert suffix.isascii()
    assert "2026-04-22 to 2026-07-14" in suffix
    peak = max(sum(dc.attributed_commits for dc in cell.counts) for cell in _MAIN_DAILY)
    assert peak == 10  # the 2026-07-04 anthropic=10 day
    assert f"peak day {peak} attributed commits" in suffix


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
                ),
            ),
        )

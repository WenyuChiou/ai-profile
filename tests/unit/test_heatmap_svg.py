"""Unit tests for the round D4 collaboration heatmap card + badge
(ADR-020, `.ai/round_d4_heatmap_spec.md`).

Fixtures are built inline from `aiprofile.viz` dataclasses (never
round-tripped through storage/aggregate), same discipline as
`test_render_summary.py` — constructing them exercises the REAL VizStats
validators at import time.

REGENERATING SNAPSHOTS: the golden files under `tests/snapshots/` for the
heatmap/badge family (`heatmap_*.svg`, `badge_*.svg`) are byte-exact
UTF-8 renders of the fixtures below. If an intentional change requires
new golden files, run this module directly:

    python tests/unit/test_heatmap_svg.py

which overwrites the family's snapshots AND the docs sample assets
(`docs/assets/heatmap-sample-{light,dark}.svg`,
`docs/assets/badge-sample-{light,dark}.svg`). Inspect the diff before
committing. (The summary family keeps its own sanctioned command in
test_render_summary.py — one command per snapshot family.)
"""

from __future__ import annotations

import datetime
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.render.badge_svg import BADGE_HEIGHT, render_badge
from aiprofile.render.heatmap_svg import (
    HM_CELL,
    HM_CUE_TEXT,
    HM_EMPTY_MESSAGE,
    HM_GRID_TOP,
    HM_GRID_X,
    HM_SHARE_BIN_COUNT,
    HM_VOLUME_MIX,
    _cell_fill,
    _grid_columns,
    _lerp_hex,
    _share_bin,
    _share_colors,
    _volume_bin,
    render_heatmap,
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

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "snapshots"
ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "assets"
SVG_NS = "{http://www.w3.org/2000/svg}"
GENERATED_ON = "2026-07-14"


def _period() -> Period:
    return Period(from_date=None, to_date=None, label="All time")


# ---------------------------------------------------------------------------
# Fixture: mirrors test_render_summary.FIXTURE_POPULATED's daily series
# (deliberately duplicated, not cross-imported — each module owns its
# fixtures) plus TWO D4-specific days the summary fixture does not need:
# a human-only day (2026-06-20, hue bin 0) and a low-share day
# (2026-06-27, 1 AI of 5 -> hue bin 1). Both exercise hue bins the
# AI-only days cannot reach.
# ---------------------------------------------------------------------------

_PROVIDERS = (
    ProviderRow(provider="anthropic", display_name="Claude", attributed_commits=120,
                actor_presences=150, active_days=40),
    ProviderRow(provider="openai", display_name="OpenAI", attributed_commits=95,
                actor_presences=118, active_days=35),
    ProviderRow(provider="google", display_name="Gemini", attributed_commits=60,
                actor_presences=75, active_days=22),
    ProviderRow(provider="github", display_name="Copilot", attributed_commits=40,
                actor_presences=50, active_days=18),
    ProviderRow(provider="cursor", display_name="Cursor", attributed_commits=25,
                actor_presences=30, active_days=12),
    ProviderRow(provider=UNRECOGNIZED_PROVIDER, display_name=UNRECOGNIZED_DISPLAY,
                attributed_commits=20, actor_presences=22, active_days=9),
    ProviderRow(provider="amazon", display_name="Amazon Q", attributed_commits=10,
                actor_presences=12, active_days=5),
    ProviderRow(provider="aider", display_name="Aider", attributed_commits=5,
                actor_presences=6, active_days=3),
)

_DAILY = (
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
    DayCell(date="2026-06-20", counts=(), total_commits=2, ai_commits=0),
    DayCell(date="2026-06-27", counts=(DayCount(provider="cursor", attributed_commits=1),),
            total_commits=5, ai_commits=1),
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

FIXTURE_HEATMAP = VizStats(
    schema_version=ACE_SCHEMA_VERSION,
    period=_period(),
    totals=Totals(
        commits_scanned=520,
        ai_attributed_commits=375,
        ai_actor_presences=463,
        human_declared_commits=5,
        unknown_commits=100,
        active_ai_days=58,
    ),
    providers=_PROVIDERS,
    provider_count=7,
    evidence=EvidenceTotals(
        verified=12, declared=400, imported=0, inferred=5, unknown=46, total_records=463
    ),
    privacy=PrivacySplit(
        explicitly_publishable_commits=200,
        anonymous_aggregate_commits=320,
        includes_anonymous_aggregate=True,
    ),
    generated_on=GENERATED_ON,
    daily=_DAILY,
)

FIXTURE_EMPTY = VizStats(
    schema_version=ACE_SCHEMA_VERSION,
    period=_period(),
    totals=Totals(0, 0, 0, 0, 0, 0),
    providers=(),
    provider_count=0,
    evidence=EvidenceTotals(0, 0, 0, 0, 0, 0),
    privacy=PrivacySplit(0, 0, False),
    generated_on=GENERATED_ON,
)

CASES = {"heatmap": FIXTURE_HEATMAP, "heatmap_empty": FIXTURE_EMPTY}
BADGE_CASES = {"badge": FIXTURE_HEATMAP, "badge_zero": FIXTURE_EMPTY}


# ---------------------------------------------------------------------------
# 1. Bin math (pure integer arithmetic — no float-equality edges).
# ---------------------------------------------------------------------------


def test_share_bin_boundaries():
    assert _share_bin(0, 5) == 0
    assert _share_bin(1, 4) == 1   # exactly 25%
    assert _share_bin(1, 3) == 2   # ~33%
    assert _share_bin(2, 4) == 2   # exactly 50%
    assert _share_bin(3, 4) == 3   # exactly 75%
    assert _share_bin(4, 5) == 4   # 80%
    assert _share_bin(5, 5) == 4   # 100%
    assert _share_bin(1, 1000) == 1  # tiny nonzero share is never bin 0


def test_volume_bin_boundaries():
    assert _volume_bin(1) == 0
    assert _volume_bin(2) == 1
    assert _volume_bin(4) == 1
    assert _volume_bin(5) == 2
    assert _volume_bin(7) == 2
    assert _volume_bin(8) == 3
    assert _volume_bin(999) == 3


def test_lerp_endpoints_are_exact_theme_hexes():
    for theme in THEMES.values():
        colors = _share_colors(theme)
        assert len(colors) == HM_SHARE_BIN_COUNT
        assert colors[0] == theme.muted.upper() or colors[0] == theme.muted
        assert colors[-1].lower() == theme.accent.lower()
        assert len(set(colors)) == HM_SHARE_BIN_COUNT  # five distinct steps


def test_lerp_hex_midpoint_deterministic():
    assert _lerp_hex("#000000", "#FFFFFF", 0.5) == "#808080"
    assert _lerp_hex("#000000", "#FFFFFF", 0.0) == "#000000"
    assert _lerp_hex("#000000", "#FFFFFF", 1.0) == "#FFFFFF"


# ---------------------------------------------------------------------------
# 2. Grid derivation (clock-free, window-bounded).
# ---------------------------------------------------------------------------


def test_grid_columns_anchor_on_series_newest_not_today():
    window_start, cols = _grid_columns(_DAILY)
    assert window_start == datetime.date(2025, 7, 15)  # 2026-07-14 - 364
    assert cols in (52, 53)


def test_all_window_days_render_and_nothing_outside():
    svg = render_heatmap(FIXTURE_HEATMAP, THEMES["github-light"])
    root = ET.fromstring(svg)
    day_rects = [
        el
        for el in root.iter(f"{SVG_NS}rect")
        if el.get("width") == str(HM_CELL) and float(el.get("y", "0")) >= HM_GRID_TOP
        and float(el.get("x", "0")) >= HM_GRID_X
    ]
    # Exactly 365 day squares (legend swatches sit above HM_GRID_TOP? no —
    # legend is below; exclude by counting: 365 days + 9 legend swatches).
    assert len(day_rects) == 365 + len(HM_VOLUME_MIX) + HM_SHARE_BIN_COUNT


def test_human_only_day_gets_neutral_hue_full_row_alignment():
    theme = THEMES["github-light"]
    svg = render_heatmap(FIXTURE_HEATMAP, theme)
    # 2026-06-20: hue bin 0 (neutral), volume bin 1 (2 commits) -> the
    # solid bg-mixed neutral hex must appear as a day cell (aesthetic
    # pass: no fill-opacity anywhere - every cell is a flat hex).
    assert f'fill="{_cell_fill(theme, 0, 1)}"' in svg
    assert "fill-opacity" not in svg


def test_low_share_day_gets_bin1_hue():
    theme = THEMES["github-light"]
    svg = render_heatmap(FIXTURE_HEATMAP, theme)
    # 2026-06-27: 1 AI of 5 -> hue bin 1, volume bin 2 (5 commits).
    assert f'fill="{_cell_fill(theme, 1, 2)}"' in svg


def _luminance(hex_color):
    channels = [int(hex_color.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_cell_palette_distinct_and_visible_in_both_themes():
    # All 20 (share, volume) cell hexes per theme: pairwise distinct,
    # and every one distinguishable from the card background (>= 1.1
    # luminance ratio, the same bar the brand tints clear).
    for theme in THEMES.values():
        palette = {
            (s_bin, v_bin): _cell_fill(theme, s_bin, v_bin)
            for s_bin in range(HM_SHARE_BIN_COUNT)
            for v_bin in range(len(HM_VOLUME_MIX))
        }
        assert len(set(palette.values())) == len(palette), theme.bg
        for key, color in palette.items():
            assert _contrast(color, theme.bg) >= 1.1, (theme.bg, key, color)


def test_window_summary_line_is_window_scoped():
    svg = render_heatmap(FIXTURE_HEATMAP, THEMES["github-light"])
    total = sum(c.total_commits for c in _DAILY)
    ai = sum(c.ai_commits for c in _DAILY)
    # Aesthetic pass: the stat line is tspan-styled (counts emphasized,
    # AI share in accent) and the window moved to a right-aligned range.
    assert f">{total}</tspan>" in svg
    assert f">{ai}</tspan>" in svg
    assert "AI-assisted" in svg
    assert "2025-07-15 → 2026-07-14" in svg


def test_month_labels_derive_from_series_dates():
    svg = render_heatmap(FIXTURE_HEATMAP, THEMES["github-light"])
    for month in ("Aug", "Nov", "Feb", "Jul"):
        assert f">{month}</text>" in svg


# ---------------------------------------------------------------------------
# 3. Card structure, honesty cues, and the permanent SMIL ban.
# ---------------------------------------------------------------------------


def test_cards_are_fully_static_and_well_formed():
    for stats in (*CASES.values(), *BADGE_CASES.values()):
        for theme in THEMES.values():
            for svg in (render_heatmap(stats, theme), render_badge(stats, theme)):
                assert "<animate" not in svg and "<set" not in svg
                assert "@keyframes" not in svg
                ET.fromstring(svg)  # well-formed XML


def test_publishable_only_cue_present():
    svg = render_heatmap(FIXTURE_HEATMAP, THEMES["github-light"])
    assert HM_CUE_TEXT in svg


def test_empty_state_message_and_no_grid():
    svg = render_heatmap(FIXTURE_EMPTY, THEMES["github-light"])
    assert HM_EMPTY_MESSAGE in svg
    assert "Volume:" not in svg
    root = ET.fromstring(svg)
    small_rects = [el for el in root.iter(f"{SVG_NS}rect") if el.get("width") == str(HM_CELL)]
    assert small_rects == []


def test_a11y_title_and_desc():
    for stats in CASES.values():
        svg = render_heatmap(stats, THEMES["github-light"])
        root = ET.fromstring(svg)
        assert root.get("role") == "img"
        assert root.find(f"{SVG_NS}title") is not None
        desc = root.find(f"{SVG_NS}desc")
        assert desc is not None and "Generated 2026-07-14" in (desc.text or "")


def test_deterministic_bytes():
    for stats in CASES.values():
        for theme in THEMES.values():
            assert render_heatmap(stats, theme) == render_heatmap(stats, theme)
    for stats in BADGE_CASES.values():
        for theme in THEMES.values():
            assert render_badge(stats, theme) == render_badge(stats, theme)


# ---------------------------------------------------------------------------
# 4. Badge.
# ---------------------------------------------------------------------------


def test_badge_share_matches_summary_headline_rounding():
    svg = render_badge(FIXTURE_HEATMAP, THEMES["github-light"])
    # 375/520 = 72.1% -> "72%" under the summary card's rounding.
    assert "72% · verified by git" in svg


def test_badge_zero_state_says_no_data():
    svg = render_badge(FIXTURE_EMPTY, THEMES["github-light"])
    assert "no data" in svg
    assert "%" not in re.sub(r"%\d", "", svg)  # no fabricated share


def test_badge_geometry_is_deterministic_and_bounded():
    for theme in THEMES.values():
        svg = render_badge(FIXTURE_HEATMAP, theme)
        root = ET.fromstring(svg)
        width = int(root.get("width"))
        assert int(root.get("height")) == BADGE_HEIGHT
        assert 120 <= width <= 260  # sane flat-shield proportions


# ---------------------------------------------------------------------------
# 5. Byte-exact snapshots (same discipline as the summary family).
# ---------------------------------------------------------------------------


def _snapshot_name(kind: str, case: str, theme_name: str) -> str:
    suffix = "light" if "light" in theme_name else "dark"
    return f"{kind}_{case}_{suffix}.svg" if case else f"{kind}_{suffix}.svg"


def _render_all():
    for case, stats in CASES.items():
        for theme_name, theme in THEMES.items():
            yield _snapshot_name("", case, theme_name).lstrip("_"), render_heatmap(stats, theme)
    for case, stats in BADGE_CASES.items():
        for theme_name, theme in THEMES.items():
            yield _snapshot_name("", case, theme_name).lstrip("_"), render_badge(stats, theme)


def test_snapshots_byte_exact():
    for name, svg in _render_all():
        golden = SNAPSHOT_DIR / name
        assert golden.exists(), f"missing snapshot {name} - run this module directly to write it"
        assert svg.encode("utf-8") == golden.read_bytes(), name


def test_docs_sample_assets_match_current_renderer():
    for kind, render, stats in (
        ("heatmap-sample", render_heatmap, FIXTURE_HEATMAP),
        ("badge-sample", render_badge, FIXTURE_HEATMAP),
    ):
        for theme_name, theme in THEMES.items():
            suffix = "light" if "light" in theme_name else "dark"
            asset = ASSETS_DIR / f"{kind}-{suffix}.svg"
            assert asset.exists(), f"missing docs asset {asset.name}"
            assert render(stats, theme).encode("utf-8") == asset.read_bytes(), asset.name


if __name__ == "__main__":
    written = 0
    for name, svg in _render_all():
        (SNAPSHOT_DIR / name).write_bytes(svg.encode("utf-8"))
        written += 1
    print(f"Wrote {written} snapshot files to {SNAPSHOT_DIR}")
    samples = 0
    for kind, render, stats in (
        ("heatmap-sample", render_heatmap, FIXTURE_HEATMAP),
        ("badge-sample", render_badge, FIXTURE_HEATMAP),
    ):
        for theme_name, theme in THEMES.items():
            suffix = "light" if "light" in theme_name else "dark"
            (ASSETS_DIR / f"{kind}-{suffix}.svg").write_bytes(
                render(stats, theme).encode("utf-8")
            )
            samples += 1
    print(f"Wrote {samples} sample assets to {ASSETS_DIR}")

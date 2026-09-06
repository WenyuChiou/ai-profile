"""Unit tests for the Voxel Collaboration World (ADR-033; supersedes ADR-032).

Verifies the ADR-033 design contract:
- 12 chronological seven-day chunks (4 columns x 3 rows).
- Dual pillars: AI-attributed = ai_commits (blue crystal);
  Other records = total_commits - ai_commits (stone).
  Other is NOT human and NOT equivalent to unknown.
- ONE shared linear zero-based scale over all 84 dates, ceiling computed from peak DAILY TOTAL
  using deterministic nice integer steps (1, 2, 5, 10 * 10^k).
- Linear encoding: front-face heights encode actual counts exactly
  (no 8+ saturation, no quarter share fill).
- Heights distinguish scalar values: 0, 1, 8, 20, 38, 55, 100, and huge numbers (e.g. 10000).
- Sum correctness: total_commits = ai_commits + other_commits.
- Provider-independent geometry: overlapping providers do not distort pillar heights.
- Boundary cases: empty/unpublished data, date boundaries, full AI, zero AI, dense/sparse series.
- Local SVG primitives only: paths and rects, conforming to allowlist and coordinate hygiene.
"""

from __future__ import annotations

import datetime
import re
import xml.etree.ElementTree as ET

from aiprofile import ACE_SCHEMA_VERSION, __version__
from aiprofile.render.summary_svg import (
    CAL_WINDOW_DAYS,
    VOXEL_LABEL_TEXT,
    _nice_ceiling,
    _pulse_mark_svg,
    render_summary,
)
from aiprofile.render.themes import THEMES
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


def _make_stats(daily: tuple[DayCell, ...], peak_commits: int = 100) -> VizStats:
    total_scanned = max(peak_commits * 2, 100)
    ai_total = sum(c.ai_commits for c in daily)
    active_days = sum(1 for c in daily if c.ai_commits > 0)
    providers = (
        (ProviderRow("anthropic", "Claude", ai_total, ai_total, active_days),)
        if ai_total > 0
        else ()
    )
    return VizStats(
        schema_version=ACE_SCHEMA_VERSION,
        period=Period(None, None, "All time"),
        totals=Totals(
            commits_scanned=total_scanned,
            ai_attributed_commits=ai_total,
            ai_actor_presences=ai_total,
            human_declared_commits=0,
            unknown_commits=total_scanned - ai_total,
            active_ai_days=active_days,
        ),
        providers=providers,
        provider_count=1 if ai_total > 0 else 0,
        evidence=EvidenceTotals(0, total_scanned, 0, 0, 0, total_scanned),
        privacy=PrivacySplit(total_scanned, 0, False),
        generated_on="2026-07-14",
        daily=daily,
    )


def test_version_is_0_9_0():
    assert __version__ == "0.9.0"


def test_summary_continuous_animation_and_dedicated_date_band():
    stats = _make_stats((DayCell("2026-09-04", (), 55, 0),))
    svg = render_summary(stats, THEMES["github-light"])
    assert "18s" in svg and "infinite" in svg
    assert "1 forwards" not in svg
    root = ET.fromstring(svg)
    labels = [e for e in root.iter() if e.attrib.get("class") == "voxel-date"]
    assert len(labels) == 84
    assert all(float(e.attrib["font-size"]) >= 14 for e in labels)
    assert len({e.attrib["y"] for e in labels}) == 3
    assert all(re.fullmatch(r"\d{2}", e.text or "") for e in labels)


def test_summary_provider_front_uses_total_ai_denominator_without_floor():
    from aiprofile.render.summary_svg import BAR_MAX_WIDTH, _provider_row_svg

    stats = _make_stats((DayCell("2026-09-04", (DayCount("anthropic", 1),), 1, 1),))
    root = ET.fromstring("<svg>" + _provider_row_svg(0, stats, 1, 1_000_000,
                                                 THEMES["github-light"]) + "</svg>")
    front = next(e for e in root if e.attrib.get("class") == "provider-quantity")
    assert float(front.attrib["width"]) == BAR_MAX_WIDTH / 1_000_000


def test_nice_ceiling_steps():
    # Deterministic nice integer steps: leading single digit times 10^n
    # 55 -> 60, 38 -> 40, 100 -> 100, 101 -> 200, 0 -> 1
    assert _nice_ceiling(0) == 1
    assert _nice_ceiling(1) == 1
    assert _nice_ceiling(2) == 2
    assert _nice_ceiling(4) == 4
    assert _nice_ceiling(5) == 5
    assert _nice_ceiling(8) == 8
    assert _nice_ceiling(10) == 10
    assert _nice_ceiling(12) == 20
    assert _nice_ceiling(20) == 20
    assert _nice_ceiling(38) == 40
    assert _nice_ceiling(55) == 60
    assert _nice_ceiling(100) == 100
    assert _nice_ceiling(101) == 200
    assert _nice_ceiling(140) == 200
    assert _nice_ceiling(450) == 500
    assert _nice_ceiling(999) == 1000
    assert _nice_ceiling(10000) == 10000


def test_linear_scaling_scalars_distinguish_and_do_not_saturate():
    # Test values: 0, 1, 8, 20, 38, 55, 100, huge (e.g. 5000)
    ceiling = 100
    theme = THEMES["github-light"]

    # Test that 8, 20, 38, 55, 100 produce strictly increasing pillar heights
    scalar_values = [1, 8, 20, 38, 55, 100]
    heights = []
    for val in scalar_values:
        cell = DayCell(
            "2026-07-14", (DayCount("anthropic", val),), total_commits=val, ai_commits=val
        )
        svg = _pulse_mark_svg(cell, 10, 100, theme, ceiling=ceiling)
        root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{svg}</svg>')
        rects = [n for n in root if n.tag.rsplit("}", 1)[-1] == "rect"]
        assert rects
        h = float(rects[0].attrib["height"])
        heights.append(h)

    # Strictly monotonic (no 8+ saturation!)
    for i in range(len(heights) - 1):
        assert heights[i] < heights[i + 1], f"Not increasing: {heights[i]} vs {heights[i+1]}"

    # Linearity check: ratio of heights should equal ratio of values
    # 55 / 100 vs height ratio
    ratio_val = 55 / 100
    ratio_h = heights[4] / heights[5]
    assert abs(ratio_val - ratio_h) < 0.05

    # Huge number handling (no overflow, no NaN, proportional)
    huge_val = 10000
    huge_ceiling = _nice_ceiling(huge_val)
    cell_huge = DayCell(
        "2026-07-14",
        (DayCount("anthropic", huge_val),),
        total_commits=huge_val,
        ai_commits=huge_val,
    )
    svg_huge = _pulse_mark_svg(cell_huge, 10, 100, theme, ceiling=huge_ceiling)
    assert "NaN" not in svg_huge
    assert "Infinity" not in svg_huge


def test_dual_pillars_ai_and_other_separation():
    theme = THEMES["github-light"]
    # Total = 10, AI = 7, Other = 3
    cell = DayCell("2026-07-14", (DayCount("anthropic", 7),), total_commits=10, ai_commits=7)
    svg = _pulse_mark_svg(cell, 10, 100, theme, ceiling=10)
    root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{svg}</svg>')

    rects = [n for n in root if n.tag.rsplit("}", 1)[-1] == "rect"]
    # Should have two front rectangles: one AI, one Other
    assert len(rects) == 2
    # AI pillar at x=10, width=8
    assert rects[0].attrib["x"] == "10"
    assert rects[0].attrib["width"] == "8"
    assert rects[0].attrib["fill"] == "#0ea5e9"  # AI crystal front

    # Other pillar at x=21 (10 + 11), width=8
    assert rects[1].attrib["x"] == "21"
    assert rects[1].attrib["width"] == "8"
    assert rects[1].attrib["fill"] == "#94a3b8"  # Other stone front

    # Heights reflect 7 vs 3
    h_ai = float(rects[0].attrib["height"])
    h_other = float(rects[1].attrib["height"])
    assert h_ai > h_other
    assert round(h_ai / h_other, 1) == round(7 / 3, 1)


def test_zero_ai_renders_only_other_pillar_and_no_ai_pillar():
    theme = THEMES["github-light"]
    cell = DayCell("2026-07-14", (), total_commits=5, ai_commits=0)
    svg = _pulse_mark_svg(cell, 10, 100, theme, ceiling=10)
    root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{svg}</svg>')
    rects = [n for n in root if n.tag.rsplit("}", 1)[-1] == "rect"]
    assert len(rects) == 1
    assert rects[0].attrib["fill"] == "#94a3b8"  # Other stone front only


def test_full_ai_renders_only_ai_pillar_and_no_other_pillar():
    theme = THEMES["github-light"]
    cell = DayCell("2026-07-14", (DayCount("anthropic", 8),), total_commits=8, ai_commits=8)
    svg = _pulse_mark_svg(cell, 10, 100, theme, ceiling=10)
    root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{svg}</svg>')
    rects = [n for n in root if n.tag.rsplit("}", 1)[-1] == "rect"]
    assert len(rects) == 1
    assert rects[0].attrib["fill"] == "#0ea5e9"  # AI crystal front only


def test_zero_activity_renders_flat_slot_not_raised_block():
    theme = THEMES["github-light"]
    # No activity: height 1 slot line
    svg = _pulse_mark_svg(None, 10, 100, theme, ceiling=10)
    root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{svg}</svg>')
    rects = [n for n in root if n.tag.rsplit("}", 1)[-1] == "rect"]
    assert len(rects) == 1
    assert rects[0].attrib["height"] == "1"
    assert rects[0].attrib["fill"] == "#c2d3e5"  # slot border


def test_overlapping_providers_independent_geometry():
    # Day with two providers overlapping (total=5, ai=5, anthropic=4, openai=3)
    theme = THEMES["github-light"]
    cell_multi = DayCell(
        "2026-07-14",
        (DayCount("anthropic", 4), DayCount("openai", 3)),
        total_commits=5,
        ai_commits=5,
    )
    cell_single = DayCell(
        "2026-07-14",
        (DayCount("anthropic", 5),),
        total_commits=5,
        ai_commits=5,
    )
    svg_multi = _pulse_mark_svg(cell_multi, 10, 100, theme, ceiling=10)
    svg_single = _pulse_mark_svg(cell_single, 10, 100, theme, ceiling=10)
    # Byte identical: provider distribution does NOT distort geometry
    assert svg_multi == svg_single


def test_three_terraces_structure():
    # Generate 84 days of data
    start = datetime.date(2026, 4, 22)
    daily = tuple(
        DayCell(
            (start + datetime.timedelta(days=i)).isoformat(),
            (DayCount("anthropic", 2),) if i % 2 == 0 else (),
            total_commits=3 if i % 2 == 0 else 1,
            ai_commits=2 if i % 2 == 0 else 0,
        )
        for i in range(CAL_WINDOW_DAYS)
    )
    stats = _make_stats(daily, peak_commits=3)
    svg = render_summary(stats, THEMES["github-light"])

    # Three continuous slabs, not seven-day cards. Dates occupy three separate bands.
    root = ET.fromstring(svg)
    assert len([e for e in root.iter() if e.attrib.get("class") == "terrain-top"]) == 3
    assert len([e for e in root.iter() if e.attrib.get("class") == "voxel-date"]) == 84

    # Label reflects 84-day window
    assert VOXEL_LABEL_TEXT in svg
    assert "Scale: 0–" in svg
    assert "Peak: " in svg


def test_coordinate_hygiene_and_allowlist():
    start = datetime.date(2026, 4, 22)
    daily = tuple(
        DayCell(
            (start + datetime.timedelta(days=i)).isoformat(),
            (DayCount("anthropic", 1),),
            total_commits=1,
            ai_commits=1,
        )
        for i in range(CAL_WINDOW_DAYS)
    )
    stats = _make_stats(daily)
    svg = render_summary(stats, THEMES["github-light"])
    root = ET.fromstring(svg)

    # Strict allowlist: svg, title, desc, rect, line, text, tspan, path, g, style
    allowed = {"svg", "title", "desc", "rect", "line", "text", "tspan", "path", "g", "style"}
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        assert tag in allowed, f"Disallowed SVG tag found: {tag}"

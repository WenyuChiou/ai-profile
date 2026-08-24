"""Recruiter-facing summary card contract (ADR-025; pulse per ADR-032).

Focused RED-first contract tests for the `AI Collaboration Record`:
the recruiter-facing section order, the semantically honest 12-week
Collaboration Pulse (pulse height = total-commit bins, accent fill
height = AI-share bins, provider rows never contribute to geometry),
the exact unpublished-daily message, the explicit non-exclusive
provider note, and the summary-card type system.

Fixtures are built inline from `aiprofile.viz` dataclasses (never
round-tripped through storage/aggregate), matching this repo's test
convention — constructing them exercises the real VizStats validators
at import time.
"""

from __future__ import annotations

import dataclasses
import re
import xml.etree.ElementTree as ET

import aiprofile
from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.render import summary_svg
from aiprofile.render._bins import _share_bin, _volume_bin
from aiprofile.render.dashboard_html import render_dashboard
from aiprofile.render.summary_svg import (
    CAL_UNPUBLISHED_TEXT,
    FONT_STACK_DISPLAY,
    FONT_STACK_MONO,
    PROVIDER_NOTE_TEXT,
    PULSE_HEIGHTS,
    PULSE_LABEL_TEXT,
    PULSE_MARK_W,
    TITLE_TEXT,
    _pulse_day_cells,
    _pulse_mark_svg,
    _pulse_mark_x,
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

SVG_NS = "{http://www.w3.org/2000/svg}"
GENERATED_ON = "2026-07-14"

_PROVIDERS = (
    ProviderRow(provider="anthropic", display_name="Claude", attributed_commits=30,
                actor_presences=32, active_days=10),
    ProviderRow(provider="openai", display_name="OpenAI", attributed_commits=10,
                actor_presences=10, active_days=4),
    ProviderRow(provider="google", display_name="Gemini", attributed_commits=6,
                actor_presences=6, active_days=2),
)

# Offsets into the 84-cell timeline grid (index 83 = the series' own
# newest date, 2026-07-14). Each day exercises one contract point.
OFFSET_ONE_COMMIT_ONE_PROVIDER = 77   # 2026-07-08: total 1, ai 1, 1 provider
OFFSET_ONE_COMMIT_TWO_PROVIDERS = 78  # 2026-07-09: total 1, ai 1, 2 providers
OFFSET_ZERO_AI = 79                   # 2026-07-10: total 3, ai 0 (zero attributed AI)
OFFSET_PARTIAL_SHARE = 80             # 2026-07-11: total 6, ai 2
OFFSET_AT_TOP_BIN = 81                # 2026-07-12: total 8, ai 8
OFFSET_OVER_TOP_BIN = 82              # 2026-07-13: total 20, ai 5
OFFSET_NEWEST = 83                    # 2026-07-14: total 4, ai 1

_DAILY = (
    DayCell(date="2026-07-08", counts=(DayCount(provider="anthropic", attributed_commits=1),),
            total_commits=1, ai_commits=1),
    DayCell(
        date="2026-07-09",
        counts=(
            DayCount(provider="anthropic", attributed_commits=1),
            DayCount(provider="google", attributed_commits=1),
        ),
        total_commits=1,
        ai_commits=1,
    ),
    DayCell(date="2026-07-10", counts=(), total_commits=3, ai_commits=0),
    DayCell(date="2026-07-11", counts=(DayCount(provider="anthropic", attributed_commits=2),),
            total_commits=6, ai_commits=2),
    DayCell(date="2026-07-12", counts=(DayCount(provider="anthropic", attributed_commits=8),),
            total_commits=8, ai_commits=8),
    DayCell(date="2026-07-13", counts=(DayCount(provider="anthropic", attributed_commits=5),),
            total_commits=20, ai_commits=5),
    DayCell(date="2026-07-14", counts=(DayCount(provider="google", attributed_commits=1),),
            total_commits=4, ai_commits=1),
)

FIXTURE_TIMELINE = VizStats(
    schema_version=ACE_SCHEMA_VERSION,
    period=Period(from_date=None, to_date=None, label="All time"),
    totals=Totals(
        commits_scanned=80,
        ai_attributed_commits=40,
        ai_actor_presences=48,
        human_declared_commits=2,
        unknown_commits=38,
        active_ai_days=12,
    ),
    providers=_PROVIDERS,
    provider_count=3,
    evidence=EvidenceTotals(
        verified=0, declared=46, imported=0, inferred=0, unknown=34, total_records=80
    ),
    privacy=PrivacySplit(
        explicitly_publishable_commits=80,
        anonymous_aggregate_commits=0,
        includes_anonymous_aggregate=False,
    ),
    generated_on=GENERATED_ON,
    daily=_DAILY,
)

FIXTURE_NO_DAILY = dataclasses.replace(FIXTURE_TIMELINE, daily=())

FIXTURE_ZERO = VizStats(
    schema_version=ACE_SCHEMA_VERSION,
    period=Period(from_date=None, to_date=None, label="All time"),
    totals=Totals(0, 0, 0, 0, 0, 0),
    providers=(),
    provider_count=0,
    evidence=EvidenceTotals(0, 0, 0, 0, 0, 0),
    privacy=PrivacySplit(0, 0, False),
    generated_on=GENERATED_ON,
)


# ---------------------------------------------------------------------------
# 1. Recruiter-first identity: title and section order.
# ---------------------------------------------------------------------------


def test_card_title_is_ai_collaboration_record():
    assert TITLE_TEXT == "AI Collaboration Record"
    svg = render_summary(FIXTURE_TIMELINE, THEMES["github-light"])
    root = ET.fromstring(svg)
    title_text = root.find(f"{SVG_NS}title").text
    assert "AI Collaboration Record" in title_text
    assert FIXTURE_TIMELINE.period.label in title_text
    assert "AI Collaboration Summary" not in svg


def test_pulse_section_precedes_the_provider_ledger():
    svg = render_summary(FIXTURE_TIMELINE, THEMES["github-light"])
    assert svg.index(PULSE_LABEL_TEXT) < svg.index("Attributed commits by provider")
    # Section headings use the shared quiet marker primitive rather than an
    # accent block, keeping accent color reserved for data marks.
    root = ET.fromstring(svg)
    assert any(
        node.attrib.get("x") == "24"
        and node.attrib.get("width") == "2"
        and node.attrib.get("height") == "12"
        and node.attrib.get("rx") == "1"
        and node.attrib.get("fill") == THEMES["github-light"].border
        for node in root
        if node.tag.rsplit("}", 1)[-1] == "rect"
    )
    assert any(
        node.attrib.get("x1") == "26"
        and node.attrib.get("x2") == "38"
        and node.attrib.get("stroke") == THEMES["github-light"].border
        for node in root
        if node.tag.rsplit("}", 1)[-1] == "line"
    )
    # The pulse renders one baseline-anchored mark per window date (a
    # pulse or a 2px tick) — no 84-cell background grid, no polygons.
    baseline = summary_svg.CAL_TOP + summary_svg.PULSE_BASELINE_Y
    base_marks = [
        node
        for node in root
        if node.tag.rsplit("}", 1)[-1] == "rect"
        and node.attrib.get("width") == str(PULSE_MARK_W)
        and int(node.attrib["y"]) + int(node.attrib["height"]) == baseline
        and node.attrib.get("fill") != THEMES["github-light"].accent
    ]
    assert len(base_marks) == summary_svg.CAL_WINDOW_DAYS
    assert "<polygon" not in svg


# ---------------------------------------------------------------------------
# 2. Pulse height: DayCell.total_commits, fixed bins 1 / 2-4 / 5-7 / 8+.
# ---------------------------------------------------------------------------


def _mark_rects(cell, offset: int = 0, baseline: int = 300) -> list[dict]:
    svg = _pulse_mark_svg(cell, _pulse_mark_x(offset), baseline, THEMES["github-light"])
    return [
        node.attrib
        for node in ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{svg}</svg>')
        if node.tag.rsplit("}", 1)[-1] == "rect"
    ]


def _pulse_height(cell, offset: int) -> int:
    return int(_mark_rects(cell, offset)[0]["height"])


def test_pulse_height_uses_fixed_total_commit_bins():
    assert PULSE_HEIGHTS == (12, 24, 36, 48)
    cells = _pulse_day_cells(FIXTURE_TIMELINE)
    for offset, total in (
        (OFFSET_ONE_COMMIT_ONE_PROVIDER, 1),
        (OFFSET_ZERO_AI, 3),
        (OFFSET_PARTIAL_SHARE, 6),
        (OFFSET_AT_TOP_BIN, 8),
        (OFFSET_OVER_TOP_BIN, 20),
    ):
        cell = cells[offset]
        assert cell is not None and cell.total_commits == total
        expected_h = PULSE_HEIGHTS[_volume_bin(total)]
        assert _pulse_height(cell, offset) == expected_h


def test_pulse_top_bin_saturates_like_the_heatmap():
    cells = _pulse_day_cells(FIXTURE_TIMELINE)
    at_cap = cells[OFFSET_AT_TOP_BIN]
    over_cap = cells[OFFSET_OVER_TOP_BIN]
    assert _pulse_height(at_cap, OFFSET_AT_TOP_BIN) == PULSE_HEIGHTS[-1]
    assert _pulse_height(over_cap, OFFSET_OVER_TOP_BIN) == PULSE_HEIGHTS[-1]


def test_provider_rows_never_contribute_to_pulse_geometry():
    """A one-commit multi-provider day must render byte-identically to a
    one-commit single-provider day at the same position: only
    total_commits and the ai/total share may influence the mark."""
    cells = _pulse_day_cells(FIXTURE_TIMELINE)
    single = cells[OFFSET_ONE_COMMIT_ONE_PROVIDER]
    multi = cells[OFFSET_ONE_COMMIT_TWO_PROVIDERS]
    assert len(single.counts) == 1 and len(multi.counts) == 2
    for theme in THEMES.values():
        assert _pulse_mark_svg(single, 400, 300, theme) == _pulse_mark_svg(
            multi, 400, 300, theme
        )


def test_pulse_mark_is_flat_not_a_provider_stack():
    cells = _pulse_day_cells(FIXTURE_TIMELINE)
    # A partial-share day: exactly two rectangles (neutral pulse + accent
    # fill). A zero-AI day: exactly one neutral rectangle, no fill.
    for offset in (OFFSET_ONE_COMMIT_TWO_PROVIDERS, OFFSET_PARTIAL_SHARE):
        svg = _pulse_mark_svg(cells[offset], 400, 300, THEMES["github-light"])
        assert svg.count("<rect") == 2
        assert "<polygon" not in svg
    zero_svg = _pulse_mark_svg(cells[OFFSET_ZERO_AI], 400, 300, THEMES["github-light"])
    assert zero_svg.count("<rect") == 1


# ---------------------------------------------------------------------------
# 3. Accent fill height: the heatmap's fixed AI-share bins, from ai/total,
#    spatially mapped to 0/25/50/75/100% of the pulse height.
# ---------------------------------------------------------------------------


def test_accent_fill_height_uses_the_heatmap_share_bins():
    theme = THEMES["github-light"]
    cells = _pulse_day_cells(FIXTURE_TIMELINE)

    zero_ai = cells[OFFSET_ZERO_AI]
    assert zero_ai.ai_commits == 0
    rects = _mark_rects(zero_ai, OFFSET_ZERO_AI)
    assert len(rects) == 1 and rects[0]["fill"] == theme.muted  # no accent, never Human

    full_ai = cells[OFFSET_AT_TOP_BIN]
    assert full_ai.ai_commits == full_ai.total_commits
    rects = _mark_rects(full_ai, OFFSET_AT_TOP_BIN)
    assert rects[1]["fill"] == theme.accent
    assert int(rects[1]["height"]) == int(rects[0]["height"])  # 100% of pulse height

    partial = cells[OFFSET_PARTIAL_SHARE]  # 2 of 6 -> share bin 2 -> 50%
    assert _share_bin(2, 6) == 2
    rects = _mark_rects(partial, OFFSET_PARTIAL_SHARE)
    assert int(rects[1]["height"]) * 2 == int(rects[0]["height"])


def test_zero_attributed_ai_day_is_visible_but_never_called_human():
    """The whole-rhythm pulse shows a day with zero attributed AI
    commits as a neutral pulse (ADR-022 supersedes the AI-only band).
    Such a day is NOT provably human — `compute_daily_commit_totals`
    counts unattributed (unknown) commits as well as explicit Human-Only
    declarations in total_commits — so the card must render it without
    labelling any of it human."""
    svg = render_summary(FIXTURE_TIMELINE, THEMES["github-light"])
    cells = _pulse_day_cells(FIXTURE_TIMELINE)
    band_top = summary_svg._calendar_top(FIXTURE_TIMELINE)
    baseline = band_top + summary_svg.PULSE_BASELINE_Y
    assert (
        _pulse_mark_svg(
            cells[OFFSET_ZERO_AI],
            _pulse_mark_x(OFFSET_ZERO_AI),
            baseline,
            THEMES["github-light"],
        )
        in svg
    )
    # Unknown/unattributed is never presented as human anywhere on the card.
    assert "Unattributed commits" in svg
    assert "Human commits" not in svg


# ---------------------------------------------------------------------------
# 4. Publishable-only honesty: the exact unpublished-daily message.
# ---------------------------------------------------------------------------


def test_empty_daily_with_nonzero_totals_says_exactly_not_published():
    assert CAL_UNPUBLISHED_TEXT == "Daily activity is not published for this profile"
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_NO_DAILY, theme)
        assert CAL_UNPUBLISHED_TEXT in svg
        assert "<polygon" not in svg  # no fabricated geometry


def test_populated_daily_never_shows_the_unpublished_message():
    svg = render_summary(FIXTURE_TIMELINE, THEMES["github-light"])
    assert CAL_UNPUBLISHED_TEXT not in svg


def test_zero_state_keeps_onboarding_not_the_unpublished_message():
    svg = render_summary(FIXTURE_ZERO, THEMES["github-light"])
    assert "No AI collaboration recorded yet" in svg
    assert CAL_UNPUBLISHED_TEXT not in svg


# ---------------------------------------------------------------------------
# 5. Provider ledger: explicitly non-exclusive.
# ---------------------------------------------------------------------------


def test_provider_totals_are_explicitly_non_exclusive():
    assert "not mutually exclusive" in PROVIDER_NOTE_TEXT
    for stats in (FIXTURE_TIMELINE, FIXTURE_NO_DAILY):
        svg = render_summary(stats, THEMES["github-light"])
        assert PROVIDER_NOTE_TEXT in svg
    zero_svg = render_summary(FIXTURE_ZERO, THEMES["github-light"])
    assert PROVIDER_NOTE_TEXT not in zero_svg


# ---------------------------------------------------------------------------
# 6. Type system: fixed sizes 12/13/18/40 (v0.8.0 Signal Console) and the
#    three local stacks.
# ---------------------------------------------------------------------------


def test_summary_type_scale_is_the_fixed_five_sizes():
    for stats in (FIXTURE_TIMELINE, FIXTURE_NO_DAILY, FIXTURE_ZERO):
        for theme in THEMES.values():
            svg = render_summary(stats, theme)
            sizes = {int(n) for n in re.findall(r'font-size="(\d+)"', svg)}
            assert sizes <= {12, 13, 18, 40}, sizes


def test_hero_value_binds_to_mono_while_header_stays_display():
    """The hero figure is numeric DATA, so it renders in the mono stack;
    the card title is display type. Bound to the actual elements, not
    just substring presence anywhere in the SVG."""
    svg = render_summary(FIXTURE_TIMELINE, THEMES["github-light"])
    hero = re.search(r'<text[^>]*font-size="40"[^>]*>40</text>', svg)
    assert hero is not None, "hero value element (40px, value 40) not found"
    assert FONT_STACK_MONO in hero.group(0)
    assert FONT_STACK_DISPLAY not in hero.group(0)
    header = re.search(r'<text[^>]*font-size="18"[^>]*>AI Collaboration Record</text>', svg)
    assert header is not None, "header title element (18px) not found"
    assert FONT_STACK_DISPLAY in header.group(0)
    assert FONT_STACK_MONO not in header.group(0)


def test_summary_uses_display_and_mono_stacks_locally():
    assert FONT_STACK_DISPLAY.startswith("'IBM Plex Sans Condensed'")
    assert FONT_STACK_MONO.startswith("'IBM Plex Mono'")
    svg = render_summary(FIXTURE_TIMELINE, THEMES["github-light"])
    assert FONT_STACK_DISPLAY in svg
    assert FONT_STACK_MONO in svg
    assert "http" not in FONT_STACK_DISPLAY + FONT_STACK_MONO  # local stacks only


# ---------------------------------------------------------------------------
# 7. Dashboard alignment and the version bump.
# ---------------------------------------------------------------------------


def test_dashboard_h1_matches_the_summary_card_title():
    html = render_dashboard(FIXTURE_TIMELINE)
    assert '<h1 class="statusbar-title">AI Collaboration Record</h1>' in html
    assert "Evidence-backed AI collaboration." not in html
    assert "Show the work behind the numbers." not in html


def test_runtime_version_is_0_8_1():
    assert aiprofile.__version__ == "0.8.1"

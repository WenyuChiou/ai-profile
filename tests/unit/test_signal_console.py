"""v0.8.0 Signal Console visual contract (ADR-031).

RED-first contract tests for the coordinated redesign of the dashboard,
summary card, heatmap card, and badge. The tests pin what the redesign
promises — compact status line with an explicit *snapshot* label, core
metric strip, primary commit map, provider toolbar, evidence/provider
sidebar, accessible disclosure for definitions, transform/opacity-only
motion, one token system, a type hierarchy the static detector can see,
and recomposed SVG geometry for README-scale legibility — without
touching VizStats, provider/evidence semantics, CSP, or determinism.

Fixtures are built inline from ``aiprofile.viz`` dataclasses, matching the
repo convention; constructing them exercises the real validators.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.render import heatmap_svg, summary_svg
from aiprofile.render.badge_svg import BADGE_HEIGHT, render_badge
from aiprofile.render.dashboard_html import render_dashboard
from aiprofile.render.heatmap_svg import render_heatmap
from aiprofile.render.summary_svg import (
    FONT_STACK_DISPLAY,
    FONT_STACK_MONO,
    PADDING,
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

ROOT = Path(__file__).resolve().parents[2]
SVG_NS = "{http://www.w3.org/2000/svg}"
GENERATED_ON = "2026-07-14"

_PROVIDERS = (
    ProviderRow("anthropic", "Claude", 30, 32, 10),
    ProviderRow("openai", "OpenAI", 10, 10, 4),
    ProviderRow("google", "Gemini", 6, 6, 2),
)

_DAILY = (
    DayCell("2026-07-10", (), total_commits=3, ai_commits=0),
    DayCell("2026-07-11", (DayCount("anthropic", 2),), total_commits=6, ai_commits=2),
    DayCell("2026-07-14", (DayCount("google", 1),), total_commits=4, ai_commits=1),
)

FIXTURE = VizStats(
    schema_version=ACE_SCHEMA_VERSION,
    period=Period(None, None, "All time"),
    totals=Totals(80, 40, 48, 2, 38, 12),
    providers=_PROVIDERS,
    provider_count=3,
    evidence=EvidenceTotals(0, 46, 0, 0, 34, 80),
    privacy=PrivacySplit(80, 0, False),
    generated_on=GENERATED_ON,
    daily=_DAILY,
)

FIXTURE_ZERO = VizStats(
    schema_version=ACE_SCHEMA_VERSION,
    period=Period(None, None, "All time"),
    totals=Totals(0, 0, 0, 0, 0, 0),
    providers=(),
    provider_count=0,
    evidence=EvidenceTotals(0, 0, 0, 0, 0, 0),
    privacy=PrivacySplit(0, 0, False),
    generated_on=GENERATED_ON,
)


def _stylesheet(html: str) -> str:
    return html.split("<style>", 1)[1].split("</style>", 1)[0]


def _body(html: str) -> str:
    return html.split("<body>", 1)[1].split('<script type="application/json"', 1)[0]


# ---------------------------------------------------------------------------
# 1. Dashboard information architecture.
# ---------------------------------------------------------------------------


def test_dashboard_first_viewport_is_status_metrics_toolbar_then_commit_map():
    """DOM order is the reading, tab, and mobile order: status line, core
    metrics, provider toolbar, commit map, provider ledger, evidence,
    then the definitions disclosure. No hero, no eyebrow, no lede."""
    html = render_dashboard(FIXTURE)
    body = _body(html)
    order = [
        body.index('<header class="statusbar">'),
        body.index('<section class="metrics"'),
        body.index('id="providerFilters"'),
        body.index('id="activityCalendar"'),
        body.index('id="providerList"'),
        body.index('id="evidenceGrid"'),
        body.index('<details class="definitions"'),
        body.index('<footer class="console-foot">'),
    ]
    assert order == sorted(order)
    assert '<h1 class="statusbar-title">AI Collaboration Record</h1>' in body
    for banned in ("hero-value", "hero-panel", 'class="eyebrow"', 'class="lede"',
                   "control-deck", "masthead", "section-kicker"):
        assert banned not in html, banned


def test_dashboard_metric_strip_replaces_hero_and_duplicate_cards():
    html = render_dashboard(FIXTURE)
    body = _body(html)
    assert 'aria-label="Core collaboration metrics"' in body
    assert body.count('class="metric ') + body.count('class="metric"') == 4
    assert 'id="primaryValue"' in body
    assert 'id="presenceValue"' in body
    assert 'id="daysValue"' in body
    assert 'id="unknownValue"' in body
    # The share bar survives as a small track inside the primary metric.
    assert 'id="shareFill"' in body
    # Exactly one element carries each number: no second "ledger" copy.
    assert body.count("AI actor presences") == 1
    assert body.count("Active AI days") == 1


def test_dashboard_snapshot_date_is_prominent_and_never_claims_live_data():
    html = render_dashboard(FIXTURE)
    body = _body(html)
    assert 'id="snapshotDate"' in body
    assert "<time" in body
    assert "Snapshot" in body
    assert "static snapshot" in html.lower()
    lowered = html.lower()
    assert "real-time" not in lowered
    assert "realtime" not in lowered
    # "live" appears only inside aria-live attributes.
    assert lowered.count("live") == lowered.count("aria-live")
    # The script fills the snapshot date from the validated contract only.
    assert '$("snapshotDate").textContent = data.generated_on' in html
    assert '$("snapshotDate").setAttribute("datetime", data.generated_on)' in html


def test_dashboard_definitions_use_a_native_disclosure():
    html = render_dashboard(FIXTURE)
    body = _body(html)
    assert '<details class="definitions"' in body
    assert '<summary class="definitions-summary">' in body
    details = body.split('<details class="definitions"', 1)[1].split("</details>", 1)[0]
    assert "Unattributed is not human" in details
    assert "Provider totals may overlap" in details
    assert 'id="privacyCopy"' in details
    assert "AI-*" in details


def test_dashboard_layout_is_activity_region_plus_sidebar_then_one_column():
    css = _stylesheet(render_dashboard(FIXTURE))
    assert ".console-grid {" in css
    grid_rule = css.split(".console-grid {", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: minmax(0, 1.6fr) minmax(18rem, 0.8fr)" in grid_rule
    tablet = css.split("@media (max-width: 54rem)", 1)[1].split("@media (max-width: 38rem)", 1)[0]
    assert ".console-grid {" in tablet
    assert "grid-template-columns: minmax(0, 1fr)" in tablet
    # Metrics: 4-up on desktop, 2-up on tablet/mobile, 1-up at 22rem.
    metrics_rule = css.split(".metrics {", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: minmax(0, 1.6fr) repeat(3, minmax(0, 1fr))" in metrics_rule
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in tablet
    narrow = css.split("@media (max-width: 22rem)", 1)[1]
    assert ".metrics {" in narrow


# ---------------------------------------------------------------------------
# 2. Token system, type hierarchy, and the banned decorative shortcuts.
# ---------------------------------------------------------------------------


def test_dashboard_has_one_token_system_and_a_visible_type_hierarchy():
    css = _stylesheet(render_dashboard(FIXTURE))
    for token in ("--text-1:", "--text-2:", "--text-3:", "--text-4:", "--text-5:"):
        assert token in css, token
    rem_sizes = [float(v) for v in re.findall(r"font-size: ([0-9.]+)rem", css)]
    var_sizes = [
        float(v)
        for v in re.findall(r"--text-\d: ([0-9.]+)rem", css)
    ]
    sizes = rem_sizes + var_sizes
    assert min(sizes) >= 0.8125
    # The static detector needs the largest plain rem size to be at least
    # twice the smallest: 13px -> 28px+ between label and metric value.
    assert max(sizes) / min(sizes) >= 2.0
    # Semantic tokens exist for both schemes.
    for token in ("--canvas:", "--surface:", "--border:", "--text:", "--muted:",
                  "--accent:", "--evidence:", "--evidence-surface:", "--focus:"):
        assert css.count(token) >= 3, token  # light, dark media, dark explicit


def test_dashboard_bans_the_generic_saas_shortcuts():
    html = render_dashboard(FIXTURE)
    css = _stylesheet(html)
    assert "text-transform: uppercase" not in css
    assert "letter-spacing: 0.1" not in css  # no tracked-out kicker labels
    assert "gradient(" not in css
    assert "backdrop-filter" not in css
    assert "--shadow" not in css
    # No hairline-border + wide-shadow pairing: every box-shadow is an
    # inset focus ring or none.
    for value in re.findall(r"box-shadow:\s*([^;]+);", css):
        assert value.strip().startswith("inset 0 0 0") or value.strip() == "none", value
    # No thick side accent stripes, no oversized display.
    assert "border-inline-start: 0.25rem" not in css
    assert "border-top: 0.25rem" not in css
    assert "clamp(4.5rem" not in css
    assert "clamp(2.6rem" not in css
    # Mono is reserved for numeric data, never body copy.
    assert ".metric-label {" in css
    assert "font-family: var(--mono)" not in css.split(".metric-label {", 1)[1].split("}", 1)[0]


def test_dashboard_motion_is_transform_or_opacity_only_and_reduced_motion_wins():
    css = _stylesheet(render_dashboard(FIXTURE))
    for value in re.findall(r"transition:\s*([^;]+);", css):
        if value.strip() == "none":
            continue
        for part in value.split(","):
            prop = part.strip().split()[0]
            assert prop in {"transform", "opacity"}, value
    assert "transition: width" not in css
    assert "transition-property" not in css
    reduced = css.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "transition: none" in reduced
    assert "transform: none" in reduced
    assert "animation" not in css.split("@media (prefers-reduced-motion: reduce)", 1)[0]


def test_dashboard_keeps_visible_focus_and_status_region():
    html = render_dashboard(FIXTURE)
    css = _stylesheet(html)
    assert ":focus-visible {" in css
    assert "outline: 0.1875rem solid" in css
    assert 'role="status"' in html
    assert 'aria-pressed' in html
    assert 'aria-current' in html


def test_dashboard_zero_state_keeps_the_console_shell():
    html = render_dashboard(FIXTURE_ZERO)
    body = _body(html)
    assert '<section class="metrics"' in body
    assert '<details class="definitions"' in body
    assert "No publishable daily activity in this profile." in html


# ---------------------------------------------------------------------------
# 3. Summary card recomposition (830 wide, README-scale legibility).
# ---------------------------------------------------------------------------


def test_summary_keeps_830_width_and_raises_the_type_floor_to_12px():
    assert summary_svg.WIDTH == 830
    for stats in (FIXTURE, FIXTURE_ZERO):
        for theme in THEMES.values():
            svg = render_summary(stats, theme)
            sizes = {int(n) for n in re.findall(r'font-size="(\d+)"', svg)}
            assert sizes <= {12, 13, 18, 40}, sizes
            assert min(sizes) >= 12


def test_summary_header_is_a_status_line_with_snapshot_label():
    svg = render_summary(FIXTURE, THEMES["github-light"])
    assert f"All time · snapshot {GENERATED_ON}" in svg
    header = re.search(r'<text[^>]*font-size="18"[^>]*>AI Collaboration Record</text>', svg)
    assert header is not None
    assert FONT_STACK_DISPLAY in header.group(0)
    hero = re.search(r'<text[^>]*font-size="40"[^>]*>40</text>', svg)
    assert hero is not None
    assert FONT_STACK_MONO in hero.group(0)


def test_summary_metric_console_has_four_secondary_cells_on_one_baseline():
    svg = render_summary(FIXTURE, THEMES["github-light"])
    root = ET.fromstring(svg)
    cells = [
        node
        for node in root
        if node.tag == f"{SVG_NS}text"
        and node.attrib.get("font-size") == "18"
        and FONT_STACK_MONO in node.attrib.get("font-family", "")
    ]
    assert [c.text for c in cells] == ["12", "3", "48", "38"]
    assert len({c.attrib["y"] for c in cells}) == 1
    xs = [int(c.attrib["x"]) for c in cells]
    assert xs == sorted(xs)
    assert xs[0] > summary_svg.HERO_CELL_WIDTH + PADDING
    # Hairline separators between cells use the border token.
    separators = [
        node
        for node in root
        if node.tag == f"{SVG_NS}line"
        and node.attrib.get("y1") == str(summary_svg.METRIC_STRIP_TOP)
        and node.attrib.get("stroke") == THEMES["github-light"].border
    ]
    assert len(separators) == 4


def test_summary_daily_block_is_the_left_aligned_collaboration_pulse():
    # v0.8.1 (ADR-032) replaces the 52px-cell matrix with the pulse:
    # 6px marks, 12 groups of 7, left-aligned on the card margin.
    assert summary_svg.PULSE_MARK_W == 6
    assert summary_svg.PULSE_X == PADDING
    assert summary_svg.PULSE_X + summary_svg.PULSE_WIDTH <= summary_svg.WIDTH - PADDING
    assert summary_svg.PULSE_HEIGHTS == (12, 24, 36, 48)


# ---------------------------------------------------------------------------
# 4. Heatmap and badge.
# ---------------------------------------------------------------------------


def test_heatmap_keeps_830_width_with_snapshot_header_and_11px_floor():
    assert heatmap_svg.WIDTH == 830
    for stats in (FIXTURE, FIXTURE_ZERO):
        for theme in THEMES.values():
            svg = render_heatmap(stats, theme)
            sizes = [int(n) for n in re.findall(r'font-size="(\d+)"', svg)]
            assert min(sizes) >= 11, sizes
            assert f"All time · snapshot {GENERATED_ON}" in svg
    svg = render_heatmap(FIXTURE, THEMES["github-light"])
    header = re.search(r'<text[^>]*font-size="18"[^>]*>Commit Activity', svg)
    assert header is not None
    assert FONT_STACK_DISPLAY in header.group(0)


def test_badge_keeps_24px_height_and_adopts_the_console_mark():
    for stats in (FIXTURE, FIXTURE_ZERO):
        for theme in THEMES.values():
            svg = render_badge(stats, theme)
            root = ET.fromstring(svg)
            assert int(root.get("height")) == BADGE_HEIGHT == 24
            assert 120 <= int(root.get("width")) <= 260
            assert 'width="6" height="6"' in svg  # commit-node mark
            assert theme.chip_bg not in svg  # left plate is the canvas, not the amber chip
            assert f'fill="{theme.bg}"' in svg


# ---------------------------------------------------------------------------
# 5. Design documentation stays the source of truth.
# ---------------------------------------------------------------------------


def test_design_docs_record_the_signal_console():
    design = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
    adr = ROOT / "docs" / "decisions" / "ADR-031-signal-console.md"
    impeccable = ROOT / ".impeccable.md"
    assert "Signal Console" in design
    assert adr.exists()
    assert "Signal Console" in adr.read_text(encoding="utf-8")
    assert impeccable.exists()
    text = impeccable.read_text(encoding="utf-8")
    assert "DESIGN.md" in text
    assert "ADR-031" in text
    assert len(text.splitlines()) <= 80

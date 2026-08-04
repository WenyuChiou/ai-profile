"""Interactive dashboard renderer contract (ADR-021)."""

from __future__ import annotations

import json
import re
from dataclasses import fields
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest

import aiprofile.render.dashboard_html as dashboard_mod
from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.render.dashboard_html import render_dashboard
from aiprofile.viz import (
    DayCell,
    DayCount,
    EvidenceTotals,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
    to_json_dict,
)


def _stats() -> VizStats:
    return VizStats(
        schema_version=ACE_SCHEMA_VERSION,
        period=Period(None, None, "All time"),
        totals=Totals(
            commits_scanned=12,
            ai_attributed_commits=8,
            ai_actor_presences=9,
            human_declared_commits=1,
            unknown_commits=3,
            active_ai_days=3,
        ),
        providers=(
            ProviderRow("anthropic", "Claude", 6, 6, 2),
            ProviderRow("openai", "OpenAI", 3, 3, 1),
        ),
        provider_count=2,
        evidence=EvidenceTotals(0, 10, 0, 0, 3, 13),
        privacy=PrivacySplit(12, 0, False),
        generated_on="2026-07-02",
        daily=(
            DayCell(
                "2026-07-01",
                (DayCount("anthropic", 2), DayCount("openai", 2)),
                total_commits=4,
                ai_commits=3,
            ),
            DayCell(
                "2026-07-02",
                (DayCount("anthropic", 1),),
                total_commits=2,
                ai_commits=1,
            ),
        ),
    )


def _zero_stats() -> VizStats:
    return VizStats(
        schema_version=ACE_SCHEMA_VERSION,
        period=Period(None, None, "All time"),
        totals=Totals(0, 0, 0, 0, 0, 0),
        providers=(),
        provider_count=0,
        evidence=EvidenceTotals(0, 0, 0, 0, 0, 0),
        privacy=PrivacySplit(0, 0, False),
        generated_on="2026-07-02",
    )


def _embedded_data(html: str) -> dict:
    match = re.search(
        r'<script type="application/json" id="profileData">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


class _StrictEnoughHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []

    def error(self, message: str) -> None:  # pragma: no cover - legacy abstract hook
        self.errors.append(message)


def test_dashboard_is_deterministic_and_embeds_exact_public_contract():
    stats = _stats()
    first = render_dashboard(stats)
    second = render_dashboard(stats)

    assert first == second
    assert first.startswith("<!doctype html>")
    assert first.endswith("</html>\n")
    assert _embedded_data(first) == to_json_dict(stats)
    assert "new Date()" not in first
    assert "Date.now" not in first
    assert "Math.random" not in first


def test_dashboard_is_self_contained_and_network_closed():
    html = render_dashboard(_stats())
    parser = _StrictEnoughHtmlParser()
    parser.feed(html)

    assert parser.errors == []
    assert "default-src 'none'" in html
    assert "connect-src 'none'" in html
    assert "http://" not in html
    assert "https://" not in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "WebSocket" not in html
    assert "<iframe" not in html
    assert "<link" not in html


def test_dashboard_exposes_provider_filter_without_mixing_metric_units():
    html = render_dashboard(_stats())

    assert 'aria-label="Filter dashboard by AI provider"' in html
    assert 'selected === "all" ? data.totals.ai_attributed_commits' not in html
    assert "row ? row.attributed_commits : data.totals.ai_attributed_commits" in html
    assert "row ? row.actor_presences : data.totals.ai_actor_presences" in html
    assert "row ? row.active_days : data.totals.active_ai_days" in html
    assert "Provider totals may overlap" in html
    assert "Unattributed commits" in html
    assert "No explicit AI or human declaration recorded." in html
    assert "published\n          all-provider record" in html
    assert "unattributed commits remain all records" in html
    assert "All ACE records" in html
    assert "publishable activity only" in html
    assert "Headline aggregates combine publishable and aggregate-only activity" in html
    assert "daily calendar uses publishable activity only" in html


def test_provider_filter_reuses_controls_and_calendar_hides_other_providers():
    html = render_dashboard(_stats())
    render_body = html.split("function render() {", 1)[1].split(
        "function setTheme", 1
    )[0]

    # Selection updates existing buttons so keyboard focus is not destroyed.
    assert "renderFilters();" not in render_body
    assert "renderProviders();" not in render_body
    assert 'document.querySelectorAll(".provider-row")' in render_body
    # A provider view marks only that provider's active dates as interactive.
    assert "cell.dataset.active = String(selectedCount > 0)" in html
    assert "if (selectedCount) {" in html


def test_calendar_uses_roving_keyboard_and_touch_accessible_days():
    html = render_dashboard(_stats())

    assert 'id="activityCalendar" role="group"' in html
    assert 'document.createElement("button")' in html
    assert "let calendarFocusIndex = null" in html
    assert "? series.length - 1" in html
    assert "cell.tabIndex = index === rovingIndex ? 0 : -1" in html
    assert "calendarFocusIndex = index" in html
    assert "calendarFocusIndex = bounded" in html
    assert re.search(r'cell\.addEventListener\(\s*"focus"', html)
    assert 'cell.addEventListener("click"' in html
    assert 'cell.addEventListener("keydown", handleCalendarKeydown)' in html
    assert 'ArrowRight: 7' in html
    assert 'ArrowDown: 1' in html
    assert 'event.key === "Escape"' in html
    assert "tooltipSuppressed = event.currentTarget" in html
    assert "tooltipHoverPaused = true" in html
    assert "event.movementX || event.movementY" in html
    assert "tooltipSuppressed !== cell" in html
    assert 'cell.setAttribute("aria-describedby", "tooltip")' in html
    assert "tooltip.getBoundingClientRect().width / 2" in html
    assert "innerWidth - halfWidth - margin" in html
    assert "% share" in html
    assert "const binOpacity = [0.42, 0.62, 0.81, 1]" in html
    assert "Math.log1p" not in html
    assert "cell.dataset.level = String(level)" in html
    assert "scroller.scrollLeft = followNewest" in html
    assert "Fixed bins: 1 / 2-4 / 5-7 / 8+ selected commits." in html


def test_selected_provider_keeps_normal_text_color():
    """Provider accents identify selection without becoming body text."""
    html = render_dashboard(_stats())

    assert '.provider-row[aria-current="true"] .provider-name' not in html
    assert '.provider-row[aria-current="true"] {' in html
    assert "border-color: var(--provider-accent)" in html
    assert "background: color-mix(in srgb, var(--provider-accent) 10%, var(--surface))" in html
    assert ".provider-name {" in html
    assert "color: var(--text)" in html
    assert "button.setAttribute(\"aria-current\"" in html


def test_dashboard_has_accessible_theme_motion_and_responsive_contracts():
    html = render_dashboard(_stats())

    assert 'name="viewport"' in html
    assert 'aria-live="polite"' in html
    assert 'aria-label="Theme: auto. Activate for light theme"' in html
    assert "prefers-color-scheme: dark" in html
    assert "prefers-reduced-motion: reduce" in html
    assert "@media (max-width: 38rem)" in html
    assert "font-size: clamp(" in html
    assert "color-mix(" in html
    rem_sizes = [float(value) for value in re.findall(r"font-size: ([0-9.]+)rem", html)]
    assert rem_sizes
    assert min(rem_sizes) >= 0.8125
    assert "min-width: 20rem" not in html
    assert "html {\n      min-width: 0;" in html
    assert ".generated {\n      color: var(--muted);" in html


def test_dashboard_stylesheet_has_balanced_rule_braces():
    """A missing CSS close brace can silently swallow every following rule."""
    html = render_dashboard(_stats())
    stylesheet = html.split("<style>", 1)[1].split("</style>", 1)[0]

    assert stylesheet.count("{") == stylesheet.count("}")


def test_dashboard_uses_a_distinctive_local_typography_system():
    """The visual voice stays technical-editorial without network fonts."""
    html = render_dashboard(_stats())

    assert '--display: "IBM Plex Sans Condensed", "Aptos Display", "Segoe UI",' in html
    assert '--body: "IBM Plex Sans", "Aptos", "Segoe UI", "Noto Sans",' in html
    assert '--mono: "IBM Plex Mono", "Cascadia Mono", "SFMono-Regular",' in html
    assert "font-variant-numeric: lining-nums tabular-nums;" in html
    assert "Inter" not in html
    assert "Space Grotesk" not in html
    assert "radial-gradient(" not in html
    assert "linear-gradient(" not in html
    assert "repeating-linear-gradient(" not in html
    assert ".hero-panel::after" not in html
    assert ".section-kicker::before" in html
    assert "background: var(--border-strong);" in html
    assert "border-inline-start: 0.25rem solid var(--warning);" in html
    assert "background: var(--canvas);" in html
    assert ".hero-panel {" in html
    assert "border-top: 0.25rem solid var(--active-accent, var(--accent));" in html
    assert "font-src 'none'" in html


def test_provider_filters_use_local_glyphs_with_visible_text_labels():
    """Provider choice is recognizable without making color carry the meaning."""
    html = render_dashboard(_stats())

    assert "const providerGlyphs = {" in html
    assert "function providerIcon(slug, label, variant)" in html
    assert 'providerIcon(row.provider, row.display_name, "filter")' in html
    assert 'providerIcon(row.provider, row.display_name, "row")' in html
    assert "document.createElementNS(SVG_NS, \"path\")" in html
    assert "document.createTextNode(row.display_name)" in html
    assert ".provider-icon--row {" in html


def test_mobile_provider_filters_wrap_without_horizontal_scrolling():
    html = render_dashboard(_stats())
    mobile_css = html.split("@media (max-width: 38rem)", 1)[1]

    assert "grid-template-columns: repeat(auto-fit, minmax(5.25rem, 1fr))" in mobile_css
    assert "grid-template-columns: minmax(0, 1fr)" in mobile_css
    assert "overflow-x: visible" in mobile_css
    assert "width: 100%" in mobile_css
    assert "padding-inline: var(--space-2)" in mobile_css


def test_narrow_22rem_reflow_prevents_zoom_overflow():
    """200%-zoom blocker (v0.4.8 visual review): at effective widths of
    145-195 CSS px the body expanded to 209px. The 22rem narrow-reflow
    rule must collapse the filters to one column, tighten panel padding,
    contain/wrap every unbreakable text run, and keep ONLY the calendar's
    intentional horizontal scroller."""
    html = render_dashboard(_stats())
    narrow = html.split("@media (max-width: 22rem)", 1)[1].split(
        "@media (pointer: coarse)", 1
    )[0]
    # Filters collapse to a single column.
    assert ".filters {" in narrow
    assert "grid-template-columns: minmax(0, 1fr)" in narrow
    assert "repeat(2, minmax(0, 1fr))" not in narrow
    # Panel padding tightens to the 1rem step.
    assert ".hero-panel," in narrow
    assert ".notes-panel {" in narrow
    assert "padding: var(--space-4)" in narrow
    # Shrink containment and wrapping for unbreakable runs.
    assert "min-width: 0" in narrow
    assert "max-width: 100%" in narrow
    assert "overflow-wrap: anywhere" in narrow
    for selector in (
        ".panel-title",
        ".panel-meta",
        ".section-kicker",
        ".provider-name",
        ".provider-detail",
        ".evidence-item",
    ):
        assert selector in narrow, selector
    assert ".provider-row-head," in narrow
    assert ".legend-scale" in narrow
    assert "flex-wrap: wrap" in narrow
    # Evidence heading stacks as a grid with left-aligned meta.
    assert ".evidence-panel .panel-heading" in narrow
    assert "display: grid" in narrow
    assert "text-align: left" in narrow
    # The calendar's horizontal scroller is intentional and untouched.
    assert ".calendar-scroll" not in narrow


def test_theme_toggle_accessible_name_includes_state_and_next_action():
    """The button visibly reads `Theme: <state>`; its accessible name must
    contain that visible text (WCAG label-in-name) plus the next action,
    and setTheme() must keep it in sync across the auto/light/dark cycle."""
    html = render_dashboard(_stats())
    assert 'aria-label="Change color theme"' not in html
    assert 'aria-label="Theme: auto. Activate for light theme"' in html
    assert (
        'const nextTheme = next === "auto" ? "light" : next === "light" ? "dark" : "auto";'
        in html
    )
    assert "`Theme: ${next}. Activate for ${nextTheme} theme`" in html
    assert 'setAttribute("aria-label"' in html


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92
        if value <= 0.04045
        else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    high, low = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (high + 0.05) / (low + 0.05)


_DARK_MARK_SURFACE = "#111923"


@pytest.mark.parametrize(
    "accent",
    [
        "#0969da",
        "#1a7f37",
        "#bf8700",
        "#8250df",
        "#cf222e",
        "#1f6feb",
        "#1f883d",
        "#9a6700",
        "#bc4c00",
        "#6e7681",
        "#6e7781",
    ],
)
def test_provider_and_evidence_accents_clear_three_to_one_in_both_themes(accent):
    assert _contrast(accent, "#fbfdff") >= 3
    assert _contrast(accent, _DARK_MARK_SURFACE) >= 3
    if accent not in {"#bf8700", "#6e7781"}:
        # Provider accents can become the large hero value, so validate the
        # lightest rendered pastel-gradient pixel rather than only a flat token.
        assert _contrast(accent, "#edf9ff") >= 3


def test_dark_mark_surfaces_use_the_validated_contrast_background():
    html = render_dashboard(_stats())

    assert html.count(f"--surface: {_DARK_MARK_SURFACE};") == 2
    assert html.count(f"--grid-empty: {_DARK_MARK_SURFACE};") == 2


@pytest.mark.parametrize(
    ("foreground", "background"),
    [
        ("#172033", "#fbfdff"),
        ("#52647a", "#fbfdff"),
        ("#eff6ff", _DARK_MARK_SURFACE),
        ("#b5c7da", _DARK_MARK_SURFACE),
    ],
)
def test_primary_and_muted_text_clear_wcag_aa(foreground, background):
    assert _contrast(foreground, background) >= 4.5


@pytest.mark.parametrize(
    ("active_border", "empty_cell"),
    [
        ("#52647a", "#e5eef7"),
        ("#b5ddff", _DARK_MARK_SURFACE),
    ],
)
def test_active_calendar_boundaries_clear_three_to_one(active_border, empty_cell):
    assert _contrast(active_border, empty_cell) >= 3


def test_calendar_marks_use_contrasting_boundaries_not_translucent_borders():
    html = render_dashboard(_stats())

    assert "--calendar-active-border: #52647a" in html
    assert "--calendar-active-border: #b5ddff" in html
    assert "border-color: var(--calendar-active-border)" in html
    assert "cell.style.borderColor = rgba" not in html


def test_dashboard_zero_state_is_valid_and_keeps_the_empty_daily_series():
    html = render_dashboard(_zero_stats())
    payload = _embedded_data(html)

    assert payload["daily"] == []
    assert payload["providers"] == []
    assert "No publishable daily activity in this profile." in html


def test_script_data_terminator_is_escaped_defense_in_depth(monkeypatch):
    monkeypatch.setattr(
        dashboard_mod,
        "to_json_dict",
        lambda _stats: {"future_field": "</script><script>alert(1)</script>&"},
    )

    html = dashboard_mod.render_dashboard(_zero_stats())

    assert "</script><script>alert(1)</script>" not in html
    assert "\\u003c/script\\u003e" in html
    assert "\\u0026" in html


@pytest.mark.parametrize("constructor", [object, dict, list])
def test_dashboard_rejects_non_vizstats_inputs(constructor):
    with pytest.raises(TypeError, match="exact VizStats"):
        render_dashboard(constructor())


def test_dashboard_rejects_fully_shaped_duck_type_with_private_canary():
    stats = _stats()
    fake = SimpleNamespace(
        **{field.name: getattr(stats, field.name) for field in fields(stats)}
    )
    fake.period = SimpleNamespace(
        from_date=stats.period.from_date,
        to_date=stats.period.to_date,
        label="PRIVATE_REPO_CANARY_X9",
    )

    with pytest.raises(TypeError, match="exact VizStats"):
        render_dashboard(fake)

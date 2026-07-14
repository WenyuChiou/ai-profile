"""Deterministic summary card SVG renderer (ADR-010, architecture.md section 9).

`render_summary(stats, theme)` is a pure function of its two arguments: no
clock reads, no randomness, no locale-dependent formatting. Byte-identical
output for identical inputs is a pinned test (mvp.md section 7 test 11).

Layout is dynamic-but-deterministic: the card height is a pure function of
the data (number of provider rows, overflow line, zero state) so sparse
profiles never show a dead band — see `card_height`.

Module graph is enforced by a separate unit test (architecture.md section 2):
this module may import stdlib plus `aiprofile.viz`, `aiprofile.render.themes`,
and `aiprofile.errors` only — never storage, gitio, schema, or sqlite3.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..viz import Totals, VizStats
from .themes import Theme

# ---------------------------------------------------------------------------
# Layout constants (ADR-010: fixed constants, no template engine).
# ---------------------------------------------------------------------------

WIDTH = 830
PADDING = 24
RADIUS = 8

FONT_STACK = "-apple-system, 'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif"

TITLE_TEXT = "AI Collaboration Summary"
MAX_PROVIDER_ROWS = 6

# Header: accent sparkle glyph + title + right-aligned period label.
HEADER_TEXT_Y = 38
GLYPH_CX = 32
GLYPH_CY = 32
TITLE_X = 48
DIVIDER1_Y = 56

# Primary metric row (three hero tiles, accent values).
METRIC_CENTERS = (172, 415, 658)
METRIC_VALUE_Y = 102
METRIC_LABEL_Y = 124
METRIC_VALUE_SIZE = 28

# Secondary line (muted labels, text-colored numbers via tspans).
SECONDARY_Y = 154

# Provider table.
TABLE_LABEL_Y = 186
ROWS_TOP = 200
ROW_HEIGHT = 26
NAME_X = PADDING
NAME_WIDTH = 150
BAR_X = 186
COUNT_X = WIDTH - PADDING  # right anchor for "count · pct%"
BAR_MAX_WIDTH = 498  # COUNT_X - reserved count column (110) - gap (12) - BAR_X
BAR_HEIGHT = 12
NAME_FONT_SIZE = 13
COUNT_FONT_SIZE = 13

MORE_LINE_EXTRA = 20  # vertical room for the "+N more" line when present

# Chips.
CHIP_GAP_ABOVE = 16
CHIP_HEIGHT = 22
CHIP_RADIUS = 11
CHIP_PAD_X = 10
CHIP_GAP = 8
CHIP_FONT_SIZE = 11
CHIP_ROW_STEP = 30
EVIDENCE_PREFIX = "Evidence (events)"
EVIDENCE_PREFIX_GAP = 10

# Footer.
FOOTER_GAP_ABOVE = 16
FOOTER1_OFFSET = 22
FOOTER2_OFFSET = 38
FOOTER_BOTTOM_PAD = 16

FOOTNOTE = "One commit may include several AI participation events."
ZERO_MESSAGE = "No AI collaboration recorded yet"
ZERO_HINT = "Add AI-* trailers or scan a repository with AI co-authored commits."
ZERO_MESSAGE_Y = 118
ZERO_HINT_Y = 142
ZERO_BODY_BOTTOM = 162

# ---------------------------------------------------------------------------
# Conservative character-width table (ADR-010: no font dependency at render
# time). Widths are fractions of the font-size, tuned to over-estimate
# slightly so truncation stays inside the column.
# ---------------------------------------------------------------------------

_WIDE_CHARS = frozenset("mMW@%&")
_NARROW_CHARS = frozenset("iIl.,:;'`|!ftj ()[]·")


def _char_width(ch: str) -> float:
    if ch in _WIDE_CHARS:
        return 0.82
    if ch in _NARROW_CHARS:
        return 0.30
    if ch.isupper():
        return 0.66
    if ch.isdigit():
        return 0.56
    return 0.52


def _text_width(s: str, font_size: int) -> float:
    """Estimated pixel width of ``s`` rendered at ``font_size``."""
    return sum(_char_width(ch) for ch in s) * font_size


def _truncate(s: str, max_width: float, font_size: int) -> str:
    """Ellipsis-truncate ``s`` (raw, pre-escape) to fit ``max_width`` px.

    Operates on the raw string so escaping (applied afterwards by the
    caller) never splits an XML entity mid-way.
    """
    if _text_width(s, font_size) <= max_width:
        return s
    ellipsis = "…"
    for end in range(len(s), 0, -1):
        candidate = s[:end].rstrip() + ellipsis
        if _text_width(candidate, font_size) <= max_width:
            return candidate
    return ellipsis


# ---------------------------------------------------------------------------
# Small SVG element builders (pure string composition, ADR-010).
# ---------------------------------------------------------------------------


def _text(
    x: float,
    y: float,
    content: str,
    *,
    size: int,
    fill: str,
    weight: int = 400,
    anchor: str = "start",
    escaped: bool = False,
) -> str:
    body = content if escaped else escape(content)
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT_STACK}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{body}</text>'
    )


def _tspan(content: str, *, fill: str, weight: int = 400) -> str:
    return f'<tspan fill="{fill}" font-weight="{weight}">{escape(content)}</tspan>'


def _rect(
    x: float, y: float, w: float, h: float, *, fill: str, rx: float = 0, stroke: str | None = None
) -> str:
    stroke_attr = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{stroke_attr}/>'


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}"/>'


def _sparkle(cx: float, cy: float, fill: str) -> str:
    """Four-point sparkle glyph (pure geometry — no external icon assets,
    proposal section 22: no provider logos)."""
    r, k = 8, 2.2
    points = (
        f"{cx},{cy - r} {cx + k},{cy - k} {cx + r},{cy} {cx + k},{cy + k} "
        f"{cx},{cy + r} {cx - k},{cy + k} {cx - r},{cy} {cx - k},{cy - k}"
    )
    return f'<polygon points="{points}" fill="{fill}"/>'


# ---------------------------------------------------------------------------
# Layout helpers (all pure functions of the data).
# ---------------------------------------------------------------------------


def _is_zero_state(totals: Totals) -> bool:
    return (
        totals.commits_scanned == 0
        and totals.ai_attributed_commits == 0
        and totals.ai_participation_events == 0
        and totals.human_declared_commits == 0
        and totals.unknown_commits == 0
        and totals.active_ai_days == 0
    )


def _visible_rows(stats: VizStats) -> int:
    return min(len(stats.providers), MAX_PROVIDER_ROWS)


def _has_more_line(stats: VizStats) -> bool:
    return len(stats.providers) > MAX_PROVIDER_ROWS


def _chips_top(stats: VizStats) -> int:
    bottom = ROWS_TOP + _visible_rows(stats) * ROW_HEIGHT
    if _has_more_line(stats):
        bottom += MORE_LINE_EXTRA
    return bottom + CHIP_GAP_ABOVE


def card_height(stats: VizStats) -> int:
    """Deterministic card height: a pure function of the data shape."""
    if _is_zero_state(stats.totals):
        divider2_y = ZERO_BODY_BOTTOM
    else:
        divider2_y = _chips_top(stats) + CHIP_ROW_STEP + CHIP_HEIGHT + FOOTER_GAP_ABOVE
    return divider2_y + FOOTER2_OFFSET + FOOTER_BOTTOM_PAD


def _desc_text(stats: VizStats, zero_state: bool) -> str:
    if zero_state:
        return f"No AI collaboration recorded yet. Generated {stats.generated_on}."
    t = stats.totals
    return (
        f"{t.ai_attributed_commits} AI-attributed commits, "
        f"{t.ai_participation_events} AI participation events across "
        f"{t.active_ai_days} active AI days, {stats.provider_count} AI providers. "
        f"Generated {stats.generated_on}."
    )


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------


def _secondary_line_svg(stats: VizStats, theme: Theme) -> str:
    spans = (
        _tspan("Unique commits scanned ", fill=theme.muted)
        + _tspan(str(stats.totals.commits_scanned), fill=theme.text, weight=600)
        + _tspan("   ·   AI providers ", fill=theme.muted)
        + _tspan(str(stats.provider_count), fill=theme.text, weight=600)
        + _tspan("   ·   Unknown commits ", fill=theme.muted)
        + _tspan(str(stats.totals.unknown_commits), fill=theme.text, weight=600)
    )
    return (
        f'<text x="{PADDING}" y="{SECONDARY_Y}" font-family="{FONT_STACK}"'
        f' font-size="12" text-anchor="start">{spans}</text>'
    )


def _provider_row_svg(
    index: int, stats: VizStats, max_attributed: int, denominator: int, theme: Theme
) -> str:
    row = stats.providers[index]
    row_top = ROWS_TOP + index * ROW_HEIGHT
    bar_y = row_top + 6
    text_y = row_top + 17

    name = _truncate(row.display_name, NAME_WIDTH, NAME_FONT_SIZE)
    elements = [
        _text(NAME_X, text_y, name, size=NAME_FONT_SIZE, fill=theme.text),
        _rect(BAR_X, bar_y, BAR_MAX_WIDTH, BAR_HEIGHT, fill=theme.bar_track, rx=6),
    ]
    if max_attributed > 0 and row.attributed_commits > 0:
        bar_w = round(BAR_MAX_WIDTH * row.attributed_commits / max_attributed)
        bar_w = max(bar_w, BAR_HEIGHT)  # keep the pill shape readable
        elements.append(_rect(BAR_X, bar_y, bar_w, BAR_HEIGHT, fill=theme.bar_fill, rx=6))

    count_spans = _tspan(str(row.attributed_commits), fill=theme.text, weight=600)
    if denominator > 0:
        pct = round(100 * row.attributed_commits / denominator)
        count_spans += _tspan(f" · {pct}%", fill=theme.muted)
    elements.append(
        f'<text x="{COUNT_X}" y="{text_y}" font-family="{FONT_STACK}"'
        f' font-size="{COUNT_FONT_SIZE}" text-anchor="end">{count_spans}</text>'
    )
    return "\n".join(elements)


def _chip(x: float, y: float, content: str, theme: Theme, *, text_fill: str) -> tuple[str, int]:
    """One rounded chip at (x, y); returns (svg, next_x).

    Coordinates are rounded to integers on entry so shipped SVG never
    carries double-precision noise (gate-review P1, 2026-07-14; pinned by
    test_coordinate_hygiene_no_float_noise)."""
    x = round(x)
    text_w = _text_width(content, CHIP_FONT_SIZE)
    chip_w = round(text_w + 2 * CHIP_PAD_X)
    svg = (
        _rect(x, y, chip_w, CHIP_HEIGHT, fill=theme.chip_bg, rx=CHIP_RADIUS, stroke=theme.border)
        + _text(
            x + CHIP_PAD_X,
            y + 15,
            content,
            size=CHIP_FONT_SIZE,
            fill=text_fill,
        )
    )
    return svg, x + chip_w + CHIP_GAP


def _evidence_chips_svg(stats: VizStats, theme: Theme, top: int) -> str:
    e = stats.evidence
    labels = [f"declared {e.declared}", f"unknown {e.unknown}"]
    for label, n in (("verified", e.verified), ("imported", e.imported), ("inferred", e.inferred)):
        if n:
            labels.append(f"{label} {n}")

    parts = [
        _text(PADDING, top + 15, EVIDENCE_PREFIX, size=CHIP_FONT_SIZE, fill=theme.muted)
    ]
    x = PADDING + _text_width(EVIDENCE_PREFIX, CHIP_FONT_SIZE) + EVIDENCE_PREFIX_GAP
    for label in labels:
        chip_svg, x = _chip(x, top, label, theme, text_fill=theme.text)
        parts.append(chip_svg)
    return "\n".join(parts)


def _privacy_chips_svg(stats: VizStats, theme: Theme, top: int) -> str:
    p = stats.privacy
    if p.includes_private:
        primary = "Includes private activity (aggregate-only)"
    else:
        primary = "Public repositories only"
    parts = []
    chip_svg, x = _chip(PADDING, top, primary, theme, text_fill=theme.text)
    parts.append(chip_svg)
    if p.includes_private and p.public_commits > 0:
        split = f"public {p.public_commits} · private {p.private_aggregate_commits}"
        chip_svg, _ = _chip(x, top, split, theme, text_fill=theme.muted)
        parts.append(chip_svg)
    return "\n".join(parts)


def render_summary(stats: VizStats, theme: Theme) -> str:
    """Render the summary card as SVG markup (ADR-010, architecture.md section 9).

    Pure function of ``(stats, theme)``: no clock, no randomness, fixed
    decimal formatting, byte-identical output for identical inputs.
    """
    zero_state = _is_zero_state(stats.totals)
    height = card_height(stats)

    title = escape(f"{TITLE_TEXT} — {stats.period.label}")
    desc = escape(_desc_text(stats, zero_state))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-labelledby="aiprofileSummaryTitle aiprofileSummaryDesc">',
        f'<title id="aiprofileSummaryTitle">{title}</title>',
        f'<desc id="aiprofileSummaryDesc">{desc}</desc>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="{RADIUS}" '
        f'fill="{theme.bg}" stroke="{theme.border}" stroke-width="1"/>',
    ]

    # Header: sparkle glyph + title + period label.
    parts.append(_sparkle(GLYPH_CX, GLYPH_CY, theme.accent))
    parts.append(
        _text(TITLE_X, HEADER_TEXT_Y, TITLE_TEXT, size=18, weight=600, fill=theme.title)
    )
    parts.append(
        _text(
            WIDTH - PADDING,
            HEADER_TEXT_Y,
            stats.period.label,
            size=12,
            fill=theme.muted,
            anchor="end",
        )
    )
    parts.append(_line(PADDING, DIVIDER1_Y, WIDTH - PADDING, DIVIDER1_Y, stroke=theme.border))

    if zero_state:
        parts.append(
            _text(
                WIDTH // 2,
                ZERO_MESSAGE_Y,
                ZERO_MESSAGE,
                size=14,
                weight=600,
                fill=theme.muted,
                anchor="middle",
            )
        )
        parts.append(
            _text(WIDTH // 2, ZERO_HINT_Y, ZERO_HINT, size=12, fill=theme.muted, anchor="middle")
        )
        divider2_y = ZERO_BODY_BOTTOM
    else:
        # Primary metric row (hero values in accent — the card's focal layer).
        metrics = (
            (stats.totals.ai_attributed_commits, "AI-attributed commits"),
            (stats.totals.ai_participation_events, "AI participation events"),
            (stats.totals.active_ai_days, "Active AI days"),
        )
        for center_x, (value, label) in zip(METRIC_CENTERS, metrics, strict=True):
            parts.append(
                _text(
                    center_x,
                    METRIC_VALUE_Y,
                    str(value),
                    size=METRIC_VALUE_SIZE,
                    weight=700,
                    fill=theme.accent,
                    anchor="middle",
                )
            )
            parts.append(
                _text(center_x, METRIC_LABEL_Y, label, size=12, fill=theme.muted, anchor="middle")
            )

        parts.append(_secondary_line_svg(stats, theme))

        # Provider table with an explicit percentage denominator
        # (proposal section 26 rule 6: percentages state their denominator).
        parts.append(
            _text(
                PADDING,
                TABLE_LABEL_Y,
                "Attributed commits by provider",
                size=12,
                weight=600,
                fill=theme.muted,
            )
        )
        if stats.totals.ai_attributed_commits > 0:
            parts.append(
                _text(
                    WIDTH - PADDING,
                    TABLE_LABEL_Y,
                    f"% of {stats.totals.ai_attributed_commits} AI-attributed commits",
                    size=11,
                    fill=theme.muted,
                    anchor="end",
                )
            )
        max_attributed = stats.providers[0].attributed_commits if stats.providers else 0
        denominator = stats.totals.ai_attributed_commits
        for i in range(_visible_rows(stats)):
            parts.append(_provider_row_svg(i, stats, max_attributed, denominator, theme))

        chips_top = _chips_top(stats)
        if _has_more_line(stats):
            more_y = ROWS_TOP + MAX_PROVIDER_ROWS * ROW_HEIGHT + 14
            remaining = len(stats.providers) - MAX_PROVIDER_ROWS
            parts.append(
                _text(PADDING, more_y, f"+{remaining} more", size=12, fill=theme.muted)
            )

        parts.append(_evidence_chips_svg(stats, theme, chips_top))
        parts.append(_privacy_chips_svg(stats, theme, chips_top + CHIP_ROW_STEP))
        divider2_y = chips_top + CHIP_ROW_STEP + CHIP_HEIGHT + FOOTER_GAP_ABOVE

    # Footer.
    parts.append(_line(PADDING, divider2_y, WIDTH - PADDING, divider2_y, stroke=theme.border))
    parts.append(
        _text(
            PADDING,
            divider2_y + FOOTER1_OFFSET,
            f"Generated {stats.generated_on} · aiprofile",
            size=11,
            fill=theme.muted,
        )
    )
    parts.append(_text(PADDING, divider2_y + FOOTER2_OFFSET, FOOTNOTE, size=11, fill=theme.muted))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"

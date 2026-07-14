"""Deterministic summary card SVG renderer (ADR-010, architecture.md section 9).

`render_summary(stats, theme)` is a pure function of its two arguments: no
clock reads, no randomness, no locale-dependent formatting. Byte-identical
output for identical inputs is a pinned test (mvp.md section 7 test 11).

Module graph is enforced by a separate unit test (architecture.md section 2):
this module may import stdlib plus `aiprofile.viz`, `aiprofile.render.themes`,
and `aiprofile.errors` only — never storage, gitio, schema, or sqlite3.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..viz import ProviderRow, Totals, VizStats
from .themes import Theme

# ---------------------------------------------------------------------------
# Layout constants (ADR-010: fixed layout, no template engine / SVG library).
# ---------------------------------------------------------------------------

WIDTH = 830
HEIGHT = 470
PADDING = 24
RADIUS = 8

FONT_STACK = "-apple-system, 'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif"

TITLE_TEXT = "AI Collaboration Summary"
MAX_PROVIDER_ROWS = 6

# Header
HEADER_TEXT_Y = 38
DIVIDER1_Y = 54

# Primary metric row (AI-attributed commits / AI participation events / active AI days)
METRIC_CENTERS = (172, 415, 658)
METRIC_VALUE_Y = 96
METRIC_LABEL_Y = 118

# Secondary line (unique commits scanned | AI providers | unknown commits)
SECONDARY_Y = 146

# Provider table
TABLE_LABEL_Y = 178
TABLE_TOP = 194  # top of row 0's bar
ROW_HEIGHT = 24
NAME_X = PADDING
NAME_WIDTH = 168
BAR_X = NAME_X + NAME_WIDTH + 14  # 206
COUNT_X = WIDTH - PADDING  # 806, text-anchor=end
COUNT_RESERVED_WIDTH = 56
BAR_MAX_WIDTH = COUNT_X - COUNT_RESERVED_WIDTH - 12 - BAR_X  # 532
BAR_HEIGHT = 14
NAME_FONT_SIZE = 13
COUNT_FONT_SIZE = 13

# "+N more" line (always reserved vertical space; drawn only when it applies)
MORE_Y = TABLE_TOP + MAX_PROVIDER_ROWS * ROW_HEIGHT + 16  # 354

# Evidence / privacy lines
EVIDENCE_Y = MORE_Y + 24  # 378
PRIVACY_Y = EVIDENCE_Y + 20  # 398

# Footer
DIVIDER2_Y = PRIVACY_Y + 14  # 412
FOOTER1_Y = DIVIDER2_Y + 22  # 434
FOOTER2_Y = FOOTER1_Y + 16  # 450

# Zero-state centered message (drawn in the region between the two dividers)
ZERO_MESSAGE_Y = 228
ZERO_HINT_Y = 252

FOOTNOTE = "One commit may include several AI participation events."
ZERO_MESSAGE = "No AI collaboration recorded yet"
ZERO_HINT = "Add AI-* trailers or scan a repository with AI co-authored commits."

# ---------------------------------------------------------------------------
# Conservative character-width table (ADR-010: no font dependency at render
# time). Widths are fractions of the font-size ("em"-like units), tuned to
# over-estimate slightly so truncation stays inside the column.
# ---------------------------------------------------------------------------

_WIDE_CHARS = frozenset("mMW@%&")
_NARROW_CHARS = frozenset("iIl.,:;'`|!ftj ()[]")


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


def _rect(x: float, y: float, w: float, h: float, *, fill: str, rx: float = 0) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"/>'


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}"/>'


# ---------------------------------------------------------------------------
# Content builders
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


def _secondary_line(stats: VizStats) -> str:
    return (
        f"Unique commits scanned {stats.totals.commits_scanned} | "
        f"AI providers {stats.provider_count} | "
        f"Unknown commits {stats.totals.unknown_commits}"
    )


def _evidence_line(stats: VizStats) -> str:
    e = stats.evidence
    parts = [f"declared {e.declared}", f"unknown {e.unknown}"]
    if e.verified:
        parts.append(f"verified {e.verified}")
    if e.imported:
        parts.append(f"imported {e.imported}")
    if e.inferred:
        parts.append(f"inferred {e.inferred}")
    return "Evidence (events): " + " | ".join(parts)


def _privacy_line(stats: VizStats) -> str:
    if stats.privacy.includes_private:
        return "Includes private activity (aggregate-only)"
    return "Public repositories only"


def _provider_row_svg(index: int, row: ProviderRow, max_attributed: int, theme: Theme) -> str:
    row_top = TABLE_TOP + index * ROW_HEIGHT
    bar_y = row_top + 5
    text_y = row_top + 16

    name = _truncate(row.display_name, NAME_WIDTH, NAME_FONT_SIZE)
    elements = [
        _text(NAME_X, text_y, name, size=NAME_FONT_SIZE, fill=theme.text),
        _rect(BAR_X, bar_y, BAR_MAX_WIDTH, BAR_HEIGHT, fill=theme.bar_track, rx=3),
    ]
    bar_w = 0
    if max_attributed > 0 and row.attributed_commits > 0:
        bar_w = round(BAR_MAX_WIDTH * row.attributed_commits / max_attributed)
    if bar_w > 0:
        elements.append(_rect(BAR_X, bar_y, bar_w, BAR_HEIGHT, fill=theme.bar_fill, rx=3))
    elements.append(
        _text(
            COUNT_X,
            text_y,
            str(row.attributed_commits),
            size=COUNT_FONT_SIZE,
            fill=theme.text,
            anchor="end",
        )
    )
    return "\n".join(elements)


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


def render_summary(stats: VizStats, theme: Theme) -> str:
    """Render the summary card as SVG markup (ADR-010, architecture.md section 9).

    Pure function of ``(stats, theme)``: no clock, no randomness, fixed
    decimal formatting, byte-identical output for identical inputs.
    """
    zero_state = _is_zero_state(stats.totals)

    title = escape(f"{TITLE_TEXT} — {stats.period.label}")
    desc = escape(_desc_text(stats, zero_state))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-labelledby="aiprofileSummaryTitle aiprofileSummaryDesc">',
        f'<title id="aiprofileSummaryTitle">{title}</title>',
        f'<desc id="aiprofileSummaryDesc">{desc}</desc>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="{RADIUS}" '
        f'fill="{theme.bg}" stroke="{theme.border}" stroke-width="1"/>',
    ]

    # Header: title + period label.
    parts.append(
        _text(PADDING, HEADER_TEXT_Y, TITLE_TEXT, size=18, weight=600, fill=theme.title)
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
                WIDTH / 2,
                ZERO_MESSAGE_Y,
                ZERO_MESSAGE,
                size=14,
                weight=600,
                fill=theme.muted,
                anchor="middle",
            )
        )
        parts.append(
            _text(
                WIDTH / 2,
                ZERO_HINT_Y,
                ZERO_HINT,
                size=12,
                fill=theme.muted,
                anchor="middle",
            )
        )
    else:
        # Primary metric row.
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
                    size=26,
                    weight=700,
                    fill=theme.text,
                    anchor="middle",
                )
            )
            parts.append(
                _text(
                    center_x,
                    METRIC_LABEL_Y,
                    label,
                    size=12,
                    fill=theme.muted,
                    anchor="middle",
                )
            )

        # Secondary line.
        parts.append(
            _text(PADDING, SECONDARY_Y, _secondary_line(stats), size=12, fill=theme.muted)
        )

        # Provider table.
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
        visible = stats.providers[:MAX_PROVIDER_ROWS]
        max_attributed = stats.providers[0].attributed_commits if stats.providers else 0
        for i, row in enumerate(visible):
            parts.append(_provider_row_svg(i, row, max_attributed, theme))

        remaining = len(stats.providers) - MAX_PROVIDER_ROWS
        if remaining > 0:
            parts.append(
                _text(PADDING, MORE_Y, f"+{remaining} more", size=12, fill=theme.muted)
            )

        # Evidence + privacy lines.
        parts.append(
            _text(PADDING, EVIDENCE_Y, _evidence_line(stats), size=12, fill=theme.text)
        )
        parts.append(
            _text(PADDING, PRIVACY_Y, _privacy_line(stats), size=12, fill=theme.text)
        )

    # Footer.
    parts.append(_line(PADDING, DIVIDER2_Y, WIDTH - PADDING, DIVIDER2_Y, stroke=theme.border))
    parts.append(
        _text(
            PADDING,
            FOOTER1_Y,
            f"Generated {stats.generated_on} | aiprofile",
            size=11,
            fill=theme.muted,
        )
    )
    parts.append(_text(PADDING, FOOTER2_Y, FOOTNOTE, size=11, fill=theme.muted))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"

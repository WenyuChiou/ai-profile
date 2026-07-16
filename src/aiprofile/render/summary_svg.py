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

# Header: accent commit-node glyph + title + right-aligned period label.
HEADER_TEXT_Y = 36
GLYPH_CX = 32
GLYPH_CY = 32
TITLE_X = 48
DIVIDER1_Y = 56

# Hero metric + secondary ledger.
HERO_VALUE_Y = 112
HERO_LABEL_Y = 140
HERO_RELATION_Y = 160
HERO_VALUE_SIZE = 38
SHARE_BAR_X = PADDING
SHARE_BAR_Y = 172
SHARE_BAR_WIDTH = 360
SHARE_BAR_HEIGHT = 7
LEDGER_LABEL_X = 512
LEDGER_VALUE_X = WIDTH - PADDING
LEDGER_FIRST_Y = 88
LEDGER_ROW_STEP = 24

# Provider table.
TABLE_LABEL_Y = 208
ROWS_TOP = 224
ROW_HEIGHT = 28
NAME_X = PADDING
NAME_WIDTH = 150
BAR_X = 184
COUNT_X = WIDTH - PADDING  # right anchor for "count · pct%"
BAR_MAX_WIDTH = 500  # COUNT_X - reserved count column (110) - gap (12) - BAR_X
BAR_HEIGHT = 7
NAME_FONT_SIZE = 13
COUNT_FONT_SIZE = 13

MORE_LINE_EXTRA = 24  # vertical room for the "+N more" line when present

# Evidence/privacy provenance panel.
PANEL_GAP_ABOVE = 20
PANEL_PAD_X = 16
PANEL_PAD_Y = 16
PANEL_HEIGHT = 104
PANEL_RADIUS = 6
EVIDENCE_FONT_SIZE = 11
EVIDENCE_LABEL_SIZE = 12
EVIDENCE_PREFIX_TEMPLATE = "Evidence (all records: {n})"
EVIDENCE_BAR_Y_OFFSET = 36
EVIDENCE_BAR_HEIGHT = 8
EVIDENCE_LEGEND_Y_OFFSET = 64
EVIDENCE_SWATCH = 8
EVIDENCE_LEGEND_GAP = 16
PRIVACY_Y_OFFSET = 88

# Footer.
FOOTER_GAP_ABOVE = 16
FOOTER1_OFFSET = 24
FOOTER2_OFFSET = 40
FOOTER_BOTTOM_PAD = 16

FOOTNOTE = "One commit may include several AI actor presences (one per provider/tool)."
ZERO_MESSAGE = "No AI collaboration recorded yet"
ZERO_HINT = "Add AI-* trailers or scan a repository with AI co-authored commits."
ZERO_MESSAGE_Y = 120
ZERO_HINT_Y = 144
ZERO_BODY_BOTTOM = 164

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
    letter_spacing: float | None = None,
) -> str:
    body = content if escaped else escape(content)
    spacing_attr = f' letter-spacing="{letter_spacing}"' if letter_spacing is not None else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT_STACK}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{spacing_attr}>{body}</text>'
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


def _commit_mark(cx: int, cy: int, theme: Theme) -> str:
    """Small commit-node mark: square ring plus centered square dot."""
    return "\n".join(
        (
            _rect(cx - 8, cy - 8, 16, 16, fill=theme.bg, rx=3, stroke=theme.accent),
            _rect(cx - 3, cy - 3, 6, 6, fill=theme.accent, rx=1),
        )
    )


# ---------------------------------------------------------------------------
# Layout helpers (all pure functions of the data).
# ---------------------------------------------------------------------------


def _pct_label(numerator: int, denominator: int) -> str:
    """Deterministic whole-number share label that never lies at the
    boundaries (gate-7 M-02): a nonzero share is never "0%" and a
    non-total share is never "100%" — rounding that would produce a
    false endpoint renders as the compact "<1%" / ">99%" instead.
    Exact endpoints stay exact."""
    if denominator <= 0 or numerator == 0:
        return "0%"
    if numerator == denominator:
        return "100%"
    pct = round(100 * numerator / denominator)
    if pct == 0:
        return "<1%"
    if pct == 100:
        return ">99%"
    return f"{pct}%"


def _is_zero_state(totals: Totals) -> bool:
    return (
        totals.commits_scanned == 0
        and totals.ai_attributed_commits == 0
        and totals.ai_actor_presences == 0
        and totals.human_declared_commits == 0
        and totals.unknown_commits == 0
        and totals.active_ai_days == 0
    )


def _visible_rows(stats: VizStats) -> int:
    return min(len(stats.providers), MAX_PROVIDER_ROWS)


def _has_more_line(stats: VizStats) -> bool:
    return len(stats.providers) > MAX_PROVIDER_ROWS


def _panel_top(stats: VizStats) -> int:
    bottom = ROWS_TOP + _visible_rows(stats) * ROW_HEIGHT
    if _has_more_line(stats):
        bottom += MORE_LINE_EXTRA
    return bottom + PANEL_GAP_ABOVE


def card_height(stats: VizStats) -> int:
    """Deterministic card height: a pure function of the data shape."""
    if _is_zero_state(stats.totals):
        divider2_y = ZERO_BODY_BOTTOM
    else:
        divider2_y = _panel_top(stats) + PANEL_HEIGHT + FOOTER_GAP_ABOVE
    return divider2_y + FOOTER2_OFFSET + FOOTER_BOTTOM_PAD


def _desc_text(stats: VizStats, zero_state: bool) -> str:
    if zero_state:
        return f"No AI collaboration recorded yet. Generated {stats.generated_on}."
    t = stats.totals
    return (
        f"{t.ai_attributed_commits} AI-attributed commits, "
        f"{t.ai_actor_presences} AI actor presences across "
        f"{t.active_ai_days} active AI days (author dates), {stats.provider_count} AI providers. "
        f"Generated {stats.generated_on}."
    )


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------


def _ledger_svg(stats: VizStats, theme: Theme) -> str:
    rows = (
        ("AI actor presences", stats.totals.ai_actor_presences),
        ("Active AI days (author dates)", stats.totals.active_ai_days),
        ("AI providers", stats.provider_count),
        ("Unknown commits", stats.totals.unknown_commits),
    )
    parts = []
    for index, (label, value) in enumerate(rows):
        y = LEDGER_FIRST_Y + index * LEDGER_ROW_STEP
        parts.append(_text(LEDGER_LABEL_X, y, label, size=12, fill=theme.muted))
        parts.append(
            _text(LEDGER_VALUE_X, y, str(value), size=13, fill=theme.text, weight=600, anchor="end")
        )
    return "\n".join(parts)


def _hero_svg(stats: VizStats, theme: Theme) -> str:
    t = stats.totals
    share = _pct_label(t.ai_attributed_commits, t.commits_scanned)
    share_w = (
        round(SHARE_BAR_WIDTH * t.ai_attributed_commits / t.commits_scanned)
        if t.commits_scanned
        else 0
    )
    parts = [
        _text(
            PADDING,
            HERO_VALUE_Y,
            str(t.ai_attributed_commits),
            size=HERO_VALUE_SIZE,
            weight=700,
            fill=theme.accent,
        ),
        _text(PADDING, HERO_LABEL_Y, "AI-attributed commits", size=12, fill=theme.muted),
        _text(
            PADDING,
            HERO_RELATION_Y,
            f"{share} of {t.commits_scanned} unique commits scanned",
            size=12,
            fill=theme.text,
            weight=600,
        ),
        _rect(
            SHARE_BAR_X,
            SHARE_BAR_Y,
            SHARE_BAR_WIDTH,
            SHARE_BAR_HEIGHT,
            fill=theme.bar_track,
            rx=2,
        ),
    ]
    if share_w > 0:
        parts.append(
            _rect(SHARE_BAR_X, SHARE_BAR_Y, share_w, SHARE_BAR_HEIGHT, fill=theme.accent, rx=2)
        )
    return "\n".join(parts)


def _provider_row_svg(
    index: int, stats: VizStats, max_attributed: int, denominator: int, theme: Theme
) -> str:
    row = stats.providers[index]
    row_top = ROWS_TOP + index * ROW_HEIGHT
    bar_y = row_top + 8
    text_y = row_top + 20

    name = _truncate(row.display_name, NAME_WIDTH, NAME_FONT_SIZE)
    elements = [
        _text(NAME_X, text_y, name, size=NAME_FONT_SIZE, fill=theme.text),
        _rect(BAR_X, bar_y, BAR_MAX_WIDTH, BAR_HEIGHT, fill=theme.bar_track, rx=2),
    ]
    if max_attributed > 0 and row.attributed_commits > 0:
        bar_w = round(BAR_MAX_WIDTH * row.attributed_commits / max_attributed)
        elements.append(_rect(BAR_X, bar_y, bar_w, BAR_HEIGHT, fill=theme.bar_fill, rx=2))

    count_spans = _tspan(str(row.attributed_commits), fill=theme.text, weight=600)
    if denominator > 0:
        pct = _pct_label(row.attributed_commits, denominator)
        count_spans += _tspan(f" · {pct}", fill=theme.muted)
    elements.append(
        f'<text x="{COUNT_X}" y="{text_y}" font-family="{FONT_STACK}"'
        f' font-size="{COUNT_FONT_SIZE}" text-anchor="end">{count_spans}</text>'
    )
    return "\n".join(elements)


def _evidence_items(stats: VizStats, theme: Theme) -> tuple[tuple[str, int, str, bool], ...]:
    e = stats.evidence
    return (
        ("verified", e.verified, theme.evidence_verified, e.verified > 0),
        ("declared", e.declared, theme.evidence_declared, True),
        ("imported", e.imported, theme.evidence_imported, e.imported > 0),
        ("inferred", e.inferred, theme.evidence_inferred, e.inferred > 0),
        ("unknown", e.unknown, theme.evidence_unknown, True),
    )


def _evidence_panel_svg(stats: VizStats, theme: Theme, top: int) -> str:
    e = stats.evidence
    panel_x = PADDING
    panel_w = WIDTH - 2 * PADDING
    inner_x = panel_x + PANEL_PAD_X
    inner_w = panel_w - 2 * PANEL_PAD_X
    bar_y = top + EVIDENCE_BAR_Y_OFFSET
    legend_y = top + EVIDENCE_LEGEND_Y_OFFSET
    parts = [
        _rect(panel_x, top, panel_w, PANEL_HEIGHT, fill=theme.chip_bg, rx=PANEL_RADIUS),
        _text(
            inner_x,
            top + PANEL_PAD_Y,
            EVIDENCE_PREFIX_TEMPLATE.format(n=e.total_records),
            size=EVIDENCE_LABEL_SIZE,
            weight=600,
            fill=theme.muted,
            letter_spacing=0.2,
        ),
    ]

    segments = [(label, count, color) for label, count, color, _ in _evidence_items(stats, theme)]
    nonzero_segments = [(label, count, color) for label, count, color in segments if count > 0]
    if not (e.total_records > 0 and nonzero_segments):
        # Empty composition: the track stands in for the bar. When segments
        # exist they span the full width and the 2px gaps between them show
        # the PANEL surface (dataviz mark spec: surface gaps, not a track
        # peeking through).
        parts.append(
            _rect(inner_x, bar_y, inner_w, EVIDENCE_BAR_HEIGHT, fill=theme.bar_track, rx=2)
        )
    if e.total_records > 0 and nonzero_segments:
        gap_total = 2 * (len(nonzero_segments) - 1)
        available_w = inner_w - gap_total
        # Cumulative rounding (gate-6 visual round, reviewer finding):
        # independently rounded widths drift, and remainder-sizing the
        # last segment went NEGATIVE for 3+ lopsided categories
        # (width="-1" reproduced). Rounding the cumulative prefix keeps
        # every width >= 0 by monotonicity and the total exactly equal
        # to available_w by construction.
        x = inner_x
        prefix = 0
        prev_end = 0
        for _, count, color in nonzero_segments:
            prefix += count
            end = round(available_w * prefix / e.total_records)
            w = end - prev_end
            prev_end = end
            parts.append(_rect(x, bar_y, w, EVIDENCE_BAR_HEIGHT, fill=color, rx=2))
            x += w + 2

    legend_x = inner_x
    for label, count, color, visible in _evidence_items(stats, theme):
        if not visible:
            continue
        text = f"{label} {count}"
        parts.append(
            _rect(
                legend_x,
                legend_y - EVIDENCE_SWATCH + 1,
                EVIDENCE_SWATCH,
                EVIDENCE_SWATCH,
                fill=color,
                rx=1,
            )
        )
        parts.append(_text(legend_x + 12, legend_y, text, size=EVIDENCE_FONT_SIZE, fill=theme.text))
        legend_x += round(12 + _text_width(text, EVIDENCE_FONT_SIZE) + EVIDENCE_LEGEND_GAP)

    p = stats.privacy
    if p.includes_anonymous_aggregate:
        primary = "Includes aggregate-only activity (repository identity withheld)"
    else:
        primary = "All activity explicitly publishable"
    privacy_text = primary
    if p.includes_anonymous_aggregate and p.explicitly_publishable_commits > 0:
        privacy_text += (
            f" — publishable {p.explicitly_publishable_commits}"
            f" · aggregate-only {p.anonymous_aggregate_commits}"
        )
    marker_y = top + PRIVACY_Y_OFFSET - EVIDENCE_SWATCH + 1
    parts.append(
        _rect(inner_x, marker_y, EVIDENCE_SWATCH, EVIDENCE_SWATCH, fill=theme.muted, rx=1)
    )
    parts.append(
        _text(inner_x + 12, top + PRIVACY_Y_OFFSET, privacy_text, size=11, fill=theme.muted)
    )
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

    # Header: commit-node glyph + title + period label.
    parts.append(_commit_mark(GLYPH_CX, GLYPH_CY, theme))
    parts.append(
        _text(TITLE_X, HEADER_TEXT_Y, TITLE_TEXT, size=16, weight=600, fill=theme.title)
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
                size=13,
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
        # Primary metric row (hero metric in accent — the card's focal layer).
        parts.append(_hero_svg(stats, theme))
        parts.append(_ledger_svg(stats, theme))

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
                letter_spacing=0.2,
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

        panel_top = _panel_top(stats)
        if _has_more_line(stats):
            more_y = ROWS_TOP + MAX_PROVIDER_ROWS * ROW_HEIGHT + 16
            remaining = len(stats.providers) - MAX_PROVIDER_ROWS
            parts.append(
                _text(PADDING, more_y, f"+{remaining} more", size=12, fill=theme.muted)
            )

        parts.append(_evidence_panel_svg(stats, theme, panel_top))
        divider2_y = panel_top + PANEL_HEIGHT + FOOTER_GAP_ABOVE

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

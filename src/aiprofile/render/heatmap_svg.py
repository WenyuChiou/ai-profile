"""Collaboration-ratio heatmap card (round D4,
`.ai/round_d4_heatmap_spec.md`; ADR-020).

A GitHub-style year grid where each day cell encodes TWO dimensions:

- INTENSITY (solid background-mix depth): the day's total_commits — the
  owner's whole working rhythm, human-only commits included (the
  round's driving requirement) — bucketed 1 / 2-4 / 5-7 / 8+.
- HUE (fill color): the day's AI-collaboration share, quantized into five
  bins (0%, and quarters up to 100%), interpolated between the theme's
  neutral and accent colors. A solo-coding week reads neutral and quiet;
  a heavy pairing week reads accent.

Pure function of ``(stats, theme)`` like every renderer here: no clock
(the grid anchors on the series' own newest date), no randomness, no
network, fixed integer arithmetic for the bin math (no float-equality
edges), FULLY STATIC output (the SMIL ban from the D2 postmortem applies
to every card in this repo).

Shares the summary card's private text/geometry helpers deliberately —
one family of cards, one set of text-metric conventions; a divergence in
font stacks or escaping between sibling cards would be a bug, not a
freedom.
"""

from __future__ import annotations

import datetime
from xml.sax.saxutils import escape

from ..viz import DayCell, VizStats
from .summary_svg import (
    PADDING,
    RADIUS,
    TITLE_X,
    WIDTH,
    _commit_mark,
    _line,
    _pct_label,
    _rect,
    _text,
    _tspan,
)
from .themes import Theme

# ---------------------------------------------------------------------------
# Geometry (constants section — the whole layout derives from these).
# The card is FULLY STATIC: no <animate>, no SMIL, no CSS animation —
# see summary_svg.py's constants-section note for the incident history.
# ---------------------------------------------------------------------------

HM_TITLE_TEXT = "Commit Activity × AI Collaboration"
HM_HEADER_TEXT_Y = 36
HM_DIVIDER1_Y = 56
HM_GLYPH_CX = 32
HM_GLYPH_CY = 31

HM_STAT_Y = 84  # window-summary line baseline

HM_CELL = 11  # square side (aesthetic pass: more ink, same 14px step)
HM_GAP = 3
HM_STEP = HM_CELL + HM_GAP  # 14
HM_ROWS = 7  # weekday rows, Mon(0) .. Sun(6)
HM_MAX_COLS = 53  # bounded by the 365-day window (52 full weeks + partials)

HM_GUTTER = 34  # left gutter for weekday labels
HM_GRID_X = PADDING + HM_GUTTER
HM_MONTH_LABEL_Y = 112  # month-label row baseline
HM_GRID_TOP = 120
HM_GRID_BOTTOM = HM_GRID_TOP + HM_ROWS * HM_STEP - HM_GAP  # 214

HM_LEGEND_Y = HM_GRID_BOTTOM + 30  # legend swatch top
HM_LEGEND_TEXT_DY = 9  # swatch-top -> label baseline delta
HM_DIVIDER2_Y = HM_LEGEND_Y + 26
HM_FOOTER_Y = HM_DIVIDER2_Y + 24
HM_HEIGHT = HM_FOOTER_Y + 18  # populated-card height

HM_EMPTY_MESSAGE = "No publishable daily activity yet."
HM_EMPTY_MESSAGE_Y = 96
HM_EMPTY_DIVIDER2_Y = 124
HM_EMPTY_HEIGHT = HM_EMPTY_DIVIDER2_Y + 42

HM_CUE_TEXT = "publishable repos only"

#: Intensity (volume) bins over total_commits — same 1 / 2-4 / 5-7 / 8+
#: bucketing the D2 band's legend derives from its cap. Expressed as
#: SOLID bg-mix weights (aesthetic pass, gate-18 round): every final
#: cell color is a flat precomputed hex — lerp(theme.bg, share_color,
#: weight) — never a fill-opacity alpha, which washed low-volume cells
#: out against the dark card and left the final pixel color to the
#: compositor instead of this renderer.
HM_VOLUME_MIX = (0.45, 0.65, 0.85, 1.0)
HM_VOLUME_LABELS = ("1", "2-4", "5-7", "8+")
HM_VOLUME_CAP = 8

#: AI-share hue bins: 0 (pure neutral) plus four quarter bins up to 1
#: (pure accent). Bin selection is integer arithmetic (ceil(4*ai/total)),
#: so no float-equality edge can flip a bin between platforms.
HM_SHARE_BIN_COUNT = 5


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _lerp_hex(a: str, b: str, t: float) -> str:
    """Channel-wise linear interpolation between two #RRGGBB colors at a
    fixed t — called only with t in {0, .25, .5, .75, 1}, producing a
    deterministic flat hex (round-half-even is irrelevant at these t
    values only when channels differ by multiples of 4; plain round() is
    deterministic for any fixed inputs, which is the actual requirement)."""
    av = [int(a.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
    bv = [int(b.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(av, bv, strict=True))


def _share_bin(ai_commits: int, total_commits: int) -> int:
    """0..4: 0 for a human-only day; otherwise ceil(4 * ai / total) via
    integer arithmetic (1 = share in (0, 25%], 4 = 100%)."""
    if ai_commits == 0:
        return 0
    return -(-4 * ai_commits // total_commits)


def _volume_bin(total_commits: int) -> int:
    """0..3 over the 1 / 2-4 / 5-7 / 8+ buckets (cap = HM_VOLUME_CAP,
    the same top bucket the D2 band derives from its own cap)."""
    if total_commits <= 1:
        return 0
    if total_commits <= HM_VOLUME_CAP // 2:
        return 1
    if total_commits < HM_VOLUME_CAP:
        return 2
    return 3


def _share_colors(theme: Theme) -> tuple[str, ...]:
    """The five flat share-bin hexes for a theme: neutral -> accent."""
    return tuple(
        _lerp_hex(theme.muted, theme.accent, bin_index / (HM_SHARE_BIN_COUNT - 1))
        for bin_index in range(HM_SHARE_BIN_COUNT)
    )


def _cell_fill(theme: Theme, share_bin: int, volume_bin: int) -> str:
    """The flat hex for one (share, volume) cell: the share-bin color
    mixed toward the card background by the volume weight. 20 possible
    values per theme, all deterministic."""
    return _lerp_hex(theme.bg, _share_colors(theme)[share_bin], HM_VOLUME_MIX[volume_bin])


def _monday_of(day: datetime.date) -> datetime.date:
    return day - datetime.timedelta(days=day.weekday())


def _grid_columns(daily: tuple[DayCell, ...]) -> tuple[datetime.date, int]:
    """(window_start, column_count) for a non-empty series: the window is
    the contract's own [newest-364, newest], columns are Monday-anchored
    weeks from the window start's week through the newest date's week."""
    newest = datetime.date.fromisoformat(daily[-1].date)
    window_start = newest - datetime.timedelta(days=364)
    weeks = (_monday_of(newest) - _monday_of(window_start)).days // 7
    return window_start, weeks + 1


def _cell_rects(daily: tuple[DayCell, ...], theme: Theme) -> str:
    """Every in-window day square: data days get the solid (share-bin x
    volume-bin) hex from _cell_fill — the single color source shared
    with the legend swatches; absent in-window days get the flat track
    square. Days outside [window_start, newest] render nothing (partial
    first/last grid columns stay blank, never fabricated)."""
    newest = datetime.date.fromisoformat(daily[-1].date)
    window_start, _cols = _grid_columns(daily)
    first_monday = _monday_of(window_start)
    by_date = {cell.date: cell for cell in daily}

    parts: list[str] = []
    day = window_start
    while day <= newest:
        col = (_monday_of(day) - first_monday).days // 7
        row = day.weekday()
        x = HM_GRID_X + col * HM_STEP
        y = HM_GRID_TOP + row * HM_STEP
        cell = by_date.get(day.isoformat())
        if cell is None:
            parts.append(_rect(x, y, HM_CELL, HM_CELL, fill=theme.bar_track, rx=3))
        else:
            fill = _cell_fill(
                theme,
                _share_bin(cell.ai_commits, cell.total_commits),
                _volume_bin(cell.total_commits),
            )
            parts.append(_rect(x, y, HM_CELL, HM_CELL, fill=fill, rx=3))
        day += datetime.timedelta(days=1)
    return "\n".join(parts)


def _month_labels(daily: tuple[DayCell, ...], theme: Theme) -> str:
    """Month label above each column whose Monday starts a new month
    relative to the previous column — derived from the series' own dates,
    never the clock (D2 convention)."""
    window_start, cols = _grid_columns(daily)
    first_monday = _monday_of(window_start)
    parts: list[str] = []
    previous_month = None
    for col in range(cols):
        monday = first_monday + datetime.timedelta(weeks=col)
        if previous_month is not None and monday.month != previous_month:
            x = HM_GRID_X + col * HM_STEP
            parts.append(
                _text(x, HM_MONTH_LABEL_Y, _MONTH_NAMES[monday.month - 1], size=11,
                      fill=theme.muted)
            )
        previous_month = monday.month
    return "\n".join(parts)


_MONTH_NAMES = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

_WEEKDAY_LABELS = ((0, "Mon"), (2, "Wed"), (4, "Fri"))


def _weekday_labels(theme: Theme) -> str:
    return "\n".join(
        _text(
            PADDING,
            HM_GRID_TOP + row * HM_STEP + HM_CELL - 1,
            label,
            size=10,
            fill=theme.muted,
        )
        for row, label in _WEEKDAY_LABELS
    )


def _legend(theme: Theme) -> str:
    """Two-axis legend (aesthetic pass): a volume ramp (the neutral
    share-0 color at the four bg-mix weights, numeric bin labels kept -
    they carry real information) and an AI-share strip with end labels
    only (the quarter-bin thresholds live in <desc>, not as label
    clutter). Every swatch is the exact hex a real day cell would use."""
    colors = _share_colors(theme)
    parts: list[str] = []
    y_text = HM_LEGEND_Y + HM_LEGEND_TEXT_DY
    x = float(PADDING)
    parts.append(_text(x, y_text, "Volume", size=10, fill=theme.muted))
    x += 46
    for volume_bin, label in enumerate(HM_VOLUME_LABELS):
        parts.append(
            _rect(x, HM_LEGEND_Y, HM_CELL, HM_CELL, fill=_cell_fill(theme, 0, volume_bin), rx=3)
        )
        x += HM_CELL + 4
        parts.append(_text(x, y_text, label, size=10, fill=theme.muted))
        x += 10 + 6 * len(label)
    x += 26
    parts.append(_text(x, y_text, "AI share", size=10, fill=theme.muted))
    x += 52
    parts.append(_text(x, y_text, "0%", size=10, fill=theme.muted))
    x += 20
    for color in colors:
        parts.append(_rect(x, HM_LEGEND_Y, HM_CELL, HM_CELL, fill=color, rx=3))
        x += HM_CELL + 3
    x += 5
    parts.append(_text(x, y_text, "100%", size=10, fill=theme.muted))
    parts.append(
        _text(
            WIDTH - PADDING,
            y_text,
            HM_CUE_TEXT,
            size=10,
            fill=theme.muted,
            anchor="end",
        )
    )
    return "\n".join(parts)


def _window_summary(daily: tuple[DayCell, ...]) -> tuple[int, int, str, str]:
    """(total, ai, window_start_iso, newest_iso) over the series — the
    stat line's numbers are WINDOW-scoped (the series is already the
    publishable-only 365-day window), never the all-time totals."""
    total = sum(cell.total_commits for cell in daily)
    ai = sum(cell.ai_commits for cell in daily)
    window_start, _cols = _grid_columns(daily)
    return total, ai, window_start.isoformat(), daily[-1].date


def _desc_text(stats: VizStats) -> str:
    if not stats.daily:
        return f"No publishable daily activity. Generated {stats.generated_on}."
    total, ai, start, end = _window_summary(stats.daily)
    return (
        f"Daily commit heatmap {start} to {end}: {total} commits,"
        f" {ai} AI-assisted ({_pct_label(ai, total)}), publishable"
        f" repositories only. Intensity is total commits (the owner's own"
        f" commits included); hue is the day's AI share."
        f" Generated {stats.generated_on}."
    )


# ---------------------------------------------------------------------------
# Card
# ---------------------------------------------------------------------------


def render_heatmap(stats: VizStats, theme: Theme) -> str:
    """Render the heatmap card as SVG markup (round D4, ADR-020).

    Pure function of ``(stats, theme)``; byte-identical output for
    identical inputs; fully static markup.
    """
    empty = not stats.daily
    height = HM_EMPTY_HEIGHT if empty else HM_HEIGHT

    title = escape(f"{HM_TITLE_TEXT} — {stats.period.label}")
    desc = escape(_desc_text(stats))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-labelledby="aiprofileHeatmapTitle aiprofileHeatmapDesc">',
        f'<title id="aiprofileHeatmapTitle">{title}</title>',
        f'<desc id="aiprofileHeatmapDesc">{desc}</desc>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="{RADIUS}" '
        f'fill="{theme.bg}" stroke="{theme.border}" stroke-width="1"/>',
        _commit_mark(HM_GLYPH_CX, HM_GLYPH_CY, theme),
        _text(TITLE_X, HM_HEADER_TEXT_Y, HM_TITLE_TEXT, size=16, weight=600, fill=theme.title),
        _text(
            WIDTH - PADDING,
            HM_HEADER_TEXT_Y,
            stats.period.label,
            size=12,
            fill=theme.muted,
            anchor="end",
        ),
        _line(PADDING, HM_DIVIDER1_Y, WIDTH - PADDING, HM_DIVIDER1_Y, stroke=theme.border),
    ]

    if empty:
        parts.append(
            _text(
                WIDTH // 2,
                HM_EMPTY_MESSAGE_Y,
                HM_EMPTY_MESSAGE,
                size=13,
                fill=theme.muted,
                anchor="middle",
            )
        )
        divider2_y = HM_EMPTY_DIVIDER2_Y
    else:
        total, ai, start, end = _window_summary(stats.daily)
        stat_body = (
            _tspan(f"{total}", fill=theme.text, weight=700)
            + _tspan(" commits", fill=theme.muted)
            + _tspan("  ·  ", fill=theme.muted)
            + _tspan(f"{ai}", fill=theme.accent, weight=700)
            + _tspan(f" AI-assisted ({_pct_label(ai, total)})", fill=theme.accent)
        )
        parts.append(_text(PADDING, HM_STAT_Y, stat_body, size=13, fill=theme.text, escaped=True))
        parts.append(
            _text(
                WIDTH - PADDING,
                HM_STAT_Y,
                f"{start} → {end}",
                size=11,
                fill=theme.muted,
                anchor="end",
            )
        )
        parts.append(_month_labels(stats.daily, theme))
        parts.append(_weekday_labels(theme))
        parts.append(_cell_rects(stats.daily, theme))
        parts.append(_legend(theme))
        divider2_y = HM_DIVIDER2_Y

    parts.append(_line(PADDING, divider2_y, WIDTH - PADDING, divider2_y, stroke=theme.border))
    parts.append(
        _text(
            PADDING,
            divider2_y + 24,
            f"Generated {stats.generated_on} · aiprofile",
            size=11,
            fill=theme.muted,
        )
    )
    parts.append("</svg>")
    return "\n".join(parts)

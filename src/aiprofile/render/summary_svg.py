"""Deterministic summary card SVG renderer (ADR-010, ADR-022,
architecture.md section 9).

`render_summary(stats, theme)` is a pure function of its two arguments: no
clock reads, no randomness, no locale-dependent formatting. Byte-identical
output for identical inputs is a pinned test (mvp.md section 7 test 11).

The v0.4.8 recruiter-facing `AI Collaboration Record` (ADR-022) is retained;
v0.4.9 (ADR-025) refines its daily treatment into a readable 12-week flat
matrix (bar height = total-commit volume bins, fill = AI-share bins — the
heatmap card's own fixed bins, shared via `render/_bins.py`). The card also
keeps its header + period, hero AI-attributed-commit figure with share of
scanned commits, secondary metric ledger, top-six provider ledger with an
explicit non-exclusive note, and compact evidence rail.

v0.8.0 (ADR-031, Signal Console) recomposes the card for README-scale
legibility: the header becomes a status line carrying the period and an
explicit *snapshot* date, the hero + right-hand ledger become one metric
console strip (hero cell plus four hairline-separated secondary cells on a
shared baseline), and the type floor rises from 11px to 12px on the fixed
12/13/18/40 scale.

v0.8.1 (ADR-032, Collaboration Pulse) replaces the daily 84-cell matrix
with a static pulse signature: the 84 window dates run oldest to newest as
baseline-anchored 6px marks in 12 groups of seven (wider structural group
gap, not a calendar-week claim), neutral pulse height carries the fixed
total-commit bins (12/24/36/48px), the accent fill rises from the baseline
to 0/25/50/75/100% of the pulse height per AI-share bin, and a
no-activity date is a 2px baseline tick. Weekday labels and quarter rails
are gone; month-boundary labels stay. Semantics, bins, provider/evidence
meanings, the publishable-only rule, and the deterministic-height contract
are unchanged.

Layout is dynamic-but-deterministic: the card height is a pure function of
the data (number of provider rows, overflow line, published daily series,
zero state) so sparse profiles never show a dead band — see `card_height`.

Module graph is enforced by a separate unit test (architecture.md section 2):
this module may import stdlib plus `aiprofile.viz`, `aiprofile.render.themes`,
`aiprofile.render.brand`, `aiprofile.render._bins`, and `aiprofile.errors`
only — never storage, gitio, schema, or sqlite3. `render.brand` (round D1,
ADR-017) is the vendored provider-glyph table and `render._bins` the shared
day-cell bin arithmetic; both are sibling render-package modules, not schema
imports, so they do not cross the isolation boundary.
"""

from __future__ import annotations

import datetime
from xml.sax.saxutils import escape

from ..viz import DayCell, ProviderRow, Totals, VizStats
from ._bins import _share_bin, _volume_bin
from .brand import BRAND, BrandSpec
from .themes import Theme

# Mirrors aiprofile.schema.vocab.UNRECOGNIZED_PROVIDER verbatim. The
# render-layer isolation boundary (architecture.md section 2) forbids
# importing aiprofile.schema here, so the Unrecognized-bucket sentinel is
# hand-mirrored — the same precedent brand.py sets for
# `_CANONICAL_PROVIDERS_MIRROR`. `tests/unit/test_brand.py` cross-checks
# this value against the real schema constant so drift fails loudly.
_UNRECOGNIZED_PROVIDER = "unrecognized"

# ---------------------------------------------------------------------------
# Layout constants (ADR-010: fixed constants, no template engine).
# Shared spacing system (introduced in v0.4.8 and retained since): 4px
# scale, 24px outer padding, 8-12px within-group gaps, 20-24px between
# sections. Fixed type sizes 12/13/18/40 (v0.8.0 Signal Console; the 11px
# floor was retired for README-scale legibility); weights 400 for labels,
# 600 for values/section labels, 700 for the hero figure.
# ---------------------------------------------------------------------------

WIDTH = 830
PADDING = 24
RADIUS = 8

#: The three local type stacks (ADR-022; mirrors the dashboard's system).
#: Body carries labels and prose, display carries the card title/header,
#: and mono carries numeric data — including the hero figure. All local
#: fallbacks — never a font fetch.
FONT_STACK = "'IBM Plex Sans', 'Aptos', 'Segoe UI', 'Noto Sans', 'DejaVu Sans', sans-serif"
FONT_STACK_DISPLAY = (
    "'IBM Plex Sans Condensed', 'Aptos Display', 'Segoe UI', "
    "'DejaVu Sans Condensed', sans-serif"
)
FONT_STACK_MONO = (
    "'IBM Plex Mono', 'Cascadia Mono', 'SFMono-Regular', 'DejaVu Sans Mono', "
    "Consolas, monospace"
)

TITLE_TEXT = "AI Collaboration Record"
MAX_PROVIDER_ROWS = 6

# Header: accent commit-node glyph + title + right-aligned status line
# ("<period> · snapshot <generated_on>"; ADR-031 — the date is a snapshot
# label, never a freshness or live-data claim).
HEADER_TEXT_Y = 36
GLYPH_CX = 32
GLYPH_CY = 32
TITLE_X = 48
TITLE_FONT_SIZE = 18
DIVIDER1_Y = 56
STATUS_SEPARATOR = " · snapshot "

# Metric console strip (ADR-031): one hero cell (AI-attributed commits,
# share line, share bar) plus four hairline-separated secondary cells on a
# shared baseline — sustained use, provider breadth, multi-actor depth, and
# the honest unattributed remainder, in that recruiter-facing order.
METRIC_STRIP_TOP = 72  # divider + 16: top of the hairline separators
METRIC_STRIP_BOTTOM = 176
HERO_CELL_WIDTH = 246  # hero cell: PADDING .. PADDING + HERO_CELL_WIDTH
HERO_VALUE_Y = 116
HERO_LABEL_Y = 140
HERO_RELATION_Y = 158
HERO_VALUE_SIZE = 40
SHARE_BAR_X = PADDING
SHARE_BAR_Y = 166
SHARE_BAR_WIDTH = HERO_CELL_WIDTH - 24  # 222: clears the first separator
SHARE_BAR_HEIGHT = 6
METRIC_CELL_COUNT = 4
METRIC_CELL_PAD_X = 14  # separator -> cell text
METRIC_VALUE_Y = 116  # secondary values share the hero's baseline
METRIC_LABEL_Y = 140
METRIC_SUBLABEL_Y = 156  # optional second label line (e.g. the day unit)
METRIC_VALUE_SIZE = 18
#: Left edge (separator x) of each secondary cell; the four cells share
#: the width right of the hero cell equally.
METRIC_CELL_WIDTH = (WIDTH - 2 * PADDING - HERO_CELL_WIDTH) // METRIC_CELL_COUNT  # 134

# Provider ledger (rendered BELOW the daily matrix — the matrix
# is the card's recruiter-facing centerpiece, ADR-022). The table's top
# depends on the daily block's height, so the row origin is a function
# (`_rows_top`), not a constant.
TABLE_LABEL_OFFSET = 12  # matrix bottom + CAL_GAP_BELOW -> table label baseline
ROWS_TOP_OFFSET = 16  # table label baseline -> first row top
ROW_HEIGHT = 28

# Provider identity tile (round D1 brand identity spec, "Provider row
# lockup"): a 20x20 rounded-rect glyph tile sits where the name used to
# start; the name shifts right to make room.
GLYPH_TILE_X = PADDING  # 24 - the old NAME_X
GLYPH_TILE_SIZE = 20
GLYPH_TILE_RADIUS = 4
GLYPH_TILE_Y_INSET = (ROW_HEIGHT - GLYPH_TILE_SIZE) // 2  # 4 - centers the tile in the row
GLYPH_RENDER_SIZE = 14  # glyph drawn at 14x14 inside the 20x20 tile
GLYPH_VIEWBOX_SIZE = 24  # BrandSpec.path is authored in a 24x24 viewBox
GLYPH_INSET = (GLYPH_TILE_SIZE - GLYPH_RENDER_SIZE) // 2  # 3 - centers the glyph in the tile
# GLYPH_RENDER_SIZE / GLYPH_VIEWBOX_SIZE (14/24) as a fixed literal: the
# transform attribute is outside the coordinate-hygiene regex (that test
# only polices x/y/x1/y1/x2/y2/width/height), but a literal string keeps
# the scale factor deterministic and readable without a runtime float format.
GLYPH_SCALE = "0.583333"
LETTER_TILE_CX = GLYPH_TILE_X + GLYPH_TILE_SIZE // 2  # 34 - horizontal tile center
LETTER_TILE_TEXT_DY = 14  # baseline offset from the tile's top y
LETTER_TILE_FONT_SIZE = 12

NAME_X = GLYPH_TILE_X + GLYPH_TILE_SIZE + 8  # 52 (spec: tile + 8px gap)
NAME_WIDTH = 120  # 4px scale: keeps the lockup column predictable
BAR_X = 184
COUNT_X = WIDTH - PADDING  # right edge for the percentage column and dividers
COUNT_VALUE_X = 748  # independent right-aligned count column
COUNT_PERCENT_X = COUNT_X  # independent right-aligned share column
BAR_MAX_WIDTH = 480  # 4px scale; leaves a readable gap before metric columns
BAR_HEIGHT = 7
NAME_FONT_SIZE = 13
COUNT_FONT_SIZE = 13

# Section marker: a quiet, non-accent editorial rule. Accent remains reserved
# for the hero, share fill, provider fills, and header mark (ADR-022).
SECTION_MARK_X = PADDING
SECTION_MARK_WIDTH = 2
SECTION_MARK_HEIGHT = 12
SECTION_MARK_RADIUS = 1
SECTION_MARK_GAP = 8
SECTION_RULE_WIDTH = 12

MORE_LINE_EXTRA = 24  # vertical room for the "+N providers not shown" line when present

#: Explicit non-exclusive statement for the provider ledger (ADR-022):
#: provider involvement totals overlap by definition, and the card says so
#: in place rather than leaving the reader to derive it from the footnote.
PROVIDER_NOTE_TEXT = (
    "Provider totals are not mutually exclusive - one commit can involve several providers."
)
PROVIDER_NOTE_BASELINE = 14  # rows bottom -> note baseline
PROVIDER_NOTE_EXTRA = 20  # vertical room the note adds below the rows

# Evidence rail: a compact rail replaces the former full-width
# provenance panel. `chip_bg` survives as a SMALL evidence-backed chip
# behind the rail label — an evidence cue, not a warning panel.
PANEL_GAP_ABOVE = 20
PANEL_PAD_X = 0  # the rail spans the full content width
PANEL_PAD_Y = 16
PANEL_HEIGHT = 104
EVIDENCE_CHIP_HEIGHT = 22
EVIDENCE_CHIP_PAD_X = 8
EVIDENCE_CHIP_RADIUS = 4
EVIDENCE_FONT_SIZE = 12
EVIDENCE_LABEL_SIZE = 12
FOOTER_FONT_SIZE = 12
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
# Collaboration Pulse (ADR-032; semantics from ADR-022/ADR-025). Rendered
# between the metric console and the provider table. The 84 published-window
# dates run OLDEST to NEWEST, left to right, as one baseline-anchored pulse
# signature — visually grouped as 12 groups of seven marks with a wider
# structural gap between groups (a 7-day rhythm, deliberately NOT labelled
# as calendar weeks). There is no 84-cell background heatmap grid.
#
# - PULSE HEIGHT encodes `DayCell.total_commits` through the fixed volume
#   bins 1 / 2-4 / 5-7 / 8+ (`_bins._volume_bin` -> PULSE_HEIGHTS) — the
#   owner's whole working rhythm, every commit regardless of attribution
#   (unattributed and explicitly human-declared included);
# - ACCENT FILL rises from the shared baseline and spatially maps the day's
#   AI-share bin (`_bins._share_bin`, 0..4) to 0/25/50/75/100% of the pulse
#   height. The fill uses the theme accent so the meaning is carried by
#   both position and hue — never color alone. A zero-attributed-AI day is
#   a pure neutral pulse: that is NOT a human claim (unattributed history
#   sits in that bin too).
# - A date with no publishable activity renders only a 2px baseline tick.
#
# Provider rows and counts NEVER contribute to pulse geometry: a
# one-commit multi-provider day renders byte-identically to a one-commit
# single-provider day (pinned in tests/unit/test_recruiter_card.py).
#
# The daily series is publishable-only (ADR-018): an empty series with
# nonzero headline totals renders the exact CAL_UNPUBLISHED_TEXT notice
# instead of a fabricated signature.
#
# Geometry is precomputed INTEGER arithmetic on purpose so coordinates and
# dimensions remain byte-stable and free of floating-point noise; every
# PULSE_HEIGHTS entry is a multiple of 4 so the quarter fills divide
# exactly.
# ---------------------------------------------------------------------------

CAL_GAP_BELOW = 20  # pulse block bottom -> provider-table label block
CAL_LABEL_BASELINE_Y = 14  # local y (band-relative) of the label's text baseline
PULSE_LABEL_TEXT = "Daily collaboration pulse · 12-week published window"

#: The exact honest message for a profile whose headline totals are
#: nonzero but whose daily series is unpublished (ADR-022).
CAL_UNPUBLISHED_TEXT = "Daily activity is not published for this profile"
CAL_NOTICE_MESSAGE_Y = 38  # local baseline of the unpublished-daily message
CAL_NOTICE_HEIGHT = 44  # total footprint of the unpublished-daily notice

#: Fixed y where the matrix block starts: the metric console strip above
#: it is fixed-height (METRIC_STRIP_BOTTOM = 176), plus a 24px section gap
#: on the 4px scale.
CAL_TOP = METRIC_STRIP_BOTTOM + 24

# Month-boundary labels sit in their own row between the band header and
# the pulse (mechanics retained from round D3 P2). PULSE_TOP_Y (below)
# derives from these so bumping either constant re-flows the whole
# band/legend/PULSE_BLOCK_HEIGHT automatically.
CAL_MONTH_LABEL_SIZE = 12
CAL_MONTH_LABEL_BASELINE_Y = 30  # local y of the month-label row's text baseline
CAL_MONTH_LABEL_GRID_GAP = 10  # month-label baseline -> pulse area top

PULSE_GROUPS = 12
PULSE_GROUP_DAYS = 7
CAL_WINDOW_DAYS = PULSE_GROUPS * PULSE_GROUP_DAYS  # 84 -- the pulse's OWN
# newest-anchored slice of the (D4: 365-day) viz.DAILY_WINDOW_DAYS series;
# gate-17 L-01

PULSE_MARK_W = 6  # activity mark width
PULSE_MARK_GAP = 2  # gap between marks inside a 7-day group
PULSE_GROUP_GAP = 10  # wider structural gap between the 12 groups
PULSE_GROUP_W = PULSE_GROUP_DAYS * PULSE_MARK_W + (PULSE_GROUP_DAYS - 1) * PULSE_MARK_GAP  # 54
PULSE_GROUP_PITCH = PULSE_GROUP_W + PULSE_GROUP_GAP  # 64
#: The pulse is left-aligned on the card margin (ADR-031 precision
#: alignment; the v0.8.0 weekday gutter is gone with the weekday labels).
PULSE_X = PADDING
PULSE_WIDTH = PULSE_GROUPS * PULSE_GROUP_PITCH - PULSE_GROUP_GAP  # 758

#: Fixed neutral pulse heights per volume bin (ADR-032): 1 -> 12px,
#: 2-4 -> 24px, 5-7 -> 36px, 8+ -> 48px. Indexed by `_bins._volume_bin`,
#: which shares the exact thresholds with the heatmap card. A documented
#: saturating top bin, not a silent clip: one outlier day cannot dwarf the
#: window or blow the card's fixed geometry budget. Every entry is a
#: multiple of PULSE_SHARE_LEVELS so quarter fills stay exact integers.
PULSE_HEIGHTS = (12, 24, 36, 48)
PULSE_MAX_HEIGHT = PULSE_HEIGHTS[-1]

#: `_bins._share_bin` levels (0..4) map to 0/25/50/75/100% of the pulse
#: height: fill_height = pulse_height * share_bin // PULSE_SHARE_LEVELS.
PULSE_SHARE_LEVELS = 4

#: A no-activity date renders only this 2px baseline tick.
PULSE_TICK_H = 2

#: Local (band-relative) y where the pulse area starts. Local y=0 is the
#: very top of the whole band; the label and month row sit above the marks.
PULSE_TOP_Y = CAL_MONTH_LABEL_BASELINE_Y + CAL_MONTH_LABEL_GRID_GAP  # 40
#: The shared baseline every mark bottom-anchors on (band-relative).
PULSE_BASELINE_Y = PULSE_TOP_Y + PULSE_MAX_HEIGHT  # 88

# Direct one-line legend under the pulse: both encodings and the standing
# publishable-only cue, stated in words instead of swatch rows.
PULSE_LEGEND_TEXT = (
    "height = total commits · fill = AI-attributed share · publishable dates only"
)
PULSE_LEGEND_TOP_GAP = 18  # baseline -> legend text baseline
PULSE_LEGEND_BOTTOM_PAD = 4  # legend baseline -> band bottom (descender clearance)

#: Local (band-relative) y of the legend row's text baseline.
PULSE_LEGEND_BASELINE_Y = PULSE_BASELINE_Y + PULSE_LEGEND_TOP_GAP  # 106

#: Total fixed footprint of the pulse block (label + month-label row +
#: pulse + legend); the notice variant occupies CAL_NOTICE_HEIGHT instead.
PULSE_BLOCK_HEIGHT = PULSE_LEGEND_BASELINE_Y + PULSE_LEGEND_BOTTOM_PAD  # 110

#: NO entrance animation - a deliberate REMOVAL, twice-earned during D2
#: visual verification (spec rule: honest > flashy):
#: 1. First attempt shipped `<g opacity="0">` + SMIL 0->1: renderers
#:    that ignore SMIL showed the band NEVER (static state = empty).
#: 2. Second attempt kept static opacity="1" with the same overriding
#:    animation: Chrome's PRINT pipeline (and any SMIL-aware static
#:    capture - screenshots, social previews) snapshots the timeline at
#:    t=0, where the animated value (0) overrides the static value ->
#:    the band was STILL invisible in every static capture, verified on
#:    a real PDF print.
#: Any from-nothing entrance has this structural problem: some real
#: consumer always captures t=0. The matrix is therefore fully static;
#: a future entrance must prove a t=0-visible capture first.

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
    family: str = FONT_STACK,
) -> str:
    body = content if escaped else escape(content)
    spacing_attr = f' letter-spacing="{letter_spacing}"' if letter_spacing is not None else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{spacing_attr}>{body}</text>'
    )


def _section_label(label: str, baseline_y: int, theme: Theme) -> str:
    """Render a section marker and label as one replaceable visual unit.

    The marker uses the border token rather than the accent token so the
    accent remains a data signal. Keeping this as a small pure helper makes
    the section grammar independently replaceable without touching metrics.
    """
    marker_y = baseline_y - SECTION_MARK_HEIGHT + 2
    return "\n".join(
        (
            _rect(
                SECTION_MARK_X,
                marker_y,
                SECTION_MARK_WIDTH,
                SECTION_MARK_HEIGHT,
                fill=theme.border,
                rx=SECTION_MARK_RADIUS,
            ),
            _line(
                SECTION_MARK_X + SECTION_MARK_WIDTH,
                baseline_y - SECTION_MARK_HEIGHT // 2,
                SECTION_MARK_X + SECTION_MARK_WIDTH + SECTION_RULE_WIDTH,
                baseline_y - SECTION_MARK_HEIGHT // 2,
                stroke=theme.border,
                stroke_opacity=0.65,
            ),
            _text(
                SECTION_MARK_X + SECTION_MARK_WIDTH + SECTION_RULE_WIDTH + SECTION_MARK_GAP,
                baseline_y,
                label,
                size=12,
                weight=600,
                fill=theme.muted,
                letter_spacing=0.2,
            ),
        )
    )


def _tspan(content: str, *, fill: str, weight: int = 400) -> str:
    return f'<tspan fill="{fill}" font-weight="{weight}">{escape(content)}</tspan>'


def _rect(
    x: float, y: float, w: float, h: float, *, fill: str, rx: float = 0, stroke: str | None = None
) -> str:
    stroke_attr = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{stroke_attr}/>'


def _line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str,
    stroke_opacity: float | None = None,
) -> str:
    opacity_attr = (
        f' stroke-opacity="{stroke_opacity}"' if stroke_opacity is not None else ""
    )
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"'
        f' stroke="{stroke}"{opacity_attr}/>'
    )


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


def _calendar_top(stats: VizStats) -> int:
    # The matrix block sits directly under the
    # fixed-height hero/ledger block (ADR-022 moved it above the provider
    # table). Kept as a function of stats for signature stability.
    del stats
    return CAL_TOP


def _timeline_block_height(stats: VizStats) -> int:
    """The daily pulse footprint: the full pulse block when a publishable
    daily series exists, the compact unpublished-daily notice otherwise
    (never zero — the zero state bypasses this layout entirely)."""
    return PULSE_BLOCK_HEIGHT if stats.daily else CAL_NOTICE_HEIGHT


def _table_label_y(stats: VizStats) -> int:
    return _calendar_top(stats) + _timeline_block_height(stats) + CAL_GAP_BELOW + TABLE_LABEL_OFFSET


def _rows_top(stats: VizStats) -> int:
    return _table_label_y(stats) + ROWS_TOP_OFFSET


def _rows_bottom(stats: VizStats) -> int:
    bottom = _rows_top(stats) + _visible_rows(stats) * ROW_HEIGHT
    if _has_more_line(stats):
        bottom += MORE_LINE_EXTRA
    return bottom


def _panel_top(stats: VizStats) -> int:
    # The evidence rail follows the provider ledger and its non-exclusive
    # note; every term is a pure function of the provider data shape.
    return _rows_bottom(stats) + PROVIDER_NOTE_EXTRA + PANEL_GAP_ABOVE


def card_height(stats: VizStats) -> int:
    """Deterministic card height: a pure function of the data shape."""
    if _is_zero_state(stats.totals):
        divider2_y = ZERO_BODY_BOTTOM
    else:
        divider2_y = _panel_top(stats) + PANEL_HEIGHT + FOOTER_GAP_ABOVE
    return divider2_y + FOOTER2_OFFSET + FOOTER_BOTTOM_PAD


def _calendar_desc_suffix(stats: VizStats) -> str:
    """One-line ASCII matrix summary appended to <desc>: the window span
    (anchored at the series' own newest date, never "today"), the peak
    day's total commits, and both encodings stated. The unpublished-daily
    state repeats the exact on-card notice so the accessible text and the
    visual text cannot disagree."""
    if not stats.daily:
        return f" {CAL_UNPUBLISHED_TEXT}."
    newest = datetime.date.fromisoformat(stats.daily[-1].date)
    window_start = newest - datetime.timedelta(days=CAL_WINDOW_DAYS - 1)
    # Peak over the matrix's OWN 84-day slice only: since D4 widened the
    # series to 365 days, an out-of-window day must not leak into this
    # window-scoped claim.
    peak_total = max(
        cell.total_commits
        for cell in stats.daily
        if cell.date >= window_start.isoformat()
    )
    return (
        f" Daily collaboration pulse {window_start.isoformat()} to {newest.isoformat()},"
        f" peak day {peak_total} commits; pulse height encodes total commits, accent fill"
        " height encodes the day's AI-attributed share; publishable dates only."
    )


def _desc_text(stats: VizStats, zero_state: bool) -> str:
    if zero_state:
        return f"No AI collaboration recorded yet. Generated {stats.generated_on}."
    t = stats.totals
    return (
        f"{t.ai_attributed_commits} AI-attributed commits, "
        f"{t.ai_actor_presences} AI actor presences across "
        f"{t.active_ai_days} active AI days (author dates), {stats.provider_count} AI providers."
        f"{_calendar_desc_suffix(stats)}"
        f" Generated {stats.generated_on}."
    )


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------


def _ledger_svg(stats: VizStats, theme: Theme) -> str:
    """The four secondary metric cells of the console strip (ADR-031).

    Order is the recruiter-facing priority (ADR-022): sustained use first,
    provider breadth second, then the multi-actor depth metric, then the
    honest unattributed remainder. Each cell is a hairline separator (border
    token, never accent), a mono value on the hero baseline, and a muted
    label; geometry is integer arithmetic on METRIC_CELL_WIDTH.
    """
    rows = (
        ("Active AI days", "(author dates)", stats.totals.active_ai_days),
        ("AI providers", "", stats.provider_count),
        ("AI actor presences", "", stats.totals.ai_actor_presences),
        ("Unattributed commits", "", stats.totals.unknown_commits),
    )
    label_width = METRIC_CELL_WIDTH - METRIC_CELL_PAD_X
    parts = []
    for index, (label, sublabel, value) in enumerate(rows):
        sep_x = PADDING + HERO_CELL_WIDTH + index * METRIC_CELL_WIDTH
        text_x = sep_x + METRIC_CELL_PAD_X
        parts.append(
            _line(sep_x, METRIC_STRIP_TOP, sep_x, METRIC_STRIP_BOTTOM, stroke=theme.border)
        )
        parts.append(
            _text(
                text_x,
                METRIC_VALUE_Y,
                str(value),
                size=METRIC_VALUE_SIZE,
                fill=theme.text,
                weight=600,
                family=FONT_STACK_MONO,
            )
        )
        parts.append(
            _text(
                text_x,
                METRIC_LABEL_Y,
                _truncate(label, label_width, 12),
                size=12,
                fill=theme.muted,
            )
        )
        if sublabel:
            parts.append(
                _text(
                    text_x,
                    METRIC_SUBLABEL_Y,
                    _truncate(sublabel, label_width, 12),
                    size=12,
                    fill=theme.muted,
                )
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
            # Numeric DATA renders in the mono stack (reviewer ruling,
            # Current type system; display type is reserved for the title.
            family=FONT_STACK_MONO,
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


def _brand_fg_tint(spec: BrandSpec, theme: Theme) -> tuple[str, str]:
    """Per-theme (fg, tint) hex pair for a vendored brand glyph tile."""
    if theme.name == "github-dark":
        return spec.dark_fg, spec.dark_tint
    return spec.light_fg, spec.light_tint


def _glyph_tile_svg(row: ProviderRow, theme: Theme, tile_y: int) -> tuple[str, str]:
    """One provider row's identity tile (round D1 spec "Provider row lockup"
    + "Fallback" sections). Returns ``(tile_svg, bar_fill)``: the bar fill
    is the brand FG for a branded row, ``theme.bar_fill`` for a fallback
    row — decided here so the caller never duplicates the branded/fallback
    branch.
    """
    spec = BRAND.get(row.provider)
    if spec is not None:
        fg, tint = _brand_fg_tint(spec, theme)
        glyph_x = GLYPH_TILE_X + GLYPH_INSET
        glyph_y = tile_y + GLYPH_INSET
        tile = "\n".join(
            (
                _rect(
                    GLYPH_TILE_X,
                    tile_y,
                    GLYPH_TILE_SIZE,
                    GLYPH_TILE_SIZE,
                    fill=tint,
                    rx=GLYPH_TILE_RADIUS,
                ),
                f'<path d="{spec.path}" fill="{fg}"'
                f' transform="translate({glyph_x},{glyph_y}) scale({GLYPH_SCALE})"/>',
            )
        )
        return tile, fg

    # Fallback tile (first-class, not an afterthought): neutral chip
    # background, muted letter, first letter of display_name uppercase -
    # or "?" for the reserved Unrecognized bucket.
    letter = "?" if row.provider == _UNRECOGNIZED_PROVIDER else row.display_name[:1].upper()
    letter_y = tile_y + LETTER_TILE_TEXT_DY
    tile = "\n".join(
        (
            _rect(
                GLYPH_TILE_X,
                tile_y,
                GLYPH_TILE_SIZE,
                GLYPH_TILE_SIZE,
                fill=theme.chip_bg,
                rx=GLYPH_TILE_RADIUS,
            ),
            _text(
                LETTER_TILE_CX,
                letter_y,
                letter,
                size=LETTER_TILE_FONT_SIZE,
                weight=600,
                fill=theme.muted,
                anchor="middle",
            ),
        )
    )
    return tile, theme.bar_fill


def _provider_row_svg(
    index: int, stats: VizStats, max_attributed: int, denominator: int, theme: Theme
) -> str:
    row = stats.providers[index]
    row_top = _rows_top(stats) + index * ROW_HEIGHT
    bar_y = row_top + 8
    text_y = row_top + 20
    tile_y = row_top + GLYPH_TILE_Y_INSET

    tile_svg, bar_fill = _glyph_tile_svg(row, theme, tile_y)

    name = _truncate(row.display_name, NAME_WIDTH, NAME_FONT_SIZE)
    elements = [
        tile_svg,
        _text(NAME_X, text_y, name, size=NAME_FONT_SIZE, fill=theme.text),
        _rect(BAR_X, bar_y, BAR_MAX_WIDTH, BAR_HEIGHT, fill=theme.bar_track, rx=2),
    ]
    if max_attributed > 0 and row.attributed_commits > 0:
        bar_w = round(BAR_MAX_WIDTH * row.attributed_commits / max_attributed)
        elements.append(_rect(BAR_X, bar_y, bar_w, BAR_HEIGHT, fill=bar_fill, rx=2))

    # Keep the count and percentage in independent right-aligned columns.
    # The old single text run made a three-digit count visually collide with
    # its percentage at README scale; separate columns preserve the exact
    # strings while giving both values a stable reading edge.
    count_span = _tspan(str(row.attributed_commits), fill=theme.text, weight=600)
    elements.append(
        f'<text x="{COUNT_VALUE_X}" y="{text_y}" font-family="{FONT_STACK_MONO}"'
        f' font-size="{COUNT_FONT_SIZE}" text-anchor="end">{count_span}</text>'
    )
    if denominator > 0:
        pct = _pct_label(row.attributed_commits, denominator)
        pct_span = _tspan(f" · {pct}", fill=theme.muted)
        elements.append(
            f'<text x="{COUNT_PERCENT_X}" y="{text_y}" font-family="{FONT_STACK_MONO}"'
            f' font-size="{COUNT_FONT_SIZE}" text-anchor="end">{pct_span}</text>'
        )
    if index < _visible_rows(stats) - 1:
        elements.append(
            _line(
                PADDING,
                row_top + ROW_HEIGHT,
                COUNT_X,
                row_top + ROW_HEIGHT,
                stroke=theme.border,
            )
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
    """The compact evidence rail: a small ``chip_bg`` label chip,
    the stacked evidence bar, its legend, and the privacy cue — no
    full-width surface. ``chip_bg`` deliberately survives only as the
    small evidence-backed chip."""
    e = stats.evidence
    inner_x = PADDING + PANEL_PAD_X
    inner_w = (WIDTH - 2 * PADDING) - 2 * PANEL_PAD_X
    bar_y = top + EVIDENCE_BAR_Y_OFFSET
    legend_y = top + EVIDENCE_LEGEND_Y_OFFSET
    prefix = EVIDENCE_PREFIX_TEMPLATE.format(n=e.total_records)
    chip_w = round(_text_width(prefix, EVIDENCE_LABEL_SIZE)) + 2 * EVIDENCE_CHIP_PAD_X
    parts = [
        _rect(
            inner_x,
            top,
            chip_w,
            EVIDENCE_CHIP_HEIGHT,
            fill=theme.chip_bg,
            rx=EVIDENCE_CHIP_RADIUS,
        ),
        _text(
            inner_x + EVIDENCE_CHIP_PAD_X,
            top + PANEL_PAD_Y,
            prefix,
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
        # the card surface (dataviz mark spec: surface gaps, not a track
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
        prefix_count = 0
        prev_end = 0
        for _, count, color in nonzero_segments:
            prefix_count += count
            end = round(available_w * prefix_count / e.total_records)
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
        _text(inner_x + 12, top + PRIVACY_Y_OFFSET, privacy_text, size=12, fill=theme.muted)
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Collaboration Pulse builders (ADR-032; semantics from ADR-022/ADR-025).
# ---------------------------------------------------------------------------

#: ASCII 3-letter English month abbreviations, index 0 = January (P2).
#: Never locale-dependent (ADR-010: fixed decimal/text formatting) and
#: never derived from the clock -- only ever indexed by a real
#: `datetime.date.month` computed from `stats.daily`.
_MONTH_ABBR = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def _pulse_day_cells(stats: VizStats) -> tuple[DayCell | None, ...]:
    """84-length tuple in oldest-to-newest offset order (index 0 = the
    window's oldest day, CAL_WINDOW_DAYS-1 = the series' own newest date)
    — ``None`` wherever there is no publishable activity for that date.
    A day that predates the series and a genuine zero-commit day inside
    the series are the SAME case here (both simply absent from
    ``stats.daily``, since VizStats forbids storing a zero-count DayCell):
    both render as the 2px baseline tick in ``_pulse_mark_svg``.
    """
    if not stats.daily:
        return (None,) * CAL_WINDOW_DAYS
    newest = datetime.date.fromisoformat(stats.daily[-1].date)
    by_date = {cell.date: cell for cell in stats.daily}
    return tuple(
        by_date.get((newest - datetime.timedelta(days=CAL_WINDOW_DAYS - 1 - offset)).isoformat())
        for offset in range(CAL_WINDOW_DAYS)
    )


def _pulse_mark_x(offset: int) -> int:
    """Left edge of the mark for a chronological window offset: 12 groups
    of seven marks, PULSE_MARK_GAP inside a group, the wider
    PULSE_GROUP_GAP between groups. Pure integer arithmetic."""
    group, member = divmod(offset, PULSE_GROUP_DAYS)
    return PULSE_X + group * PULSE_GROUP_PITCH + member * (PULSE_MARK_W + PULSE_MARK_GAP)


def _pulse_mark_svg(cell: DayCell | None, x: int, baseline_y: int, theme: Theme) -> str:
    """One baseline-anchored pulse mark carrying the daily encodings:

    - PULSE HEIGHT is the fixed volume bin of ``cell.total_commits``
      (PULSE_HEIGHTS via `_bins._volume_bin` — the heatmap's own
      1 / 2-4 / 5-7 / 8+ buckets), drawn as a neutral (muted) column;
    - the ACCENT FILL rises from the baseline to ``pulse_height *
      share_bin // PULSE_SHARE_LEVELS`` (`_bins._share_bin`, 0..4 ->
      0/25/50/75/100% of the pulse height). A zero-attributed-AI day
      keeps the pure neutral column — never a human claim, since
      unattributed history sits in that bin too.
    - ``None`` (no publishable activity) renders only a 2px baseline
      tick in the border token.

    Provider counts never reach this geometry: a one-commit multi-provider
    day renders byte-identically to a one-commit single-provider day.
    """
    if cell is None:
        return _rect(x, baseline_y - PULSE_TICK_H, PULSE_MARK_W, PULSE_TICK_H, fill=theme.border)
    height = PULSE_HEIGHTS[_volume_bin(cell.total_commits)]
    fill_h = height * _share_bin(cell.ai_commits, cell.total_commits) // PULSE_SHARE_LEVELS
    parts = [_rect(x, baseline_y - height, PULSE_MARK_W, height, fill=theme.muted)]
    if fill_h > 0:
        parts.append(_rect(x, baseline_y - fill_h, PULSE_MARK_W, fill_h, fill=theme.accent))
    return "\n".join(parts)


def _month_boundaries(dates: tuple[datetime.date, ...]) -> tuple[tuple[int, str], ...]:
    """Raw ``(col, 3-letter month label)`` pairs for every month BOUNDARY
    in an ordered, contiguous, oldest-to-newest date sequence (P2) -- col
    = index // PULSE_GROUP_DAYS, matching `_pulse_mark_x`'s own group
    math. A "boundary" is a transition INTO a new month: the sequence's
    own first (possibly partial) month is never a boundary, so a
    single-month input yields an empty tuple (falsifiable directly, no
    need to construct a real 84-day window to prove it). Deterministic in
    ``dates`` alone -- never `datetime.date.today()`; the caller is
    responsible for deriving ``dates`` from `stats.daily` only.
    """
    if not dates:
        return ()
    boundaries: list[tuple[int, str]] = []
    prev_month = dates[0].month
    for index, d in enumerate(dates):
        if d.month != prev_month:
            boundaries.append((index // PULSE_GROUP_DAYS, _MONTH_ABBR[d.month - 1]))
            prev_month = d.month
    return tuple(boundaries)


def _dedupe_colliding_month_labels(
    boundaries: tuple[tuple[int, str], ...],
) -> tuple[tuple[int, str], ...]:
    """Collision rule (P2, documented not just implemented): a boundary is
    DROPPED outright -- never shifted, abbreviated further, or allowed to
    overlap -- when it would land in the SAME group column as the
    immediately preceding KEPT label (not the raw previous boundary, so a
    run of 3+ same-column boundaries collapses to the first one rather
    than alternating). Real calendar months are always >= 28 days == >= 4
    seven-day groups apart, so this never actually fires on a real
    `stats.daily` window (see test_month_boundaries_span_three_to_four_months
    for the real-date case) -- it exists as a documented, independently
    falsifiable invariant, exercised directly with synthetic input.
    """
    kept: list[tuple[int, str]] = []
    for col, label in boundaries:
        if kept and kept[-1][0] == col:
            continue
        kept.append((col, label))
    return tuple(kept)


def _month_label_columns(stats: VizStats) -> tuple[tuple[int, str], ...]:
    """``(col, label)`` pairs to actually render (P2): derives the
    window's own contiguous date sequence purely from `stats.daily`'s
    newest date (never the clock -- same anchor `_pulse_day_cells`
    uses), then applies the boundary + collision rules above. Empty when
    there is no daily series."""
    if not stats.daily:
        return ()
    newest = datetime.date.fromisoformat(stats.daily[-1].date)
    window_start = newest - datetime.timedelta(days=CAL_WINDOW_DAYS - 1)
    dates = tuple(
        window_start + datetime.timedelta(days=offset) for offset in range(CAL_WINDOW_DAYS)
    )
    return _dedupe_colliding_month_labels(_month_boundaries(dates))


def _pulse_month_labels_svg(stats: VizStats, theme: Theme, top: int) -> str:
    """The month-boundary label row (P2), centered over the seven-day
    group in which the boundary date falls."""
    baseline_y = top + CAL_MONTH_LABEL_BASELINE_Y
    parts = [
        _text(
            PULSE_X + col * PULSE_GROUP_PITCH + PULSE_GROUP_W // 2,
            baseline_y,
            label,
            size=CAL_MONTH_LABEL_SIZE,
            fill=theme.muted,
            anchor="middle",
        )
        for col, label in _month_label_columns(stats)
    ]
    return "\n".join(parts)


def _pulse_legend_svg(theme: Theme, top: int) -> str:
    """The direct one-line legend (ADR-032): both encodings and the
    standing publishable-only cue stated in words, muted, on the 12px
    floor — no swatch rows, no ramp."""
    return _text(
        PADDING,
        top + PULSE_LEGEND_BASELINE_Y,
        PULSE_LEGEND_TEXT,
        size=12,
        fill=theme.muted,
    )


def _calendar_notice_svg(theme: Theme, top: int) -> str:
    """The unpublished-daily notice (ADR-022): the pulse section's label
    plus the exact CAL_UNPUBLISHED_TEXT message — rendered whenever the
    headline totals are nonzero but no daily series is published. Never a
    fabricated signature, never a warning panel."""
    return "\n".join(
        (
            _section_label(PULSE_LABEL_TEXT, top + CAL_LABEL_BASELINE_Y, theme),
            _text(
                WIDTH // 2,
                top + CAL_NOTICE_MESSAGE_Y,
                CAL_UNPUBLISHED_TEXT,
                size=12,
                fill=theme.muted,
                anchor="middle",
            ),
        )
    )


def _pulse_svg(stats: VizStats, theme: Theme, top: int) -> str:
    """The Collaboration Pulse: section label, month-boundary row, the 84
    chronological baseline-anchored marks, and the direct legend."""
    cells = _pulse_day_cells(stats)
    baseline_y = top + PULSE_BASELINE_Y
    marks_svg = "\n".join(
        _pulse_mark_svg(cells[offset], _pulse_mark_x(offset), baseline_y, theme)
        for offset in range(CAL_WINDOW_DAYS)
    )

    sections = (
        _section_label(PULSE_LABEL_TEXT, top + CAL_LABEL_BASELINE_Y, theme),
        _pulse_month_labels_svg(stats, theme, top),
        marks_svg,
        _pulse_legend_svg(theme, top),
    )
    return "\n".join(section for section in sections if section)


def render_summary(stats: VizStats, theme: Theme) -> str:
    """Render the summary card as SVG markup (ADR-010, ADR-022,
    architecture.md section 9).

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
        _text(
            TITLE_X,
            HEADER_TEXT_Y,
            TITLE_TEXT,
            size=TITLE_FONT_SIZE,
            weight=600,
            fill=theme.title,
            family=FONT_STACK_DISPLAY,
        )
    )
    # Status line (ADR-031): period + explicit snapshot date. The date is
    # the generation date already carried by VizStats; labelling it
    # "snapshot" states what it is without implying live data.
    parts.append(
        _text(
            WIDTH - PADDING,
            HEADER_TEXT_Y,
            f"{stats.period.label}{STATUS_SEPARATOR}{stats.generated_on}",
            size=12,
            fill=theme.muted,
            anchor="end",
            family=FONT_STACK_MONO,
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

        # Collaboration Pulse (ADR-032): the card's centerpiece, directly
        # under the headline block. An unpublished daily series renders
        # the exact honest notice instead.
        timeline_top = _calendar_top(stats)
        if stats.daily:
            parts.append(_pulse_svg(stats, theme, timeline_top))
        else:
            parts.append(_calendar_notice_svg(theme, timeline_top))

        # Provider ledger with an explicit percentage denominator
        # (proposal section 26 rule 6: percentages state their denominator).
        table_label_y = _table_label_y(stats)
        parts.append(
            _section_label("Attributed commits by provider", table_label_y, theme)
        )
        if stats.totals.ai_attributed_commits > 0:
            parts.append(
                _text(
                    WIDTH - PADDING,
                    table_label_y,
                    f"% of {stats.totals.ai_attributed_commits} AI-attributed commits",
                    size=12,
                    fill=theme.muted,
                    anchor="end",
                )
            )
        max_attributed = stats.providers[0].attributed_commits if stats.providers else 0
        denominator = stats.totals.ai_attributed_commits
        for i in range(_visible_rows(stats)):
            parts.append(_provider_row_svg(i, stats, max_attributed, denominator, theme))

        if _has_more_line(stats):
            more_y = _rows_top(stats) + MAX_PROVIDER_ROWS * ROW_HEIGHT + 16
            remaining = len(stats.providers) - MAX_PROVIDER_ROWS
            parts.append(
                _text(
                    PADDING,
                    more_y,
                    f"+{remaining} providers not shown",
                    size=12,
                    fill=theme.muted,
                )
            )

        # Explicit non-exclusive note (ADR-022).
        parts.append(
            _text(
                PADDING,
                _rows_bottom(stats) + PROVIDER_NOTE_BASELINE,
                PROVIDER_NOTE_TEXT,
                size=12,
                fill=theme.muted,
            )
        )

        panel_top = _panel_top(stats)
        parts.append(_evidence_panel_svg(stats, theme, panel_top))
        divider2_y = panel_top + PANEL_HEIGHT + FOOTER_GAP_ABOVE

    # Footer.
    parts.append(_line(PADDING, divider2_y, WIDTH - PADDING, divider2_y, stroke=theme.border))
    parts.append(
        _text(
            PADDING,
            divider2_y + FOOTER1_OFFSET,
            f"Generated {stats.generated_on} · aiprofile",
            size=FOOTER_FONT_SIZE,
            fill=theme.muted,
            family=FONT_STACK_MONO,
        )
    )
    parts.append(
        _text(
            PADDING,
            divider2_y + FOOTER2_OFFSET,
            FOOTNOTE,
            size=FOOTER_FONT_SIZE,
            fill=theme.muted,
        )
    )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"

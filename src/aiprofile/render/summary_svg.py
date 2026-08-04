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
from ._bins import VOLUME_CAP, _share_bin, _share_colors, _volume_bin
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
# Shared spacing system (introduced in v0.4.8 and retained in v0.4.9): 4px
# scale, 24px outer padding, 8-12px
# within-group gaps, 20-24px between sections. Fixed type sizes
# 11/12/13/16/38; weights 400 for labels, 600 for values/section labels,
# 700 for the hero figure.
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
LETTER_TILE_FONT_SIZE = 11

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
SECTION_MARK_WIDTH = 4
SECTION_MARK_HEIGHT = 12
SECTION_MARK_RADIUS = 2
SECTION_MARK_GAP = 8

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
# Flat collaboration timeline (ADR-025; semantics from ADR-022). Rendered
# between the secondary ledger and the provider table. Each published day is
# one compact 2D cell:
#
# - BAR HEIGHT encodes `DayCell.total_commits` through the fixed volume bins
#   0 / 1 / 2-4 / 5-7 / 8+ (`_bins._volume_bin` -> VOLUME_BAR_HEIGHTS) — the
#   owner's whole working rhythm, every commit regardless of attribution
#   (unattributed and explicitly human-declared included);
# - FILL HUE encodes the day's AI share (`ai_commits /
#   total_commits`) through the heatmap card's own fixed share bins
#   (`_bins._share_bin` -> `_bins._share_colors`).
#
# Provider rows and counts NEVER contribute to matrix geometry: a
# one-commit multi-provider day is exactly as tall as a one-commit
# single-provider day (pinned in tests/unit/test_recruiter_card.py).
#
# The daily series is publishable-only (ADR-018): an empty series with
# nonzero headline totals renders the exact CAL_UNPUBLISHED_TEXT notice
# instead of a fabricated grid.
#
# Geometry is precomputed INTEGER grid arithmetic on purpose so coordinates
# and dimensions remain byte-stable and free of floating-point noise.
# ---------------------------------------------------------------------------

CAL_GAP_BELOW = 20  # matrix bottom -> provider-table label block
CAL_LABEL_SIZE = 12
CAL_LABEL_BASELINE_Y = 14  # local y (band-relative) of the label's text baseline
CAL_LABEL_TEXT = "Daily collaboration (last 12 weeks)"

#: The exact honest message for a profile whose headline totals are
#: nonzero but whose daily series is unpublished (ADR-022).
CAL_UNPUBLISHED_TEXT = "Daily activity is not published for this profile"
CAL_NOTICE_MESSAGE_Y = 38  # local baseline of the unpublished-daily message
CAL_NOTICE_HEIGHT = 44  # total footprint of the unpublished-daily notice

#: Fixed y where the matrix block starts: the hero/ledger block above it
#: is fixed-height (share bar bottom 179 / ledger baseline 160), plus a
#: 24px section gap on the 4px scale.
CAL_TOP = 204

# Round D3 P2: month-boundary labels sit in their own row between the band
# header and the flat cell grid. CAL_GRID_TOP_Y (below) derives from these so
# bumping either constant here re-flows the whole grid/legend/CAL_HEIGHT
# automatically.
CAL_MONTH_LABEL_SIZE = 11
CAL_MONTH_LABEL_BASELINE_Y = 30  # local y of the month-label row's text baseline
CAL_MONTH_LABEL_GRID_GAP = 10  # month-label baseline -> grid top

CAL_WEEKS = 12
CAL_DAYS = 7
CAL_WINDOW_DAYS = CAL_WEEKS * CAL_DAYS  # 84 -- the matrix's OWN newest-anchored
# slice of the (D4: 365-day) viz.DAILY_WINDOW_DAYS series; gate-17 L-01

CAL_CELL_W = 38
CAL_CELL_H = 20
CAL_CELL_GAP = 6
CAL_BAR_INSET = 4
CAL_MAX_BAR_HEIGHT = 12

#: Fixed bar heights per volume bin (ADR-025): 1 -> 3px, 2-4 -> 6px,
#: 5-7 -> 9px, 8+ -> CAL_MAX_BAR_HEIGHT. Indexed by `_bins._volume_bin`,
#: which shares the exact thresholds with the heatmap card. A documented
#: saturating top bin, not a silent clip: one outlier day cannot dwarf the
#: window or blow the card's fixed geometry budget.
VOLUME_BAR_HEIGHTS = (3, 6, 9, CAL_MAX_BAR_HEIGHT)

#: The volume cap used by the shared render/_bins contract (8).
CAL_CAP_COMMITS = VOLUME_CAP

#: Local (band-relative) y where the matrix starts. Local y=0 is the very
#: top of the whole band; the label and month row sit above the cells.
CAL_GRID_TOP_Y = CAL_MONTH_LABEL_BASELINE_Y + CAL_MONTH_LABEL_GRID_GAP  # 40
CAL_GRID_WIDTH = CAL_WEEKS * CAL_CELL_W + (CAL_WEEKS - 1) * CAL_CELL_GAP
CAL_GRID_HEIGHT = CAL_DAYS * CAL_CELL_H + (CAL_DAYS - 1) * CAL_CELL_GAP
CAL_GRID_X = (WIDTH - CAL_GRID_WIDTH) // 2
CAL_GRID_BOTTOM_Y = CAL_GRID_TOP_Y + CAL_GRID_HEIGHT

# Flat legend: one compact line under the matrix stating both encodings:
# volume-bar bins, the five-step neutral-to-accent AI-share ramp, and the
# standing "publishable repos only" cue.
CAL_LEGEND_SWATCH = 10
CAL_LEGEND_LABEL_SIZE = 11
CAL_LEGEND_LABEL_GAP = 4
CAL_LEGEND_ITEM_GAP = 10
CAL_LEGEND_TOP_GAP = 18  # grid bottom -> legend baseline
CAL_LEGEND_BOTTOM_PAD = 4  # legend baseline -> band bottom (descender clearance)
CAL_LEGEND_GROUP_GAP = 12  # gap between the height group and the share group
CAL_LEGEND_RAMP_STEP = 4
CAL_LEGEND_CUE_TEXT = "publishable repos only"
CAL_LEGEND_HEIGHT_LABEL = "Volume"
CAL_LEGEND_SHARE_LABEL = "AI share"

#: Local (band-relative) y of the legend row's text baseline.
CAL_LEGEND_BASELINE_Y = CAL_GRID_BOTTOM_Y + CAL_LEGEND_TOP_GAP

#: Total fixed footprint of the daily matrix (label + month-label row + grid +
#: legend); the notice variant occupies CAL_NOTICE_HEIGHT instead.
CAL_HEIGHT = CAL_LEGEND_BASELINE_Y + CAL_LEGEND_BOTTOM_PAD

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
            _text(
                SECTION_MARK_X + SECTION_MARK_WIDTH + SECTION_MARK_GAP,
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
    """The daily matrix footprint: the full grid when a publishable
    daily series exists, the compact unpublished-daily notice otherwise
    (never zero — the zero state bypasses this layout entirely)."""
    return CAL_HEIGHT if stats.daily else CAL_NOTICE_HEIGHT


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
    # note; every term is a pure function of the data shape.
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
        f" Daily collaboration {window_start.isoformat()} to {newest.isoformat()},"
        f" peak day {peak_total} commits; bar height is total commits, fill is the day's"
        " AI share; publishable repositories only."
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
    # Secondary metric order is the recruiter-facing priority (ADR-022):
    # sustained use first, provider breadth second, then the multi-actor
    # depth metric, then the honest unattributed remainder.
    rows = (
        ("Active AI days (author dates)", stats.totals.active_ai_days),
        ("AI providers", stats.provider_count),
        ("AI actor presences", stats.totals.ai_actor_presences),
        ("Unattributed commits", stats.totals.unknown_commits),
    )
    parts = []
    for index, (label, value) in enumerate(rows):
        y = LEDGER_FIRST_Y + index * LEDGER_ROW_STEP
        parts.append(_text(LEDGER_LABEL_X, y, label, size=12, fill=theme.muted))
        parts.append(
            _text(
                LEDGER_VALUE_X,
                y,
                str(value),
                size=13,
                fill=theme.text,
                weight=600,
                anchor="end",
                family=FONT_STACK_MONO,
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
        _text(inner_x + 12, top + PRIVACY_Y_OFFSET, privacy_text, size=11, fill=theme.muted)
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Flat collaboration timeline builders (ADR-025; semantics from ADR-022).
# ---------------------------------------------------------------------------

#: ASCII 3-letter English month abbreviations, index 0 = January (P2).
#: Never locale-dependent (ADR-010: fixed decimal/text formatting) and
#: never derived from the clock -- only ever indexed by a real
#: `datetime.date.month` computed from `stats.daily`.
_MONTH_ABBR = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def _calendar_grid_cells(stats: VizStats) -> tuple[DayCell | None, ...]:
    """84-length tuple in oldest-to-newest offset order (index 0 = the
    window's oldest day, CAL_WINDOW_DAYS-1 = the series' own newest date)
    — ``None`` wherever there is no publishable activity for that date.
    A day that predates the series and a genuine zero-commit day inside
    the series are the SAME case here (both simply absent from
    ``stats.daily``, since VizStats forbids storing a zero-count DayCell):
    both render as the neutral track cell in ``_day_cell_svg``.
    """
    if not stats.daily:
        return (None,) * CAL_WINDOW_DAYS
    newest = datetime.date.fromisoformat(stats.daily[-1].date)
    by_date = {cell.date: cell for cell in stats.daily}
    return tuple(
        by_date.get((newest - datetime.timedelta(days=CAL_WINDOW_DAYS - 1 - offset)).isoformat())
        for offset in range(CAL_WINDOW_DAYS)
    )


def _day_cell_svg(cell: DayCell | None, cx: int, cy: int, theme: Theme) -> str:
    """One flat grid cell whose bottom bar carries the daily encodings:

    - BAR HEIGHT is the fixed volume bin of ``cell.total_commits``
      (VOLUME_BAR_HEIGHTS via `_bins._volume_bin` — the heatmap's own
      1 / 2-4 / 5-7 / 8+ buckets), and
    - FILL HUE is the fixed AI-share bin of ``cell.ai_commits /
      cell.total_commits`` (`_bins._share_bin` -> `_bins._share_colors`,
      neutral for a day with zero attributed AI commits — never a human
      claim, since unattributed history sits in that bin too — and accent
      for a day whose commits are all AI-attributed).

    Provider counts never reach this geometry: a one-commit multi-provider
    day renders byte-identically to a one-commit single-provider day.
    """
    cell_x = cx - CAL_CELL_W // 2
    cell_y = cy - CAL_CELL_H // 2
    parts = [_rect(cell_x, cell_y, CAL_CELL_W, CAL_CELL_H, fill=theme.bar_track, rx=4)]
    if cell is not None:
        height_px = VOLUME_BAR_HEIGHTS[_volume_bin(cell.total_commits)]
        color = _share_colors(theme)[_share_bin(cell.ai_commits, cell.total_commits)]
        bar_x = cell_x + CAL_BAR_INSET
        bar_y = cell_y + CAL_CELL_H - CAL_BAR_INSET - height_px
        bar_w = CAL_CELL_W - 2 * CAL_BAR_INSET
        parts.append(_rect(bar_x, bar_y, bar_w, height_px, fill=color, rx=2))
    return "\n".join(parts)


def _calendar_cell_position(offset: int) -> tuple[int, int, int, int]:
    """``(col, row, cx, cy)`` for a grid offset, cy relative to the band's
    own local origin (add the band's absolute top separately)."""
    col, row = offset // CAL_DAYS, offset % CAL_DAYS
    cx = CAL_GRID_X + col * (CAL_CELL_W + CAL_CELL_GAP) + CAL_CELL_W // 2
    cy = CAL_GRID_TOP_Y + row * (CAL_CELL_H + CAL_CELL_GAP) + CAL_CELL_H // 2
    return col, row, cx, cy


def _calendar_weekday_labels_svg(stats: VizStats, theme: Theme, top: int) -> str:
    """Render weekday labels aligned to the matrix's anchored window.

    The matrix is oldest-to-newest in seven-row weekday order, but its
    oldest date may begin on any weekday. Rotate the Monday-first vocabulary
    from that actual window start so the left rail never claims the wrong day.
    """
    newest = datetime.date.fromisoformat(stats.daily[-1].date)
    window_start = newest - datetime.timedelta(days=CAL_WINDOW_DAYS - 1)
    monday_first = ("M", "T", "W", "T", "F", "S", "S")
    labels = tuple(
        monday_first[(window_start.weekday() + row) % CAL_DAYS] for row in range(CAL_DAYS)
    )
    return "\n".join(
        _text(
            CAL_GRID_X - 8,
            top + CAL_GRID_TOP_Y + row * (CAL_CELL_H + CAL_CELL_GAP) + CAL_CELL_H // 2 + 4,
            label,
            size=11,
            fill=theme.muted,
            anchor="end",
        )
        for row, label in enumerate(labels)
    )


def _month_boundaries(dates: tuple[datetime.date, ...]) -> tuple[tuple[int, str], ...]:
    """Raw ``(col, 3-letter month label)`` pairs for every month BOUNDARY
    in an ordered, contiguous, oldest-to-newest date sequence (P2) -- col
    = index // CAL_DAYS, matching `_calendar_cell_position`'s own column
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
            boundaries.append((index // CAL_DAYS, _MONTH_ABBR[d.month - 1]))
            prev_month = d.month
    return tuple(boundaries)


def _dedupe_colliding_month_labels(
    boundaries: tuple[tuple[int, str], ...],
) -> tuple[tuple[int, str], ...]:
    """Collision rule (P2, documented not just implemented): a boundary is
    DROPPED outright -- never shifted, abbreviated further, or allowed to
    overlap -- when it would land in the SAME grid column as the
    immediately preceding KEPT label (not the raw previous boundary, so a
    run of 3+ same-column boundaries collapses to the first one rather
    than alternating). Real calendar months are always >= 28 days == >=
    4 CAL_DAYS-wide columns apart, so this never actually fires on a real
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
    newest date (never the clock -- same anchor `_calendar_grid_cells`
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


def _calendar_month_labels_svg(stats: VizStats, theme: Theme, top: int) -> str:
    """The month-boundary label row (P2), aligned to flat matrix columns."""
    baseline_y = top + CAL_MONTH_LABEL_BASELINE_Y
    parts = [
        _text(
            CAL_GRID_X + col * (CAL_CELL_W + CAL_CELL_GAP) + CAL_CELL_W // 2,
            baseline_y,
            label,
            size=CAL_MONTH_LABEL_SIZE,
            fill=theme.muted,
            anchor="middle",
        )
        for col, label in _month_label_columns(stats)
    ]
    return "\n".join(parts)


def _legend_bins(cap: int) -> tuple[tuple[int, str], ...]:
    """Up to 4 ``(representative_count, ASCII label)`` volume bins
    derived from ``cap`` (P1): "1", "2-{mid}", "{mid+1}-{cap-1}",
    "{cap}+" where ``mid = cap // 2`` -- e.g. cap=8 (CAL_CAP_COMMITS
    today) gives exactly "1", "2-4", "5-7", "8+", matching
    `_bins._volume_bin`'s own thresholds. Recomputed from ``cap`` alone
    (never a hand-typed literal): a smaller cap collapses degenerate
    ranges (low > high, e.g. cap=3's would-be "2-1") down to 2-3 bins
    automatically instead of emitting a bogus range."""
    mid = cap // 2
    candidates = ((1, 1), (2, mid), (mid + 1, cap - 1))
    bins: list[tuple[int, str]] = []
    for low, high in candidates:
        if low > high:
            continue
        label = str(low) if low == high else f"{low}-{high}"
        bins.append((high, label))
    bins.append((cap, f"{cap}+"))
    return tuple(bins)


def _calendar_legend_svg(theme: Theme, top: int) -> str:
    """The flat legend (ADR-025): volume swatches and a share ramp state the
    height bins over total commits, the five-step neutral-to-accent ramp
    stating the AI-share hue, and the standing "publishable repos only"
    cue. Every color is a theme token or a `_bins._share_colors` step —
    exactly the hexes real day bars use."""
    baseline_y = top + CAL_LEGEND_BASELINE_Y
    parts: list[str] = []
    x = PADDING
    parts.append(
        _text(x, baseline_y, CAL_LEGEND_HEIGHT_LABEL, size=CAL_LEGEND_LABEL_SIZE, fill=theme.muted)
    )
    x += round(_text_width(CAL_LEGEND_HEIGHT_LABEL, CAL_LEGEND_LABEL_SIZE)) + 8
    for height, (_, label) in zip(VOLUME_BAR_HEIGHTS, _legend_bins(CAL_CAP_COMMITS), strict=True):
        swatch_y = baseline_y - height + 2
        parts.append(
            _rect(x, swatch_y, CAL_LEGEND_SWATCH, height, fill=theme.muted, rx=2)
        )
        label_x = x + CAL_LEGEND_SWATCH + CAL_LEGEND_LABEL_GAP
        parts.append(
            _text(label_x, baseline_y, label, size=CAL_LEGEND_LABEL_SIZE, fill=theme.muted)
        )
        x = label_x + round(_text_width(label, CAL_LEGEND_LABEL_SIZE)) + CAL_LEGEND_ITEM_GAP
    x += CAL_LEGEND_GROUP_GAP
    parts.append(
        _text(x, baseline_y, CAL_LEGEND_SHARE_LABEL, size=CAL_LEGEND_LABEL_SIZE, fill=theme.muted)
    )
    x += round(_text_width(CAL_LEGEND_SHARE_LABEL, CAL_LEGEND_LABEL_SIZE)) + 8
    parts.append(_text(x, baseline_y, "0%", size=CAL_LEGEND_LABEL_SIZE, fill=theme.muted))
    x += round(_text_width("0%", CAL_LEGEND_LABEL_SIZE)) + 6
    for color in _share_colors(theme):
        parts.append(
            _rect(
                x,
                baseline_y - CAL_LEGEND_SWATCH + 2,
                CAL_LEGEND_SWATCH,
                CAL_LEGEND_SWATCH,
                fill=color,
                rx=2,
            )
        )
        x += CAL_LEGEND_SWATCH + CAL_LEGEND_RAMP_STEP
    x += CAL_LEGEND_LABEL_GAP
    parts.append(_text(x, baseline_y, "100%", size=CAL_LEGEND_LABEL_SIZE, fill=theme.muted))
    parts.append(
        _text(
            WIDTH - PADDING,
            baseline_y,
            CAL_LEGEND_CUE_TEXT,
            size=CAL_LEGEND_LABEL_SIZE,
            fill=theme.muted,
            anchor="end",
        )
    )
    return "\n".join(parts)


def _calendar_notice_svg(theme: Theme, top: int) -> str:
    """The unpublished-daily notice (ADR-022): the matrix section's label
    plus the exact CAL_UNPUBLISHED_TEXT message — rendered whenever the
    headline totals are nonzero but no daily series is published. Never a
    fabricated grid, never a warning panel."""
    return "\n".join(
        (
            _section_label(CAL_LABEL_TEXT, top + CAL_LABEL_BASELINE_Y, theme),
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


def _calendar_svg(stats: VizStats, theme: Theme, top: int) -> str:
    """The flat daily matrix and two-encoding legend."""
    cells = _calendar_grid_cells(stats)
    cells_svg = []
    for offset in range(CAL_WINDOW_DAYS):
        _, _, cx, cy = _calendar_cell_position(offset)
        cells_svg.append(_day_cell_svg(cells[offset], cx, top + cy, theme))

    sections = (
        _section_label(CAL_LABEL_TEXT, top + CAL_LABEL_BASELINE_Y, theme),
        _calendar_month_labels_svg(stats, theme, top),
        _calendar_weekday_labels_svg(stats, theme, top),
        "\n".join(cells_svg),
        _calendar_legend_svg(theme, top),
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
            size=16,
            weight=600,
            fill=theme.title,
            family=FONT_STACK_DISPLAY,
        )
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

        # Flat daily collaboration matrix (ADR-025): the card's
        # centerpiece, directly under the headline block. An unpublished
        # daily series renders the exact honest notice instead.
        timeline_top = _calendar_top(stats)
        if stats.daily:
            parts.append(_calendar_svg(stats, theme, timeline_top))
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
                    size=11,
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
                size=11,
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
            size=11,
            fill=theme.muted,
            family=FONT_STACK_MONO,
        )
    )
    parts.append(_text(PADDING, divider2_y + FOOTER2_OFFSET, FOOTNOTE, size=11, fill=theme.muted))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"

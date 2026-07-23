"""Deterministic summary card SVG renderer (ADR-010, architecture.md section 9).

`render_summary(stats, theme)` is a pure function of its two arguments: no
clock reads, no randomness, no locale-dependent formatting. Byte-identical
output for identical inputs is a pinned test (mvp.md section 7 test 11).

Layout is dynamic-but-deterministic: the card height is a pure function of
the data (number of provider rows, overflow line, zero state) so sparse
profiles never show a dead band — see `card_height`.

Module graph is enforced by a separate unit test (architecture.md section 2):
this module may import stdlib plus `aiprofile.viz`, `aiprofile.render.themes`,
`aiprofile.render.brand`, and `aiprofile.errors` only — never storage,
gitio, schema, or sqlite3. `render.brand` (round D1, ADR-017) is the vendored
provider-glyph table; it is a sibling render-package module, not a schema
import, so it does not cross the isolation boundary.
"""

from __future__ import annotations

import datetime
from xml.sax.saxutils import escape

from ..viz import DayCell, ProviderRow, Totals, VizStats
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

# Provider identity tile (round D1 brand identity spec, "Provider row
# lockup"): a 20x20 rounded-rect glyph tile sits where the name used to
# start; the name shifts right to make room. BAR_X, COUNT_X, ROW_HEIGHT are
# unchanged (minimal geometry churn per the spec).
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
NAME_WIDTH = 122  # 150 - 28 (spec: NAME_WIDTH shrinks by 28)
BAR_X = 184
COUNT_X = WIDTH - PADDING  # right anchor for "count · pct%"
BAR_MAX_WIDTH = 500  # COUNT_X - reserved count column (110) - gap (12) - BAR_X
BAR_HEIGHT = 7
NAME_FONT_SIZE = 13
COUNT_FONT_SIZE = 13

MORE_LINE_EXTRA = 24  # vertical room for the "+N providers not shown" line when present

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
# Isometric daily-activity calendar band (round D2, ADR-018,
# .ai/round_d2_isometric_calendar_spec.md "Renderer" section). Rendered
# between the provider rows and the evidence panel, ONLY when
# `stats.daily` is non-empty — an empty series omits the band entirely
# and every geometry constant below drops out of the layout, so a
# no-daily card stays byte-identical to the pre-D2 renderer (pinned by
# tests/unit/test_calendar_band.py::test_empty_daily_omits_band_and_matches_pre_d2_geometry).
#
# Geometry is precomputed INTEGER affine arithmetic on purpose: every
# constant here (tile half-extents, the stack-height cap, the grid
# origin) is an int, and col/row/elevation are always ints too, so a
# <polygon> "points" list can never carry floating-point noise — the
# same "no float noise" discipline test_coordinate_hygiene_no_float_noise
# enforces on x/y/width/height (that regex does not reach "points";
# test_calendar_band.py::test_polygon_points_carry_no_float_noise pins the
# same invariant for the new element).
# ---------------------------------------------------------------------------

CAL_GAP_ABOVE = 20  # rows/"+N providers not shown" bottom -> label top (mirrors PANEL_GAP_ABOVE)
CAL_GAP_BELOW = 20  # calendar bottom -> evidence panel top (mirrors PANEL_GAP_ABOVE)
CAL_LABEL_SIZE = 12
CAL_LABEL_BASELINE_Y = 14  # local y (band-relative) of the label's text baseline
CAL_LABEL_TEXT = "Daily AI collaboration (last 84 days)"

# Round D3 P2: month-boundary labels sit in their own row between the band
# header and the diamond grid. CAL_GRID_TOP_Y (below) derives from these so
# bumping either constant here re-flows the whole grid/legend/CAL_HEIGHT
# automatically -- the same "everything downstream recomputes" discipline
# the original D2 layout uses for CAL_GRID_TOP_Y itself.
CAL_MONTH_LABEL_SIZE = 11
CAL_MONTH_LABEL_BASELINE_Y = 30  # local y of the month-label row's text baseline
CAL_MONTH_LABEL_GRID_GAP = 10  # month-label baseline -> grid top

CAL_WEEKS = 12
CAL_DAYS = 7
CAL_WINDOW_DAYS = CAL_WEEKS * CAL_DAYS  # 84 -- matches viz.DAILY_WINDOW_DAYS exactly

CAL_TILE_HW = 18  # isometric tile half-width
CAL_TILE_HH = 9  # isometric tile half-height (2:1 diamond ratio)
CAL_MAX_STACK_PX = 32  # column height at CAL_CAP_COMMITS attributed commits
#: A day with >= this many attributed commits (summed across providers)
#: renders at the full CAL_MAX_STACK_PX column height. Documented cap, not
#: a silent clip: one outlier day cannot dwarf the rest of the 84-day
#: window or blow out the card's fixed geometry budget.
CAL_CAP_COMMITS = 8

#: Local (band-relative) y where the grid starts: high enough that even a
#: full-height column at (col=0, row=0) never draws above y=0 within the
#: band. Local y=0 is the very top of the whole band (the label's own
#: baseline sits below it, at CAL_LABEL_BASELINE_Y). Round D3 P2 moved this
#: from a bare literal (24) to a derived value: the month-label row now
#: owns the space between the band header and the grid.
CAL_GRID_TOP_Y = CAL_MONTH_LABEL_BASELINE_Y + CAL_MONTH_LABEL_GRID_GAP  # 40
CAL_GRID_BOTTOM_MARGIN = 6

#: Bounding box of the flat (unraised) diamond grid, in a LOCAL x space
#: centered on nothing in particular (col=0,row=0 sits at local x=0) --
#: used only to size/center the grid; final absolute x adds CAL_X_OFFSET.
CAL_LEFTMOST_LOCAL_X = -(CAL_DAYS - 1) * CAL_TILE_HW - CAL_TILE_HW  # -126
CAL_RIGHTMOST_LOCAL_X = (CAL_WEEKS - 1) * CAL_TILE_HW + CAL_TILE_HW  # 216
#: Centers the grid horizontally within the card (integer floor division;
#: WIDTH/tile constants are fixed, so this is a deterministic constant).
CAL_X_OFFSET = WIDTH // 2 - (CAL_LEFTMOST_LOCAL_X + CAL_RIGHTMOST_LOCAL_X) // 2

#: Shifts the grid's own (col=0, row=0, elevation=0) tile center so that
#: the topmost possible point (col=0, row=0, full CAL_MAX_STACK_PX column)
#: lands exactly at CAL_GRID_TOP_Y.
CAL_ORIGIN_Y = CAL_GRID_TOP_Y + CAL_TILE_HH + CAL_MAX_STACK_PX

#: Bottommost point of the grid (col=CAL_WEEKS-1, row=CAL_DAYS-1, elevation 0).
CAL_GRID_BOTTOM_Y = CAL_ORIGIN_Y + (CAL_WEEKS - 1 + CAL_DAYS - 1) * CAL_TILE_HH + CAL_TILE_HH

# Round D3 P1: a compact single-line intensity legend sits under the grid
# (CAL_CAP_COMMITS-derived bins, see `_legend_bins`) plus the "publishable
# repos only" cue. CAL_LEGEND_ROW_HEIGHT is the NAMED constant CAL_HEIGHT
# grows by -- the legend renders only inside the same `if stats.daily:`
# branch as the rest of the band, so an empty-daily card never sees it.
CAL_LEGEND_TILE_HW = 6  # legend diamond half-width (smaller than a grid tile)
CAL_LEGEND_TILE_HH = 3  # legend diamond half-height (2:1 ratio, matches CAL_TILE_HW/HH)
CAL_LEGEND_LABEL_SIZE = 11
CAL_LEGEND_LABEL_GAP = 4  # a diamond's right edge -> its own label's x
CAL_LEGEND_ITEM_GAP = 14  # one bin's label -> the next bin's diamond
CAL_LEGEND_DIAMOND_DY = -4  # diamond center, relative to the legend baseline
CAL_LEGEND_TOP_GAP = 14  # grid-bottom margin -> legend baseline
CAL_LEGEND_BOTTOM_PAD = 4  # legend baseline -> band bottom (descender clearance)
CAL_LEGEND_ROW_HEIGHT = CAL_LEGEND_TOP_GAP + CAL_LEGEND_BOTTOM_PAD  # the named growth constant
CAL_LEGEND_CUE_TEXT = "publishable repos only"

#: Local (band-relative) y of the legend row's text baseline.
CAL_LEGEND_BASELINE_Y = CAL_GRID_BOTTOM_Y + CAL_GRID_BOTTOM_MARGIN + CAL_LEGEND_TOP_GAP

#: Fixed literal fill-opacity per bin index (never computed/blended, same
#: discipline as CAL_FACE_OPACITY_*): all legend diamonds share the SAME
#: theme.muted fill and are distinguished only by opacity, lightest bin
#: first. Never indexed past its own length (`_legend_bins` never returns
#: more than 4 bins).
CAL_LEGEND_OPACITIES = (0.35, 0.55, 0.75, 1.0)

#: Total fixed footprint of the band (label + month-label row + grid +
#: legend); added to the layout only when stats.daily is non-empty.
CAL_HEIGHT = CAL_LEGEND_BASELINE_Y + CAL_LEGEND_BOTTOM_PAD

#: Isometric face shading -- same flat token color for all three faces of a
#: column, distinguished only by fill-opacity (never a computed/blended
#: hex): top face full strength, the two side "walls" progressively
#: dimmer, giving a 3D cube read without introducing any new color value.
CAL_FACE_OPACITY_TOP = 1
CAL_FACE_OPACITY_LEFT = 0.72
CAL_FACE_OPACITY_RIGHT = 0.5

#: SMIL entrance (spec: "grow-in ... only if deterministic + byte-stable").
#: Fixed literal dur/begin, one-shot (SMIL's default repeatCount is 1 --
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
#: consumer always captures t=0. The calendar band is therefore fully
#: static; a future entrance must prove a t=0-visible capture first.

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


def _rows_bottom(stats: VizStats) -> int:
    bottom = ROWS_TOP + _visible_rows(stats) * ROW_HEIGHT
    if _has_more_line(stats):
        bottom += MORE_LINE_EXTRA
    return bottom


def _calendar_top(stats: VizStats) -> int:
    return _rows_bottom(stats) + CAL_GAP_ABOVE


def _panel_top(stats: VizStats) -> int:
    # Round D2: when a publishable daily series exists, the calendar band
    # sits between the provider rows and the evidence panel, and the panel
    # shifts down by the band's fixed height. When stats.daily is empty
    # this branch is never taken, so _rows_bottom(stats) + PANEL_GAP_ABOVE
    # is EXACTLY the pre-D2 expression — zero geometry shift, byte-identical
    # output for a no-daily card (pinned by test_calendar_band.py).
    if stats.daily:
        return _calendar_top(stats) + CAL_HEIGHT + CAL_GAP_BELOW
    return _rows_bottom(stats) + PANEL_GAP_ABOVE


def card_height(stats: VizStats) -> int:
    """Deterministic card height: a pure function of the data shape."""
    if _is_zero_state(stats.totals):
        divider2_y = ZERO_BODY_BOTTOM
    else:
        divider2_y = _panel_top(stats) + PANEL_HEIGHT + FOOTER_GAP_ABOVE
    return divider2_y + FOOTER2_OFFSET + FOOTER_BOTTOM_PAD


def _calendar_desc_suffix(stats: VizStats) -> str:
    """One-line ASCII calendar summary appended to <desc> (round D2 spec
    item 5): the window span (anchored at the series' own newest date,
    never "today") plus the peak day's total attributed commits. Empty
    string when there is no daily series to summarize."""
    if not stats.daily:
        return ""
    newest = datetime.date.fromisoformat(stats.daily[-1].date)
    window_start = newest - datetime.timedelta(days=CAL_WINDOW_DAYS - 1)
    peak = max(sum(dc.attributed_commits for dc in cell.counts) for cell in stats.daily)
    return (
        f" Daily activity calendar {window_start.isoformat()} to {newest.isoformat()},"
        f" peak day {peak} attributed commits."
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
    row_top = ROWS_TOP + index * ROW_HEIGHT
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


# ---------------------------------------------------------------------------
# Isometric calendar band builders (round D2, ADR-018; round D3 P1/P2
# card-polish additions live alongside it, same module section).
# ---------------------------------------------------------------------------

#: ASCII 3-letter English month abbreviations, index 0 = January (P2).
#: Never locale-dependent (ADR-010: fixed decimal/text formatting) and
#: never derived from the clock -- only ever indexed by a real
#: `datetime.date.month` computed from `stats.daily`.
_MONTH_ABBR = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def _calendar_color(provider: str, theme: Theme) -> str:
    """Same branded/fallback/unrecognized precedence as the provider table
    (`_glyph_tile_svg`'s bar_fill), reused for calendar column segments so
    a provider's color reads identically in the table and the calendar."""
    spec = BRAND.get(provider)
    if spec is not None:
        return _brand_fg_tint(spec, theme)[0]
    if provider == _UNRECOGNIZED_PROVIDER:
        return theme.evidence_unknown
    return theme.bar_fill


def _calendar_grid_cells(stats: VizStats) -> tuple[DayCell | None, ...]:
    """84-length tuple in oldest-to-newest offset order (index 0 = the
    window's oldest day, CAL_WINDOW_DAYS-1 = the series' own newest date)
    — ``None`` wherever there is no publishable activity for that date.
    Per the spec, a day that predates the series and a genuine zero-commit
    day inside the series are the SAME case here (both simply absent from
    ``stats.daily``, since VizStats forbids storing a zero-count DayCell):
    both render as the flat base diamond in ``_day_cell_svg``.
    """
    if not stats.daily:
        return (None,) * CAL_WINDOW_DAYS
    newest = datetime.date.fromisoformat(stats.daily[-1].date)
    by_date = {cell.date: cell for cell in stats.daily}
    return tuple(
        by_date.get((newest - datetime.timedelta(days=CAL_WINDOW_DAYS - 1 - offset)).isoformat())
        for offset in range(CAL_WINDOW_DAYS)
    )


def _iso_tile_corners(
    cx: int, cy: int, elevation: int
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
    """(top, right, bottom, left) corners of the diamond tile centered at
    ``(cx, cy)``, raised ``elevation`` px (screen-space vertical extrusion —
    the standard flat-shaded approximation for an isometric column)."""
    y = cy - elevation
    return (
        (cx, y - CAL_TILE_HH),
        (cx + CAL_TILE_HW, y),
        (cx, y + CAL_TILE_HH),
        (cx - CAL_TILE_HW, y),
    )


def _polygon(
    points: tuple[tuple[int, int], ...], *, fill: str, opacity: float | None = None
) -> str:
    pts = " ".join(f"{x},{y}" for x, y in points)
    has_opacity = opacity is not None and opacity != 1
    opacity_attr = f' fill-opacity="{opacity}"' if has_opacity else ""
    return f'<polygon points="{pts}" fill="{fill}"{opacity_attr}/>'


def _day_cell_svg(cell: DayCell | None, cx: int, cy: int, theme: Theme) -> str:
    """One grid cell: a flat base diamond (zero/no-data day) or a stacked
    isometric column — one prism "layer" per provider, bottom to top in
    the cell's own slug-ascending order (the VizStats-enforced order),
    each layer's height proportional to its share of the day's (capped)
    total. Segment heights use the same cumulative-prefix-rounding trick
    as `_evidence_panel_svg` (gate-6 finding): independently rounding each
    segment can drift or go negative; rounding the running prefix keeps
    every layer >= 0px and the layers sum exactly to the column height.
    """
    if cell is None:
        top, right, bottom, left = _iso_tile_corners(cx, cy, 0)
        return _polygon((top, right, bottom, left), fill=theme.bar_track)

    total = sum(dc.attributed_commits for dc in cell.counts)
    scaled = min(total, CAL_CAP_COMMITS)
    height_px = round(CAL_MAX_STACK_PX * scaled / CAL_CAP_COMMITS)

    parts: list[str] = []
    prev_end = 0
    prefix = 0
    for dc in cell.counts:
        prefix += dc.attributed_commits
        end = round(height_px * prefix / total)
        if end > prev_end:
            color = _calendar_color(dc.provider, theme)
            _, right0, bottom0, left0 = _iso_tile_corners(cx, cy, prev_end)
            _, right1, bottom1, left1 = _iso_tile_corners(cx, cy, end)
            parts.append(
                _polygon(
                    (left1, bottom1, bottom0, left0), fill=color, opacity=CAL_FACE_OPACITY_LEFT
                )
            )
            parts.append(
                _polygon(
                    (bottom1, right1, right0, bottom0), fill=color, opacity=CAL_FACE_OPACITY_RIGHT
                )
            )
        prev_end = end

    # The cap (top face) always sits at the FINAL height_px regardless of
    # whether the last provider's own slice rounded to 0px — its color
    # still represents the top of the stack (cell.counts is non-empty and
    # slug-ascending, enforced by VizStats validation).
    top_color = _calendar_color(cell.counts[-1].provider, theme)
    top1, right1, bottom1, left1 = _iso_tile_corners(cx, cy, height_px)
    parts.append(
        _polygon((top1, right1, bottom1, left1), fill=top_color, opacity=CAL_FACE_OPACITY_TOP)
    )
    return "\n".join(parts)


def _calendar_cell_position(offset: int) -> tuple[int, int, int, int]:
    """``(col, row, cx, cy)`` for a grid offset, cy relative to the band's
    own local origin (add the band's absolute top separately)."""
    col, row = offset // CAL_DAYS, offset % CAL_DAYS
    cx = CAL_X_OFFSET + (col - row) * CAL_TILE_HW
    cy = CAL_ORIGIN_Y + (col + row) * CAL_TILE_HH
    return col, row, cx, cy


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
    `stats.daily` window (see test_month_labels_span_three_to_four_months
    for the real-date case) -- it exists as a documented, independently
    falsifiable invariant, exercised directly here with synthetic input.
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
    """The month-boundary label row (P2), rendered between the band header
    and the diamond grid (see CAL_MONTH_LABEL_BASELINE_Y). Each label
    anchors at its month's own first visible column, using that column's
    row=0 x (the top/left-most point of its isometric skew)."""
    baseline_y = top + CAL_MONTH_LABEL_BASELINE_Y
    parts = [
        _text(
            CAL_X_OFFSET + col * CAL_TILE_HW,
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
    """Up to 4 ``(representative_count, ASCII label)`` intensity bins
    derived from ``cap`` (P1): "1", "2-{mid}", "{mid+1}-{cap-1}",
    "{cap}+" where ``mid = cap // 2`` -- e.g. cap=8 (CAL_CAP_COMMITS
    today) gives exactly "1", "2-4", "5-7", "8+". Recomputed from ``cap``
    alone (never a hand-typed literal), so a future CAL_CAP_COMMITS change
    keeps the legend true: a smaller cap collapses degenerate ranges
    (low > high, e.g. cap=3's would-be "2-1") down to 2-3 bins
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


def _legend_diamond_points(cx: int, cy: int) -> tuple[tuple[int, int], ...]:
    """(top, right, bottom, left) corners of a flat legend diamond
    centered at ``(cx, cy)`` -- same 2:1 shape as the grid tiles, sized by
    the smaller CAL_LEGEND_TILE_HW/HH constants (P1, no elevation: the
    legend never stacks)."""
    return (
        (cx, cy - CAL_LEGEND_TILE_HH),
        (cx + CAL_LEGEND_TILE_HW, cy),
        (cx, cy + CAL_LEGEND_TILE_HH),
        (cx - CAL_LEGEND_TILE_HW, cy),
    )


def _calendar_legend_svg(theme: Theme, top: int) -> str:
    """The compact single-line intensity legend (P1): CAL_CAP_COMMITS
    -derived bins (`_legend_bins`) so it stays true if the cap changes,
    plus the "publishable repos only" cue. Diamonds are uniform size and
    share theme.muted, distinguished only by CAL_LEGEND_OPACITIES (never a
    new hex value -- same discipline as CAL_FACE_OPACITY_*)."""
    baseline_y = top + CAL_LEGEND_BASELINE_Y
    diamond_cy = baseline_y + CAL_LEGEND_DIAMOND_DY
    parts: list[str] = []
    x = PADDING
    for index, (_, label) in enumerate(_legend_bins(CAL_CAP_COMMITS)):
        opacity = CAL_LEGEND_OPACITIES[min(index, len(CAL_LEGEND_OPACITIES) - 1)]
        cx = x + CAL_LEGEND_TILE_HW
        parts.append(
            _polygon(_legend_diamond_points(cx, diamond_cy), fill=theme.muted, opacity=opacity)
        )
        label_x = cx + CAL_LEGEND_TILE_HW + CAL_LEGEND_LABEL_GAP
        parts.append(
            _text(label_x, baseline_y, label, size=CAL_LEGEND_LABEL_SIZE, fill=theme.muted)
        )
        x = label_x + round(_text_width(label, CAL_LEGEND_LABEL_SIZE)) + CAL_LEGEND_ITEM_GAP
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


def _calendar_svg(stats: VizStats, theme: Theme, top: int) -> str:
    """The calendar band: an always-visible label, the month-boundary row
    (P2), the isometric grid, and the intensity legend (P1) -- fully
    STATIC (see the no-entrance-animation note in the constants section -
    two animation attempts each left the band invisible in static
    captures). ``top`` is the band's absolute y (see `_calendar_top`);
    all local y math from the constants section is offset by it here,
    once.
    """
    cells = _calendar_grid_cells(stats)
    # Painter's algorithm: cells must be drawn back-to-front (ascending
    # depth = col+row) or a tall column can visually occlude — or be
    # wrongly occluded by — a neighboring column drawn out of order, since
    # adjacent diamonds share an edge and a raised column overlaps into
    # its back neighbors' screen space. The offset order used to look up
    # dates (column-major) is unrelated and NOT depth order, so it is
    # re-sorted here purely for draw order (deterministic tiebreak on the
    # offset itself keeps output stable).
    draw_order = sorted(range(CAL_WINDOW_DAYS), key=lambda o: ((o // CAL_DAYS) + (o % CAL_DAYS), o))

    diamonds = []
    for offset in draw_order:
        _, _, cx, cy = _calendar_cell_position(offset)
        diamonds.append(_day_cell_svg(cells[offset], cx, top + cy, theme))

    sections = (
        _text(
            PADDING,
            top + CAL_LABEL_BASELINE_Y,
            CAL_LABEL_TEXT,
            size=CAL_LABEL_SIZE,
            weight=600,
            fill=theme.muted,
            letter_spacing=0.2,
        ),
        _calendar_month_labels_svg(stats, theme, top),
        "\n".join(diamonds),
        _calendar_legend_svg(theme, top),
    )
    return "\n".join(section for section in sections if section)


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
                _text(
                    PADDING,
                    more_y,
                    f"+{remaining} providers not shown",
                    size=12,
                    fill=theme.muted,
                )
            )

        # Isometric daily-activity calendar band (round D2, ADR-018): only
        # when a publishable daily series exists — an empty series omits
        # the band entirely, and _panel_top already collapses to the
        # pre-D2 expression in that case (zero geometry shift).
        if stats.daily:
            parts.append(_calendar_svg(stats, theme, _calendar_top(stats)))

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

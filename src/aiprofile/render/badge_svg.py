"""Inline AI-collaboration badge (round D4, `.ai/round_d4_heatmap_spec.md`;
ADR-020): the smallest embeddable unit — a flat two-segment shield reading
"AI-assisted | <share> · verified by git".

The share is the summary card's own headline number
(``ai_attributed_commits / commits_scanned``, same never-lies rounding via
``_pct_label``), so the badge can never disagree with the card it links
back to. ``commits_scanned == 0`` renders the honest "no data" state.

Pure function of ``(stats, theme)``: fixed-width character arithmetic
(the same estimator the summary card uses for truncation — no font
metrics, no platform dependence), flat theme colors, fully static markup.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..viz import VizStats
from .summary_svg import FONT_STACK, _pct_label, _text_width
from .themes import Theme

BADGE_HEIGHT = 24
BADGE_RADIUS = 4
BADGE_FONT_SIZE = 11
BADGE_PAD_X = 8
BADGE_LABEL_TEXT = "AI-assisted"
BADGE_SUFFIX_TEXT = "verified by git"
BADGE_NO_DATA_TEXT = "no data"
BADGE_TEXT_Y = 16  # baseline for the 11px text inside the 24px shield


def _segment_width(text: str) -> int:
    """Deterministic segment width: estimated text width plus symmetric
    padding, rounded up to a whole pixel."""
    return int(_text_width(text, BADGE_FONT_SIZE) + 0.999) + 2 * BADGE_PAD_X


def render_badge(stats: VizStats, theme: Theme) -> str:
    """Render the badge as standalone SVG markup (round D4, ADR-020)."""
    t = stats.totals
    if t.commits_scanned == 0:
        value_text = BADGE_NO_DATA_TEXT
    else:
        share = _pct_label(t.ai_attributed_commits, t.commits_scanned)
        value_text = f"{share} · {BADGE_SUFFIX_TEXT}"

    left_w = _segment_width(BADGE_LABEL_TEXT)
    right_w = _segment_width(value_text)
    width = left_w + right_w

    desc = (
        f"{t.ai_attributed_commits} of {t.commits_scanned} commits AI-assisted,"
        " from explicit git provenance."
        if t.commits_scanned
        else "No commits scanned yet."
    )

    # Left segment: theme text color as a dark plate with the card bg as
    # label text (light theme) — in both themes the pairing is
    # (theme.title on theme.chip_bg) for the left and (bg-on-accent) for
    # the right; every value is a flat theme hex, no blending.
    return "\n".join(
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}"'
            f' height="{BADGE_HEIGHT}" viewBox="0 0 {width} {BADGE_HEIGHT}" role="img"'
            f' aria-labelledby="aiprofileBadgeTitle aiprofileBadgeDesc">',
            f'<title id="aiprofileBadgeTitle">{escape(BADGE_LABEL_TEXT)}: '
            f"{escape(value_text)}</title>",
            f'<desc id="aiprofileBadgeDesc">{escape(desc)}</desc>',
            f'<clipPath id="aiprofileBadgeClip"><rect width="{width}"'
            f' height="{BADGE_HEIGHT}" rx="{BADGE_RADIUS}"/></clipPath>',
            '<g clip-path="url(#aiprofileBadgeClip)">',
            f'<rect x="0" y="0" width="{left_w}" height="{BADGE_HEIGHT}"'
            f' fill="{theme.chip_bg}"/>',
            f'<rect x="{left_w}" y="0" width="{right_w}" height="{BADGE_HEIGHT}"'
            f' fill="{theme.accent}"/>',
            "</g>",
            f'<rect x="0.5" y="0.5" width="{width - 1}" height="{BADGE_HEIGHT - 1}"'
            f' rx="{BADGE_RADIUS}" fill="none" stroke="{theme.border}" stroke-width="1"/>',
            f'<text x="{left_w // 2}" y="{BADGE_TEXT_Y}" font-family="{FONT_STACK}"'
            f' font-size="{BADGE_FONT_SIZE}" font-weight="600" fill="{theme.title}"'
            f' text-anchor="middle">{escape(BADGE_LABEL_TEXT)}</text>',
            f'<text x="{left_w + right_w // 2}" y="{BADGE_TEXT_Y}"'
            f' font-family="{FONT_STACK}" font-size="{BADGE_FONT_SIZE}"'
            f' font-weight="600" fill="{theme.bg}"'
            f' text-anchor="middle">{escape(value_text)}</text>',
            "</svg>",
        )
    )

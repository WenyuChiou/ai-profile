"""Shared fixed-bin arithmetic for day-cell renderers (ADR-020, ADR-022).

One private home for the volume and AI-share bin math that the heatmap
card (round D4) and the summary card's flat daily matrix (v0.4.8) must
agree on. The two cards may never disagree about what "2-4 commits" or
"a 50% AI-share day" means, so the arithmetic lives here exactly once:

- volume bins over ``DayCell.total_commits``: 1 / 2-4 / 5-7 / 8+
  (``_volume_bin``, cap ``VOLUME_CAP``);
- AI-share bins over ``ai_commits / total_commits``: bin 0 reserved for
  a day with zero attributed AI commits, then integer-arithmetic quarters
  up to 100% (``_share_bin``, ``SHARE_BIN_COUNT`` flat colors via
  ``_share_colors``). Bin 0 is NOT a human-authorship claim: a day's
  unattributed (unknown) commits and explicit Human-Only declarations are
  indistinguishable at this level — zero attributed AI is all it states.

Stdlib-only by design: this module sits inside the render package's
isolation boundary (architecture.md section 2) and is covered by the same
module-graph and AST import tests as every other ``render/*`` file.
"""

from __future__ import annotations

from .themes import Theme

#: Volume cap: a day at or above this many total commits sits in the top
#: volume bin. Fixed contract value (ADR-020's 1 / 2-4 / 5-7 / 8+ buckets).
VOLUME_CAP = 8

#: AI-share hue bins: 0 (zero attributed AI, pure neutral) plus four
#: quarter bins up to 1 (pure accent).
SHARE_BIN_COUNT = 5


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
    """0..4: 0 for a day with zero attributed AI commits (which may be
    unattributed, explicitly human-declared, or both — never a human
    claim); otherwise ceil(4 * ai / total) via integer arithmetic
    (1 = share in (0, 25%], 4 = 100%)."""
    if ai_commits == 0:
        return 0
    return -(-4 * ai_commits // total_commits)


def _volume_bin(total_commits: int) -> int:
    """0..3 over the 1 / 2-4 / 5-7 / 8+ buckets (cap = VOLUME_CAP)."""
    if total_commits <= 1:
        return 0
    if total_commits <= VOLUME_CAP // 2:
        return 1
    if total_commits < VOLUME_CAP:
        return 2
    return 3


def _share_colors(theme: Theme) -> tuple[str, ...]:
    """The five flat share-bin hexes for a theme: neutral -> accent."""
    return tuple(
        _lerp_hex(theme.muted, theme.accent, bin_index / (SHARE_BIN_COUNT - 1))
        for bin_index in range(SHARE_BIN_COUNT)
    )

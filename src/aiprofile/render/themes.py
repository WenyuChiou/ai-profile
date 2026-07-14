"""Theme tokens for the summary SVG card (ADR-010, architecture.md section 9).

Colors mirror the GitHub Primer palette (docs/proposal.md section 21:
"github-light" / "github-dark"). Tokens are named, never hard-coded inline
in the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """One named color token set. All fields are hex color strings."""

    name: str
    bg: str
    border: str
    title: str
    text: str
    muted: str
    accent: str
    bar_fill: str
    bar_track: str


THEMES: dict[str, Theme] = {
    "github-light": Theme(
        name="github-light",
        bg="#ffffff",
        border="#d1d9e0",
        title="#1f2328",
        text="#1f2328",
        muted="#59636e",
        accent="#0969da",
        bar_fill="#0969da",
        bar_track="#eff2f5",
    ),
    "github-dark": Theme(
        name="github-dark",
        bg="#0d1117",
        border="#3d444d",
        title="#f0f6fc",
        text="#f0f6fc",
        muted="#9198a1",
        accent="#4493f8",
        bar_fill="#4493f8",
        bar_track="#21262d",
    ),
}

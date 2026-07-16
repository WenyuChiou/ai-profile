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
    chip_bg: str  # Primer canvas-subtle: chip/badge background
    evidence_verified: str
    evidence_declared: str
    evidence_imported: str
    evidence_inferred: str
    evidence_unknown: str


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
        chip_bg="#f6f8fa",
        # Ordinal evidence ramp, validator-passed (dataviz skill,
        # --ordinal vs the #f6f8fa panel): monotone L, gaps >= 0.06,
        # light end 3.18:1 (the previous #80ccff end sat at 1.64:1).
        evidence_verified="#033d8b",
        evidence_declared="#0550ae",
        evidence_imported="#0969da",
        evidence_inferred="#218bff",
        # Primer fg-muted gray: 4.27:1 on the #f6f8fa panel (gate-7 L-01 —
        # #8c959f sat at 2.85:1, under the 3:1 graphical threshold).
        evidence_unknown="#6e7781",
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
        chip_bg="#161b22",
        # Validator-passed vs the #161b22 panel: light end 3.73:1
        # (the previous #0d419d end sat at 1.86:1).
        evidence_verified="#a5d6ff",
        evidence_declared="#58a6ff",
        evidence_imported="#388bfd",
        evidence_inferred="#1f6feb",
        evidence_unknown="#6e7681",
    ),
}

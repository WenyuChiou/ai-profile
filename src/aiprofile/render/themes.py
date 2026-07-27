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
        bg="#fbfdff",
        border="#c2d3e5",
        title="#172033",
        text="#172033",
        muted="#52647a",
        accent="#005cc5",
        bar_fill="#005cc5",
        bar_track="#d9eaff",
        chip_bg="#fff0bd",
        # Ordinal evidence ramp validated against the #fff0bd provenance
        # panel: monotone luminance, light end 3.14:1.
        evidence_verified="#033d8b",
        evidence_declared="#0550ae",
        evidence_imported="#0969da",
        evidence_inferred="#1f87f8",
        # Neutral unknown mark: 3.99:1 on the #fff0bd provenance panel.
        evidence_unknown="#6e7781",
    ),
    "github-dark": Theme(
        name="github-dark",
        bg="#091321",
        border="#34526f",
        title="#eff6ff",
        text="#eff6ff",
        muted="#b5c7da",
        accent="#8bc8ff",
        bar_fill="#8bc8ff",
        bar_track="#1e3852",
        chip_bg="#3b331e",
        # Ordinal evidence ramp validated against the #3b331e provenance
        # panel: light end 3.34:1.
        evidence_verified="#a5d6ff",
        evidence_declared="#58a6ff",
        evidence_imported="#388bfd",
        evidence_inferred="#2f81f7",
        evidence_unknown="#8d9baa",
    ),
}

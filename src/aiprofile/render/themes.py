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
    model_fill: str  # neutral model-family bar, separate from the collaboration accent
    bar_track: str
    chip_bg: str  # Primer canvas-subtle: chip/badge background
    evidence_verified: str
    evidence_declared: str
    evidence_imported: str
    evidence_inferred: str
    evidence_unknown: str


# Model-family marks are categorical evidence, not a second provider metric.
# Keep the mapping keyed by the canonical category slug so adding/removing a
# row never recolours an existing family.  The values are deliberately muted
# enough for a small bar/mark and have a light/dark counterpart; body text
# continues to use ``Theme.text``.  Unknown/other stay neutral so the honest
# bucket cannot look like a named vendor.
MODEL_CATEGORY_COLORS: dict[str, dict[str, str]] = {
    "github-light": {
        "claude": "#8a3f2f",
        "gpt": "#146b5a",
        "gemini": "#4b4aa3",
        "llama": "#705700",
        "mistral": "#7a3f99",
        "deepseek": "#0b5b78",
        "qwen": "#8b3d75",
        "grok": "#404b5d",
        "kimi": "#6b4d2a",
        "other": "#52647a",
        "unknown": "#52647a",
    },
    "github-dark": {
        "claude": "#ff9b83",
        "gpt": "#5ee0b4",
        "gemini": "#b1afff",
        "llama": "#f0cf7a",
        "mistral": "#d99af4",
        "deepseek": "#7dd7ff",
        "qwen": "#f2a9d0",
        "grok": "#c8d4e5",
        "kimi": "#e8b98b",
        "other": "#b5c7da",
        "unknown": "#b5c7da",
    },
}


def model_category_color(theme: Theme, category: str) -> str:
    """Return the stable presentation colour for a validated model slug.

    This is intentionally a small theme helper, not a model normalizer.  The
    renderer has already received a canonical category from ``VizStats``;
    unknown values therefore fail closed to the neutral model token.
    """

    return MODEL_CATEGORY_COLORS.get(theme.name, {}).get(category, theme.model_fill)


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
        model_fill="#3d5a80",
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
        model_fill="#9ecbff",
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

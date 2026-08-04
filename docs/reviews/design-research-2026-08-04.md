# Visual research and Editorial Signal decision

Date: 2026-08-04  
Review posture: independent visual/product research before an implementation slice  
Scope: `ai-profile` summary SVG, self-contained dashboard, README/profile presentation

## Decision

Keep the existing flat Evidence Ledger as the data grammar and add a small,
replaceable **Editorial Signal** skin. The skin has four rules:

1. quiet paper/ink surfaces;
2. blue is the collaboration signal and warm yellow is the evidence cue;
3. a 4px rhythm, explicit alignment rails, and local open fonts;
4. every visual mark has a visible label or a textual description.

This is a presentation change only. ACE/schema fields, aggregation units,
unknown-versus-human semantics, privacy modes, CLI behavior, output names,
SVG allowlist, and deterministic rendering remain unchanged.

## Research basis

### Nanako0129 / Nyanako

The [profile README](https://raw.githubusercontent.com/Nanako0129/Nanako0129/main/README.md)
uses a terminal transcript as a layout system: a prompt establishes scope,
fixed-width bars carry quantities, and generated blocks are marked with
`START/END` boundaries. The surrounding prose explains why a project exists
before listing implementation detail. This is useful information choreography,
not a reason to copy the author's ASCII art, host facts, or personal telemetry.

The [coralline README](https://raw.githubusercontent.com/Nanako0129/coralline/main/README.md)
shows a segmented statusline, a restrained palette, configurable gauges, and an
ASCII fallback when a terminal lacks Nerd Fonts. The portability warning is
particularly relevant: essential data must not depend on a decorative glyph.

The [TokenBar README](https://raw.githubusercontent.com/Nanako0129/TokenBar/main/README.md)
leads with a one-sentence promise, then a visual proof, then explains its local
data boundary and architecture. It also credits [tokscale](https://github.com/junhoyeo/tokscale),
RunCat, and other upstream work rather than presenting derived motifs as new.
Its glass/3D treatment is intentionally rejected for this repository because
it does not improve the evidence question and would weaken static-card
legibility.

### Open-source design systems

- [GitHub Primer primitives](https://github.com/primer/primitives) and the
  [Primer foundations](https://www.primer.style/product/getting-started/foundations/color-usage/)
  support semantic color roles, light/dark pairs, spacing tokens, and a
  hierarchy that does not depend on color alone.
- [Carbon typography and chart anatomy](https://carbondesignsystem.com/data-visualization/chart-anatomy/)
  reinforce IBM Plex, direct labels, legends, 3:1 graphical contrast, 4.5:1
  text contrast, and a table/text fallback for dense marks.
- [Radix Colors](https://www.radix-ui.com/colors) demonstrates a small,
  role-based scale with separate surface, border, solid, and text roles. We
  borrow the role separation, not a runtime dependency.
- [Vega-Lite](https://vega.github.io/vega-lite/docs/encoding.html) is a useful
  conceptual contract: a mark has a data domain, a scale, and an accessible
  description. The renderer stays a small pure Python SVG function rather
  than adding Vega or JavaScript.

### Profile generators and contrasts

- [github-readme-stats](https://github.com/anuraghazra/github-readme-stats)
  demonstrates why static, self-hosted or Action-generated artifacts are more
  reliable than a shared image endpoint. We keep the same local/static bias.
- [lowlighter/metrics](https://github.com/lowlighter/metrics) proves the value
  of separating data, templates, and export formats; its 47-plugin/335-option
  surface is also a warning against uncontrolled option sprawl in v0.4.x.
- [activity-graph](https://github.com/Ashutosh00710/github-readme-activity-graph),
  [capsule-render](https://github.com/kyechan99/capsule-render),
  [snk](https://github.com/Platane/snk), and
  [github-profile-3d-contrib](https://github.com/yoshi389111/github-profile-3d-contrib)
  are useful contrasts. They rely on hosted endpoints, animation, decoration,
  or perspective. Those mechanisms are not adopted as the primary evidence
  view here.

## What is adopted

| Pattern | Adaptation in ai-profile | Guardrail |
| --- | --- | --- |
| Terminal prompt / scope framing | Compact period and provenance labels around the card's existing sections | No host, path, repo, prompt, SHA, or raw session data |
| Fixed-width bars | Existing share, provider, and evidence rails | Counts and denominators remain visible; bars never stand alone |
| Semantic design tokens | Theme-owned surface, ink, border, signal, and evidence roles | No scattered renderer hex literals |
| Editorial grid | Alignment rails and section marker grammar in the flat timeline | No perspective, polygon terrain, gradients, or animation |
| Local type stack | IBM Plex Sans / Condensed / Mono with system fallbacks | No network font request; minimum 11px in SVG |
| Static artifact workflow | Sanctioned snapshot and profile regeneration | Two-run byte stability, privacy sweep, clean-wheel smoke |

## What is explicitly rejected

- 3D/isometric/prism geometry, glassmorphism, neon glow, and decorative
  background patterns;
- a generic AI score, percentile, or skill inference;
- provider totals used as unique commit totals;
- remote image/API endpoints, runtime chart libraries, telemetry, or private
  data in public URLs;
- an open-ended theme/plugin matrix before a second validated skin exists;
- critical meaning conveyed by color, icon, Nerd Font, animation, or hover.

## Implementation boundary

The implementation is intentionally small and reversible:

1. reuse the existing `Theme` semantic tokens and keep the skin's fixed
   marker/rail geometry as named private render constants;
2. refine the section marker and timeline alignment rails;
3. keep the current provider glyph tiles, flat volume/share encodings, and
   evidence rail unchanged in meaning;
4. add renderer contract tests for the new tokens/rails and preserve all
   existing data, privacy, allowlist, and determinism tests;
5. regenerate summary snapshots/assets only through the sanctioned script;
6. document the skin and update the real profile only after the full release
   and browser gates are green.

No NCB/plugin or new runtime dependency is justified: the current private
section functions already provide the necessary replaceable boundaries, while
an external design package would add more maintenance and privacy surface than
value.

The low-opacity rails and short rules are alignment guides, not graphical data
marks. They must never carry quantitative or state meaning; any future change
that promotes them to a data channel must use a full semantic token and pass
the graphical-contrast gate.

## Acceptance criteria

- populated, sparse, aggregate-only, and zero cards remain semantically honest;
- every visual state is readable at README width in light and dark themes;
- text remains at least 4.5:1 and meaningful graphical marks at least 3:1;
- the SVG uses only the existing allowlist and contains no external reference;
- two renders of every affected output are byte-identical;
- full pytest, Ruff, README parity, snapshot drift, privacy, and clean-wheel
  smoke gates remain green;
- no unresolved Critical or High finding remains before any public release.

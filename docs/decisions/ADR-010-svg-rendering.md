# ADR-010: SVG rendering strategy

Status: accepted (2026-07-14)

## Context

One polished summary card, deterministic, accessible, light+dark, readable
at GitHub README width, zero runtime deps. Candidates: a template engine
(jinja2), an SVG library (svgwrite), or pure-python string building.

## Decision

- Pure-python string composition in `render/summary_svg.py`: small helper
  functions building SVG elements with escaped text; **no template engine,
  no SVG library**.
- Determinism rules: pure function of `(VizStats, Theme)`; no clock, no
  randomness, no locale-dependent formatting; fixed decimal formatting;
  byte-identical snapshot tests for light, dark, zero-state, and a
  populated fixture.
- Layout is **dynamic-but-deterministic** (2026-07-14 polish revision):
  card height is a pure function of the data shape (`card_height`) so
  sparse profiles show no dead band; visual hierarchy uses one accent
  hero value for AI-attributed commits, an explicit share bar against
  unique commits scanned, and a subordinate right-aligned ledger for the
  remaining headline counts; provider rows carry count + percentage with
  the denominator stated in the table header (proposal §26 rule 6);
  evidence and privacy render inside a subtle provenance panel using the
  `chip_bg` theme token, a stacked evidence bar, square swatches, and one
  quiet privacy statement. Icons are pure inline geometry (a square
  commit-node mark) — never provider logos or emoji (proposal §22;
  emoji glyphs are font-dependent and would break determinism across
  renderers).
- Themes are token dicts (`render/themes.py`): `github-light`,
  `github-dark` (colors mirror GitHub Primer palette values; tokens named,
  not hard-coded inline).
- Two output assets (`summary-light.svg`, `summary-dark.svg`) embedded via
  `<picture>` — reliable GitHub-native theme switching (mvp.md §5).
- Text sizing: a local humanist stack
  (`'Trebuchet MS', Corbel, 'Avenir Next', Avenir, Ubuntu, sans-serif`)
  chosen to avoid generic AI-dashboard typography without adding a font
  request; conservative character-width table for layout and ellipsis
  truncation for long provider names.
- Accessibility: `<title>` + `<desc>`, `role="img"`, labels ≥ 11px, metric
  names spelled out, no color-only distinctions (counts always printed).

## Consequences

- Renderer code is plain and auditable; adding calendars later reuses the
  same primitives.
- Sophisticated text metrics are approximate; layouts leave margin and are
  verified visually once per theme during review.

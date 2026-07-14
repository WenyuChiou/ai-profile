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
- Themes are token dicts (`render/themes.py`): `github-light`,
  `github-dark` (colors mirror GitHub Primer palette values; tokens named,
  not hard-coded inline).
- Two output assets (`summary-light.svg`, `summary-dark.svg`) embedded via
  `<picture>` — reliable GitHub-native theme switching (mvp.md §5).
- Text sizing: system font stack
  (`-apple-system, 'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif`),
  conservative character-width table for layout, ellipsis truncation for
  long provider names.
- Accessibility: `<title>` + `<desc>`, `role="img"`, labels ≥ 11px, metric
  names spelled out, no color-only distinctions (counts always printed).

## Consequences

- Renderer code is plain and auditable; adding calendars later reuses the
  same primitives.
- Sophisticated text metrics are approximate; layouts leave margin and are
  verified visually once per theme during review.

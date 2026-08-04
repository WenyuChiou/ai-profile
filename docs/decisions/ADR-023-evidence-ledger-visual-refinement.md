# ADR-023: Evidence-ledger visual refinement

Date: 2026-08-04  ·  Status: proposed for the post-v0.4.8 design branch
Supersedes: none

## Context

The v0.4.8 Public Beta card is semantically correct and visually coherent,
but the provider ledger's combined count/percentage text is difficult to scan
at README scale. The visual research round also confirmed that trustworthy
technical products make their data boundary, freshness, and status legible
without turning every metric into a decorative effect.

## Decision

Refine the existing renderer as an evidence ledger while preserving its
contract:

- Keep `render_summary(stats, theme) -> str`, the 830px width, dynamic
  deterministic height, both themes, the eight output names, and the current
  SVG element/security allowlist.
- Keep the existing IBM Plex Sans Condensed / IBM Plex Sans / IBM Plex Mono
  local fallback stacks. No paid font, font download, runtime CSS, animation,
  or network request is introduced.
- Keep the existing 4px spacing scale. Provider rows use a stable identity,
  meter, and two-column metric lockup; the count and percentage have separate
  right edges so neither can visually collide with the other.
- Use a quiet border-token section marker for terrain and provider headings.
  Accent remains reserved for the hero value, share fill, provider fills and
  header mark; provider identity colors remain limited to glyph tiles and thin
  fills.
- Keep the terrain's meaning unchanged: height is unique daily commit volume
  bins, top-face hue is daily AI share, and provider presences never affect
  geometry. Keep unknown separate from human and preserve all privacy notices.
- Keep the dashboard's filters, theme cycle, keyboard behavior, CSP,
  reduced-motion behavior, and self-contained local-first architecture.

## Non-goals

This refinement does not change ACE/schema fields, aggregation semantics,
historical attribution, repository policies, CLI commands, dashboard data
payloads, or public/private boundaries. It does not add generic GitHub stats,
role aggregation, hosted analytics, Liquid Glass/aurora decoration, or a new
user-configurable theme engine.

## Consequences

The summary snapshot and committed synthetic sample assets must be regenerated
with `python tests/unit/test_render_summary.py`. The heatmap/badge family is
unchanged unless a shared theme/bin token is later modified. The release
branch must pass the existing full test, Ruff, privacy, deterministic, and
browser gates before any version tag or public upload.

## Research basis

The design direction is informed by the 2026-08-04 independent research in
`.coord/research/` (ignored working notes): Nanako0129's profile,
TokenBar, coralline, pilotfish, remora-cc, GitHub Primer, IBM Carbon, Radix,
Vercel Geist, Shopify Polaris, Vega-Lite, Observable Plot, and Grafana. The
transferable patterns are evidence-first hierarchy, semantic tokens,
progressive disclosure, chart/table parity, explicit privacy boundaries, and
responsive/focus/reduced-motion behavior. Their decorative styles and hosted
sharing assumptions are intentionally not copied.

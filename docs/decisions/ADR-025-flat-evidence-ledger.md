# ADR-025: Flat Evidence Ledger visual system

Date: 2026-08-04
Status: accepted on `codex/v050-flat-evidence-ledger`
Supersedes: ADR-024 and ADR-022's perspective daily-visual clauses

## Context

The Structural Current prototype preserved the data contract but used an
isometric prism terrain. Independent visual review found that the perspective
and shading added decoration without improving the recruiter-facing answers:
how much activity exists, how sustained it is, and what evidence supports it.
The card is a static GitHub README asset, so a flat editorial treatment is
more legible at small sizes and easier to compare across themes.

## Decision

Use a flat 2D evidence timeline in the summary card:

- a 12-column by 7-row matrix of neutral tracks;
- a small bottom-anchored bar per published day, with height from the fixed
  total-commit volume bin;
- a discrete fill ramp from the day's AI share;
- aligned month and weekday labels, a text legend, and the existing provider
  ledger/evidence rail.

No perspective, polygon prism, shading, gradient, animation, or decorative
3D mark is part of the summary contract. The dashboard keeps its existing
flat panels and filters.

## Boundaries

This is presentation-only. ACE/schema fields, aggregation units, unknown vs
Human semantics, privacy modes, CLI behavior, output filenames, deterministic
rendering, and the SVG security allowlist do not change. Renderers still
consume validated `VizStats` only.

## Consequences

The static card is easier to scan at README width and has fewer geometry
primitives. Volume/share semantics remain explicit in the legend and
accessible description. The old isometric branch remains available as a
rollback until the flat branch passes independent review and release gates.

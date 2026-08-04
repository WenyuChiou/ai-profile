# ADR-024: Structural Current visual system

Date: 2026-08-04
Status: accepted for the post-v0.4.8 design branch
Supersedes: none

## Context

The v0.4.8 Public Beta established an evidence-ledger summary and an
interactive static dashboard. Independent review of Nanako0129's profile and
tools, GitHub Primer, IBM Carbon, Radix, Geist, Vega-Lite, and related systems
found a common strength: a clear promise and scope precede metrics, semantic
roles survive theme changes, and charts are paired with labels/fallbacks.

The repository must remain a local-first, privacy-safe, deterministic static
generator. Copying terminal telemetry, remote fonts, glass/aurora effects,
animated 3D, or hosted analytics would conflict with that architecture.

## Decision

Adopt **Structural Current / Evidence Ledger** as the visual direction:

- a strict 4px rhythm with generous group separation;
- ice-blue/light and deep-blue/dark grounds with one cool data signal and one
  small warm evidence signal;
- local fallback stacks for display, body, and tabular numbers;
- stable composition: scope/period → hero fact → supporting ledger → daily
  terrain → provider ledger → evidence/privacy → generated metadata;
- visible numeric labels, denominator notes, non-color state cues, keyboard
  focus, reduced-motion behavior, and accessible descriptions;
- static terrain may use a faint structural grid, but its encoding remains
  unchanged: height is daily total-commit volume and top-face hue is daily AI
  share; provider presences never change geometry.

`DESIGN.md` is the human- and agent-readable source of truth for these roles.
Runtime code continues to use the typed `Theme`, closed provider registry, and
private pure render helpers. The design file is not loaded as configuration and
cannot carry event or repository data.

## Boundaries

The decision does not change ACE/schema fields, aggregation semantics,
historical attribution, privacy policy, CLI, output filenames, or renderer
dependency direction. Unknown remains distinct from Human. Provider totals are
non-exclusive. No plugin loader, design-system dependency, external font,
network request, animation, or new output is permitted.

## Consequences

Visual changes require focused semantic and accessibility assertions, both
theme snapshots, deterministic regeneration, privacy sweeps, and the existing
release/artifact checks. A future chart/table companion must consume only
validated aggregate rows and be justified by a separate ADR if it changes the
public contract.

## Research record

The independent source review is recorded in
`docs/reviews/design-reverse-engineering.md`. It labels observed facts,
inferences, adaptations, boundaries, confidence, and open questions rather
than treating a designer's style as a product requirement.

# ADR-028: Stable model-category visual encoding

- **Status:** Accepted
- **Date:** 2026-08-04
- **Decision owners:** ai-profile maintainers
- **Supersedes:** the presentation-only portion of ADR-027 that described one
  neutral model bar token

## Context

`VizStats.models` contains validated, canonical model-family rows. The summary
and dashboard already show those rows as an all-time, non-exclusive ledger, but
using one neutral bar colour makes the family contribution harder to scan. A
row-index colour would be worse: adding a category could recolour every family
on the next refresh and undermine visual comparison.

The daily series has no model-by-day aggregate. The renderer must not infer one
from all-time model rows or from provider counts.

## Decision

Use a small, fixed light/dark categorical palette keyed by the canonical model
category slug. Render each model row with four redundant channels:

1. canonical short mark (`Cl`, `Gp`, `Ge`, etc.);
2. canonical display label;
3. attributed-commit count and percentage of unique AI-attributed commits; and
4. a category-coloured bar and mark outline.

`other` and `unknown` use the neutral model token. Body text remains the normal
text/muted colour. The palette is presentation-only and lives in the render
theme module; it does not alter the ACE schema, aggregation, privacy contract,
or output count.

The daily matrix remains unchanged: bar height is unique daily commit volume
and fill is daily AI share. Model rows never affect its geometry. A future
model-by-day view requires a new validated aggregate field and a separate ADR.

## Consequences

**Positive:** model-family contribution is visible at a glance; category colours
remain stable across refreshes; labels and marks preserve meaning without
colour; unknown stays honest; no network asset or dependency is introduced.

**Trade-off:** the palette adds a few fixed tokens and makes snapshots change.
All palette values must clear the existing graphical/text contrast checks and
snapshots must be regenerated only by the sanctioned writer.

## Verification

- unit tests assert category-key stability and light/dark mapping;
- existing model/daily-semantics tests assert that model rows do not alter daily
  geometry;
- deterministic summary/dashboard, privacy, CSP, and full-suite tests remain
  required;
- no raw model declaration is permitted in public output.

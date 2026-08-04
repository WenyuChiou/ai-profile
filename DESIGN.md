---
name: ai-profile visual system
version: 0.1
status: beta
audience: maintainers, contributors, and design-aware agents
source_of_truth: [docs/decisions/ADR-025-flat-evidence-ledger.md, docs/decisions/ADR-028-stable-model-category-palette.md]
themes: [github-light, github-dark]
fonts: local-fallback-only
network_assets: forbidden
---

# Flat Evidence Ledger

This file is the maintainable visual contract for ai-profile. It describes
how validated aggregate facts are presented; it is not a second data model and
must never be used to carry repository identity, raw events, prompts, or
credentials.

## Product promise

The interface should let a reader answer, in roughly five seconds:

1. How much explicitly attributed AI collaboration is recorded?
2. How sustained is the activity and how broad is provider participation?
3. What evidence and publication scope support those numbers?

The interface must also make the honest boundary visible: unknown is not
human, provider presences can overlap one commit, and aggregate-only activity
is identity redaction rather than anonymity.

Model-family contribution is a separate all-time, non-exclusive ledger. Its
canonical category mark, label, count/share, and stable category-coloured bar
are redundant presentation channels; it never changes the daily matrix and it
never implies a model-by-day aggregate. See ADR-028.

## Normative tokens

```yaml
spacing:
  unit: 4px
  within_group: [8px, 12px]
  between_groups: [20px, 24px]
  outer: 24px
type:
  sizes_px: [11, 12, 13, 16, 38]
  labels: 400
  metrics: 600
  hero: 700
  display: "IBM Plex Sans Condensed, Aptos Display, Segoe UI, DejaVu Sans Condensed, sans-serif"
  body: "IBM Plex Sans, Aptos, Segoe UI, Noto Sans, DejaVu Sans, sans-serif"
  numbers: "IBM Plex Mono, Cascadia Mono, SFMono-Regular, DejaVu Sans Mono, Consolas, monospace"
roles:
  light:
    canvas: "#fbfdff"
    text: "#172033"
    muted: "#52647a"
    accent: "#005cc5"
    border: "#c2d3e5"
    evidence_surface: "#fff0bd"
    unknown: "#6e7781"
  dark:
    canvas: "#091321"
    text: "#eff6ff"
    muted: "#b5c7da"
    accent: "#8bc8ff"
    border: "#34526f"
    evidence_surface: "#3b331e"
    unknown: "#8d9baa"
model_categories:
  key: canonical_category_slug
  units: attributed_commits_and_actor_presences
  denominator: unique_ai_attributed_commits
  unknown: neutral_mark_and_label
behavior:
  deterministic: true
  external_fonts: false
  gradients: false
  animation: false
  color_only_meaning: false
  renderer_input: VizStats
```

The YAML block is intentionally small and reviewable. Runtime renderers keep
their existing typed `Theme` and closed provider registry; adding a token is a
contract change and requires a focused test plus an ADR update.

## Composition grammar

The order is stable across the static summary and dashboard:

`scope / period → hero fact → supporting ledger → daily timeline → provider
ledger → evidence / privacy → generated metadata`

The summary is a static profile artifact. The dashboard may add provider
filters and keyboard affordances, but it must consume the same `VizStats` and
must not recalculate or infer attribution.

## Signal rules

- Accent is reserved for hero values, share fills, provider marks/fills, focus,
  and the header mark.
- Warm evidence color is a small surface/mark only; it is never a large warning
  panel.
- Text labels remain text-colored or muted. A provider hue identifies a closed
  vocabulary item; it does not certify authorship.
- Every chart has a text/ARIA explanation and visible numeric legend. A future
  table view must be generated from the same validated aggregate rows.
- Unknown keeps a neutral mark and explicit label. It must never be recolored
  or renamed to imply Human.

## Editorial Signal skin

The v0.6 candidate keeps the flat ledger and adds a restrained editorial
instrument rhythm: section headings use a short rule plus datum bar, and the
12-week matrix uses sparse quarter-window alignment rails. These rails are
structural guides only; they never encode a third statistic. The goal is a
distinctive, recruiter-readable card without perspective, prisms, glass,
gradients, neon, animation, or decorative background patterns. The full
research record is `docs/reviews/design-research-2026-08-04.md`; the decision
record is ADR-026.

## Extension points

The renderer is intentionally composable through private pure functions:

- summary: hero, ledger, flat daily timeline, provider row, evidence rail,
  footer, and Editorial Signal section/rail helpers;
- dashboard: masthead, filter deck, hero, activity, providers, evidence,
  definitions, and the matching section-marker grammar.

An extension may replace a visual primitive only if it preserves the same
validated input, semantic units, privacy boundary, element/security allowlist,
deterministic bytes, and light/dark accessibility checks. Do not add a plugin
loader, network registry, or new output file for visual experimentation.

## Review checklist

- Does the change improve hierarchy or legibility at 320px and GitHub README
  width, or is it merely decoration?
- Are all numbers labelled with their unit and denominator?
- Can a keyboard, screen reader, reduced-motion user, or no-hover reader
  understand the state?
- Does the output remain byte-stable and free of private canaries?
- Are snapshots regenerated only by the sanctioned scripts?

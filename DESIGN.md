---
name: ai-profile visual system
version: 0.2
status: beta
audience: maintainers, contributors, and design-aware agents
source_of_truth: [docs/decisions/ADR-032-collaboration-pulse.md, docs/decisions/ADR-031-signal-console.md, docs/decisions/ADR-025-flat-evidence-ledger.md, docs/decisions/ADR-029-provider-ledger-only-rendering.md]
themes: [github-light, github-dark, system]
fonts: local-fallback-only
network_assets: forbidden
---

# Signal Console (on the Flat Evidence Ledger)

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

Model-family evidence remains in `VizStats` and `profile.json` for
machine-readable consumers. The summary and dashboard intentionally expose one
contribution ledger: providers. No model palette or category mark is part of
the active visual contract. See ADR-029.

## Normative tokens

```yaml
spacing:
  unit: 4px
  within_group: [8px, 12px]
  between_groups: [16px, 20px, 24px]
  outer: 24px
type:
  svg_sizes_px: [12, 13, 18, 40]        # summary card; heatmap labels may use 11
  dashboard_scale_px: [13, 15, 18, 28, 36]  # --text-1 .. --text-5
  labels: 400
  metrics: 600
  hero: 700
  mono_is_for: numbers and dates only
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
  dashboard_light:
    canvas: "#f3f7fb"
    surface: "#fbfdff"
    border_strong: "#7590aa"
    grid_empty: "#e5eef7"
    evidence_text: "#9a6700"
  dashboard_dark:
    canvas: "#0b1625"
    surface: "#111923"
    border_strong: "#6683a0"
    grid_empty: "#111923"
    evidence_text: "#eac54f"
behavior:
  deterministic: true
  external_fonts: false
  gradients: false
  shadows: inset focus/selection ring only
  uppercase_labels: false
  motion: transform/opacity state changes only, <= 120ms, off under prefers-reduced-motion
  color_only_meaning: false
  renderer_input: VizStats
  freshness_claim: none - generated_on is labelled "snapshot"
```

The YAML block is intentionally small and reviewable. Runtime renderers keep
their existing typed `Theme` and closed provider registry; adding a token is a
contract change and requires a focused test plus an ADR update.

## Composition grammar

The order is stable across the static summary and dashboard (ADR-031):

`status line (title · period · snapshot date) → metric console (hero fact +
supporting cells) → provider controls (dashboard) → daily commit map →
provider ledger → evidence / privacy → definitions → generated metadata`

Dashboard layout: desktop = primary activity region + provider/evidence
sidebar; below 54rem one column in the same DOM order; metrics 4-up → 2-up →
1-up at 22rem. DOM order is reading order is tab order. Definitions live in a
native `<details>` disclosure.

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

## Signal Console

The v0.8.0 Signal Console (ADR-031) keeps the flat ledger and the restrained
editorial instrument rhythm of v0.6 (short rule + datum bar section markers —
structural guides only, never a third statistic) and recomposes every surface
around a console reading: a compact status line that labels `generated_on` as
a snapshot, a metric strip with hairline separators and a shared baseline,
and on the dashboard a provider toolbar, primary commit map, and
evidence/provider sidebar. Tech feeling comes from information architecture,
status treatment, precision alignment, typography, and data interaction.
Banned: neon, glassmorphism, gradients, gradient text, oversized hero/title,
decorative thin border + large shadow, thick side accent stripes, uppercase
tracked labels, monospace-as-tech, and width/layout-property animation. The
earlier research record is `docs/reviews/design-research-2026-08-04.md`
(ADR-026); the v0.8.0 browser evidence is `docs/reviews/v0.8.0-visual-qa.md`.

## Collaboration Pulse (summary card daily block)

v0.8.1 (ADR-032) replaces the summary card's 84-cell daily matrix with a
static pulse signature — summary card only; the heatmap card remains the
sole calendar-grid surface. The 84 published-window dates run oldest to
newest as 6px baseline-anchored marks in 12 groups of seven with a wider
structural group gap (a 7-day rhythm, never labelled as calendar weeks).
Neutral (muted) pulse height carries the fixed total-commit bins at
12/24/36/48px; the accent fill rises from the baseline to 0/25/50/75/100%
of the pulse height per shared AI-share bin, so the share is positional as
well as hued; a no-activity date is a 2px border-token baseline tick.
Month-boundary labels stay (derived only from `stats.daily`); weekday
labels and the quarter-window rails are gone. Legend, direct and one line:
`height = total commits · fill = AI-attributed share · publishable dates
only`. Zero attributed AI keeps the neutral pulse and is never presented
as human.

## Extension points

The renderer is intentionally composable through private pure functions:

- summary: status-line header, hero cell, metric console cells, the
  Collaboration Pulse (mark, month-label, and legend helpers), provider
  row, evidence rail, footer, and section helpers;
- dashboard: status line, metric strip, provider toolbar, commit map,
  provider ledger, evidence panel, definitions disclosure, and footer.

An extension may replace a visual primitive only if it preserves the same
validated input, semantic units, privacy boundary, element/security allowlist,
deterministic bytes, and light/dark accessibility checks. Do not add a plugin
loader, network registry, or new output file for visual experimentation.

## Review checklist

- Does the change improve hierarchy or legibility at 320px (and the 195px
  extreme-narrow case) and GitHub README width, or is it merely decoration?
- Does `npx impeccable detect` on the rendered dashboard still return zero
  findings, and does the page still say *snapshot* rather than live?
- Are all numbers labelled with their unit and denominator?
- Can a keyboard, screen reader, reduced-motion user, or no-hover reader
  understand the state?
- Does the output remain byte-stable and free of private canaries?
- Are snapshots regenerated only by the sanctioned scripts?

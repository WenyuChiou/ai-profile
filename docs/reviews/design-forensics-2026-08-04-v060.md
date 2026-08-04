# Visual design forensics and v0.6 implementation plan

**Date:** 2026-08-04  
**Scope:** ai-profile static summary SVG, self-contained dashboard, README-facing
assets, and the model-family contribution view.  
**Posture:** independent design and architecture review; no private data or
personal profile payloads were used as design inputs.

## Executive synthesis

The current product already has the right architectural constraint for a
commercially credible profile card: a renderer accepts only validated
`VizStats`, emits deterministic self-contained output, and keeps repository
identity outside the public contract. The next visual step should therefore be
an editorial evidence instrument, not another pseudo-3D activity map.

The recommended direction is **Quiet Evidence Console**:

- a calm opaque surface with a single blue signal accent and a warm evidence
  accent;
- a compact display/body/monospace type hierarchy with tabular numbers;
- an explicit “overview → ledger → details” reading order;
- model-family contribution shown as a separate, labelled, non-exclusive
  evidence ledger; and
- redundant text/mark/bar encoding so colour is never the only meaning.

This keeps the product recognisable as a GitHub Profile asset while making the
reason for using it obvious to a recruiter: it shows how much activity is
AI-attributed, how sustained it is, which providers and model families are
represented, and how much evidence remains unknown.

## Source ledger (primary evidence)

All sources were read on 2026-08-04. Observations below are facts about the
referenced revision; proposed ai-profile adaptations are explicitly labelled as
inferences.

| Source | Observed design practice | Safe inference for ai-profile |
| --- | --- | --- |
| [Nanako0129 profile](https://github.com/Nanako0129) | Fixed-width terminal/neofetch framing, explicit `cat`/`ls`/`git log`/lineage blocks, and a model-token view. | Use authored evidence blocks and a restrained console eyebrow, but never copy personal host, repository, organisation, or raw model data. |
| [TokenBar at commit 2c1e6f6](https://github.com/Nanako0129/TokenBar/tree/2c1e6f609228413d503002d092e4ea1b814f244e) and its [heatmap](https://raw.githubusercontent.com/Nanako0129/TokenBar/2c1e6f609228413d503002d092e4ea1b814f244e/Sources/TokenBar/Charts/ContributionHeatmap.swift) | Scope tabs, a lens switch, stable heatmap geometry, hover ring, and a small set of explicit levels. | Keep overview and filter controls separate; derive geometry once; make model category a clear lens/ledger rather than a decorative colour wash. |
| [TokenBar landing styles](https://raw.githubusercontent.com/Nanako0129/TokenBar/2c1e6f609228413d503002d092e4ea1b814f244e/landing/src/styles/global.css) | Display/body/mono roles, generous rhythm, dark indigo surface, small bright accents, and explicit light-mode fallback. | Add semantic theme aliases and a local-font fallback stack; do not import fonts or use glass/blur/aurora in static assets. |
| [coralline at commit 83da6ae](https://github.com/Nanako0129/coralline/tree/83da6ae18bc1594e55f90a0850d8f01f12f856d4) | Compact status grammar, segment-level degradation, responsive wrapping, and explicit missing-data handling. | Give every metric a unit/denominator and distinguish “not published” from zero. |
| [pilotfish design rationale](https://raw.githubusercontent.com/Nanako0129/pilotfish/ad9600c5af3a4462c7de4bc9832f9b3a3c5e9d36/docs/design.md) and [remora architecture](https://raw.githubusercontent.com/Nanako0129/remora-cc/28e6c9a4d51f88c09bee57e7edad07d09d38fd77/docs/architecture.md) | Trust boundaries, capability tables, and explicit approval/egress language. | Keep the privacy cue adjacent to the evidence rail; describe what is and is not published without operational overclaims. |
| [Tokscale at commit 633ea94](https://github.com/junhoyeo/tokscale/tree/633ea94688210c6ef7d14ed51bb9113aee29b06a) | Model grouping/filtering, multiple views, compact metric cards, and an embed sized for profile surfaces. | Preserve the eight-output contract, but make the model ledger visually legible and stable by category key. Do not copy its remote-font or public-upload assumptions. |
| [GitHub contribution reference](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference) | Contribution dates use author-date semantics and private activity can be anonymised. | Keep the author-date note and publishable-only daily boundary visible. |
| [Primer data visualisation](https://primer.style/product/ui-patterns/data-visualization/) | Chart title/context, legends for multiple series, 4.5:1 text contrast, 3:1 mark contrast, and no colour-only meaning. | Add explicit model legend/labels and test both contrast and text fallback. |
| [Carbon data visualisation basics](https://www.ibm.com/design/language/data-visualization/design/basics/) | Overview first, then zoom/filter, then details on demand; missing periods must not be interpolated. | Keep the daily matrix as an overview and the model/provider ledgers as details; do not fabricate model-by-day values. |
| [Geist colour and typography](https://vercel.com/geist/colors), [Geist typography](https://vercel.com/geist/typography), and [Radix colour](https://www.radix-ui.com/themes/docs/theme/color) | Semantic colour roles, high-contrast scales, portable system typography, and tabular numbers. | Name roles (`surface`, `ink`, `muted`, `signal`, `model`, `focus`) instead of sprinkling literal colours through renderers. |
| [Vega-Lite](https://vega.github.io/vega-lite/) and [Observable Plot](https://observablehq.github.io/plot/) | Declarative data→mark→scale grammar. | Borrow the mental model as private pure helpers only; do not add a runtime chart dependency. |

## What is safe to reuse versus what is not

**Reuse as principles:** semantic tokens, stable key-based categorical colour,
small fixed bins, type roles, explicit legends, focus rings, responsive
progressive disclosure, and a trust/privacy caption. These are presentation
rules and do not weaken the ACE or `VizStats` boundary.

**Do not import or copy:** React/Radix/Carbon/Geist/Plot/Vega runtime code,
remote fonts, provider trademarks, Liquid Glass/backdrop blur, animated
auroras, 3D/orbit geometry, token/quota claims, public upload flows, or
personal profile identifiers. They add dependency, licensing, privacy, or
static-rendering risk without improving the core evidence question.

## Model-category contribution contract

The visual must show model-family contribution, but it must not imply data that
the contract does not contain.

1. `VizStats.models` remains an all-time, validated, non-exclusive ledger.
2. Each row is keyed by the canonical category slug (`claude`, `gpt`,
   `gemini`, and so on), not by row position. A category keeps the same mark
   and colour when another category appears or disappears.
3. Bars and labels report **attributed commits** with the denominator stated as
   unique AI-attributed commits. Presences and active author dates remain
   secondary values; they are never added to commit totals.
4. The model ledger is visually separate from the daily matrix. The matrix
   height continues to encode unique daily commits and its fill continues to
   encode daily AI share. No model-by-day story is invented from all-time rows.
5. Every model row has redundant channels: short canonical mark, text label,
   numeric count/share, and a bar. Unknown remains a labelled `?`/unknown row,
   never human and never silently dropped.
6. A future model-by-day view requires a new validated aggregate field and an
   ADR; it is not a renderer inference.

## Proposed component and token system

The existing renderer already has the correct section order. The v0.6 change
should refine the primitives rather than add a framework:

| Primitive | Role | Contract |
| --- | --- | --- |
| `signal mark` | header and hero | accent only; never used as a paragraph background |
| `metric lockup` | hero and secondary metrics | label, value, unit/denominator, tabular number |
| `daily matrix` | sustained activity overview | fixed 84-day geometry, volume/share bins, publishable-only |
| `provider ledger` | provider breadth | brand mark/initial fallback, non-exclusive note |
| `model ledger` | model-family contribution | stable category mark, bar, count/share/presences/days |
| `evidence rail` | evidence quality and privacy | explicit category labels, chip-sized verified cue, no warning panel |
| `state notice` | zero/unpublished | honest copy, no fabricated cells |

Theme aliases should map these semantic roles to the existing light/dark
`Theme` fields. The SVG and dashboard may have different layout code, but both
must consume the same role vocabulary and model ordering rules. No runtime
plugin loader is needed; adding a new presentation skin should be a small,
reviewable token/helper change selected by the existing `Theme` value.

## Phased implementation plan

### Phase 1 — evidence and red tests

- Add tests for stable category mark/colour mapping, unknown visibility, model
  denominator text, and unchanged daily geometry when only model rows change.
- Add dashboard assertions that model rows have text/mark/count and that
  selected provider filters do not mutate the model ledger into a daily claim.
- Add deterministic double-render and light/dark token parity checks for the
  new presentation primitives.

### Phase 2 — presentation-only implementation

- Refine `themes.py` with semantic aliases while keeping public constructor
  compatibility.
- Refine `summary_svg.py` private helpers: one geometry calculation per row,
  stable category marks, clear “all-time · non-exclusive” model caption, and
  quieter flat daily matrix treatment. Preserve width 830, SVG allowlist,
  integer coordinates, and output count.
- Refine dashboard CSS/DOM copy to match the same hierarchy and model ledger
  semantics. Keep the current CSP, keyboard controls, provider filters, and
  self-contained HTML.

### Phase 3 — sanctioned regeneration and QA

- Regenerate summary and heatmap snapshots only through their sanctioned
  scripts; run the script twice and assert zero second-run diff.
- Run the complete pytest suite and Ruff. Perform SVG element, active-content,
  privacy-canary, contrast, 320/390/768/1280/1440, 200% zoom, dark/light/system,
  keyboard/focus/reduced-motion, and README-render checks.
- Do not republish or alter the ACE schema until the new output passes the
  independent gate review. If a model-by-day requirement emerges, open an ADR
  instead of inferring it in the renderer.

## Acceptance criteria

- Full suite remains green (baseline observed before this round: `667 passed,
  4 skipped`) and Ruff remains clean.
- Identical `VizStats` plus theme produces byte-identical SVG/HTML.
- Model category order, mark, and colour are stable under row insertion/removal;
  unknown stays separate from human.
- No model row changes daily matrix coordinates, heights, or share bins.
- All model values state their unit and denominator; no percentage sum is
  presented as a unique-commit total.
- No raw repository name/path/org/SHA/email/prompt/model declaration is added
  to public assets; only canonical model-family labels may appear.
- No external font, network request, JavaScript event attribute, active SVG
  element, gradient, glass/blur, or 3D/perspective geometry is introduced.
- README/profile preview remains legible at mobile width and the dashboard
  remains keyboard and reduced-motion accessible.

## Open decision

The model ledger is the correct v0.5/v0.6 representation because the validated
contract has model-family totals but no model-by-day aggregate. A future
interactive “Claude only / GPT only” daily view is desirable, but should be
planned as an explicit aggregate/schema extension rather than smuggling an
inference into the current renderer. This preserves both visual honesty and
the product’s strongest differentiator: evidence users can explain.

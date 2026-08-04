# Visual design reverse-engineering review

Date: 2026-08-04
Reviewer posture: independent design and architecture review before the next
visual implementation slice.

## Decision in one sentence

ai-profile should borrow the evidence-first information architecture and
semantic token discipline seen in Nanako0129's tools and mature design systems;
it should not copy their personal terminal data, glass effects, remote fonts,
hosted telemetry, or animated 3D surfaces.

## Primary sources inspected

The source reads were pinned to immutable commits during the review. The
following links are the public primary sources used for the observations.

- [Nanako0129 profile README](https://raw.githubusercontent.com/Nanako0129/Nanako0129/a81172c1efeb871ff767104012dabb4acafd9471/README.md)
- [TokenBar README](https://raw.githubusercontent.com/Nanako0129/TokenBar/ea905af92df872778c1e7577b25ebe8722b9a428/README.md), [landing tokens](https://raw.githubusercontent.com/Nanako0129/TokenBar/ea905af92df872778c1e7577b25ebe8722b9a428/landing/src/styles/global.css), and [privacy section](https://raw.githubusercontent.com/Nanako0129/TokenBar/ea905af92df872778c1e7577b25ebe8722b9a428/landing/src/components/Privacy.astro)
- [coralline README](https://raw.githubusercontent.com/Nanako0129/coralline/83da6ae18bc1594e55f90a0850d8f01f12f856d4/README.md)
- [pilotfish design rationale](https://raw.githubusercontent.com/Nanako0129/pilotfish/ad9600c5af3a4462c7de4bc9832f9b3a3c5e9d36/docs/design.md)
- [remora-cc architecture](https://raw.githubusercontent.com/Nanako0129/remora-cc/28e6c9a4d51f88c09bee57e7edad07d09d38fd77/docs/architecture.md)
- [Tokscale README](https://raw.githubusercontent.com/junhoyeo/tokscale/bcd4c2203f69ee16bba7f6ea40aa2a8b11281c9d/README.md)
- [GitHub Primer data visualization](https://primer.style/product/ui-patterns/data-visualization/)
- [IBM Carbon themes](https://carbondesignsystem.com/elements/themes/overview/) and [data-table accessibility](https://preview.carbondesignsystem.com/building-blocks/core/components/data-table/accessibility)
- [Vercel Geist typography](https://vercel.com/geist/typography)
- [Radix color roles](https://www.radix-ui.com/themes/docs/theme/color)
- [Vega-Lite accessibility encoding](https://vega.github.io/vega-lite/docs/encoding.html)
- [Google Labs DESIGN.md specification](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md)

## Observed patterns and safe adaptations

| Observed pattern | Why it works | ai-profile adaptation |
| --- | --- | --- |
| Nanako0129 uses console framing and makes the source/update cadence explicit. | Each block reads like a query with a clear evidence boundary rather than decoration. | Use a restrained “evidence ledger” grammar: scope, period, freshness, headline, terrain, provider ledger, evidence rail. Never expose host, repo, stars, SHAs, or personal telemetry. |
| TokenBar leads with promise, product proof, progressive views, privacy, install, and fallback. | A reader understands value before implementation details and can find trust claims near the action. | Keep README order value → real profile preview → outputs → quickstart → privacy → limitations. Keep the dashboard filterable but static and self-contained. |
| coralline and the design systems use semantic roles instead of raw color names. | Light/dark and future accessibility modes can change values without changing meaning. | Document roles (`text`, `muted`, `accent`, `evidence`, `unknown`, `border`) in `DESIGN.md`; keep provider color as identity, never confidence. |
| Primer, Carbon, Radix and Vega-Lite pair marks with labels, focus, descriptions, and tables. | The visual is useful at a glance and remains understandable without color or hover. | Preserve visible counts and percentages, add accessible descriptions, keyboard focus, reduced-motion, and a future table companion only from `VizStats`. |
| Pilotfish/remora make boundaries, rollback, and support paths explicit. | Operational trust is part of product design, not a footer afterthought. | Keep local-first/privacy copy next to publish actions and document exact fallback/limitations. |

## Do not copy

- No personal host/OS/homelab facts, repository names, stars, downloads,
  commit logs, lineage graphs, or contact identities.
- No glass/aurora/blur, gradients, neon, animated 3D, remote font requests,
  JavaScript fetches, telemetry, or hosted account assumptions.
- No generic GitHub activity score, line-level AI detector, provider sum used as
  unique commits, or source-code-style inference.
- No runtime React/Radix/Vega/Plot dependency and no open-ended plugin that can
  receive private event data. A design system is documentation and tested
  render primitives, not a new data path.

## Recommended visual direction

The selected direction is **Structural Current / Evidence Ledger**:

1. A quiet ice-blue or deep-blue ground with a strict 4px rhythm.
2. One cool verified signal (blue/teal) and one warm evidence signal (amber).
3. One display face for hierarchy, a readable body face, and a tabular mono
   face for numbers; all are local fallback stacks.
4. Information ranked by size and alignment, not by saturation or effects.
5. Static terrain with a faint structural grid and explicit height/share legend;
   the terrain remains a data encoding, never an illustration.
6. Provider rows are a ledger: icon + name + bar + count + percentage, with the
   overlap statement adjacent to the values.

This gives the profile a distinctive technical character without pretending
that a visual style is evidence of AI participation.

## Confidence and gaps

- High confidence: semantic roles, progressive disclosure, chart/table parity,
  privacy copy near publication, and local fallback behavior are repeated across
  the primary sources and already fit the repository architecture.
- Medium confidence: a terminal-inspired micro-label and faint terrain grid are
  likely to improve memorability, but must be checked at 320px README scale and
  with the existing SVG allowlist.
- Unknown: recruiter preference is not a measurable truth in this repository;
  evaluate with the real Profile preview and synthetic zero/aggregate-only
  states rather than adding an unvalidated “score.”

## Implementation boundary

The next slice is presentation-only: a documented token contract, a small set
of pure SVG/dashboard primitives, stronger visual QA, and no ACE/schema,
aggregation, privacy, CLI, or output-count changes.

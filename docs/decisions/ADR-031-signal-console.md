# ADR-031: Signal Console visual system

- **Status:** Accepted (v0.8.0 candidate)
- **Date:** 2026-08-23
- **Decision owners:** ai-profile maintainers
- **Supersedes:** the presentation portions of ADR-026 (Editorial Signal
  skin) for the dashboard; refines ADR-025 (Flat Evidence Ledger) for the
  summary card, heatmap, and badge. ADR-021 (self-contained dashboard),
  ADR-020 (heatmap/badge semantics), ADR-029 (provider-ledger-only
  rendering), and ADR-030 (automation) are unchanged.

## Context

The v0.6–v0.7 dashboard opened with an oversized hero headline, a tracked-out
uppercase eyebrow, a lede paragraph, a sticky filter deck with a wide soft
shadow over a hairline border, and a second "ledger" column that repeated the
hero numbers. A general GitHub visitor on a phone saw the title and one
number above the fold and had to scroll past decoration to reach the commit
map. An independent anti-pattern scan (`npx impeccable detect`) reported six
findings on that page: layout-property animation (`transition: width`), a
hero eyebrow chip, all-caps body text, hairline border paired with a wide
shadow (twice), and a flat type hierarchy. Separately, the README-width SVGs
used an 11px floor and a centred 12-week matrix that read small after GitHub
scales the 830px card.

## Decision

Adopt one coordinated **Signal Console** grammar across the dashboard, summary
SVG, heatmap SVG, and badge. "Tech feeling" comes from information
architecture, status treatment, precision alignment, typography, and data
interaction — not from neon, glass, gradients, gradient text, oversized
titles, thin-border-plus-shadow cards, thick side stripes, or monospace as
decoration.

### Dashboard

- First viewport: a compact **status line** (title, `Snapshot <date> UTC`,
  period, schema), a four-cell **core metric strip** (AI-attributed commits
  with share track; AI actor presences; active AI days; unattributed
  commits), the **provider toolbar**, and the **commit map**. The hero
  block, eyebrow, lede, sticky deck, and duplicate ledger are removed.
- Desktop: primary activity region plus a provider/evidence sidebar
  (`minmax(0, 1.6fr) minmax(18rem, 0.8fr)`). Below 54rem everything stacks
  in one column in DOM order: metrics, toolbar, commit map, providers,
  evidence. Metrics go 4-up → 2-up → 1-up (22rem). DOM order equals reading
  order equals tab order at every width.
- Definitions (unique commits, unattributed ≠ human, how to improve
  attribution, privacy boundary) move into a native `<details>` disclosure
  with a visible chevron and keyboard-operable `<summary>`.
- `generated_on` is shown prominently and labelled **snapshot** in the
  status line and footer; the page never says live or real-time. Daily
  freshness remains the publishing workflow's responsibility.
- One token system: semantic colour roles (`--canvas`, `--surface`,
  `--border`, `--text`, `--muted`, `--accent`, `--evidence`,
  `--evidence-surface`, `--grid-empty`, `--focus`) for light, system-dark,
  and explicit dark; a five-step type scale `--text-1..5`
  (13/15/18/28/36px) with a ≥2:1 span the static detector can see; mono
  reserved for numeric data and dates.
- Motion is limited to short `transform`/`opacity` state changes (day-cell
  hover scale, disclosure chevron). No width/layout-property transitions.
  `prefers-reduced-motion: reduce` removes both the transition and the
  transform.
- No `box-shadow` except the inset focus/selection ring; no uppercase
  labels; no gradients.
- Theme default follows the system; the explicit auto → light → dark
  toggle, provider filter, provider rows, roving-tabindex calendar, tooltip
  (hover, focus, click-pin, Escape), live status region, and CSP/network
  closure are unchanged in behaviour.

### Summary SVG (830 wide)

- Header becomes a status line: 18px display title on the left,
  `<period> · snapshot <generated_on>` in mono on the right.
- The hero figure (40px mono accent) and four secondary metrics form one
  **metric console strip**: hairline separators in the border token, values
  on a shared baseline, labels below (`Active AI days` carries its
  `(author dates)` unit on a second line).
- The 12-week matrix is left-aligned on the card margin (24px weekday
  gutter) with 52px cells instead of centred 38px cells; bins, bar heights,
  share ramp, rails, legend, and the publishable-only cue are unchanged.
- Type floor rises from 11px to 12px on the fixed 12/13/18/40 scale.

### Heatmap SVG (830 wide)

- Same status-line header; label floor 10px → 11px; month labels 12px;
  grid geometry unchanged (it already fills the card width).

### Badge (24px high)

- Left plate is the card canvas with a 6×6 accent commit-node mark before
  `AI-assisted`; right plate stays the accent share. The amber evidence chip
  is no longer used on the badge.

## Non-goals and invariants

`VizStats`, `profile.json`, the ACE schema (`0.3.0`), the CLI, the eight
output filenames, provider/evidence semantics ("unknown is not human",
provider counts may overlap, the daily map shows publishable dates only),
determinism, self-containment, CSP, and the zero-network rule are unchanged.
No framework, remote font, API, tracker, renderer data source, generated
output class, or dependency is added. v0.8.0 is a product feature version,
not a schema version.

## Consequences

Summary, heatmap, and badge snapshots and README sample assets change and are
regenerated only through the sanctioned commands. `DESIGN.md` records the
token system and composition grammar; the repository-root `.impeccable.md`
points design tooling at those canonical documents. The dashboard must stay
at zero `impeccable detect` findings; responsive browser QA covers 1440,
1024, 768, 390, 320, and the 195px extreme-narrow case in light, dark, and
system themes.

## Verification

- `tests/unit/test_signal_console.py` (red-first) pins the information
  architecture, token/type contract, motion rules, snapshot labelling,
  disclosure semantics, and the SVG geometry above; existing dashboard,
  summary, calendar-band, heatmap, and badge contracts are updated where the
  presentation deliberately changed.
- `npx impeccable detect --json` on the rendered dashboard returns `[]`.
- Playwright QA records zero horizontal overflow at every viewport, the
  390px first viewport containing the metric strip and commit map, working
  filter/theme/tooltip/keyboard/disclosure interactions, reduced-motion
  behaviour, and zero network requests (`docs/reviews/v0.8.0-visual-qa.md`).

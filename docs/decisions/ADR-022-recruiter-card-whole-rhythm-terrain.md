# ADR-022: Recruiter-first summary card with a whole-rhythm terrain

Date: 2026-08-01 · Status: accepted; daily visual clauses superseded by ADR-025
Superseded by: ADR-025 for the summary-card daily visual
Supersedes: ADR-020's "Band interplay" clause only ("The isometric band
stays AI-only ... a zero-attributed-AI day renders as the flat base
diamond" — quoted as corrected by ADR-020's 2026-08-01 erratum).
Every other ADR-020 decision (heatmap card, badge, `DayCell`
whole-rhythm contract, bundle allowlist) is unchanged.

> Status note (2026-08-04): ADR-025 replaces the perspective/prism treatment
> described below. This ADR remains the source for the recruiter-facing card
> order, whole-rhythm volume/share semantics, honest empty states,
> provider-overlap disclosure, and compatible typography/privacy boundaries;
> read ADR-025 for the active flat daily visual contract.

## Context

The summary card is the first thing a recruiter or hiring manager sees
on a GitHub Profile. The pre-v0.4.8 card was organized around the
project's internal vocabulary (summary → providers → AI-only calendar →
evidence panel), and its isometric band encoded *summed
provider-attributed counts* as stacked per-provider prisms — an
intensity unit that overlaps across providers, needs a caveat sentence
to stay honest, and renders a day with zero attributed AI commits
identically to a no-data day even though ADR-020 already added the
day's whole rhythm (`DayCell.total_commits`) to the contract.

The owner asked for an HR-first redesign: a reader should understand the
record in about five seconds, and the terrain — the card's most
distinctive visual — should be semantically honest without a footnote
doing the load-bearing work.

## Decision

**The card becomes the `AI Collaboration Record`** with this fixed
recruiter-facing order: header + period → hero AI-attributed unique
commits with its share of scanned commits → secondary ledger (active AI
days, provider count, actor presences, unattributed commits) → the
12-week isometric collaboration terrain → the top-six provider ledger →
a compact evidence rail, privacy cue, generation date, and the existing
multi-actor footnote.

**The terrain charts the whole rhythm with the heatmap's own fixed
bins** (shared arithmetic in `render/_bins.py` so the two cards can
never disagree):

- HEIGHT is `DayCell.total_commits` through the fixed volume bins
  0 / 1 / 2-4 / 5-7 / 8+ (`TERRAIN_HEIGHTS`, saturating top bin — a
  documented cap, not a silent clip);
- the TOP-FACE HUE is the day's AI share
  (`DayCell.ai_commits / total_commits`) through the heatmap's fixed
  share bins: neutral for a day with zero attributed AI commits (which
  is not provably human — `compute_daily_commit_totals` counts
  unattributed as well as explicitly human-declared commits in the
  total), quantized quarters to full accent for a day whose commits are
  all AI-attributed;
- provider rows and counts NEVER contribute to terrain geometry — a
  one-commit multi-provider day renders byte-identically to a
  one-commit single-provider day (pinned by regression test). The
  stacked per-provider prism encoding is retired; provider identity
  lives in the provider ledger and the dashboard.

**Honest empty states.** The daily terrain remains publishable-only
(ADR-018). A profile with nonzero headline totals but no published daily
series renders exactly `Daily activity is not published for this
profile` in the terrain slot — never a fabricated grid. A profile with
no data at all keeps the existing onboarding zero state. Unknown /
unattributed activity is never labelled human anywhere on the card.

**Non-exclusive provider ledger.** The provider table carries an
explicit in-place statement that provider totals are not mutually
exclusive, instead of leaving the overlap to the footer footnote alone.

**Visual system.** 4px spacing scale, 24px outer padding, 20-24px
between sections; fixed SVG type sizes 11/12/13/16/38 with weights 400
(labels) / 600 (values, section labels) / 700 (hero); three local type
stacks mirroring the dashboard (display: `IBM Plex Sans Condensed`
first; body: `IBM Plex Sans`; numeric/data: `IBM Plex Mono`) with local
fallbacks and no font fetch. `chip_bg` survives as a small
evidence-backed chip behind the evidence-rail label — an evidence cue,
not a large warning panel. Provider brand color appears only on glyphs
and thin bars; body text stays the theme text color. The dashboard H1
becomes `Evidence-backed AI collaboration.` to match.

## Consequences

- `render_summary(stats, theme) -> str` keeps its signature, the 830px
  width, dynamic deterministic height, and both themes; `VizStats`, the
  ACE schema, aggregation, privacy policy, CLI, and the eight-output
  bundle are untouched.
- The summary snapshot family regenerates via its sanctioned command
  (`python tests/unit/test_render_summary.py`); the heatmap/badge family
  is byte-unchanged (the `_bins` extraction is a pure refactor).
- The terrain now discloses per-day total-commit volume for explicitly
  publishable repositories on the summary card, exactly as the heatmap
  card already does for the same repositories (ADR-020 accepted that
  disclosure); aggregate-only repositories still never surface dates.
- A day with zero attributed AI commits is now visible on the summary
  card (neutral prism) instead of indistinguishable from a no-data day —
  the honest reading ADR-020 introduced for the heatmap, applied
  consistently. The neutral hue states only "zero attributed AI": such a
  day's commits may be unattributed, explicitly human-declared, or both,
  and the card never claims human authorship for them.
- Fully static SVG: the SMIL ban and the no-entrance-animation ruling
  remain permanent.

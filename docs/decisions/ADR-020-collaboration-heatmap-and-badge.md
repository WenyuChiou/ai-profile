# ADR-020: Collaboration-ratio heatmap + badge (round D4)

Date: 2026-07-23 · Status: accepted
Spec: `.ai/round_d4_heatmap_spec.md` (binding decisions frozen there)
Erratum (2026-08-01, v0.4.8 review round): wording that equated a day
with `ai_commits == 0` with "human-only" was corrected below to
"zero-attributed-AI" — `compute_daily_commit_totals` counts unattributed
(unknown) commits as well as explicit `AI-Mode: Human-Only` declarations
in `total_commits`, so such a day is never provably human. The decisions
themselves are unchanged.

## Context

The owner asked for a GitHub-style commit-history heatmap with an
explicit requirement: it must include their OWN commits, not only the
AI-attributed subset. GitHub's graph answers "did you work?"; no
existing tool draws "HOW do you work with AI?" — that ratio view is
this project's most differentiated visual.

## Decision

**Two-dimensional day cells.** A separate heatmap card
(`heatmap-{light,dark}.svg`) renders a Monday-anchored year grid where
each day cell encodes:

- intensity (fill-opacity, 4 steps): `total_commits` — every commit
  regardless of attribution, zero-attributed-AI commits included,
  bucketed 1 / 2-4 / 5-7 / 8+ (the D2 band's own bucketing);
- hue (fill color, 5 flat steps): the day's AI share, selected by
  integer arithmetic (`ceil(4·ai/total)`, bin 0 reserved for
  zero-attributed-AI days) and interpolated neutral→accent per theme. Quantized
  bins, not a continuous ramp: legend-explainable, snapshot-stable, no
  false precision, no float-equality platform edges.

**Whole-rhythm data contract.** `DayCell` gains `total_commits` (≥1)
and `ai_commits` (0..total); `counts` may now be empty exactly when
`ai_commits == 0`. Cross-invariants validated in `VizStats`:
`max(counts) ≤ ai_commits ≤ sum(counts)` when counts exist. The daily
window widens 84 → 365 days (ADR-018 addendum records the disclosure
change). Aggregation adds policy-free
`compute_daily_commit_totals` (DISTINCT commits per author-day; the
DISTINCT ai/mixed subset per the section-15 definition), and
`privacy._build_daily` merges totals at the single chokepoint —
publishable-only, clock-free, and raising (never fabricating, never
silently dropping) if provider rows arrive without totals.

**The badge.** `badge-{light,dark}.svg` — a flat two-segment shield
"AI-assisted | K% · verified by git" where K is the summary card's own
headline share with the same never-lies rounding, so the badge cannot
disagree with the card. `commits_scanned == 0` → "no data". The
smallest embeddable adoption unit.

**Bundle.** `write_outputs` takes a filename→markup mapping from a
CLOSED allowlist (six SVG names + profile.json) in one transactional
bundle; sorted-by-name deterministic order. `aiprofile render` emits
all six.

**Band interplay.** The isometric band stays AI-only: it slices the
365-day series to its own newest-anchored 84 days, and a
zero-attributed-AI day renders as the flat base diamond (byte-identical
to a no-data day). The whole-rhythm view belongs to the heatmap card
exclusively. (Superseded by ADR-022, v0.4.8: the summary card's terrain
is whole-rhythm.)

## Consequences

- profile.json day cells gain `total_commits`/`ai_commits` (additive;
  no ACE event-schema change — stored events are untouched).
- Snapshot families: the heatmap/badge family regenerates only via
  `python tests/unit/test_heatmap_svg.py`; the summary family keeps
  its own command (AGENTS.md records both).
- Publishing daily totals discloses human-activity volume per day for
  explicitly publishable repositories — accepted by the owner's ask;
  aggregate-only repositories still never surface dates
  (privacy-canary e2e sweeps now cover all seven dist files).
- Fully static SVG (the SMIL ban is permanent, pinned per card).

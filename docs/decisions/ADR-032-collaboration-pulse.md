# ADR-032: Summary-card Collaboration Pulse

Date: 2026-08-23
Status: Accepted

## Context

Since ADR-025 the summary card's daily section has been an 84-cell
12-week matrix: one background track cell per date, a small volume bar
inside each cell, weekday labels in a left gutter, and quarter-window
alignment rails. At README scale the section read as a second, smaller
heatmap — visually redundant with the standalone heatmap card and
generic among GitHub profile cards. v0.8.0 (ADR-031) widened the cells
but kept the grid form.

The semantics under the matrix are settled and must not move: the daily
series is publishable-only (ADR-018), day geometry is provider-
independent (ADR-022), volume and AI-share use the fixed shared bins in
`render/_bins.py` (ADR-020/ADR-025), zero attributed AI is never a
human claim, and `render_summary(stats, theme)` stays a deterministic
pure function (ADR-010).

## Decision

Replace the summary card's 84-cell matrix with a **Collaboration
Pulse** — a distinctive static pulse signature. Summary card only: the
dashboard, standalone heatmap, and badge are unchanged.

- The 84 window dates run **oldest to newest, left to right**, as one
  row of baseline-anchored marks, visually grouped as **12 groups of
  seven** with a wider gap between groups. The grouping is a structural
  7-day rhythm; it is never labelled as calendar weeks. There are no 84
  background heatmap cells.
- Each activity mark is **6px wide**. The **neutral outer pulse height**
  maps the existing total-commit bins 1 / 2-4 / 5-7 / 8+ to
  **12/24/36/48px** (`PULSE_HEIGHTS`, indexed by `_bins._volume_bin`).
- The **accent fill rises from the baseline** and spatially maps the
  existing `_bins._share_bin` levels (0..4) to **0/25/50/75/100%** of
  the pulse height. The fill uses the theme accent token, so the AI
  share is carried by both position and hue — never color alone. A
  zero-attributed-AI day keeps the pure neutral (muted) pulse; that is
  not a human claim, because unattributed history sits in that bin too.
- A date with **no publishable activity renders only a 2px baseline
  tick** in the border token.
- All geometry is integer arithmetic (every pulse height is a multiple
  of 4, so the quarter fills divide exactly); output stays byte-stable.
- **Month-boundary labels stay**, derived only from `stats.daily`
  (never the clock), centered over the group containing the boundary
  date. **Weekday labels and the quarter-window rails are removed** —
  the wider group gaps carry the reading rhythm instead.
- Section label: `Daily collaboration pulse · 12-week published
  window`. Legend, direct and one line: `height = total commits ·
  fill = AI-attributed share · publishable dates only`.
- The `<desc>` states the exact date window, the window's peak daily
  total, both encodings, and the publishable-only scope.
- The unpublished-daily notice, zero state, card width 830, theme
  tokens, local font stacks, and the 12px type floor are unchanged; the
  card height is recomputed deterministically from the new block height
  (the pulse block is shorter than the old grid, so the card shrinks
  with no dead band).

## Consequences

- The summary card gains a recognizable, non-generic signature mark
  while the heatmap card remains the only calendar-grid surface —
  the two cards no longer duplicate a form.
- `VizStats`, `DayCell`, `profile.json`, ACE 0.3.0, the CLI, the eight
  output filenames, and `render_summary(stats, theme)` are untouched.
  This is presentation-only (product v0.8.1, no schema bump).
- The AI share is now read against a day's own pulse height (a
  proportion), not an absolute hue step; the legend and `<desc>` state
  this directly. The five share bins and four volume bins are shared
  with the heatmap exactly as before, so the two cards still cannot
  disagree about what a bin means.
- Weekday information is no longer available on the summary card; the
  heatmap card retains weekday rows for readers who need them.
- Snapshot family regenerated only via the sanctioned
  `python tests/unit/test_render_summary.py`; heatmap and badge
  snapshots stay byte-identical.

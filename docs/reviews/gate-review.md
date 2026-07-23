# Gate 18 D6 heatmap aesthetics verification review

Date: 2026-07-23

Review range: `b70f3a5..63f00c6`

Reviewer posture: independent Principal Software Engineer; verification only.
No production code, test code, schema, or design code was changed during this
review. This report overwrites the prior gate review artifact per repository
convention.

## Executive summary

Round D6 is behaviorally sound but should take a small cleanup before the next
gate. The requested aesthetic changes render correctly: populated day cells are
11px squares on the same 14px step, `rx=3`, solid hex fills replace heatmap
`fill-opacity`, the stat line uses styled `tspan`s, the date window is
right-aligned, and the redesigned legend renders with numeric volume labels and
0%/100% share endpoints.

Full suite and lint are clean. Independent probes confirmed byte determinism,
snapshot/sample consistency, unchanged badge and empty-state bytes from the
pre-range tree, unchanged Monday-anchored grid positions, no SMIL, well-formed
XML, intact title/desc accessibility metadata, no heatmap `fill-opacity`, no
color collisions with the card background or empty-track color, and no
repo/path/email leakage across an end-to-end temp-home render.

The remaining issues are narrow maintainability/documentation defects in the
renderer source: `_cell_rects` duplicates the color formula instead of using the
new `_cell_fill` helper, and two comments/docstrings still describe the old
opacity model.

## Findings

| Severity | Issue | Location |
|---|---|---|
| Low | `_cell_rects` recomputes day-cell colors with `_lerp_hex(...)` instead of calling `_cell_fill(...)`, even though the D6 brief says `_cell_fill` is the single color source for day cells and legend swatches. The current output matches, but this leaves two formulas that can drift on the next palette change. | `src/aiprofile/render/heatmap_svg.py:176`, `src/aiprofile/render/heatmap_svg.py:189` |
| Low | Stale renderer comments still describe intensity as `fill-opacity` / `volume-bin opacity` after the implementation moved to solid bg-mixed hexes. This is not user-facing output, but it contradicts the new renderer contract and can mislead future changes. | `src/aiprofile/render/heatmap_svg.py:6`, `src/aiprofile/render/heatmap_svg.py:168` |

## Review basis

Reviewed `README.md`, `CONTRIBUTING.md`, the handoff brief, the
`b70f3a5..63f00c6` diff, and the changed source/test artifacts:
`CHANGELOG.md`, `src/aiprofile/render/heatmap_svg.py`,
`tests/unit/test_heatmap_svg.py`, `tests/snapshots/heatmap_light.svg`,
`tests/snapshots/heatmap_dark.svg`,
`docs/assets/heatmap-sample-light.svg`, and
`docs/assets/heatmap-sample-dark.svg`.

The range is renderer/test/sample scoped. `git diff --name-only
b70f3a5..63f00c6` does not touch `src/aiprofile/viz.py`,
aggregate/privacy/export/CLI modules, `src/aiprofile/render/badge_svg.py`, or
`src/aiprofile/render/summary_svg.py`.

## Verification evidence

Commands and observed results:

- `git status --short`: clean before verification.
- `git rev-parse --short HEAD`: `63f00c6`.
- `git log --oneline --decorate -5`: HEAD was `63f00c6 (HEAD -> main, origin/main) Round D6: heatmap aesthetic pass (solid cells, styled stats, clean legend)`.
- `git diff --name-only b70f3a5..63f00c6`: only `CHANGELOG.md`, heatmap sample assets, `src/aiprofile/render/heatmap_svg.py`, heatmap snapshots, and `tests/unit/test_heatmap_svg.py`.
- `git diff --stat b70f3a5..63f00c6`: 7 files changed, 1680 insertions, 1626 deletions.
- `git diff --check b70f3a5..63f00c6`: no whitespace errors.
- `python -m pytest tests -p no:cacheprovider`: `493 passed, 4 skipped in 26.86s` (exit 0). The run emitted unrelated global-environment warnings from `requests` and `langsmith`.
- `python -m ruff check src tests scripts`: `All checks passed!` (exit 0).
- Byte-safe `git show b70f3a5:<path>` comparisons against current files:
  `tests/snapshots/badge_light.svg`, `badge_dark.svg`,
  `badge_zero_light.svg`, `badge_zero_dark.svg`,
  `heatmap_empty_light.svg`, `heatmap_empty_dark.svg`,
  `docs/assets/badge-sample-light.svg`, and
  `docs/assets/badge-sample-dark.svg` were all byte-identical.
- `rg -n "fill-opacity|opacity|_cell_fill" ...`: heatmap rendered SVG/tests
  correctly ban `fill-opacity`; the remaining heatmap source matches were the
  stale comments/docstrings listed above and the intended `_cell_fill` helper
  usage in the legend/tests.

Independent renderer probe result:

```text
determinism populated light True
determinism empty dark True
github-light bg/track collisions: none
github-light share0-volume0: #B4B9BE track: #eff2f5 bg: #ffffff
github-dark bg/track collisions: none
github-dark share0-volume0: #484E55 track: #21262d bg: #0d1117
geometry light: positions_equal=True; old_day_count=365 current_day_count=365; old_widths=['10']; current_widths=['11']; current_rx=['3']
geometry dark: positions_equal=True; old_day_count=365 current_day_count=365; old_widths=['10']; current_widths=['11']; current_rx=['3']
populated-light role img title True desc True smil False fill-opacity False
empty-dark role img title True desc True smil False fill-opacity False
```

Independent privacy canary result:

```text
assets: badge-dark.svg, badge-light.svg, heatmap-dark.svg, heatmap-light.svg, profile.json, summary-dark.svg, summary-light.svg
badge-dark.svg: leaks=0
badge-light.svg: leaks=0
heatmap-dark.svg: leaks=0
heatmap-light.svg: leaks=0
profile.json: leaks=0
summary-dark.svg: leaks=0
summary-light.svg: leaks=0
total_leaks=0
```

The canary used a temp `AIPROFILE_HOME`, a temp git repo named
`SECRET_REPO_NAME_CANARY`, author email
`secret.email.canary@example.test`, and filename
`sensitive_file_canary.txt`; none appeared in the seven dist assets.

## Verified areas without blocking findings

- Heatmap day cells are flat hex fills; `fill-opacity` is absent from
  populated and empty heatmap output.
- All 20 `(share_bin, volume_bin)` colors per theme are pairwise distinct by
  the committed tests; the independent probe also found no collisions with
  `theme.bg` or `theme.bar_track`.
- The share-0/volume-0 color is distinguishable from empty-track and card-bg
  colors in both themes.
- Monday-anchored `x,y` positions match the pre-range populated heatmap
  snapshots; only cell width changed from 10 to 11.
- XML is well-formed; `role="img"`, `<title>`, and `<desc>` are present.
- The static rendering ban remains intact for the heatmap path: no `<animate`,
  `<set`, or `@keyframes`.
- Snapshot and docs sample assets match the current renderer; badge and
  heatmap empty-state files are byte-identical to the pre-range tree.

## Severity summary

- Critical: 0
- High: 0
- Medium: 0
- Low: 2

## Final recommendation

READY AFTER MINOR FIXES

# Gate 17 D5 + D4 verification review

Date: 2026-07-23

Review range: `bd0e3ce..1864d65`

Reviewer posture: independent Principal Software Engineer; verification only.
No production code, test code, schema, or design code was changed during this
review. This report overwrites the prior gate review artifact per repository
convention.

## Executive summary

Rounds D5 and D4 are ready for the next gate. The D4 privacy boundary is the
right shape: aggregation remains policy-free, `_build_daily` applies the
FULL-only chokepoint to both provider rows and whole-rhythm totals, and a
provider-date without a matching totals row fails loudly instead of fabricating
or dropping data.

Full suite and lint are clean. Independent probes confirmed aggregate-only
dates/totals do not surface through `build_viz_stats` or through an end-to-end
`init -> scan -> render` flow across all seven dist assets; invalid D4
`DayCell` shapes are rejected; heatmap bin math, Monday anchoring, badge
rounding, zero-state behavior, SMIL/static rendering, and the closed bundle
allowlist behave as expected.

## Findings

| Severity | Issue | Location |
|---|---|---|
| Low | Stale source comment says the 84-day summary band window "matches viz.DAILY_WINDOW_DAYS exactly"; D4 intentionally widened the validated daily contract to 365 days while the band slices its own 84-day window. The code is correct, but the comment now contradicts the design and can mislead future maintenance. | `src/aiprofile/render/summary_svg.py:171` |

## Review basis

Reviewed `README.md`, `CONTRIBUTING.md`, the handoff brief, the
`bd0e3ce..1864d65` diff, and the relevant changed files:
`src/aiprofile/aggregate.py`, `src/aiprofile/privacy.py`,
`src/aiprofile/viz.py`, `src/aiprofile/export.py`, `src/aiprofile/cli.py`,
`src/aiprofile/render/summary_svg.py`, `src/aiprofile/render/heatmap_svg.py`,
`src/aiprofile/render/badge_svg.py`, `src/aiprofile/render/brand.py`,
`scripts/vendor_brand_icons.py`, `THIRD_PARTY_NOTICES.md`, and the D4/D5
unit and integration tests.

The codebase-memory MCP discovery call was cancelled by the tool, so review
fell back to local diff/file inspection.

## Verification evidence

Commands and observed results:

- `git status --short`: clean before verification.
- `git log --oneline --decorate -8`: HEAD was `1864d65 (HEAD -> main, origin/main) Round D4: collaboration-ratio heatmap + badge (your own commits included)`.
- `git diff --stat bd0e3ce..1864d65`: 47 files changed, 3918 insertions, 161 deletions.
- `git diff --name-only bd0e3ce..1864d65`: confirmed the expected D5/D4 source, docs, asset, and test files.
- `python -m pytest tests -p no:cacheprovider`: `491 passed, 4 skipped in 25.05s` (exit 0). The run emitted unrelated global-environment warnings from `requests` and `langsmith`.
- `python -m ruff check src tests scripts`: `All checks passed!` (exit 0).
- `python scripts/vendor_brand_icons.py --source lobe --ref fbd2d56e3f734e889f1373e71c8368cc4e60e0d7 --map openai:openai:OpenAI --map xai:grok:Grok`: exit 0; `2 vendored, 0 skipped, 2 attempted`, with OpenAI/Grok BrandSpec stubs and WCAG contrast rows emitted.
- Follow-up direct network fetch using `vendor_one_lobe(...)` failed with `WinError 10051` unreachable network. Because of that sandbox flake, I did not claim a second independent network byte-diff; I verified the successful pinned vendoring output plus local committed constraints.
- Local D5 constraint probe: `BRAND["openai"]` and `BRAND["xai"]` are present, ASCII path strings, forbidden XML-attribute characters absent, and their achromatic color fields match the vendoring tool output (`#000000/#EBEBEB`, `#7A7A7A/#2E2E2E`).
- `Select-String THIRD_PARTY_NOTICES.md` confirmed the lobe-icons pinned source, commit `fbd2d56e3f734e889f1373e71c8368cc4e60e0d7`, MIT License header, and `Copyright (c) 2023 LobeHub`.
- `Select-String src/aiprofile/render/*.py -Pattern "datetime\.today|datetime\.now|<animate|<set|@keyframes"` found no render-time clock use or SMIL/CSS animation; the only match was a comment documenting the ban.
- `Select-String tests/snapshots/*.svg -Pattern "<animate|<set|@keyframes"` found no snapshot animation markup.

Independent adversarial probe result:

```text
custom probes passed: in-process privacy, CLI canary assets, DayCell contract, bin math, badge honesty, grid anchoring
```

That probe covered:

- Direct `build_viz_stats` input with one FULL repo and one aggregate-only repo. The private repo carried AI and human-only canary dates (`2026-07-21`, `2026-07-20`) and distinctive totals; `stats.daily`, `profile.json`, summary SVG, heatmap SVG, and badge SVG carried only the FULL dates.
- End-to-end CLI flow with two real git repositories: `init`, `scan --full` for the FULL repo, default aggregate-only `scan` for the private repo, then `render`. The seven output files were exactly `badge-dark.svg`, `badge-light.svg`, `heatmap-dark.svg`, `heatmap-light.svg`, `profile.json`, `summary-dark.svg`, and `summary-light.svg`; none contained the private date or repo-name canaries. `profile.json["daily"]` contained only the FULL repo dates.
- `_build_daily` raised on provider rows without matching whole-rhythm totals.
- Invalid `DayCell` shapes were rejected: `ai_commits > total_commits`, nonempty counts with `ai_commits == 0`, provider count greater than `ai_commits`, `ai_commits` greater than sum of provider counts, bool leaves, and a 365-day span. A 364-day span was accepted.
- Heatmap share bins at zero, tiny nonzero, 1/4, 1/2, 3/4, and 100%; volume bins at 1, 2, 4, 5, 7, and 8.
- Badge percentage uses the summary `_pct_label` behavior, including `<1%`, `>99%`, exact `100%`, and zero-commit `no data`.
- Known-date grid anchoring: newest Sunday `2026-07-19` yields window start `2025-07-20`, 53 Monday-anchored columns, and the summary band keeps an 84-cell newest-anchored slice.

## Verified areas without blocking findings

- `compute_daily_commit_totals` counts all stored commits per repository/date
  and AI/mixed distinct commits as the subset, using the author-date ISO prefix
  rather than SQLite date conversion.
- `_build_daily` filters both provider rows and totals rows through resolved
  publication levels, merges same-date FULL repo totals, includes human-only
  FULL days, trims clock-free from the newest publishable date, and refuses
  mismatched provider/totals input.
- `VizStats` validates the D4 whole-rhythm fields with exact int/bool rules,
  ordered unique dates, ordered unique provider counts, provider-row subset
  checks, 365-day window bound, and canonical provider vocabulary.
- Heatmap rendering is deterministic, static, window-scoped, and uses integer
  share-bin arithmetic.
- The summary calendar band correctly slices its own last 84 days and renders
  D4 human-only days as flat base diamonds.
- Badge share matches the summary headline rounding and has the honest
  `commits_scanned == 0` state.
- `write_outputs` now uses the closed six-name SVG allowlist plus
  `profile.json`, sorted deterministic output order, and the existing rollback
  guarantees remain covered by `test_export_atomic`.
- D5 keeps unsupported multi-path marks as letter tiles rather than
  approximating them, and lobe-icons notice preservation is documented.

## Severity summary

- Critical: 0
- High: 0
- Medium: 0
- Low: 1

## Final recommendation

READY FOR NEXT GATE

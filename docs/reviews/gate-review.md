# Gate 14 D2 calendar verification review

Date: 2026-07-22

Review range: `383792f..5b01195`

Reviewer posture: independent Principal Software Engineer; verification only. No production code, test code, schema, or design code was changed during this review. This report overwrites the prior gate review artifact per repository convention.

## Executive summary

The round D2 daily activity calendar is functionally ready, but one minor hygiene issue should be fixed before the next gate: `git diff --check 383792f..5b01195` fails on a blank line at EOF in `tests/unit/test_calendar_band.py`.

The privacy-critical behavior held under live CLI verification: an aggregate-only repository with an in-window canary date contributed to totals but did not publish its date in `profile.json` or either SVG, while the `--full` repository's date appeared as the positive control. The VizStats daily contract rejected malformed containers, duck records, subclass leaves, ordering violations, window-boundary violations, and provider-row subset violations. SQL, renderer, schema-version, lint, full-suite, and snapshot stability checks otherwise passed.

## Findings

| Severity | Issue | Location |
|---|---|---|
| Low | `git diff --check 383792f..5b01195` reports a new blank line at EOF. This is not a behavior defect, but it leaves the range failing Git whitespace hygiene and is trivial to remove. | `tests/unit/test_calendar_band.py:440` |

## Review basis

Reviewed `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, the handoff brief, `.ai/round_d2_isometric_calendar_spec.md`, the commit body for `5b01195`, the full `383792f..5b01195` file list/stat, `docs/decisions/ADR-018-daily-activity-series.md`, `src/aiprofile/viz.py`, `src/aiprofile/aggregate.py`, `src/aiprofile/privacy.py`, `src/aiprofile/cli.py`, `src/aiprofile/config.py`, `src/aiprofile/storage/db.py`, `src/aiprofile/render/summary_svg.py`, `tests/unit/test_aggregate.py`, `tests/unit/test_calendar_band.py`, `tests/unit/test_privacy_boundary.py`, `tests/unit/test_render_summary.py`, `tests/unit/test_schema_event.py`, `tests/unit/test_viz_contract.py`, and the integration helper/end-to-end tests needed for the live CLI probe.

## Verification evidence

Commands and observed results:

- `git status --porcelain=v1` before verification: clean.
- `git diff --stat 383792f..5b01195`: 19 files changed, 2270 insertions, 132 deletions.
- `git diff --name-only 383792f..5b01195`: `CHANGELOG.md`, 2 docs sample SVGs, `docs/decisions/ADR-018-daily-activity-series.md`, `src/aiprofile/__init__.py`, `src/aiprofile/aggregate.py`, `src/aiprofile/cli.py`, `src/aiprofile/privacy.py`, `src/aiprofile/render/summary_svg.py`, `src/aiprofile/viz.py`, 2 SVG snapshots, and 8 unit test files.
- `python -m pytest tests -p no:cacheprovider`: `421 passed, 4 skipped in 23.52s` (exit 0). The run emitted unrelated global-environment warnings from `requests` and `langsmith`.
- `python -m ruff check src tests scripts`: `All checks passed!` (exit 0).
- `python -m pytest tests/unit/test_calendar_band.py tests/unit/test_render_summary.py -p no:cacheprovider`: `53 passed in 0.25s` (exit 0), with the same unrelated warnings.
- `python tests/unit/test_render_summary.py`: wrote 8 snapshot files and 2 sample assets; subsequent `git status --porcelain=v1` produced no output.
- `python tests/unit/test_render_summary.py` again: wrote the same 8 snapshot files and 2 sample assets; subsequent `git status --porcelain=v1` again produced no output.
- `git diff --check 383792f..5b01195`: failed with `tests/unit/test_calendar_band.py:440: new blank line at EOF.`

Independent live CLI privacy probe:

```text
CMD ['init'] RC 0
CMD ['scan', '--full', '<temp>\\publishable'] RC 0
CMD ['scan', '<temp>\\aggregate_only'] RC 0
CMD ['render', '--out', '<temp>\\dist'] RC 0
profile_daily [{'counts': [{'attributed_commits': 1, 'provider': 'anthropic'}], 'date': '2026-07-20'}]
private_date_hits {'profile.json': False, 'summary-dark.svg': False, 'summary-light.svg': False}
full_date_hits {'profile.json': True, 'summary-dark.svg': True, 'summary-light.svg': True}
privacy {'anonymous_aggregate_commits': 1, 'explicitly_publishable_commits': 1, 'includes_anonymous_aggregate': True}
totals {'active_ai_days': 2, 'ai_actor_presences': 2, 'ai_attributed_commits': 2, 'commits_scanned': 2, 'human_declared_commits': 0, 'unknown_commits': 0}
```

Independent VizStats adversarial probe:

```text
ACCEPT 83-day span boundary
REJECT 84-day span boundary
REJECT daily container list
REJECT duck day cell
REJECT duck day count
REJECT str subclass date
REJECT str subclass provider
REJECT int subclass count
REJECT bool count
REJECT unknown slug
REJECT provider without row
REJECT daily exceeds provider total
REJECT duplicate date
REJECT duplicate slug
REJECT slug order
VIZ_PROBE_DONE
```

Independent SQL/schema probe:

```text
sqlite_date_shift ('2026-06-30', '2026-07-01')
multi_provider_rows (DailyProviderRow(repository_uid='repo-sql', date='2026-07-01', provider='anthropic', attributed_commits=1), DailyProviderRow(repository_uid='repo-sql', date='2026-07-01', provider='openai', attributed_commits=1))
schema_010_daily accepted
schema_010_repo_count 1
schema_030_rejected compute_daily_provider_counts unsupported ACE schema_version '0.3.0'
schema_030_rejected compute_repo_aggregates unsupported ACE schema_version '0.3.0'
SQL_PROBE_DONE
```

Independent renderer probe:

```text
github-light polygon_count 100 bounds (244, 432, 586, 611) viewbox (830, 813) animate False g_opacity False
github-dark polygon_count 100 bounds (244, 432, 586, 611) viewbox (830, 813) animate False g_opacity False
RENDER_PROBE_DONE
```

Independent privacy-builder probe:

```text
normal_build_daily (DayCell(date='2026-07-20', counts=(DayCount(provider='anthropic', attributed_commits=1),)),)
string_full_rejected True
lying_dict_direct_internal_dates ['2026-07-18', '2026-07-19', '2026-07-20']
production_build_viz_daily (DayCell(date='2026-07-20', counts=(DayCount(provider='anthropic', attributed_commits=1),)),)
PRIVACY_BUILDER_PROBE_DONE
```

The `LyingDict` result is not listed as a finding because it requires direct misuse of private `_build_daily`; the production path through `build_viz_stats` constructs `levels` via `resolve_publication_levels(cfg)` and preserved the publishable-only filter in the same probe.

## Verified areas without findings

- `privacy._build_daily` is the production policy chokepoint for the new daily series. The live two-repo CLI probe proved an in-window aggregate-only date stayed out of all dist outputs while the publishable date appeared.
- Daily rows remain an honest subset of provider rows: VizStats rejects daily providers without corresponding provider rows and rejects daily totals exceeding provider-row attributed commits.
- The hard window is enforced at the contract layer: an 83-day span is accepted; an 84-day span is rejected, matching the `DAILY_WINDOW_DAYS=84` "span fewer than 84 days" implementation.
- Daily record structure follows the prior sealed-contract posture: exact tuple containers, exact `DayCell`/`DayCount`, exact `str` and `int` leaves, `bool` rejection, date ordering, slug ordering, and duplicate rejection all held.
- `compute_daily_provider_counts` is policy-free and groups by repository uid, verbatim `substr(author_date, 1, 10)`, provider, and distinct commit id. The SQLite probe independently confirmed that `date()` would shift a non-UTC-offset timestamp while `substr()` preserves the author-local date.
- Same-commit multi-provider attribution is represented as one attributed commit in each provider row for that date.
- ACE `0.1.0` stored events remain aggregatable; fabricated `0.3.0` events are rejected by both repo aggregation and daily aggregation.
- The calendar renderer is fully static in the probed SVGs: no `<animate>` and no `<g opacity=...>` markup.
- Calendar polygon coordinates for the capped fixture stayed inside the viewBox in both light and dark themes.
- Snapshot/sample regeneration is byte-stable across two sanctioned runs.

## Severity summary

- Critical: 0
- High: 0
- Medium: 0
- Low: 1

## Final recommendation

READY AFTER MINOR FIXES

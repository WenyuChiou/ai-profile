# v0.4.5 Public Beta promotion dogfood

Date: 2026-07-26

Evaluation baseline:
`05c55e7ee4f743e5e4844eb67c2e8182f1a25e0e`

## Executive result

The sealed-box dogfood gate passed. Four independent user roles used only the
canonical `README.md` and the same native-Linux candidate wheel:

```text
ai_profile_cli-0.4.5-py3-none-any.whl
SHA-256 c03cbf694737bcf53ee44e88b0ddd4feb6ef4d68226a3ff372b03bb5051cff8b
```

| Role | Result | README-external hints | Blocking friction |
|---|---|---:|---:|
| New user | PASS | 0 | 0 |
| Privacy-sensitive user | PASS | 0 | 0 |
| Multiple-provider user | PASS | 0 | 0 |
| Profile publisher | PASS | 0 | 0 |

Gate totals:

- roles completed: 4/4;
- exact candidate-digest matches: 4/4;
- exact eight-file output inventories: 4/4;
- installation or configuration dead ends: 0;
- privacy-canary hits: 0/816 cross-file/cross-encoding checks;
- hand-derived aggregation mismatches: 0;
- executed dashboard-filter mismatches: 0;
- local Profile/Pages-preparation dead ends: 0.

Raw reports and command ledgers are retained outside Git under:

```text
.artifact/v045-dogfood-final/
```

## Role evidence

### New user

The role installed the exact wheel, verified `aiprofile 0.4.5`, and completed
`init -> scan -> aggregate -> render` without external product guidance:

```text
commits scanned = 2
AI-attributed commits = 1
actor presences = 1
unknown commits = 1
outputs = 8
```

The plain commit remained unknown. The explicit Anthropic trailer produced
one Claude presence and one unique AI-attributed commit.

### Privacy-sensitive user

Three isolated repositories exercised `aggregate_only`, `full`, and
`excluded`. The aggregate contained the full and aggregate-only commits; the
excluded repository contributed nothing.

Thirty-four private canaries covered repository and organization names,
paths, prompts, commit subjects and messages, emails, URLs, full and short
SHAs, repository UIDs, and the private salt. Each canary was checked
case-insensitively across all eight public assets as UTF-8, UTF-16LE, and
UTF-16BE:

```text
34 canaries * 8 outputs * 3 encodings = 816 checks
hits = 0
```

Distinct dates independently verified the publication boundary:

| Publication level | Synthetic date | Public result |
|---|---|---|
| `aggregate_only` | 2026-02-11 | absent |
| `full` | 2026-02-12 | present in all six date-bearing outputs (8 occurrences) |
| `excluded` | 2026-02-13 | absent |

### Multiple-provider user

The fixture contained one unknown commit, one `Human-Only` commit, and one
commit with contiguous Anthropic and OpenAI actor groups.

| Metric | Hand-derived | Observed |
|---|---:|---:|
| Commits scanned | 3 | 3 |
| Unique AI-attributed commits | 1 | 1 |
| AI actor presences | 2 | 2 |
| Claude commits / presences / active days | 1 / 1 / 1 | 1 / 1 / 1 |
| OpenAI commits / presences / active days | 1 / 1 / 1 | 1 / 1 / 1 |
| Human-declared commits | 1 | 1 |
| Unknown commits | 1 | 1 |
| Evidence declared / unknown / total | 3 / 1 / 4 | 3 / 1 / 4 |

Executed Chromium checks for All AI, Claude, and OpenAI preserved the
commit/presence distinction, the one-commit active-day denominator, the 100%
share, and the selected state. At 390 pixels, the calendar opened at its
newest edge; its sole roving tab stop was the newest date, keyboard focus did
not scroll back to the oldest date, and the selected focus index survived
filter and theme rerenders. No browser console or page error occurred.

### Profile publisher

The role produced exactly eight assets, parsed all six SVGs, verified the
self-contained CSP dashboard, and copied the responsive clickable summary
card plus light/dark heatmap from the README into a disposable Profile
repository.

The local publication payload used `main`, `/ (root)`, and the exact-case
`dist/dashboard.html` path. No remote existed or was mutated, and no
README-external hint was needed.

## Root reconciliation

The root reviewer independently recomputed the digest, all four inventories,
all four public JSON structures, and the privacy sweep:

```text
wheel digest = c03cbf694737bcf53ee44e88b0ddd4feb6ef4d68226a3ff372b03bb5051cff8b
output inventories = 8 / 8 / 8 / 8
new user = scanned 2, AI 1, presences 1, unknown 1
privacy = scanned 2, AI 2, presences 2, excluded omitted
multi-provider = scanned 3, AI 1, presences 2, human 1, unknown 1
publisher = scanned 3, AI 2, presences 2, unknown 1
privacy = 34 canaries * 8 outputs * 3 encodings, hits 0
date boundary = aggregate-only absent, full present, excluded absent
```

## Findings and dispositions

### Low — Isolated homes trigger a conservative warning

- **Impact:** Evaluators see a warning because private test homes sit beneath
  the ignored outer worktree.
- **Recommendation:** Keep the warning; real users should store private state
  outside published repositories.
- **Disposition:** Accepted as accurate, useful, and non-blocking.

### Low — Windows harnesses require careful stderr and HOME handling

- **Impact:** PowerShell can promote native warnings to
  `NativeCommandError`, and `HOME` is a protected variable name. One
  multi-provider setup attempt briefly created two new files at the user-home
  root before any scan or render.
- **Recommendation:** Treat this as harness friction, not product failure;
  assert every mutable path before product execution and retain raw command
  exit codes and native stderr separately.
- **Disposition:** Resolved. The two newly created files were identified,
  removed, and independently confirmed absent; no pre-existing or tracked
  file was affected. The role restarted with a literal, scope-checked
  `AIPROFILE_HOME`. All final product commands exited zero.

## Dogfood verdict

The native-Linux v0.4.5 candidate passes the promotion dogfood gate: four
independent roles, one digest, zero external hints, zero privacy leaks, exact
aggregation semantics, exact output sets, executed provider filters, and no
installation, configuration, dashboard, keyboard-navigation, or
Profile/Pages-preparation blocker.

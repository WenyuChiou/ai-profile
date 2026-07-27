# v0.4.5 Public Beta promotion dogfood

Date: 2026-07-26

Evaluation baseline:
`371c4273415daab27d029edc3bc89bb060242b41`

## Executive result

The sealed-box dogfood gate passed. Four independent user roles used only the
canonical `README.md` and the same native-Linux candidate wheel:

```text
ai_profile_cli-0.4.5-py3-none-any.whl
SHA-256 1d59db3568c5ebce99fcca09838d806f763f80c5c87289191c9f3b2fbffb51ca
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
.artifact/v045-dogfood/
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
| `aggregate_only` | 2026-01-11 | absent |
| `full` | 2026-01-12 | present in all six date-bearing outputs (8 occurrences) |
| `excluded` | 2026-01-13 | absent |

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
commit/presence distinction, the three-commit denominator, the 33.3% share,
and the selected state. No browser console or page error occurred.

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
wheel digest = 1d59db3568c5ebce99fcca09838d806f763f80c5c87289191c9f3b2fbffb51ca
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
  `NativeCommandError`, and `HOME` is a protected variable name.
- **Recommendation:** Treat this as harness friction, not product failure;
  retain raw command exit codes and native stderr separately.
- **Disposition:** Accepted. All final product commands exited zero and the
  publisher role reported no product stderr.

## Dogfood verdict

The native-Linux v0.4.5 candidate passes the promotion dogfood gate: four
independent roles, one digest, zero external hints, zero privacy leaks, exact
aggregation semantics, exact output sets, executed provider filters, and no
installation, configuration, dashboard, or Profile/Pages-preparation blocker.

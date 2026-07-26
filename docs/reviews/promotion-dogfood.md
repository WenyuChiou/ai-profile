# v0.4.4 Public Beta promotion dogfood

Date: 2026-07-26
Evaluation baseline:
`363fc615e3c4133551f99a881046b26d45b027ac`

## Executive result

The final sealed-box dogfood gate passed. Four roles used only the canonical
`README.md` and the same native-Linux candidate wheel:

```text
ai_profile_cli-0.4.4-py3-none-any.whl
SHA-256 668cf226cd9f292681427ccc2dbc3305d6e886e9a4aa03650f2c160f7074ca3d
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
- installation or configuration dead ends: 0;
- privacy-canary hits: 0/342 pattern/file checks;
- hand-derived aggregation mismatches: 0;
- dashboard filter mismatches: 0;
- local Profile/Pages-preparation dead ends: 0.

All results against the earlier Windows-worktree wheel
`ff7ad454...7a99` are invalidated and excluded from this verdict. Raw final
reports and command ledgers are retained outside Git under:

```text
.artifact/v044-dogfood-r2/
```

## Role evidence

### New user

The role installed the exact wheel, verified `aiprofile 0.4.4`, and completed
`init -> scan -> aggregate -> render` without external product guidance. A
single commit without explicit provenance remained unknown:

```text
commits scanned = 1
AI-attributed commits = 0
actor presences = 0
unknown commits = 1
outputs = 8
```

### Privacy-sensitive user

Three repositories exercised `aggregate_only`, `full`, and `excluded`.
Aggregate output contained one full and one aggregate-only commit; the
excluded repository was omitted.

Thirty-eight private patterns covered repository and organization names,
paths, branches, file content, prompts, commit messages, email, URL, trailer
values, and each actual full/short commit SHA. Every pattern was searched
case-insensitively as UTF-8, UTF-16LE, and UTF-16BE across the aggregate
publication preview and all eight public assets:

```text
38 patterns * 9 public outputs = 342 pattern/file checks
hits = 0
```

Distinct dates independently verified the publication boundary:

| Publication level | Synthetic date | Public result |
|---|---|---|
| `aggregate_only` | 2024-01-11 | absent |
| `full` | 2024-02-22 | date-bearing assets only |
| `excluded` | 2024-03-23 | absent |

### Multiple-provider user

The fixture contained one unknown commit, one `Human-Only` commit, and one
commit with contiguous OpenAI and Anthropic actor groups.

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

The shared commit remained one unique AI commit and two actor presences.
Visible-browser assertions for All AI, Claude, and OpenAI preserved those
units, active days, evidence totals, and the selected state.

### Profile publisher

The role generated a disposable Profile repository with exactly eight assets,
parsed all six SVGs, loaded the self-contained dashboard in Chrome, and copied
the responsive clickable card plus light/dark heatmap from the README. The
Pages instructions identified `main`, `/ (root)`, the case-sensitive
dashboard URL, and deployment-delay recovery. No remote mutation occurred.

## Root reconciliation

The root reviewer recomputed the digest, four inventories, public JSON totals,
and privacy sweep directly from the retained artifacts:

```text
wheel digest = 668cf226...ca3d
output inventories = 8 / 8 / 8 / 8
new user = scanned 1, AI 0, presences 0, unknown 1
privacy = scanned 2, AI 2, presences 2, excluded omitted
multi-provider = scanned 3, AI 1, presences 2, human 1, unknown 1
publisher = scanned 1, AI 1, presences 1, unknown 0
privacy = 38 patterns * 9 outputs, hits 0
date boundary = aggregate-only absent, full present, excluded absent
```

## Findings and dispositions

### High — The first candidate was not built from a native-Linux checkout

- **Impact:** A wheel validated from a WSL process over a Windows worktree had
  different line-ending bytes from the release workflow's Linux checkout and
  could not authorize the bytes CI would publish.
- **Evidence:** The first PR release-candidate job rebuilt
  `668cf226...ca3d` while the manifest expected `ff7ad454...7a99`.
- **Recommendation:** Build from Git blobs exported into a native-Linux
  filesystem, freeze that digest, and invalidate every role result after any
  artifact-byte change.
- **Disposition:** Fixed. A Git-archive source exported to Linux `/tmp`
  reproduced CI's `668cf226...ca3d`. The candidate was replaced and all four
  README-only roles reran from fresh environments against that exact digest.

### Low — Isolated homes trigger a conservative warning

- **Impact:** Evaluators see a warning because retained private test homes sit
  beneath an ignored outer worktree.
- **Recommendation:** Keep the warning; real users should store private state
  outside published repositories.
- **Disposition:** Accepted as accurate, non-blocking privacy guidance.

### Low — Anthropic evidence is displayed as Claude

- **Impact:** A first-time user may not immediately recognize provider
  canonicalization from the trailer example alone.
- **Recommendation:** Clarify provider display aliases in a future
  documentation-only release without changing the frozen candidate bytes.
- **Disposition:** Accepted for v0.4.4. Cardinality and attribution remain
  correct, and `profile.json` preserves the canonical provider identifier.

## Dogfood verdict

The native-Linux v0.4.4 candidate passes the promotion dogfood gate: 4/4
roles, one digest, zero external hints, zero privacy leaks, exact aggregation
semantics, exact output sets, and no installation, configuration, dashboard,
or local Profile/Pages-preparation blocker.

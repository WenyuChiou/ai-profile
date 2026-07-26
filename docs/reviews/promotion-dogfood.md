# v0.4.4 Public Beta promotion dogfood

Date: 2026-07-26
Evaluation baseline:
`c543663d29e8fb7a05e7349242ff0b9b5167253e`

## Executive result

The sealed-box dogfood gate passed. Four roles used only the canonical
`README.md` and the same candidate wheel:

```text
ai_profile_cli-0.4.4-py3-none-any.whl
SHA-256 ff7ad454ab4a06ebc21b4dc82e284e718bce8f3e01446213e63b9cc4c5267a99
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
- public-output privacy-canary hits: 0/648 exact comparisons;
- hand-derived aggregation mismatches: 0;
- dashboard filter mismatches: 0;
- local Profile/Pages-preparation dead ends: 0.

Raw reports and command ledgers are retained outside Git under:

```text
.artifact/v044-dogfood/
```

## Role evidence

### New user

The role installed the exact wheel, verified `aiprofile 0.4.4`, and completed
`init -> scan -> aggregate -> render` without product guidance beyond the
README. A single commit without explicit provenance remained unknown:

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
excluded repository was omitted and refused rescan.

The role created private canaries in repository and organization names,
absolute and relative paths, branches, file contents, prompts, commit
messages, emails, URLs, trailers, models, tools, and roles. The sweep searched
72 exact original/lowercase UTF-8 tokens across the aggregate publication
preview and all eight assets:

```text
72 tokens * 9 public outputs = 648 comparisons
hits = 0
broader fragment hits = 0
```

Distinct dates independently verified the publication boundary:

| Publication level | Synthetic date | Public matches |
|---|---|---:|
| `aggregate_only` | 2011-01-11 | 0 |
| `full` | 2012-02-22 | 8 |
| `excluded` | 2013-03-03 | 0 |

### Multiple-provider user

The fixture contained one unknown commit, one `Human-Only` commit, and one
commit with contiguous OpenAI and Anthropic actor groups.

| Metric | Hand-derived | Observed |
|---|---:|---:|
| Commits scanned | 3 | 3 |
| Unique AI-attributed commits | 1 | 1 |
| AI actor presences | 2 | 2 |
| Claude commits / presences | 1 / 1 | 1 / 1 |
| OpenAI commits / presences | 1 / 1 | 1 / 1 |
| Human-declared commits | 1 | 1 |
| Unknown commits | 1 | 1 |
| Evidence declared / unknown / total | 3 / 1 / 4 | 3 / 1 / 4 |

The shared commit remained one unique AI commit and two actor presences.
Browser assertions for All AI, Claude, and OpenAI preserved those units and
the selected state.

### Profile publisher

The role generated a disposable Profile repository with exactly eight assets,
parsed all six SVGs, loaded the self-contained dashboard in Chrome, and copied
the responsive clickable card plus light/dark heatmap from the README. The
Pages instructions identified `main`, `/ (root)`, the case-sensitive
dashboard URL, and deployment-delay recovery. No remote mutation occurred.

## Root reconciliation

The root reviewer recomputed the candidate digest, inventories, public JSON
totals, and privacy sweep from raw artifacts:

```text
wheel digest = ff7ad454...7a99
output inventories = 8 / 8 / 8 / 8
new user = scanned 1, AI 0, presences 0, unknown 1
privacy = scanned 2, AI 2, presences 2, excluded omitted
multi-provider = scanned 3, AI 1, presences 2, human 1, unknown 1
publisher = scanned 1, AI 1, presences 1, unknown 0
privacy = 72 tokens * 9 outputs, hits 0
date matches = aggregate-only 0, full 8, excluded 0
```

## Findings and dispositions

### Medium — Dogfood harnesses touched state outside their intended scope

- **Impact:** Two role runs could not claim a pristine, never-touched
  evaluation workspace even though the candidate behavior was unaffected.
- **Evidence:** One PowerShell `$home` collision initialized two new files in
  the user home. Another setup loop harmlessly reinitialized the existing
  workspace Git directory three times with its alternate initial-branch
  request ignored, then briefly set workspace-local Git `user.name` and
  `user.email`; its `git add`, commit, and remote changes failed.
- **Recommendation:** Treat these as harness incidents, preserve the raw
  evidence, remediate exact paths only, and independently verify final
  workspace state before accepting product results.
- **Disposition:** Fixed. The two new home files were moved into the isolated
  evidence directory. The workspace index, tracked files, branch, commit,
  remotes, and local identity keys were independently verified clean. Every
  role subsequently completed a clean candidate run.

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

The exact v0.4.4 candidate passes the promotion dogfood gate: 4/4 roles, one
digest, zero external hints, zero privacy leaks, exact aggregation semantics,
exact output sets, and no installation, configuration, dashboard, or Profile
or Pages-preparation blocker.

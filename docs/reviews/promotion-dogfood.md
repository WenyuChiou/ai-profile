# v0.4.2 Public Beta promotion dogfood

Date: 2026-07-26
Frozen evaluation baseline:
`02068ba5cf7a1ce6a194b18f70f6245603081916`

## Executive result

The frozen dogfood gate passed. All four roles completed from a role-local
copy of the same final `README.md` and the same candidate wheel, without
external hints, source access, or tracked-file edits.

Final candidate:

```text
ai_profile_cli-0.4.2-py3-none-any.whl
SHA-256 51F9646F64E32889FF6909360928265E841A5C28CC228062FD9C0469CF872149
```

| Role | Result | External hints | Blocking friction |
|---|---|---:|---:|
| New user | PASS | 0 | 0 |
| Privacy-sensitive user | PASS | 0 | 0 |
| Multiple-provider user | PASS | 0 | 0 |
| Profile publisher | PASS | 0 | 0 |

Frozen gate totals:

- Completed roles: 4/4
- Exact candidate-hash matches: 4/4
- Installation failures: 0
- Configuration dead ends: 0
- Privacy-canary hits: 0
- Hand-derived metric mismatches: 0
- GitHub Pages dead ends: 0

## Candidate and isolation

The candidate passed `python -m build`, Twine validation, the wheel/sdist
artifact contract, and the clean-wheel release smoke before distribution.
Each role then calculated the full wheel digest as its first product check and
matched the value above.

Every role used a separate virtual environment, disposable Git repository,
and `AIPROFILE_HOME`. Retained evidence lives under
`.artifact/promotion/dogfood/<role>-release/`; the privacy role created its
runtime objects under a unique system-temp root and deleted that root after
evidence capture. Roles were prohibited from reading project source, tests,
other documentation, Git history, or another role's artifacts. The final
no-product-tool synthesizer read only the four natural-language reports.

## Role evidence

### New user

The role completed offline install, version check, `init`, `scan`,
`aggregate`, and `render`. One ordinary trailer-free commit produced one
stored record, one scanned commit, one `unknown` commit, and zero
AI-attributed commits. The role correctly understood that this was an honest
absence of explicit evidence, not a scan failure or human attribution.

The rendered directory contained exactly:

```text
badge-dark.svg
badge-light.svg
dashboard.html
heatmap-dark.svg
heatmap-light.svg
profile.json
summary-dark.svg
summary-light.svg
```

Evidence:
`.artifact/promotion/dogfood/new-user-release/report.md` and
`evidence/00-wheel-sha256.log` through
`evidence/17-unknown-honesty-validation.log`.

### Privacy-sensitive user

The role deliberately reproduced the documented Windows PowerShell 5.1
encoding hazard:

- BOM prefix `EF-BB-BF-7B`: `aggregate` exited 1 with the expected strict JSON
  error.
- UTF-8-without-BOM prefix `7B-0D-0A-20`: `aggregate` exited 0 and remained
  usable through later policy edits.

Publication modes matched the README:

- `aggregate_only` retained totals and withheld repository activity dates.
- `full` retained totals and exposed the two fixture activity dates.
- `excluded` contributed no totals, providers, daily rows, or evidence.
- All public assets retained the UTC generation date, as documented.

Each mode produced the exact eight-file bundle. The role seeded 15 distinct
private canaries covering repository and organization names, paths, prompts,
commit messages, email addresses, URL components, author identity, and the
fixture's actual full and seven-character commit SHAs. Fifteen canaries
across eight files and three modes produced 360 exact raw-byte comparisons
and zero hits.

Evidence:
`.artifact/promotion/dogfood/privacy-release/report.md`,
`evidence-release/commands.jsonl`,
`evidence-release/raw-byte-sweep.csv`, and
`evidence-release/output-manifest.json`.

### Multiple-provider user

The fixture contained four commits:

1. One contiguous two-actor trailer block for Anthropic and OpenAI.
2. One commit without provenance.
3. One OpenAI-only commit.
4. One `Human-Only` commit.

Hand-derived and generated values agreed:

| Metric | Expected | Observed |
|---|---:|---:|
| Commits scanned | 4 | 4 |
| Unique AI-attributed commits | 2 | 2 |
| AI actor presences | 3 | 3 |
| OpenAI attributed commits | 2 | 2 |
| Anthropic attributed commits | 1 | 1 |
| Active AI days | 2 | 2 |
| Human-declared commits | 1 | 1 |
| Unknown commits | 1 | 1 |
| Evidence total / declared / unknown | 5 / 4 / 1 | 5 / 4 / 1 |

The shared-provider day contained `ai_commits: 1` and two provider rows. This
directly verifies that one commit with multiple actor presences remains one
unique AI commit.

Real headless Chromium exercised All AI, OpenAI, and Anthropic filters.
Provider-specific values changed correctly, `unknown` stayed separate from
human and global across filters. All 71 role assertions passed, and a
separate 46-check visual matrix verified widths 320/390/768/1440, 200%
equivalent scaling, light/dark/system themes, keyboard focus, reduced motion,
normal-text and meaningful-mark contrast, and no horizontal overflow.

Evidence:
`.artifact/promotion/dogfood/multi-provider-release/report.md`,
`evidence/profile.json`, `evidence/validation-results.json`,
`evidence/browser-results.json`, `visual-acceptance.json`, and the three
filter screenshots.

### Profile publisher

The role created a disposable `USERNAME/USERNAME`-style repository on `main`
with no remote and no push. It generated the exact eight-file bundle and
validated:

- a clickable summary card linked to the dashboard;
- light and dark summary and heatmap images;
- a standalone dashboard link;
- the `https://USERNAME.github.io/USERNAME/dist/dashboard.html` URL;
- GitHub Pages `main` and `/ (root)` setup;
- temporary-404 recovery instructions.

All local references resolved. The maintainer dashboard and four live Profile
assets returned HTTP 200. Live and settled local screenshots rendered
successfully. There was no Pages dead end and no remote mutation.

Evidence:
`.artifact/promotion/dogfood/publisher-release/report.md`,
`evidence/15-publisher-validation.log`,
`evidence/18-live-dashboard-request.log`,
`evidence/19-live-assets.log`, and screenshots 21 and 23.

## Synthesis and independent reconciliation

The no-product-tool synthesizer read only the four release reports. It confirmed
that all four state the same full wheel SHA-256, found no result
contradiction, identified role-specific coverage, and issued no promotion
verdict. Its matrix is
`.artifact/promotion/dogfood/release-synthesis.md`.

The root reviewer then ignored the synthesis result and independently read
the role-local wheels, canonical JSON/CSV, output directories, and final
publisher validation:

```text
PASS root recomputation
candidate hashes: 4/4 exact matches
commits=4 ai=2 presences=3 openai=2 anthropic=1 days=2
human=1 unknown=1 evidence=5 declared=4 unknown_evidence=1
multi_actor_day_ai=1 provider_rows=2
privacy_canaries=15 privacy_comparisons=360 privacy_hits=0
new_user_files=8 publisher_files=8 publisher_validation=true
```

## Findings and dispositions

### High — Initial dogfood evidence mixed candidate builds

- **Impact:** The first 4/4 result could not establish that all roles tested
  the same final product bytes.
- **Evidence:** Pre-commit review found three roles on one wheel and the
  privacy rerun on another.
- **Recommendation:** Invalidate the mixed evidence, build one candidate, and
  rerun all four roles from fresh packets with a full digest gate.
- **Disposition:** Fixed. Later renderer and release remediations invalidated
  the second candidate as well. This report uses only the four
  `*-release` runs on SHA-256 `51F9646F...CF872149`.

### Medium — PowerShell 5.1 can add an incompatible UTF-8 BOM

- **Impact:** A common manual config-editing command can make `config.json`
  temporarily unreadable.
- **Evidence:** Both the discovery run and final privacy run reproduced the
  negative control; the no-BOM path completed every publication mode.
- **Recommendation:** Retain explicit UTF-8-without-BOM guidance in both
  READMEs. Consider a configuration CLI only as separately scoped v0.5.0
  work if real-user evidence shows README-only editing is still unreliable.
- **Disposition:** README fixed and exact candidate rerun; no remaining dead
  end.

### Low — Legacy Windows console display friction

- **Impact:** PowerShell 5.1 can display smart punctuation as mojibake even
  though files, commands, package metadata, and GitHub rendering are valid
  UTF-8.
- **Evidence:** Role reports disclosed the display issue; GitHub Markdown
  rendering was separately validated.
- **Recommendation:** Keep UTF-8 source and canonical GitHub rendering; do
  not add a BOM solely for legacy console display.
- **Disposition:** Accepted as a shell display limitation.

### Low — Isolated homes trigger the worktree privacy warning

- **Impact:** Dogfood `init` stderr contains a warning.
- **Evidence:** The evaluation contract required all temporary state under
  the repository-local artifact directory, which is inside a Git worktree.
- **Recommendation:** Retain the warning; it is correct privacy guidance.
- **Disposition:** Accepted as containment-harness friction.

## Dogfood verdict

The frozen dogfood gate passes: 4/4 roles, one exact candidate digest, zero
external hints, zero privacy leaks, exact aggregation semantics, exact output
sets, and no configuration or Pages dead end. No unresolved Critical or High
finding remains.

# v0.4.2 Public Beta promotion dogfood

Date: 2026-07-26
Frozen evaluation baseline:
`02068ba5cf7a1ce6a194b18f70f6245603081916`

## Executive result

The frozen sealed-box dogfood gate passed. All four roles used a role-local
copy of the same `README.md` and the same canonical Linux-built wheel. They
had no source, test, history, other-role artifact, or orchestrator hint access.

```text
ai_profile_cli-0.4.2-py3-none-any.whl
SHA-256 8B6E28BB2172A63AC4CD37E14023ECEE079E4CEB6E8148ACB3B3D0438BFF332E
```

| Role | Result | External hints | Blocking friction |
|---|---|---:|---:|
| New user | PASS | 0 | 0 |
| Privacy-sensitive user | PASS | 0 | 0 |
| Multiple-provider user | PASS | 0 | 0 |
| Profile publisher | PASS | 0 | 0 |

Gate totals:

- completed roles: 4/4;
- exact candidate-hash matches: 4/4;
- installation failures: 0;
- configuration dead ends: 0;
- privacy-canary hits: 0;
- hand-derived metric mismatches: 0;
- GitHub Pages dead ends: 0.

## Candidate and isolation

The wheel was built from clean Linux checkouts with
`SOURCE_DATE_EPOCH=1785024000`. A direct source-file copy and a separate
Linux-side `git diff | git apply` checkout both produced the digest above,
and the wheels compared byte-for-byte equal. The wheel passed Twine,
clean-wheel onboarding, notice inspection, CSP, privacy, and determinism
checks before role distribution.

Each role used its own virtual environment, disposable Git repository, and
`AIPROFILE_HOME` under
`.artifact/promotion/dogfood-linux-candidate-v2/<role>/`. No role configured
or mutated a real remote. The root reviewer separately confirmed that the
real home contained no stray `config.json`, `aiprofile.db`, or default
`.aiprofile` private state.

## Role evidence

### New user

The role installed the exact wheel offline, verified version `0.4.2`, and
completed `init`, `scan`, `aggregate`, and `render`. One ordinary
trailer-free commit became exactly one `unknown` commit, zero AI-attributed
commits, zero actor presences, zero human declarations, and evidence
`1 / 0 / 1` total/declared/unknown. The output directory contained exactly
the eight documented files.

Evidence:
`.artifact/promotion/dogfood-linux-candidate-v2/new-user/report.md` and
`evidence.md`.

### Privacy-sensitive user

The role exercised `aggregate_only`, `full`, and `excluded`:

- `aggregate_only` retained totals and withheld daily repository activity;
- `full` retained totals and published the fixture day;
- `excluded` contributed no totals, provider rows, daily rows, or evidence.

Each mode produced exactly eight files. Twenty-nine private canaries covered
the actual full and short commit SHA, repository and organization names,
Windows/POSIX/file-URL paths, prompt, subject/body, identities, emails, URLs,
branch, source content, trailers, model/tool/role values, salt, and repository
UID. The raw-byte sweep performed exactly
`29 canaries × 8 files × 3 modes = 696` comparisons and found zero hits.

An actual UTF-8 BOM caused the documented controlled parse failure. Restoring
the exact pre-BOM bytes recovered successfully. Containment guards passed,
the real default private home was unchanged, and the disposable runtime
state was cleaned after evidence capture.

Evidence:
`.artifact/promotion/dogfood-linux-candidate-v2/privacy/report.md`,
`evidence/run-result.json`, `evidence/commands.json`, and
`evidence/canaries.json`.

### Multiple-provider user

The fixture contained one contiguous OpenAI-plus-Anthropic trailer commit,
one unknown commit, one OpenAI-only commit, and one `Human-Only` commit.
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

The shared-provider day remained one AI commit with two provider rows. Chrome
and Playwright then passed 822/822 checks over 36 standard states and nine
200%-equivalent states: widths 320/390/768/1440, light/dark/system,
All AI/OpenAI/Claude filters, count semantics, persistent non-color selected
state, normal text color, keyboard/focus, reduced motion, contrast, and no
horizontal overflow. Minimum measured normal-text contrast was 5.3338:1;
page and console errors were zero.

Evidence:
`.artifact/promotion/dogfood-linux-candidate-v2/multi-provider/report.md`,
`evidence-definitive/fixture-verification.json`,
`evidence-definitive/browser/results.json`, and
`evidence-definitive/supplemental-checks.json`.

### Profile publisher

The role created a disposable `USERNAME/USERNAME` repository on `main` with
zero remotes. It generated exactly eight outputs and validated the clickable
summary card, light/dark summary and heatmap assets, dashboard URL, Pages
`main` plus `/ (root)` configuration, and temporary-404 recovery. Strict
UTF-8/XML/JSON, CSP, self-containment, privacy needles, and local references
all passed. Mutation-free requests returned HTTP 200 for the current
maintainer dashboard and seven companion public assets. Browser presentation
claims are supplied by the independent multiple-provider role, not this
structural publisher role.

Evidence:
`.artifact/promotion/dogfood-linux-candidate-v2/publisher/report.md`,
`evidence/raw-command-log.txt`, `evidence/validation.txt`, and
`evidence/http-head.txt`.

## Synthesis and independent reconciliation

The no-product-tool synthesizer read only the four natural-language v2
reports. It compared their digest, outcomes, coverage, and disclosed
limitations without issuing a promotion verdict. Its matrix is
`.artifact/promotion/dogfood-linux-candidate-v2/synthesis.md`.

The root reviewer then ignored the synthesis conclusion and recomputed the
claims from role-local wheels, canonical JSON, raw sweep records, output
directories, Git remotes, and browser results:

```text
PASS root recomputation
candidate hashes: 4/4 exact matches
new-user: commits=1 ai=0 presences=0 human=0 unknown=1 evidence=1/0/1
multi-provider: commits=4 ai=2 presences=3 openai=2 anthropic=1 days=2
human=1 unknown=1 evidence=5/4/1 shared-day-ai=1 provider-rows=2
privacy: canaries=29 comparisons=696 hits=0 modes=3 files-per-mode=8
publisher: files=8 remotes=0 public-http=8/8
browser: checks=822 failures=0 standard-states=36 scale-200-states=9
```

## Findings and dispositions

### High — Earlier dogfood evidence mixed or superseded candidate bytes

- **Impact:** Earlier 4/4 claims did not authorize the byte sequence intended
  for publication.
- **Evidence:** Review found mixed candidate digests, followed by later
  renderer and release-contract changes.
- **Recommendation:** Invalidate all prior role sets and rerun every role with
  a first-action full SHA-256 gate.
- **Disposition:** Fixed. Only the four v2 roles on
  `8B6E28BB...BFF332E` are counted here.

### High — The first PR candidate was not reproducible on Ubuntu

- **Impact:** CI could not promote the dogfooded Windows-built wheel.
- **Evidence:** GitHub Actions run `30197407962` built a different digest.
  ZIP platform metadata and timestamps differed.
- **Recommendation:** Use one canonical Ubuntu builder with a
  manifest-frozen `SOURCE_DATE_EPOCH`, then smoke the retained universal wheel
  on all operating systems.
- **Disposition:** Fixed locally. Three clean-Linux build paths reproduced the
  current digest; external corrected CI remains a release-readiness gate.

### Medium — Provider filters overflowed at 320 px

- **Impact:** Claude was clipped behind a visible horizontal scrollbar in all
  nine 320 px theme/provider states.
- **Evidence:** The first independent browser matrix reproduced
  `clientWidth=278` and `scrollWidth=288`.
- **Recommendation:** Wrap provider controls into an equal-width mobile grid
  and add a static responsive regression.
- **Disposition:** Fixed. The final 822-check matrix reports zero overflow at
  320 px and no regression at wider sizes or 200% scaling.

### Medium — PowerShell 5.1 can add an incompatible UTF-8 BOM

- **Impact:** An encoding-unspecified manual edit can temporarily make
  `config.json` unreadable.
- **Evidence:** The privacy role reproduced the controlled BOM failure and
  exact-byte recovery.
- **Recommendation:** Retain UTF-8-without-BOM guidance. Add a config CLI only
  as separately scoped v0.5.0 work if real users still encounter a dead end.
- **Disposition:** Accepted for v0.4.2: the README path completed and recovery
  was explicit; no configuration dead end remained.

### Low — Contained homes trigger a conservative worktree warning

- **Impact:** Test users see a warning in deliberately repository-contained
  evaluation layouts.
- **Evidence:** Valid roles disclosed the warning while their private paths
  remained correctly isolated and unpublished.
- **Recommendation:** Keep the safety warning for v0.4.2 and assess trigger
  precision separately.
- **Disposition:** Accepted as non-blocking, privacy-conservative friction.

## Dogfood verdict

The frozen dogfood gate passes: 4/4 roles, one exact candidate digest, zero
external hints, zero privacy leaks, exact aggregation semantics, exact output
sets, and no configuration or Pages dead end. No unresolved Critical or High
dogfood finding remains.

# v0.4.2 Public Beta promotion readiness review

Date: 2026-07-26
Frozen evaluation baseline:
`02068ba5cf7a1ce6a194b18f70f6245603081916`
Candidate wheel:
`ai_profile_cli-0.4.2-py3-none-any.whl`
Candidate wheel SHA-256:
`8b6e28bb2172a63ac4cd37e14023ecee079e4ceb6e8148acb3b3d0438bff332e`

## Reviewer posture

This is an evidence-based release gate, not a design approval. Product scope
remains frozen: no ACE schema, aggregation, attribution, or CLI contract
change is included. A gate is complete only when supported by a retained
artifact, command output, independent review, or verified external state.

## Executive summary

The v0.4.1 wheel-notice defect is fixed and regression-tested. The current
v0.4.2 wheel contains `LICENSE` and `THIRD_PARTY_NOTICES.md`, reports one
version across package/runtime metadata, passes Twine and exact-wheel smoke,
renders deterministically, retains the privacy boundary, and preserves
aggregation semantics.

Independent browser verification found a real 320 px overflow after the first
dogfood pass. The provider controls now wrap into an equal-width mobile grid;
the final Chrome matrix passed 822/822 checks. Because that source change
altered the wheel, all four sealed-box roles were invalidated and rerun on the
new digest. The final role set passed 4/4, with 696 privacy comparisons and
zero hits.

The first GitHub Actions candidate job also proved that a Windows-built wheel
was not byte-reproducible on Ubuntu. The corrected contract freezes
`SOURCE_DATE_EPOCH`, uses Ubuntu as the only canonical builder, and fans those
retained bytes to Windows and macOS. Three clean-Linux build paths now produce
the same candidate wheel, including a Linux-side patch path that excludes
Windows checkout-line-ending effects.

Promotion is still blocked. Corrected GitHub-hosted three-platform execution,
the final release-commit wheel/sdist pair, PyPI/GitHub Release digest parity,
real Profile refresh, Pages, homepage, and branch protection remain external
gates. The current verdict therefore remains `NO-GO`.

## Verification evidence

### Local quality gates

```text
python -m pytest tests -p no:cacheprovider
544 passed, 4 skipped

python -m ruff check src tests scripts
All checks passed!

python scripts/check_readme_parity.py
PASS: README English/Traditional Chinese structure and contract parity

python tests/unit/test_render_summary.py
python tests/unit/test_heatmap_svg.py
git diff --exit-code -- tests/snapshots docs/assets
PASS: sanctioned regeneration completed with zero snapshot/sample drift

PyYAML parse: .github/workflows/ci.yml
PyYAML parse: .github/workflows/publish.yml
PASS
```

### Candidate artifact gates

```text
clean Linux build A wheel SHA-256
8b6e28bb2172a63ac4cd37e14023ecee079e4ceb6e8148acb3b3d0438bff332e

clean Linux build B wheel SHA-256
8b6e28bb2172a63ac4cd37e14023ecee079e4ceb6e8148acb3b3d0438bff332e

clean Linux clone + Linux-side git apply wheel SHA-256
8b6e28bb2172a63ac4cd37e14023ecee079e4ceb6e8148acb3b3d0438bff332e

cmp build-A.whl build-B.whl
BYTE_IDENTICAL

cmp build-A.whl linux-git-apply.whl
PASS_CRLF_INDEPENDENT

clean Linux Python 3.12 wheel SHA-256
8b6e28bb2172a63ac4cd37e14023ecee079e4ceb6e8148acb3b3d0438bff332e

cmp python-3.11.whl python-3.12.whl
PASS_PYTHON_312_IDENTICAL

python -m twine check <candidate-wheel>
PASSED

python scripts/release_smoke.py --wheel <candidate-wheel>
  --expected-version 0.4.2
RESULT: PASS - all steps green

wheel notice inspection
PASS: LICENSE
PASS: THIRD_PARTY_NOTICES.md
PASS: 34 unique archive members
```

The final sdist digest is intentionally not recorded yet: documentation and
review evidence still change the sdist. The tag workflow must build the final
wheel/sdist pair from the release commit, verify the frozen wheel digest, and
record both exact filenames and digests before either upload.

### Sealed-box dogfood

The release-authorizing role set is complete for the candidate digest above:

- 4/4 roles completed with zero external hints;
- root recomputation matched every metric;
- 29 canaries × 8 files × 3 modes = 696 comparisons, zero hits;
- browser/accessibility passed 822/822 checks over 36 standard and nine
  200%-equivalent states;
- current maintainer public family returned 8/8 HTTP 200;
- no role configured or mutated a real remote.

The full record is
`docs/reviews/promotion-dogfood.md`. Public-link evidence remains in
`docs/reviews/promotion-public-link-evidence.json`.

### Pending external gates

- corrected PR candidate build and Python 3.11–3.14 suite;
- Ubuntu/Windows/macOS Python 3.12 onboarding of the same wheel;
- final release-commit wheel/sdist, Twine, notice, version, tag, and digest
  parity;
- PyPI and GitHub Release exact-byte verification and clean live install;
- real Profile regeneration, privacy sweep, CI, and Pages verification;
- repository homepage and `main` branch protection.

## Findings and dispositions

### High — Release gates and publication consumed different builds

- **Impact:** Dogfood or OS evidence could apply to bytes that were never
  uploaded.
- **Evidence:** Independent architecture, security, requirements, and bug
  reviewers traced separate build paths.
- **Recommendation:** Build once, retain one pair, fan it out, and upload only
  the verified pair.
- **Disposition:** Fixed in workflow code; corrected CI and tag execution
  remain required before closure.

### High — Build code shared repository-write release authority

- **Impact:** Executed project or dependency code could influence a later
  repository-write operation.
- **Evidence:** Security review reproduced job-level permission sharing.
- **Recommendation:** Separate read-only build, PyPI OIDC, and GitHub Release
  jobs with digest-verified handoff.
- **Disposition:** Fixed in workflow code.

### High — Earlier dogfood mixed or cited superseded candidate evidence

- **Impact:** A nominal 4/4 result did not identify one releasable product.
- **Evidence:** Review found different wheel digests and stale publisher
  citations in earlier role sets.
- **Recommendation:** Invalidate every superseded set, enforce a first-action
  SHA-256 gate, and retain resolvable v2 citations.
- **Disposition:** Fixed. Only the four roles on
  `8B6E28BB...BFF332E` are counted.

### High — Publisher evidence and public-link claims were not reproducible

- **Impact:** The report could not independently support its live-publication
  claims.
- **Evidence:** Completion-integrity review found stale log numbers and no
  retained 26-link matrix.
- **Recommendation:** Retain link-level evidence and bind it statically to
  both READMEs.
- **Disposition:** Fixed in
  `promotion-public-link-evidence.json` and the current v2 publisher evidence.

### High — Candidate wheel was not byte-reproducible on Ubuntu

- **Impact:** GitHub Actions rejected the dogfooded Windows wheel, blocking
  exact-byte promotion.
- **Evidence:** Run `30197407962` produced a different Ubuntu digest. ZIP
  platform metadata and timestamps were not canonical.
- **Recommendation:** Freeze `SOURCE_DATE_EPOCH`, build only on Ubuntu, and
  smoke the retained universal wheel on all target operating systems.
- **Disposition:** Fixed locally and covered by workflow regressions. External
  corrected CI is still pending, so one High gate remains open.

### Medium — Required commit-SHA privacy canaries were absent

- **Impact:** The prior sweep did not prove that full or short commit IDs were
  excluded.
- **Evidence:** Requirements review compared the canary catalog with the
  frozen evaluation specification.
- **Recommendation:** Include actual fixture SHAs in every mode/output sweep.
- **Disposition:** Fixed. The final 29-canary, 696-comparison sweep had zero
  hits.

### Medium — Provider selection lacked a persistent non-color row cue

- **Impact:** Selected and unselected provider rows could look identical after
  focus moved.
- **Evidence:** Bug review traced `aria-current` to a missing selected-state
  visual.
- **Recommendation:** Keep provider text at normal text color and use a
  persistent accent border/mark.
- **Disposition:** Fixed and verified across the browser matrix.

### Medium — Provider filters overflowed at 320 px

- **Impact:** The Claude control was clipped behind a visible horizontal
  scrollbar in nine mobile states.
- **Evidence:** Independent Chrome reproduction measured
  `clientWidth=278`, `scrollWidth=288`.
- **Recommendation:** Use a wrapping equal-width mobile grid and pin the
  responsive contract.
- **Disposition:** Fixed with a regression test; final browser result is
  822/822 with zero 320 px overflow.

### Medium — Release smoke could fail at UTC midnight

- **Impact:** Correct renders spanning a date boundary could appear
  nondeterministic.
- **Evidence:** Bug review traced independent `generated_on` values.
- **Recommendation:** Detect the boundary and retry a bounded same-date pair.
- **Disposition:** Fixed with a simulated rollover regression.

### Medium — Artifact validation admitted weak failure paths

- **Impact:** An unrelated notice, extra file, missing metadata, or invalid
  checksum could bypass or obscure the release contract.
- **Evidence:** Security and code-quality reviewers supplied concrete archive
  counterexamples.
- **Recommendation:** Bind notices to the distribution metadata, require the
  canonical two-file set, validate metadata and checksums, and fail clearly.
- **Disposition:** Fixed with additive regressions.

### Medium — Bilingual parity enforcement was structural but not semantic

- **Impact:** CTA, feature, privacy, or setup promises could drift while
  headings still matched.
- **Evidence:** Requirements and code-quality reviewers supplied passing
  counterexamples.
- **Recommendation:** Enforce ordered headings, command blocks, CTA targets,
  link multiplicity, and paired claims.
- **Disposition:** Fixed with positive and negative parity tests.

### Medium — Checksum manifests depended on the local directory name

- **Impact:** Correct downloaded bytes could fail verification outside a
  directory literally named `dist`.
- **Evidence:** Pre-commit review reproduced the relocation failure.
- **Recommendation:** Canonicalize entries as `dist/<filename>` independent of
  the local verification directory.
- **Disposition:** Fixed and regression-tested.

### Medium — PyPI recovery could skip files without proving identity

- **Impact:** A retry could accept immutable filenames without proving that
  their bytes matched the retained release pair.
- **Evidence:** Release review traced `skip-existing` without post-upload
  digest verification.
- **Recommendation:** Query the version-specific PyPI API, require the exact
  filename set, compare both digests, and gate GitHub Release.
- **Disposition:** Fixed in workflow code; live tag execution remains pending.

### Medium — GitHub Release recovery admitted extra assets

- **Impact:** Correct wheel, sdist, and checksum files could coexist with an
  unrelated stale or manually added public asset.
- **Evidence:** Final release review traced the recovery path through
  `gh release upload --clobber` without an exact asset-set check.
- **Recommendation:** Require exactly the three authorized asset names,
  re-download them, and verify package bytes against `SHA256SUMS`.
- **Disposition:** Fixed with post-upload name-set verification, a byte
  comparison between public and retained manifests, package verification
  against the retained manifest, and static workflow regressions.

### Low — README unknown-attribution wording was ambiguous

- **Impact:** Users could read the copy as reversing the product's honest
  `unknown` behavior.
- **Evidence:** Code-quality review compared English and Traditional Chinese
  wording with runtime behavior.
- **Recommendation:** State directly that commits without explicit evidence
  stay unknown.
- **Disposition:** Fixed in both READMEs.

### Low — Release diagnostics and documentation lagged automation

- **Impact:** Failure messages and operator steps could point at the wrong
  artifact or workflow.
- **Evidence:** Code-quality review found stale smoke and determinism wording.
- **Recommendation:** Name only changed artifacts and document the exact
  candidate path.
- **Disposition:** Fixed and regression-tested.

### Low — Fresh disposable Pages deployment was not performed

- **Impact:** The sealed-box publisher validated instructions and current live
  routes, not a newly mutated public repository.
- **Evidence:** The role correctly recorded zero remotes and zero pushes.
- **Recommendation:** Preserve the sealed-box no-mutation boundary and require
  the planned real maintainer Profile deployment after PyPI publication.
- **Disposition:** Accepted pre-release with maintainer ownership. Promotion
  remains blocked until the real Profile and Pages gate completes.

## Verified areas without findings

- No ACE schema, event identity, vocabulary, normalization, or version
  contract changed.
- Unique commits, actor presences, provider commits, active days, evidence,
  unknown, and human remain separate.
- Renderers still consume validated `VizStats`; they do not scan Git, access
  SQLite, infer attribution, or recalculate aggregation.
- Dashboard output remains self-contained and CSP-bound.
- Runtime remains dependency-free and Beta-classified.
- v0.4.1 remains immutable; the corrective disclosure is in the changelog.

## Severity summary

| Severity | Total | Fixed | Accepted | Pending |
|---|---:|---:|---:|---:|
| Critical | 0 | 0 | 0 | 0 |
| High | 5 | 4 | 0 | 1 |
| Medium | 9 | 9 | 0 | 0 |
| Low | 3 | 2 | 1 | 0 |

## Final verdict

NO-GO

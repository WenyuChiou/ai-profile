# v0.4.2 Public Beta promotion readiness review

Date: 2026-07-26
Frozen evaluation baseline:
`02068ba5cf7a1ce6a194b18f70f6245603081916`
Candidate wheel:
`ai_profile_cli-0.4.2-py3-none-any.whl`
Candidate wheel SHA-256:
`51f9646f64e32889ff6909360928265e841a5c28cc228062fd9c0469cf872149`

## Reviewer posture

This is an evidence-based release gate, not a design approval. Product scope
remains frozen: no ACE schema, aggregation, attribution, or CLI change is
included. A gate is marked complete only from a command result, retained
artifact, independent review, or live external-state verification.

This report is intentionally updated as the release moves through its
irreversible stages. The current verdict remains blocking until
GitHub-hosted cross-platform checks and the post-publication gates complete.

## Executive summary

The v0.4.1 wheel-notice defect is fixed and regression-tested. The v0.4.2
candidate contains both required notices in its wheel and sdist, reports one
version across project/runtime/artifact metadata, passes Twine, installs from
the exact wheel, renders deterministically, retains the privacy boundary, and
preserves aggregation semantics.

The initial release workflow did not promote one immutable artifact through
all operating systems and exposed repository-write permission to build code.
Independent review rejected that design. The workflow now builds once,
records an exact two-file manifest, fans the same bundle to Ubuntu, Windows,
and macOS, and separates read-only build, PyPI OIDC, and GitHub Release
authority. The dogfooded wheel digest is a checked release input.

The exact wheel completed all four sealed-box roles without external hints,
privacy leaks, metric mismatches, or onboarding dead ends. Promotion is not
yet authorized in this revision because CI must execute the shared artifact
on all three operating systems, and post-publication/Profile/governance gates
cannot precede their external mutations.

## Verification evidence

### Local quality and artifact gates

```text
python -m pytest tests -p no:cacheprovider
540 passed, 4 skipped

python -m ruff check src tests scripts
All checks passed!

python scripts/check_readme_parity.py
PASS: README English/Traditional Chinese structure and contract parity

python tests/unit/test_render_summary.py
python tests/unit/test_heatmap_svg.py
git diff --exit-code -- tests/snapshots docs/assets
PASS: sanctioned regeneration completed with zero snapshot/sample drift

python -m build --outdir .artifact/promotion/candidate-v042-final8
python -m twine check .artifact/promotion/candidate-v042-final8/*
python scripts/check_release_artifacts.py ...
PASS: wheel and sdist; LICENSE and THIRD_PARTY_NOTICES.md present

python scripts/release_smoke.py --wheel <candidate> --expected-version 0.4.2
RESULT: PASS - all steps green
```

Candidate bundle at the pre-review-report checkpoint:

```text
wheel  51f9646f64e32889ff6909360928265e841a5c28cc228062fd9c0469cf872149
sdist  2dfaa1ca07c0a33ce68496db5d2ef15f2132b30c9c67e715ef55fb78ec7f7264
```

The sdist digest is informational and predates this report's final text; the
publish workflow records and promotes the exact pair built from the frozen
release commit. The wheel digest is frozen because it authorizes dogfood and
is enforced by CI and the
tag workflow through `docs/reviews/promotion-candidate.json`.

### Independent review

The hard-complexity comprehensive review used two static reviewers for each
of architecture, security, performance, code quality, requirements, and bug
correctness. Reviewers did not run tests and independently converged on the
release-artifact identity and permission-isolation defects. A separate
pre-commit reviewer also rejected the earlier mixed-wheel dogfood evidence.

The four-role evidence is complete for wheel SHA-256
`51f9646f...872149`: 4/4 roles completed with zero external hints, the root
recomputation matched every metric, 360 privacy comparisons had zero hits,
the browser/accessibility matrix passed 46/46 checks, and 26/26 public links
returned HTTP 200. The public-link matrix and GitHub Markdown render counts
are retained in
`docs/reviews/promotion-public-link-evidence.json` and statically checked
against both current READMEs.

The final completion-integrity review independently re-derived the wheel
identity, dogfood metrics, privacy matrix, visual matrix, retained citations,
checksum portability, and release-recovery ordering. It found no unresolved
Critical or High issue.

The following evidence remains pending before the verdict can change:

- GitHub Actions Ubuntu/Windows/macOS results for the shared bundle;
- PyPI/GitHub Release digest parity and clean live install;
- real Profile refresh, CI/Pages verification, homepage, and branch
  protection.

## Findings and dispositions

### High — Release gates and publication consumed different builds

- **Impact:** Dogfood and operating-system evidence could apply to bytes that
  were never uploaded.
- **Evidence:** Both architecture reviewers, both security reviewers,
  performance reviewers, requirements reviewers, and bug reviewers
  independently identified separate builds in the original CI and publish
  workflows.
- **Recommendation:** Build one bundle, retain it, fan it out, and upload only
  that bundle. Bind the wheel to the frozen dogfood digest.
- **Disposition:** Fixed in code. CI and tag-workflow execution remain
  required before closure.

### High — Build code shared repository-write release authority

- **Impact:** Executed project or dependency code could influence a later
  `gh` invocation holding a contents-write token.
- **Evidence:** Both security reviewers and architecture reviewers reproduced
  the job-level permission scope.
- **Recommendation:** Use fresh jobs with least privilege and digest-verified
  artifact handoff.
- **Disposition:** Fixed in code. Build uses contents-read; PyPI and GitHub
  publication use separate runners and distinct permissions.

### High — Initial dogfood mixed candidate wheel bytes

- **Impact:** A 4/4 result did not authorize one identifiable release wheel.
- **Evidence:** Mandatory pre-commit review found different digests across the
  first role packets.
- **Recommendation:** Invalidate those results and rerun all roles with a
  first-command full-digest gate.
- **Disposition:** Earlier evidence is invalidated. A second exact-byte run
  closed the immediate finding, then renderer/release remediation changed the
  wheel. The release-authorizing rerun completed all four roles on
  `51f9646f...872149`; every role calculated and matched the digest before
  product use.

### High — Final dogfood report cited superseded publisher evidence

- **Impact:** The checked-in promotion conclusion was not reproducible from
  the paths it named, despite the final evidence existing locally.
- **Evidence:** Completion-integrity and onboarding reviewers independently
  resolved every citation and found that the publisher section still used
  old log numbers. They also found that the 26-link result lacked a retained
  matrix.
- **Recommendation:** Point only to the release-authorizing 15/18/19 logs and
  screenshots 21/23, retain the public-link matrix, and statically bind that
  matrix to both current READMEs.
- **Disposition:** Fixed. Every publisher citation now resolves under the
  final `publisher-release` tree, and
  `promotion-public-link-evidence.json` records all 26 HTTP results plus both
  GitHub Markdown render results.

### Medium — Required commit-SHA privacy canary was absent

- **Impact:** The previous 312 comparisons did not establish the frozen SHA
  leakage requirement.
- **Evidence:** Requirements review compared the canary catalog with the
  evaluation specification and found neither full nor short commit SHA.
- **Recommendation:** Add actual fixture SHAs and rerun every mode/output
  comparison.
- **Disposition:** Fixed. The final privacy role included the fixture's actual
  full and seven-character SHAs among 15 canaries. Its raw CSV and independent
  root recomputation confirm 360 comparisons and zero hits.

### Medium — Provider selection lost a persistent visible row cue

- **Impact:** After focus moved, selected and unselected provider rows could
  appear identical.
- **Evidence:** Bug review traced `aria-current` to a deleted selected-state
  selector.
- **Recommendation:** Keep provider-name text at the normal text color and use
  a non-text accent border for state.
- **Disposition:** Fixed with a four-pixel selected-row border, explicit
  normal provider-name color, regression assertions, and computed-style
  browser evidence across the accessibility matrix.

### Medium — Release smoke could fail at UTC midnight

- **Impact:** Two correct renders spanning a UTC date boundary looked
  nondeterministic.
- **Evidence:** Both bug reviewers traced independent `generated_on` values.
- **Recommendation:** Detect a date boundary and rerun the pair before byte
  comparison.
- **Disposition:** Fixed with bounded same-date retry and a simulated rollover
  regression.

### Medium — Artifact validation admitted weak or confusing failure paths

- **Impact:** An unrelated `.dist-info` notice, extra distribution entry, or
  missing `PKG-INFO` could bypass the intended release contract or diagnostic.
- **Evidence:** Security and code-quality reviewers provided concrete archive
  constructions.
- **Recommendation:** Tie notices to the metadata directory, require exactly
  two canonical regular files, verify checksums, and translate missing
  metadata to a controlled failure.
- **Disposition:** Fixed with additive regressions. Artifact-only mode also
  separates historical bundle inspection from mutable source parity.

### Medium — Bilingual parity enforcement was structural but not semantic

- **Impact:** CTA, feature, or privacy prose could drift while global tokens
  remained.
- **Evidence:** Both requirements reviewers and code-quality review supplied
  passing counterexamples.
- **Recommendation:** Enforce ordered heading pairs, block-level command
  contracts, link multiplicity, CTA targets, and paired feature/privacy
  claims.
- **Disposition:** Fixed with negative CTA, feature, and privacy drift tests.

### Medium — Checksum manifest was bound to the local directory name

- **Impact:** Exact artifacts copied from `dist/` into a verification
  directory failed against their correct manifest, contradicting the live
  release runbook.
- **Evidence:** The final pre-commit reviewer relocated the wheel and sdist
  and reproduced a mismatch because the checker derived paths from
  `path.parent.name`.
- **Recommendation:** Canonicalize manifest entries as `dist/<filename>`,
  document the parent/`dist` layout, and add a relocation regression.
- **Disposition:** Fixed and reproduced green with the same bytes under a
  differently named download directory.

### Medium — Recovery could skip PyPI files without proving byte identity

- **Impact:** A retry could report a successful PyPI step for an existing
  immutable filename without proving that its wheel and sdist matched the
  retained release bundle.
- **Evidence:** Final release review traced `skip-existing: true` without a
  subsequent PyPI digest comparison.
- **Recommendation:** Verify both served PyPI digests after publication and
  require the exact retained filename set, then prevent GitHub Release
  publication until that comparison succeeds.
- **Disposition:** Fixed. The PyPI job queries the version-specific API with
  bounded cache-bypassing retries, rejects missing or additional
  distributions, compares both SHA-256 digests, and gates the GitHub Release
  job.

### Low — README wording reversed the unknown-attribution promise

- **Impact:** “No evidence stays unknown” could be read as the opposite of the
  product behavior.
- **Evidence:** Code-quality review compared the English line with the
  adjacent explanation and Traditional Chinese version.
- **Recommendation:** State that commits without explicit evidence stay
  unknown.
- **Disposition:** Fixed in the canonical README.

### Low — Release diagnostics and documentation lagged automation

- **Impact:** Determinism errors named unchanged files and the smoke header
  described only the old source-tree/manual mode.
- **Evidence:** Both code-quality reviewers identified the exact lines.
- **Recommendation:** Report only changed artifacts and document candidate
  wheel CI/publish use.
- **Disposition:** Fixed and regression-tested.

### Low — Fresh disposable Pages deployment was not performed

- **Impact:** The publisher role validated instructions and existing live
  routes rather than mutating a new remote repository.
- **Evidence:** The role explicitly recorded no remote and no push.
- **Recommendation:** Do not expand a sealed-box documentation role into an
  undeclared public mutation. Require the planned real maintainer Profile
  deployment as the post-release end-to-end Pages gate.
- **Disposition:** Accepted for pre-release dogfood with owner: maintainer;
  rationale: the frozen role required embeds, URL construction, and dead-end
  recording, while the approved final plan separately requires a real Profile
  push and live Pages verification. Promotion remains blocked until that
  post-release gate completes.

## Verified areas without findings

- No ACE schema, event identity, controlled vocabulary, normalization, or
  version contract changed.
- No aggregation implementation changed. Unique commits, actor presences,
  provider commits, active days, evidence records, unknown, and human remain
  distinct.
- Renderers still consume validated `VizStats`; no Git, SQLite, attribution,
  or statistics logic moved into rendering.
- The dashboard remains self-contained and CSP-bound.
- The package remains dependency-free at runtime and Beta-classified.
- v0.4.1 and earlier releases remain immutable; the corrective disclosure is
  in the changelog.

## Severity summary

| Severity | Total | Fixed | Accepted | Pending |
|---|---:|---:|---:|---:|
| Critical | 0 | 0 | 0 | 0 |
| High | 4 | 3 | 0 | 1 |
| Medium | 7 | 7 | 0 | 0 |
| Low | 3 | 2 | 1 | 0 |

## Final verdict

NO-GO

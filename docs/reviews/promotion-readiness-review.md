# v0.4.6 Public Beta promotion-readiness review

Date: 2026-07-27
Candidate implementation source: 25ea364b3ca7f6a7b8898a901fa6cda2c64cd373
Promotion-evidence documentation source: 73c133f6e397debc5126da685ce01fe34a906ef1
Wheel SHA-256: 26227c0435d2d6a80ff8a46ad878270509b2cadeeb6d0dd78555019884239d8a

## Reviewer posture

Independent release-readiness verification. This review does not redesign ACE,
aggregation, attribution, privacy modes, or the CLI. It records only evidence
reproduced from the candidate, CI, dogfood reports, and the browser target.

## Executive summary

The v0.4.6 wheel, source checks, cross-platform CI, privacy smoke, bilingual
README parity, sanctioned SVG regeneration, and four-role dogfood gate are
green. The candidate must nevertheless not be promoted yet: the exact
candidate dashboard could not be opened by the approved browser target, so
the required candidate-specific visual and keyboard accessibility checks remain
unscored. A second process defect also remains: the checked-in canonical
promotion specification names v0.4.2 rather than this v0.4.6 candidate; the
Round 048 plan froze dogfood criteria but is ignored operational evidence, not
a versioned, tracked complete promotion specification.

## Verification evidence

### Local and artifact gates

~~~
python -m pytest tests -p no:cacheprovider
553 passed, 4 skipped in 26.82s

python -m ruff check src tests scripts
All checks passed!

python scripts/check_readme_parity.py
PASS: README English/Traditional Chinese structure and contract parity

python tests/unit/test_render_summary.py
python tests/unit/test_heatmap_svg.py
git diff --exit-code -- tests/snapshots docs/assets
PASS: sanctioned regeneration completed with zero drift
~~~

The candidate artifact contract and clean-wheel smoke were independently run
against the SHA-256 above. They passed the notice-file, non-editable install,
runtime-version, eight-output, deterministic-render, CSP, and public-canary
checks.

### CI and portability

PR [#11](https://github.com/WenyuChiou/ai-profile/pull/11) is still a draft.
The implementation candidate is the source commit recorded above; its
documentation-only evidence commit rebuilt the same pinned wheel in GitHub
Actions run
[30243159885](https://github.com/WenyuChiou/ai-profile/actions/runs/30243159885).
That run passed release-candidate build; Python 3.11, 3.12, 3.13, and 3.14;
and clean wheel onboarding on Ubuntu, Windows, and macOS with Python 3.12.

### Dogfood and browser evidence

- The four README-only roles passed against the same digest; the reconciliation
  preserves the separation of unique commits, actor presences, providers,
  Human-Only, and unknown. See
  [promotion-dogfood.md](promotion-dogfood.md).
- The public, already-deployed dashboard was checked at 320, 390, 768, and
  1440 CSS pixels with no horizontal overflow; provider pointer interaction
  and automatic/light/dark theme cycling worked. It is not the frozen v0.4.6
  candidate artifact and therefore is not substituted for candidate evidence.
- The browser target correctly rejected file: access to the local candidate
  dashboard. Its keyboard activation result for the public dashboard was also
  not scorable because the browser control did not deliver Enter or Space to
  the focused provider control. No local-server or equivalent bypass was used.

## Findings and dispositions

| Severity | Description and evidence | Impact | Recommendation | Disposition |
| --- | --- | --- | --- | --- |
| High | **Candidate visual/accessibility gate is unscored.** The approved browser target rejected the local candidate dashboard.html; the live public dashboard is a different artifact. Candidate 320/390/768/1440, 200% zoom, system theme, keyboard activation/focus, and reduced-motion verification therefore lacks valid evidence. | Releasing would overstate the verification of the exact bytes users will receive. | Host the immutable candidate dashboard at an approved browser-accessible staging URL, then rerun the required visual/accessibility matrix against that URL. Do not use a local-file or local-server workaround. | Open — promotion blocker. |
| High | **No tracked v0.4.6 immutable promotion specification exists before its final evidence.** docs/reviews/promotion-eval-spec.md explicitly targets v0.4.2; Round 048 froze only dogfood criteria and is ignored operational evidence. | The complete v0.4.6 release gate is not independently auditable as a version-aligned, pre-result contract. Retrofitting it after seeing results would weaken the gate. | Before the next candidate, commit a v0.4.6-specific complete evaluation specification, freeze it, then regenerate candidate evidence required by that specification. | Open — promotion blocker. |
| Low | Dogfood non-access claims are role attestations rather than mechanically enforced controls. | Evidence provenance is bounded, although all observed workflows and checks passed. | Preserve scoped briefs and raw command ledgers; phrase this limitation plainly. | Accepted. |
| Low | Some dogfood homes placed AIPROFILE_HOME inside a temporary Git worktree and correctly received the product's conservative warning; the documented flow still completed. | The warning can be noisy for that disposable layout, but no installation or configuration dead end was reproduced. | Keep the README instruction to store AIPROFILE_HOME outside Git worktrees visible; revisit only if future independent users report repeated confusion. | Accepted. |

## Verified without findings

- Wheel digest matches the checked-in candidate manifest and independently
  verified artifact contract.
- License and third-party notice content are present in the tested distribution
  path.
- Static renderers retained deterministic, CSP-contained, privacy-redacted
  output boundaries under the smoke and snapshot gates.
- Exact aggregation-unit separation and provider display normalization passed
  the multi-provider dogfood fixture.
- The English and Traditional Chinese README contracts are structurally in
  parity, and the candidate did not introduce a source/test or schema change.

## Severity summary

| Severity | Open | Accepted |
| --- | ---:| ---:|
| Critical | 0 | 0 |
| High | 2 | 0 |
| Medium | 0 | 0 |
| Low | 0 | 2 |

## Final recommendation

**NO-GO**

Do not make PR #11 ready, merge, tag v0.4.6, publish to PyPI, or refresh the
maintainer Profile until both High findings have been resolved and independently
verified.

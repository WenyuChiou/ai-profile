# v0.4.6 Public Beta promotion-readiness review

Date: 2026-07-29
Candidate branch: `codex/v046-product-studio` at `a7b32eba68e0b5180f80c634feb177f82ea2f245`
Pinned wheel SHA-256: `26227c0435d2d6a80ff8a46ad878270509b2cadeeb6d0dd78555019884239d8a`

## Reviewer posture

Independent release-readiness verification. This review does not redesign
ACE, aggregation, attribution, privacy modes, or the CLI. It records only
reproduced evidence and leaves any incomplete promotion condition open.

## Executive summary

The candidate package, deterministic renderers, cross-platform wheel
onboarding, staging artifact, README parity, privacy canary smoke, and fresh
R2 dogfood are green. The branch is rebased cleanly onto
main, its post-rebase CI is green, and the public staging dashboard is byte
matched to the pinned wheel.

Promotion is still blocked. The approved browser surface did not apply the
required 320/390/768/1440 viewports or browser zoom, did not offer
reduced-motion emulation, and did not provide a second Chrome surface. Its
keyboard injection did not activate the focused provider button, so this is
an unscored harness result rather than evidence of product failure. The
pre-registered browser gate makes this a release blocker. A later discarded
dogfood retry left local synthetic configuration residue; it is a Low cleanup
item and does not invalidate the completed R2 privacy role.

## Verification evidence

### Local, artifact, and documentation gates

~~~text
python -m pytest tests -p no:cacheprovider
564 passed, 4 skipped in 27.31s

python -m ruff check src tests scripts
All checks passed!

python scripts/check_readme_parity.py
PASS: README English/Traditional Chinese structure and contract parity

python scripts/check_release_artifacts.py --dist-dir .ai/candidate-046-r2/dist \
  --expected-version 0.4.6 --expected-wheel-sha256 <pinned digest>
PASS: artifact contract for ai-profile-cli 0.4.6
  required notices: LICENSE, THIRD_PARTY_NOTICES.md

python scripts/release_smoke.py --wheel .ai/candidate-046-r2/dist/ai_profile_cli-0.4.6-py3-none-any.whl
RESULT: PASS - all steps green

python tests/unit/test_render_summary.py
python tests/unit/test_heatmap_svg.py
git diff --exit-code -- tests/snapshots docs/assets
PASS: sanctioned regeneration completed with zero drift
~~~

The release smoke included a fresh non-editable wheel install, runtime-version
parity, all eight outputs, repeat-render determinism, SVG well-formedness,
self-contained dashboard/CSP validation, and a byte-level public-output
canary sweep. All non-template external README links returned HTTP 200.

### CI, branch, and package portability

- The candidate was rebased onto current `main`; the sole conflict was the
  staging workflow, resolved by retaining the complete candidate workflow.
  An independent post-rebase review approved its manual trigger, owner guard,
  narrow Pages permissions, SHA-pinned actions, exact-wheel verification,
  fresh-wheel render, and synthetic-only publication boundary.
- GitHub Actions [run 30503107844](https://github.com/WenyuChiou/ai-profile/actions/runs/30503107844)
  passed the release-candidate build; Python 3.11–3.14 suites; and clean-wheel
  onboarding on Ubuntu, Windows, and macOS (Python 3.12).
- The exact wheel's `LICENSE` and `THIRD_PARTY_NOTICES.md` are present in both
  artifact contract checks. The candidate remains a Draft PR and has not been
  tagged, published, merged, or copied to the maintainer Profile.

### Immutable staging and browser evidence

- `promotion-eval-spec-v046.md` was committed before the R2 evaluation. The
  manual staging workflow rebuilt the candidate from the frozen epoch,
  verified the exact wheel digest, installed that wheel in a fresh venv, and
  deployed only a deterministic synthetic dashboard.
- Public `staging-manifest.json` returned HTTP 200 with the pinned wheel SHA
  and dashboard SHA `694823d0e5566bf79ffc086b97073401ced7d22a8452fb37775f86078f8c3b96`.
  A direct byte hash of the public `dashboard.html` matched that manifest;
  repository names, paths, organization names, emails, URLs, and candidate
  canaries were absent.
- The live candidate page loaded. All-provider and Claude pointer filters,
  visible focus styling, automatic/light/dark theme selection, the semantic
  dashboard structure, and no desktop horizontal overflow were observed.
- The browser viewport API accepted requested 320, 390, 768, and 1440 values
  but the page remained `window.innerWidth = 1280` even after reload. Browser
  zoom did not change `devicePixelRatio`, reduced-motion emulation was not
  available, and the alternative Chrome surface was unavailable. Enter/Space
  injection did not change the focused provider state despite semantic native
  buttons in the rendered page; this control limitation cannot prove a product
  keyboard defect or a keyboard pass.

### Fresh R2 dogfood

See [promotion-dogfood.md](promotion-dogfood.md). All four README-only roles
produced valid R2 evidence: the privacy role rendered all three modes to
separate directories and found zero exact canary matches in 24 public
artifacts. A later discarded retry caused the local cleanup item below and is
not substituted for the passing role.

## Findings and dispositions

| Severity | Description and evidence | Impact | Recommendation | Disposition |
| --- | --- | --- | --- | --- |
| High | **Candidate responsive/accessibility matrix is unscored.** Exact staging bytes were reachable, but the only approved browser did not apply 320/390/768/1440 viewport overrides or 200% zoom, could not emulate reduced motion, and its keyboard-injection behavior was inconclusive. | The release cannot truthfully claim its required responsive, zoom, keyboard, and reduced-motion gate passed. | Re-run the pre-registered matrix on a browser surface that demonstrably changes viewport, zoom, keyboard state, and media preference; retain screenshots/state measurements for the exact staging URL. | Open — promotion blocker. |
| Low | A discarded post-pass test-harness retry left a local config at `C:\Users\wenyu\config.json`; local command policy prevented deletion by this review. | It is local synthetic test residue rather than a public asset and does not invalidate the successful privacy role, but it should not remain ambiguous. | Inspect and delete it if it is not intended user data before normal use of that home. | Open — cleanup required. |

## Verified without findings

- ACE aggregation units remained separate: one commit can have several AI
  presences; provider counts may overlap; unknown remains distinct from
  human-declared activity.
- Renderers consumed validated `VizStats` data, staging used a fixed synthetic
  fixture, and public assets did not scan Git, query SQLite, or infer
  attribution.
- The public staging page and generated artifacts passed the observed privacy
  sweep, deterministic hash, self-contained/CSP, SVG, theme, and desktop
  visual checks.
- English and Traditional Chinese README structure/contract parity, all real
  public links, license/notice packaging, and cross-platform clean-wheel
  onboarding passed.

## Severity summary

| Severity | Open | Accepted |
| --- | ---:| ---:|
| Critical | 0 | 0 |
| High | 1 | 0 |
| Medium | 0 | 0 |
| Low | 1 | 0 |

## Final recommendation

**NO-GO**

Do not make PR #11 ready, merge, tag v0.4.6, publish to PyPI, or update the
maintainer Profile until the High browser finding has been independently
resolved. Separately, inspect and remove the local synthetic config before
normal use of that home.

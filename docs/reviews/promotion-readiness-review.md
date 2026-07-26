# v0.4.3 Public Beta promotion readiness review

Date: 2026-07-26
Review head: `bd2a20b`
Evaluation baseline:
`773113562871a99da02d50056a118f993794baac`
Candidate wheel:
`ai_profile_cli-0.4.3-py3-none-any.whl`
Candidate SHA-256:
`b3baebac895927897ef39ae86227d3ed89455ed1d925be74cc6cc385468781a8`

## Reviewer posture

This is a release verification, not a redesign. v0.4.3 changes dashboard
accessibility, responsive Profile presentation, release metadata, and
regression evidence only. ACE schema, aggregation semantics, provider
vocabulary, privacy boundary, SVG contract, and CLI remain unchanged.

## Executive summary

The v0.4.3 candidate is code-complete and passes its pre-publication gates:

- full suite and Ruff are green;
- the clean-Linux wheel is reproducible and pinned by SHA-256;
- Twine, artifact notice/metadata contract, clean-wheel smoke, CSP,
  determinism, and privacy checks pass;
- Ubuntu, Windows, and macOS consume the same retained wheel;
- four README-only dogfood roles pass with zero external hints;
- 480 privacy-canary comparisons have zero hits;
- hand-derived unique commits, actor presences, provider commits, active
  days, human, unknown, and evidence records match exactly;
- the exact-wheel headed-browser matrix passes responsive, keyboard, touch,
  accessibility-tree, contrast, reduced-motion, and overflow gates;
- independent architecture, security/privacy, and packaging reviewers report
  no unresolved Critical, High, Medium, or Low code findings.

Promotion remains blocked until the tag workflow publishes the exact retained
bytes and the released PyPI wheel regenerates the real maintainer Profile.
The real GitHub-rendered `<picture>` sanitizer behavior, responsive source
selection, Profile privacy sweep, PR/Pages deployment, and final live install
therefore remain mandatory external gates. The current verdict is `NO-GO`.

## Verification evidence

### Local quality gates

```text
python -m pytest tests -p no:cacheprovider
549 passed, 4 skipped

python -m ruff check src tests scripts
All checks passed!

python scripts/check_readme_parity.py
PASS: README English/Traditional Chinese structure and contract parity

python tests/unit/test_render_summary.py
python tests/unit/test_heatmap_svg.py
git diff --exit-code -- tests/snapshots docs/assets
PASS: sanctioned regeneration completed with zero drift
```

### Candidate artifact

```text
clean Linux wheel SHA-256
b3baebac895927897ef39ae86227d3ed89455ed1d925be74cc6cc385468781a8

python -m twine check <wheel> <sdist>
PASSED

python scripts/check_release_artifacts.py --dist-dir <candidate>
  --expected-wheel-sha256 b3baebac...781a8
PASS

python scripts/release_smoke.py --wheel <candidate-wheel>
  --expected-version 0.4.3
RESULT: PASS - all steps green
```

The wheel contains both `LICENSE` and `THIRD_PARTY_NOTICES.md`. The sdist
contains both notices at archive root. Runtime, project metadata, candidate
manifest, and artifact filenames all report `0.4.3`.

### GitHub-hosted matrix

PR #5 run `30203764991` passes eight required checks:

- Python 3.11, 3.12, 3.13, and 3.14;
- Release candidate build;
- wheel onboarding on Ubuntu, Windows, and macOS with Python 3.12.

The CI release bundle uses the manifest-pinned wheel digest. Windows and
macOS consume the retained Ubuntu-built universal wheel rather than
rebuilding platform-specific ZIP metadata.

### Dogfood and privacy

The final role set is documented in
`docs/reviews/promotion-dogfood.md`.

```text
roles: 4/4 PASS
candidate hash matches: 4/4
README-external hints: 0
installation/configuration dead ends: 0
privacy: 20 canaries * 8 outputs * 3 modes = 480, hits 0
aggregation/dashboard mismatches: 0
local Pages configuration dead ends: 0
```

### Exact-wheel browser matrix

```text
viewport/theme states: 12
provider states: 36
widths: 320 / 390 / 768 / 1440
themes: light / dark / system
maximum document overflow: 0
minimum meaningful-mark contrast: 5.011:1
minimum normal metadata contrast: 5.010:1
accessibility dates present: all 294 rendered dates per state
200% rendering: PASS; tooltip in viewport; calendar locally scrollable
keyboard / focus / hover / touch / reduced motion: PASS
console errors / external requests: 0 / 0
```

Evidence is retained under
`.artifact/promotion/browser-v043/exact-wheel-browser/`.

## Independent reviews

### Architecture and maintainability

**APPROVE — Critical 0, High 0, Medium 0, Low 0.**

The renderer still accepts exact sealed `VizStats`; embedded dashboard data
remains `profile.json`-equivalent; no schema, aggregation, CLI, vocabulary,
or privacy contract changed. Accessibility logic remains inside the
self-contained renderer.

### Security and privacy

**APPROVE — Critical 0, High 0, Medium 0, Low 0.**

The reviewer independently recomputed the 480-byte sweep, verified all three
publication modes, checked embedded JSON equality, CSP/network closure, and
unknown/human plus commit/presence separation.

### Packaging, release, and onboarding

**APPROVE — Critical 0, High 0, Medium 0, Low 0.**

The reviewer independently inspected the retained CI bundle, notices,
metadata, checksums, Twine results, exact-wheel smoke, version parity,
three-platform onboarding, and checkout-free GitHub Release commands.

### Visual, accessibility, and README accuracy

**APPROVE — Critical 0, High 0, Medium 0, Low 0 code findings.**

The first pass found missing runtime evidence and a zoomed-tooltip risk.
Re-review confirmed the measured-width clamp and exact-wheel headed-browser
matrix close both code findings. The real Profile/GitHub sanitizer gate
remains intentionally pending until the package is published.

## Findings and dispositions

### High — Candidate evidence must bind to one wheel

- **Impact:** Passing checks on a different wheel would not authorize the
  uploaded bytes.
- **Evidence:** Windows CRLF and the subsequent tooltip patch each changed
  the wheel digest.
- **Recommendation:** Build in a clean Linux checkout, pin SHA-256, fan out
  the retained wheel, and invalidate all role evidence after byte changes.
- **Disposition:** Fixed. CI and all four final roles use
  `b3baebac...781a8`.

### High — Exact-wheel browser evidence was initially incomplete

- **Impact:** String-level tests could not prove responsive, interaction,
  accessibility-tree, or composited-contrast behavior.
- **Recommendation:** Retain a headed-browser matrix generated by the exact
  candidate wheel.
- **Disposition:** Fixed. The final matrix covers 12 viewport/theme and 36
  provider states plus zoom, touch, keyboard, focus, hover, and screenshots.

### High — Real Profile sanitizer and Pages behavior is unverified

- **Impact:** GitHub could reject or alter responsive `<picture>` behavior,
  or the published Profile could fail its mobile/readability/privacy gate.
- **Recommendation:** Regenerate from the released PyPI wheel, merge through
  the Profile PR path, verify GitHub-rendered `currentSrc` at all required
  widths/themes, then wait for Pages and public HTTP checks.
- **Disposition:** Pending external gate; promotion blocker.

### Medium — Fixed tooltip center could clip under zoom

- **Impact:** Calendar evidence could become unreadable at a viewport edge.
- **Recommendation:** Clamp by measured half-width plus a 16 px margin.
- **Disposition:** Fixed, regression-tested, and runtime-verified.

### Low — Isolated dogfood homes trigger a conservative warning

- **Impact:** Evaluators see an accurate warning because ignored test homes
  sit inside the outer worktree.
- **Disposition:** Accepted; the warning is privacy-conservative and caused
  no workflow dead end.

## Verified areas without findings

- Unknown remains separate from human; no source-style inference exists.
- Unique commits, actor presences, provider commits, active days, and
  evidence records remain distinct.
- Renderers consume validated aggregate data only and never scan Git, read
  SQLite, infer attribution, or recalculate aggregation.
- Public assets contain no repository names, organizations, paths, prompts,
  commit messages, emails, URLs, or SHAs from privacy fixtures.
- README English and Traditional Chinese retain setup, command, CTA, link,
  privacy, limitation, and claim parity.
- The package remains `0.x` Public Beta; no Stable/GA claim was introduced.

## Severity summary

| Severity | Fixed | Accepted | Pending |
|---|---:|---:|---:|
| Critical | 0 | 0 | 0 |
| High | 2 | 0 | 1 |
| Medium | 1 | 0 | 0 |
| Low | 0 | 1 | 0 |

## Pending external gates

- merge PR #5 and tag `v0.4.3`;
- verify PyPI and GitHub Release serve the retained wheel and final sdist;
- clean-install from live PyPI and repeat package smoke;
- regenerate the maintainer Profile only from the released wheel;
- verify GitHub sanitizer, responsive asset selection, Profile privacy,
  Profile PR/CI, Pages, public links, homepage, and branch protection.

## Final verdict

NO-GO

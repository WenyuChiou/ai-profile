# v0.4.3 Public Beta promotion readiness review

Date: 2026-07-26
Release source: `bf9bb5ae741eeb3dba9efbcb79dcb0a24c84930e`
Evaluation baseline:
`773113562871a99da02d50056a118f993794baac`

Published artifacts:

- wheel: `ai_profile_cli-0.4.3-py3-none-any.whl`
- wheel SHA-256:
  `b3baebac895927897ef39ae86227d3ed89455ed1d925be74cc6cc385468781a8`
- sdist: `ai_profile_cli-0.4.3.tar.gz`
- sdist SHA-256:
  `1707195748c2f989c594016be4215c0a4a40411cd4d6a2bebf991d12be580a49`

## Reviewer posture

This is a release and promotion verification, not a redesign. The review
tests the frozen v0.4.3 gate without changing ACE schema, aggregation
semantics, provider vocabulary, privacy boundaries, SVG contracts, or CLI
behavior.

## Executive summary

v0.4.3 satisfies the frozen Public Beta promotion gate:

- PyPI and GitHub Release serve the exact retained wheel and sdist;
- the live PyPI wheel clean-installs and passes the release smoke contract;
- all eight protected CI checks and the release workflow are green;
- four README-only dogfood roles complete with zero external hints;
- the exact-wheel browser matrix passes responsive, interaction,
  accessibility, contrast, and network-closure checks;
- the maintainer's real GitHub Profile was regenerated only from live PyPI,
  passed a 52,392-comparison privacy sweep, and was merged through PR #7;
- GitHub's rendered Profile preserves the responsive `<picture>` contract at
  every required width and theme;
- GitHub Pages serves all eight generated assets as exact bytes from Profile
  `main`;
- all 31 non-placeholder README and canonical promotion URLs return HTTP 200;
- independent architecture, privacy, packaging, visual, and completion
  integrity reviews have no unresolved Critical or High finding.

The approved positioning remains **Public Beta** under `0.x`. This review
does not claim Stable or GA status.

## Verification evidence

### Product quality gates

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

The four skips are declared platform/fixture cases; no required promotion
check was silently omitted.

### Published artifact identity

GitHub Actions publish run
[`30204355152`](https://github.com/WenyuChiou/ai-profile/actions/runs/30204355152)
completed successfully. It tested, built, retained, smoked on Ubuntu,
Windows, and macOS, published through PyPI trusted publishing, verified
digests, and created the GitHub Release from the same bytes.

Live verification:

```text
PyPI wheel SHA-256
b3baebac895927897ef39ae86227d3ed89455ed1d925be74cc6cc385468781a8

PyPI sdist SHA-256
1707195748c2f989c594016be4215c0a4a40411cd4d6a2bebf991d12be580a49

python scripts/check_release_artifacts.py --artifact-only ...
PASS

clean venv: python -m pip install ai-profile-cli==0.4.3
aiprofile version: 0.4.3
release smoke: PASS
```

The wheel and sdist both contain `LICENSE` and
`THIRD_PARTY_NOTICES.md`. GitHub Release contains exactly the wheel, sdist,
and `SHA256SUMS`.

### Dogfood and aggregation correctness

Raw role evidence and the reconciled report are retained under
`.artifact/promotion/dogfood-v043/` and summarized in
`docs/reviews/promotion-dogfood.md`.

```text
README-only roles: 4/4 PASS
README-external hints: 0
installation/configuration dead ends: 0
privacy dogfood: 20 canaries * 8 outputs * 3 modes = 480, hits 0
multi-provider fixture:
  unique commits = 4
  unique AI-attributed commits = 2
  AI actor presences = 3
  provider commit counts = 3
  human commits = 1
  unknown commits = 1
  evidence records = 5
```

One commit with two AI actors remains one unique commit and two actor
presences. Human and unknown remain disjoint.

### Exact-wheel browser and accessibility matrix

Canonical evidence:
`.artifact/promotion/browser-v043/exact-wheel-browser/browser-gate.json`.

```text
viewport/theme states: 12
provider states: 36
widths: 320 / 390 / 768 / 1440
themes: light / dark / system
maximum document overflow: 0
minimum meaningful-mark contrast: 5.011:1
minimum normal metadata contrast: 5.010:1
accessible dates: all 294 rendered dates per state
200% rendering: tooltip remains in viewport; calendar scrolls locally
keyboard / focus / hover / touch / reduced motion: PASS
console errors / external requests: 0 / 0
```

The selected-provider label uses normal text color; selection remains
visible through a mark, border, and state text rather than color alone.

### Real GitHub Profile

Profile source commit:
`605b186dafbbdae9008d334b6d13aceabf99f338` (PR #7).
The assets were generated in an isolated home by a clean environment
installed from live PyPI v0.4.3.

```text
repositories scanned: 11
commits scanned: 1673
unique AI-attributed commits: 1125
AI actor presences: 1144
human commits: 0
unknown commits: 548
active AI days: 89
providers: 2
evidence records: 1692

identity checks:
1673 = 1125 AI + 0 human + 548 unknown
1144 = 1098 Anthropic + 46 OpenAI presences
1692 = 1144 declared presences + 548 unknown records
```

The retained real-output privacy runner derives 6,549 unique canaries from
the private salt and paths, repository names and UIDs, organization and
remote values, identities and author emails, all database full/short SHAs,
and every exact commit subject and full commit message:

```text
6549 unique canaries * 8 canonical public outputs = 52,392 comparisons
privacy hits: 0
deterministic double-render differences: 0 of 8 files
```

Canonical evidence:
`.artifact/promotion/profile-v043/privacy-sweep.json`; reproducible runner:
`.artifact/promotion/profile-v043/run-privacy-sweep.py`. An earlier
5,304/42,432 summary had no retained raw manifest and is superseded by this
computed result. The runner reads canonical Profile Git blobs, whose digests
match live Pages, rather than the CRLF-normalized Windows checkout.

GitHub-rendered Profile evidence:
`.artifact/promotion/profile-v043/github-live/github-profile-gate.json`.
Across 320, 390, 768, and 1440 pixels in light and dark themes, GitHub
preserves all three ordered `<source>` elements and selects:

- mobile light -> `badge-light.svg`;
- mobile dark -> `badge-dark.svg`;
- desktop light -> `summary-light.svg`;
- desktop dark -> `summary-dark.svg`.

The card anchor resolves to the live dashboard, document overflow is zero,
and the smallest compact rendered text is 13.7068 px.

### Pages, links, and repository controls

Pages run
[`30204801474`](https://github.com/WenyuChiou/WenyuChiou/actions/runs/30204801474)
completed successfully for Profile commit
`605b186dafbbdae9008d334b6d13aceabf99f338`. Pages is public, HTTPS-only,
and sourced from `main` at `/`.

The live responses for all eight generated outputs return HTTP 200 and are
byte-identical to their canonical Git blobs. Evidence:
`.artifact/promotion/profile-v043/pages-live.json`.

All 31 real README and promotion endpoints return HTTP 200. Placeholder
`USERNAME` examples are intentionally excluded. Evidence:
`.artifact/promotion/public-links-v043.json` and
`docs/reviews/promotion-public-link-evidence.json`.

The project homepage is the live dashboard. `main` requires a pull request,
strict current status checks, the eight release/onboarding checks, and
administrator enforcement.

## Independent review synthesis

| Lens | Verdict | Critical | High | Medium | Low |
|---|---|---:|---:|---:|---:|
| Architecture and maintainability | APPROVE | 0 | 0 | 0 | 0 |
| Security and privacy | APPROVE | 0 | 0 | 0 | 0 |
| Packaging, release, onboarding | APPROVE | 0 | 0 | 0 | 0 |
| Visual, accessibility, README accuracy | APPROVE | 0 | 0 | 0 | 0 |
| Completion integrity | APPROVE | 0 | 0 | 0 | 0 |

## Findings and dispositions

### High — Candidate evidence must bind to one wheel

- **Impact:** Checks on a different wheel cannot authorize published bytes.
- **Recommendation:** Retain one Linux-built wheel, pin its digest, fan out
  that wheel to every platform and role, and upload only those bytes.
- **Disposition:** Fixed. All release and dogfood evidence binds to
  `b3baebac...781a8`; PyPI and GitHub Release match.

### High — Exact-wheel browser evidence was initially incomplete

- **Impact:** Static tests cannot prove browser layout, accessibility tree,
  interaction, or composited contrast.
- **Recommendation:** Exercise the exact wheel in a headed browser across
  the frozen viewport, theme, provider, zoom, and input matrix.
- **Disposition:** Fixed. The retained 12-state/36-provider matrix passes.

### High — Real Profile sanitizer and Pages behavior was unverified

- **Impact:** GitHub could alter responsive sources or Pages could publish
  stale/private output.
- **Recommendation:** Generate from live PyPI, merge through the Profile PR,
  inspect GitHub `currentSrc`, sweep privacy, and compare Pages to Git blobs.
- **Disposition:** Fixed. The eight live Profile states and all eight Pages
  assets pass.

### Medium — Fixed tooltip center could clip under zoom

- **Impact:** Edge calendar evidence could become unreadable.
- **Recommendation:** Clamp with measured tooltip width and a 16 px margin.
- **Disposition:** Fixed, regression-tested, and browser-verified.

### Low — Isolated dogfood homes trigger a conservative warning

- **Impact:** Evaluators see an accurate warning because ignored test homes
  sit inside an outer worktree.
- **Recommendation:** Keep the warning; do not weaken path protection for a
  cosmetic dogfood environment.
- **Disposition:** Accepted. It caused no privacy or onboarding dead end.

## Verified areas without findings

- Renderers consume sealed, validated aggregate data and do not scan Git,
  access SQLite, infer attribution, or recalculate statistics.
- Unique commits, actor presences, provider commits, active days, and
  evidence records remain separate.
- Unknown remains separate from human; no source-style inference exists.
- Aggregate-only and excluded modes emit no repository, organization, path,
  prompt, message, email, URL, or SHA canary.
- README English and Traditional Chinese maintain command, CTA, link,
  privacy, limitation, and claim parity.
- The package adds no configuration CLI or other feature outside the frozen
  v0.4.3 scope.

## Severity summary

| Severity | Fixed | Accepted | Pending |
|---|---:|---:|---:|
| Critical | 0 | 0 | 0 |
| High | 3 | 0 | 0 |
| Medium | 1 | 0 | 0 |
| Low | 0 | 1 | 0 |

There are no unresolved Critical or High findings. The accepted Low is
documented behavior and is not a promotion blocker.

## Final verdict

GO — PUBLIC BETA

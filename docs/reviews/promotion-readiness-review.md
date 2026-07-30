# v0.4.6 Public Beta promotion-readiness review

Date: 2026-07-30

Candidate branch: `codex/v046-product-studio` at
`1e91c0bb4f0a5d3c86b9d541aa3022679a8c157a`

Implementation source commit:
`3f77aa1c29222fa4ce95adc076f5ddc32535640b`

Pinned wheel SHA-256:
`84aa13766c70ad082fe70e4e860f2b15f77472826abbc579531376d5cdc4bcdb`

Pinned sdist SHA-256:
`9af25ed34c866376bf777e34458f876fb9b1c7160446638ee4966085fd702cc2`

## Reviewer posture

Independent promotion verification against the frozen
[R5 evaluation specification](promotion-eval-spec-v046-r5.md). This review
does not redesign ACE, aggregation, attribution, privacy modes, or the CLI.
R4 evidence was discarded after its provider-overlap wording failure. Every
result below was reproduced against the exact R5 candidate or the exact
public staging bytes derived from it.

## Executive summary

The v0.4.6 Public Beta candidate passes package, test, CI, dogfood, staging,
browser, privacy, determinism, documentation, and visual-quality gates.
Four blind README-only user roles completed without product hints or dead
ends. Public assets had zero canary hits, and one commit with two providers
remained one unique AI-attributed commit plus two actor presences.

The public staging manifest, public dashboard, and an independent local
render from the retained wheel are byte-consistent. The browser matrix
scored 13/13, including responsive layouts, 200% scaling, themes, pointer and
keyboard filters, focus, reduced motion, contrast, and non-color selection.
Independent packaging/onboarding and visual/accessibility reviews found no
Critical or High issue.

One Medium refinement is explicitly accepted for Public Beta: fine-pointer
calendar cells do not meet WCAG 2.2's 24 CSS-pixel target-size/spacing
criterion, although the coarse-pointer layout reaches the spacing threshold
and the grid is fully keyboard operable. The maintainer owns a v0.4.7
follow-up to enlarge the hit area without changing the data layout. This
does not weaken any pre-registered R5 gate or any privacy/aggregation claim.

## Verification evidence

### Local quality gates

```text
python -m pytest tests -p no:cacheprovider
568 passed, 4 skipped in 27.30s

python -m ruff check src tests scripts
All checks passed!

python scripts/check_readme_parity.py
PASS: README English/Traditional Chinese structure and contract parity

python tests/unit/test_render_summary.py
Wrote 8 snapshot files and 2 sample assets

python tests/unit/test_heatmap_svg.py
Wrote 8 snapshot files and 4 sample assets

git diff --exit-code -- tests/snapshots docs/assets
PASS: zero sanctioned-regeneration drift
```

The full suite includes the overlap-qualified summary description,
runtime/vendor theme parity, exact workflow permissions and artifact tree,
canonical staging manifest, and the job-level GitHub expression-context
regression. Repeated sanctioned regeneration remained byte-stable.

### Exact artifact gates

The retained candidate bundle came from GitHub Actions run
[30530460205](https://github.com/WenyuChiou/ai-profile/actions/runs/30530460205).
The local download reproduced `SHA256SUMS`:

```text
84aa13766c70ad082fe70e4e860f2b15f77472826abbc579531376d5cdc4bcdb  dist/ai_profile_cli-0.4.6-py3-none-any.whl
9af25ed34c866376bf777e34458f876fb9b1c7160446638ee4966085fd702cc2  dist/ai_profile_cli-0.4.6.tar.gz
```

```text
python -m twine check <retained-dist>/*
PASSED (wheel and sdist)

python scripts/check_release_artifacts.py \
  --dist-dir <retained-dist> \
  --expected-version 0.4.6 \
  --expected-wheel-sha256 84aa...cdb
PASS: artifact contract for ai-profile-cli 0.4.6
required notices: LICENSE, THIRD_PARTY_NOTICES.md

python scripts/release_smoke.py \
  --wheel <retained-wheel> --expected-version 0.4.6
RESULT: PASS - all steps green
```

The smoke installed the non-editable retained wheel in a fresh venv,
confirmed runtime version parity, produced all eight outputs, checked SVG and
dashboard structure/CSP, repeated deterministic rendering, and found zero
privacy-canary hits.

### CI and portability

GitHub Actions run
[30530460205](https://github.com/WenyuChiou/ai-profile/actions/runs/30530460205)
passed:

- release-candidate build and exact digest verification;
- Python 3.11, 3.12, 3.13, and 3.14 full suites;
- clean-wheel onboarding on Ubuntu, Windows, and macOS with Python 3.12.

The PR is cleanly mergeable, and every required status check is green.

### Staging integrity

The first R5 staging attempt failed closed at workflow parsing because
`runner.temp` was used in a job-level expression context. It built and
deployed nothing. A red-first regression moved `STAGING_ROOT` derivation into
step contexts; full tests and an independent security review approved the
fix.

Manual staging run
[30530538138](https://github.com/WenyuChiou/ai-profile/actions/runs/30530538138)
then passed both jobs:

- build job permissions: `{contents: read}`;
- deploy job permissions: `{pages: write, id-token: write}`;
- deploy performed no checkout, package installation, build, or project-code
  execution;
- exactly `v0.4.6/dashboard.html` and
  `v0.4.6/staging-manifest.json` crossed the job boundary;
- both jobs rejected symlinked roots, nested symlinks, and extra entries;
- both jobs re-verified canonical manifest bytes and pinned digests.

The public
[staging manifest](https://wenyuchiou.github.io/ai-profile/v0.4.6/staging-manifest.json)
and
[dashboard](https://wenyuchiou.github.io/ai-profile/v0.4.6/dashboard.html)
returned HTTP 200:

```text
package_version     0.4.6
wheel_sha256        84aa13766c70ad082fe70e4e860f2b15f77472826abbc579531376d5cdc4bcdb
dashboard_sha256    17f2627e60c42a008e20af583af4cd51ca9a0814773163df5c5d1ec4982af192
```

Direct hashing of the served dashboard and an independent render from the
retained wheel both produced the same dashboard digest. Structural sweeps
found zero HTTP URLs, email addresses, Git SHAs, Windows paths, POSIX home
paths, or GitHub remotes in the staged aggregate payload.

### Fresh R5 dogfood

[promotion-dogfood.md](promotion-dogfood.md) records four of four passing
README-only roles. The privacy role made 504 artifact/canary comparisons
with zero hits. The multi-provider role exactly reproduced:

```text
one unique AI-attributed commit
two AI actor presences
one human-declared commit
one unknown commit
```

Both summary themes explicitly described the daily peak as a summed
provider-attributed count whose provider counts may overlap. The Profile
publisher produced eight deterministic outputs and completed the clickable
card plus Pages main/root dry run.

### Browser, visual, and accessibility gates

Retained evidence:
`.ai/browser-evidence-r5/gate-b-results.json` and the associated screenshots.

```text
assertions: 13
pass:       13
fail:       0
unscored:   0

pointer Claude:      hero 16 | presences 17 | active days 9 | calendar labels 32
Enter OpenAI:        hero 10 | presences 9  | active days 6 | calendar labels 32
Space Claude:        hero 16 | presences 17 | active days 9 | calendar labels 32
```

Verified:

- no horizontal overflow at 320, 390, 768, or 1440 CSS pixels;
- no overflow at 200% scale (720 CSS pixels on a 1440-pixel surface);
- automatic, explicit light, explicit dark, and automatic dark themes;
- pointer, Enter, and Space provider filtering with exact hero, actor-presence,
  active-day, and all 32 calendar-label aggregates independently derived
  from the embedded validated data;
- visible 3px focus on every Tab stop;
- reduced-motion transitions and animations reduced to 0.01ms;
- normal text contrast at least 4.5:1;
- large text and meaningful marks at least 3:1;
- selection conveyed by text, border/state, `aria-pressed`,
  `aria-current`, and live status, not color alone.

Independent visual review approved the hierarchy, spacing, restrained
pastel-blue/yellow palette, distinctive commercial typography, provider
icons with adjacent text, responsive composition, and both themes for Public
Beta.

### README and OSS onboarding

- English and Traditional Chinese README structure, commands, links,
  features, and privacy promises passed the repository parity gate.
- GitHub's Markdown API rendered both canonical README files successfully.
- Every concrete external README URL returned HTTP 200. The literal
  `USERNAME.github.io/...` example was correctly excluded as a substitution
  template, not treated as a live project link.
- The quickstart, fallback module invocation, identity setup,
  `aggregate_only`/`full`/`excluded`, multi-repository refresh, eight-output
  contract, clickable card, Pages configuration, 404 recovery, limitations,
  contribution path, security policy, license, and third-party notices are
  discoverable from the public docs.
- The release remains explicitly `0.x` Public Beta and makes no Stable/GA
  claim.

## Findings and dispositions

| Severity | Description | Impact | Evidence | Recommendation | Disposition |
| --- | --- | --- | --- | --- | --- |
| Medium | Fine-pointer calendar cells are approximately 13×13 CSS px with 4.5px gaps, below WCAG 2.2's 24px target-size/spacing criterion. Coarse-pointer CSS reaches 16px cells with 8px gaps, and keyboard operation is complete. | Fine-pointer users with motor impairments have a smaller-than-preferred click target. | Independent visual review of the exact staging page; Gate B confirms keyboard, focus, zoom, and coarse-pointer behavior. | Maintainer to enlarge the cell hit area or spacing while preserving the compact calendar in v0.4.7; add a target-size browser assertion. | Explicitly accepted for Public Beta. Owner: maintainer. Rationale: alternative keyboard path is complete, coarse-pointer threshold passes, and changing candidate CSS now would invalidate every R5 artifact gate. |
| Low | Singular fixtures produce plural count nouns in the summary SVG accessible description. | Minor screen-reader copy polish only; values and units remain accurate. | R5 provider fixture: `1 AI-attributed commits` and `1 active AI days`. | Add count-aware grammar with snapshot tests in a later renderer release. | Accepted post-beta polish. |
| Low | `human_declared_commits` remains structurally distinct but has no dedicated visible dashboard tile. | A dashboard-only reader cannot directly inspect this secondary total. Unknown is still never counted as human. | R5 provider JSON/dashboard recomputation. | Consider a secondary human-declared metric without expanding v0.4.6 scope. | Accepted future visualization refinement. |
| Low | Normal local CLI status output may contain a local path, configured identity, repository display name, or output path. | Users should not paste raw local terminal logs publicly without review; no public artifact leak occurred. | R5 privacy role; 504 public-output canary comparisons had zero hits. | Clarify normal operational output versus sanitized parser diagnostics in a future privacy-doc update. | Accepted; local-first boundary remains accurate. |
| Low | Several pinned GitHub actions generated Node 20 compatibility annotations while GitHub forced Node 24, including artifact upload/download, Pages configuration, and Pages deployment actions. | No run failure or byte-integrity effect; future runner removal could require maintenance. | Staging run 30530538138 annotations. | Update every affected action to reviewed SHAs that declare current Node runtime support. | Accepted dependency-maintenance item. |
| Low | Secondary text inside the 830px README summary preview becomes dense when GitHub scales the SVG down. | Some supporting labels are less comfortable to read at narrow widths. | Independent visual review; the live Profile example already swaps to the purpose-built badge below 600px. | Continue using the badge fallback and revisit summary-card label density in a later visual pass. | Accepted; the shipped responsive embed already mitigates the issue. |
| Low | `CHANGELOG.md` records v0.4.6 as 2026-07-26 although public publication occurs later. | Readers could interpret the preparation date as the exact registry publication date. | Independent packaging review; prior releases also use source preparation dates while GitHub/PyPI retain authoritative publication timestamps. | In a future release, define changelog dates explicitly as preparation or publication dates and apply the convention consistently. | Accepted to preserve frozen R5 artifact bytes; live registry and Release timestamps remain authoritative. |

## Severity summary

| Severity | Open blocker | Explicitly accepted | Deferred polish |
| --- | ---: | ---: | ---: |
| Critical | 0 | 0 | 0 |
| High | 0 | 0 | 0 |
| Medium | 0 | 1 | 0 |
| Low | 0 | 3 | 3 |

## Release authorization

This verdict authorizes Gate R only for the exact retained candidate bytes.
The tag, PyPI files, GitHub Release assets, and checksums must reproduce the
digests above. The maintainer Profile may be refreshed only after a clean
install from live PyPI passes.

The final completion-integrity review initially rejected the browser claim
because the keyboard evidence retained only the hero and live status. The
unversioned acceptance harness was strengthened and replayed against the
same public staging digest. The replacement evidence retains and asserts,
for both Enter and Space, the exact actor-presence total, active-day total,
and every provider-specific calendar label in addition to the hero and
status. The replay remained `13 passed, 0 failed, 0 unscored`.

## Final verdict

**GO — PUBLIC BETA**

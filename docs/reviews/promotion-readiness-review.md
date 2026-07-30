# v0.4.7 Public Beta promotion-readiness review

Date: 2026-07-30

Candidate branch: `codex/v047-sdist-cleanup`

Application/package source commit:
`4ce6af0d4e16da97c8f82546279e96d5c8c87327`

Pinned wheel SHA-256:
`75b896c7a1bfa462d1caa6df7025bca79650e8ad48a006272e76eb9bfb5667d8`

## Reviewer posture

Independent promotion verification against the frozen
[v0.4.7 evaluation specification](promotion-eval-spec-v047.md). v0.4.7 is
an artifact-only remediation of the immutable v0.4.6 source distribution.
It does not change the ACE schema, aggregation semantics, CLI, privacy
model, renderers, or visual design.

## Executive summary

The candidate closes the v0.4.6 source-distribution defect. Hatch now
excludes generated caches and private working roots, while the artifact
contract independently rejects cache directories, coverage and bytecode
files, `.ai`, `.artifact`, `.claude`, build outputs, archive-root escape,
parent traversal, non-canonical and duplicate paths, links, and special
members.

The full local suite passes at `603 passed, 4 skipped`; Ruff, README parity,
sanctioned snapshot regeneration, Twine, the artifact contract, and
clean-wheel release smoke pass. GitHub Actions run
[30535142355](https://github.com/WenyuChiou/ai-profile/actions/runs/30535142355)
passed Python 3.11–3.14, the exact candidate build, and Ubuntu, Windows, and
macOS onboarding against the same retained wheel.

Four independent README-only user roles completed 4/4 with no product hints,
no dead ends, exact aggregation agreement, deterministic eight-file
renders, and zero privacy-canary hits. The exact staging build artifact
matches the pinned wheel and dashboard digests. A 13/13 Playwright gate
passed responsiveness, 200% scaling, themes, pointer/keyboard filters,
exact provider aggregates, focus, reduced motion, contrast, and non-color
selection.

The feature-branch Pages deployment was correctly rejected by the existing
GitHub environment rule that permits deployment only from `main`; the
unprivileged staging build itself passed. Therefore promotion remains
conditional on a protected-main deployment and live browser replay before
the release tag.

## Verification evidence

### Local quality gates

```text
python -m pytest tests -p no:cacheprovider
603 passed, 4 skipped in 28.22s

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

The artifact regression was proven red before the fix: all generated-cache
fixtures were initially accepted. Independent pre-commit review then found
and reproduced root-level `.coverage`, private `.ai` content, and
`root/../...` traversal bypasses. Each was fixed fail-closed and retained as
a regression.

### Build and artifact contract

After the full suite had generated local test caches:

```text
python -m build
Successfully built ai_profile_cli-0.4.7.tar.gz and
ai_profile_cli-0.4.7-py3-none-any.whl

python -m twine check <dist>/*
PASSED

python scripts/check_release_artifacts.py \
  --dist-dir <dist> --expected-version 0.4.7
PASS: artifact contract for ai-profile-cli 0.4.7

forbidden/private/generated/traversal members: 0
```

The first Ubuntu candidate run failed closed against the deliberately stale
v0.4.6 digest and revealed the canonical v0.4.7 wheel digest. After that
digest was pinned consistently, run 30535142355 retained:

```text
ai_profile_cli-0.4.7-py3-none-any.whl
ai_profile_cli-0.4.7.tar.gz
SHA256SUMS
```

Independent download verification confirmed the wheel digest, both license
notices, metadata/version parity, checksum manifest, one archive root, and
zero forbidden members. The preliminary retained sdist had 155 members.
Because these promotion reports are themselves sdist members, that
preliminary sdist is discarded after this report commit; the final CI run
must retain and re-verify the rebuilt pair after the last tracked edit.

The wheel release smoke installed non-editably into a clean venv, confirmed
version 0.4.7, completed `init`, `scan`, `aggregate`, and `render`, produced
all eight files, enforced a network-closed dashboard CSP, found zero canary
hits, and reproduced every byte on a second render.

### CI and cross-platform onboarding

Run 30535142355 passed:

- release-candidate build and exact pinned wheel verification;
- Python 3.11, 3.12, 3.13, and 3.14 full suites;
- Ubuntu Python 3.12 clean-wheel onboarding;
- Windows Python 3.12 clean-wheel onboarding;
- macOS Python 3.12 clean-wheel onboarding.

All onboarding jobs downloaded the retained candidate artifact; none rebuilt
a platform-specific wheel.

### README-only dogfood

[promotion-dogfood.md](promotion-dogfood.md) records:

- newcomer: install through render, 8/8 deterministic files, 224 privacy
  comparisons with zero hits;
- privacy: all three publication modes, exact four-commit exclusion delta,
  558 primary plus 27 exclusion comparisons with zero hits;
- multi-provider: one unique AI commit, two actor presences, Claude 1,
  OpenAI 1, human 1, unknown 1, exact dashboard filters;
- Profile publisher: all eight files, mobile/theme embeds, Pages main/root
  dry run, deterministic rerender, zero canary hits.

No role read source/tests/scripts or required an outside-README product
instruction.

### Staging, browser, and visual quality

Staging workflow run
[30535224447](https://github.com/WenyuChiou/ai-profile/actions/runs/30535224447)
passed its unprivileged build and exact-byte transfer job. Its manifest
contained:

```text
package_version     0.4.7
wheel_sha256        75b896c7a1bfa462d1caa6df7025bca79650e8ad48a006272e76eb9bfb5667d8
dashboard_sha256    17f2627e60c42a008e20af583af4cd51ca9a0814773163df5c5d1ec4982af192
```

The deployment job executed no project code and was rejected before deploy
because the `github-pages` environment allows only `main`. This protection
remains unchanged.

The exact transferred dashboard passed the local Playwright gate:

```text
assertions: 13
pass:       13
fail:       0
unscored:   0
```

Verified:

- no horizontal overflow at 320, 390, 768, or 1440 CSS pixels;
- no overflow at 200% scale;
- automatic, light, dark, and system theme behavior;
- pointer, Enter, and Space provider filtering;
- exact hero, actor-presence, active-day, and all 32 calendar-label values;
- visible focus on all seven Tab stops;
- reduced-motion behavior;
- normal text at least 4.5:1 and large text/meaningful marks at least 3:1;
- selection conveyed by text and semantic state, not color alone.

The v0.4.6 visual system remains byte-identical: restrained ice-blue and
warm-yellow surfaces, dark-indigo contrast, local commercially usable IBM
Plex fallbacks, adjacent provider names/icons, and no downloaded fonts.

## Findings and dispositions

| Severity | Description | Impact | Recommendation | Disposition |
| --- | --- | --- | --- | --- |
| Medium | Fine-pointer calendar day controls remain approximately 13×13 CSS px with about 4.5px gaps, below WCAG 2.2's 24px target-size/spacing criterion. | Users with motor impairments have a smaller-than-preferred pointer target. | Enlarge the hit area without changing calendar data density and add a browser assertion. | Accepted for Public Beta: coarse-pointer spacing and complete keyboard/focus operation provide alternatives. Owner: maintainer, v0.5 visual follow-up. |
| Medium | The tag workflow rebuilds the deterministic sdist from the identical source commit rather than comparing it to a pre-tag sdist digest. A tracked digest would be self-referential because this report is inside the sdist. | A pre-tag versus tag-build drift would be caught before upload by artifact checks but not by a stored pre-tag digest comparison. | Future releases should promote an immutable CI bundle or store a signed digest outside the source archive. | Accepted for Public Beta if the final post-report CI bundle is verified, no tracked edits follow, and the tag workflow retains/uploads one checked pair. |
| Low | Singular histories produce plural grammar in two dashboard explanatory sentences. | Cosmetic polish issue for one-commit histories. | Add count-aware copy with renderer tests. | Accepted to preserve the artifact-only boundary. |
| Low | README-only users may not immediately derive evidence-record and active-AI-day semantics. | Initial hand calculation can differ, though CLI labels and data remain accurate. | Add a metric glossary. | Accepted documentation follow-up. |
| Low | Pinned artifact actions emit Node runtime deprecation annotations. | No current failure or byte-integrity effect; future runner changes may require maintenance. | Update to reviewed action SHAs that use the current Node runtime. | Accepted dependency-maintenance item. |

## Severity summary

| Severity | Unresolved blocker | Explicitly accepted |
| --- | ---: | ---: |
| Critical | 0 | 0 |
| High | 0 | 0 |
| Medium | 0 | 2 |
| Low | 0 | 3 |

## Release authorization

Before tag or publication, all of the following must complete:

1. commit these final promotion reports;
2. run final CI and independently verify the rebuilt retained sdist after
   that last tracked edit;
3. merge through protected `main`;
4. deploy `/v0.4.7/` from `main` and replay the 13/13 browser gate against
   the public URL;
5. make no further tracked source edits before tagging.

The tag workflow must then build once, validate and retain one wheel/sdist
pair, pass all three platform onboarding jobs, upload those exact bytes, and
verify PyPI and GitHub Release digests. Any mismatch, cache/private member,
privacy leak, or live failure cancels authorization.

## Final verdict

**GO WITH CONDITIONS**

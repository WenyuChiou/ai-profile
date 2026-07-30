# v0.4.6 Public Beta promotion re-run (R5) evaluation specification

Status: frozen before any R5 evidence
Frozen on: 2026-07-30
Target: `ai-profile-cli` 0.4.6 Public Beta

This is the complete promotion contract for the fifth v0.4.6 evaluation.
It is committed before any R5 CI, dogfood, staging, browser, or readiness
evidence exists. After this commit the file must remain byte-identical.
Any candidate-byte change requires another pre-registration and fresh
affected gates. Thresholds may not be weakened within R5.

## Candidate identity

Every R5 gate scores exactly this candidate:

- Package version: `0.4.6`
- Implementation source commit:
  `3f77aa1c29222fa4ce95adc076f5ddc32535640b`
- Canonical build platform: GitHub-hosted `ubuntu-latest`, Python 3.12
- Wheel: `ai_profile_cli-0.4.6-py3-none-any.whl`
- Wheel SHA-256:
  `84aa13766c70ad082fe70e4e860f2b15f77472826abbc579531376d5cdc4bcdb`
- Frozen `SOURCE_DATE_EPOCH`: `1785024000`
- Synthetic staging dashboard SHA-256:
  `17f2627e60c42a008e20af583af4cd51ca9a0814773163df5c5d1ec4982af192`

Evidence from any other bytes scores nothing. A canonical rebuild with a
different digest invalidates this specification.

## Why R4 failed

R4 dogfood found that a daily cell containing one unique commit with two
providers produced the accessible phrase `peak day 2 attributed commits`.
The calendar's approved ADR-018 intensity unit is the sum of per-provider
attributed-commit counts, which may overlap; the phrase could be mistaken
for the all-provider unique-commit unit. R4 therefore failed Gate D.

The R5 remediation keeps ADR-018's data and rendering semantics but names
the unit and overlap caveat explicitly. The same remediation also:

- synchronizes the standalone brand-vendoring contrast surfaces with the
  runtime themes and adds an automated parity regression; and
- separates unprivileged staging build work from Pages/OIDC deployment,
  transfers only an exact non-symlink tree, and re-verifies pinned dashboard
  plus canonical manifest bytes in the privileged job.

The discovery run intentionally failed closed against the invalid R4 wheel
pin and independently produced the R5 digest above. No R4 result carries
forward.

## Gate P — package, test, and CI checks

1. `python -m pytest tests -p no:cacheprovider`,
   `python -m ruff check src tests scripts`, and
   `python scripts/check_readme_parity.py` pass with observed counts.
   Existing tests may not be deleted or weakened.
2. Both sanctioned snapshot regeneration commands are byte-stable:
   `python tests/unit/test_render_summary.py` and
   `python tests/unit/test_heatmap_svg.py`.
3. The multi-provider regression proves one unique AI commit, two provider
   counts, and accessible wording that never presents the provider sum as a
   unique-commit count.
4. The vendoring-tool background mirrors equal runtime theme backgrounds.
5. The staging workflow has exact permission maps: workflow `{}`, build
   `{contents: read}`, deploy `{pages: write, id-token: write}`. The deploy
   job performs no checkout, package installation, build, or project-code
   execution and accepts only the exact pinned two-file tree.
6. Twine, the artifact contract, and clean-wheel release smoke pass against
   the pinned wheel. Wheel and sdist contain `LICENSE` and
   `THIRD_PARTY_NOTICES.md`.
7. Candidate-PR CI is green: Python 3.11–3.14 pass, one canonical candidate
   bundle is retained, and Ubuntu, Windows, and macOS onboarding jobs
   download, verify, install, and smoke that exact wheel with Python 3.12.

## Gate D — fresh four-role dogfood

Run the newcomer, privacy, multi-provider, and Profile-publisher roles from
scratch. Each role may read only `README.md` and the pinned wheel, uses a
fresh repository, venv, and task-specific `AIPROFILE_HOME` outside every Git
worktree, and records commands, exit codes, stderr, elapsed time, and
friction.

Pass requires 4/4 roles, zero installation failures, zero external
orchestrator product hints, zero configuration/privacy/Pages dead ends, zero
canary hits, exact hand-derived aggregate matches, and both summary SVGs
using the honest overlap-qualified daily unit.

## Gate S — staging integrity

The manual-only `staging-preview` workflow must:

1. run build/render/package installation only in the unprivileged build job;
2. reproduce the pinned wheel and dashboard digests;
3. transfer exactly:
   `v0.4.6/dashboard.html` and `v0.4.6/staging-manifest.json`;
4. reject a symlinked root, nested symlinks, or any additional entry;
5. re-verify the canonical manifest bytes and pinned dashboard digest in the
   Pages/OIDC job before upload; and
6. deploy to
   `https://wenyuchiou.github.io/ai-profile/v0.4.6/dashboard.html`.

The served manifest, served dashboard, and an independent render from the
retained wheel must be byte-consistent. The fixture is synthetic.

## Gate B — browser matrix

Run every assertion against the Gate-S-verified public bytes:

- 320, 390, 768, and 1440 CSS-pixel viewports with no document overflow;
- 200% browser-scale rendering with a 720 CSS-pixel layout viewport on a
  1440 physical-pixel surface at device scale 2;
- light, dark, and system themes;
- pointer plus keyboard Enter/Space provider filtering with exact aggregates;
- visible focus on every Tab stop and reduced-motion behavior;
- normal text contrast at least 4.5:1;
- large text and meaningful marks at least 3:1 against the actual adjacent
  background; and
- semantic/text selection state, never color alone.

Retain measurements and screenshots. Any unexecuted assertion is UNSCORED
and blocks GO.

## Gate R — published-release checks

Only after a GO verdict: publish the exact retained canonical bytes under
`docs/RELEASING.md`. PyPI and the GitHub Release must serve the retained
wheel/sdist digests. Refresh the maintainer Profile only after the live
package passes its clean-install verification.

## Verdict rule

The final verdict is exactly one of `GO — PUBLIC BETA`,
`GO WITH CONDITIONS`, or `NO-GO`.

- Any failed gate, unresolved Critical/High finding, or UNSCORED browser
  assertion forces `NO-GO`.
- Every Medium finding must be fixed or explicitly accepted with owner,
  rationale, and follow-up before a GO form.
- `GO WITH CONDITIONS` may attach only conditions outside Gates P, D, S,
  and B.
- The release may be described only as Public Beta, never Stable or GA.

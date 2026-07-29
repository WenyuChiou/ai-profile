# v0.4.6 Public Beta promotion re-run (R2) evaluation specification

Status: frozen before any R2 evidence
Frozen on: 2026-07-29
Target: `ai-profile-cli` 0.4.6 Public Beta

This file is the complete, version-aligned promotion contract for the
second (R2) v0.4.6 promotion evaluation. It is committed before any R2
dogfood, staging, or browser evidence exists. After this commit the file
must remain byte-identical; any later change invalidates all evidence
collected against the earlier bytes and requires every affected gate to be
rerun. Pass thresholds may not be weakened within the v0.4.6 R2 round.

`docs/reviews/promotion-eval-spec.md` is the immutable historical v0.4.2
evaluation baseline and is intentionally not changed. Its protocol
definitions are incorporated by reference where this file says so; this
file is the v0.4.6 R2 pre-registration and the only specification R2
evidence may cite.

## Candidate identity

Every R2 gate scores exactly this candidate:

- Package version: `0.4.6`
- Implementation source commit:
  `25ea364b3ca7f6a7b8898a901fa6cda2c64cd373`
- Wheel: `ai_profile_cli-0.4.6-py3-none-any.whl`
- Wheel SHA-256:
  `26227c0435d2d6a80ff8a46ad878270509b2cadeeb6d0dd78555019884239d8a`
- Frozen `SOURCE_DATE_EPOCH`: `1785024000`
  (`docs/reviews/promotion-candidate.json`)

Evidence produced from any other bytes — including the previously deployed
public v0.4.5 dashboard — scores nothing. If the candidate is rebuilt to a
different digest, this specification is invalidated and a new
pre-registration must be committed before new evidence is collected.

## Prior evidence does not carry over

The R1 reports (`promotion-dogfood.md` and
`promotion-readiness-review.md`, 2026-07-27) predate this specification
and ended in NO-GO with two open High findings. They are historical
context only. No R1 dogfood, review, or browser observation may be
counted toward any R2 gate; every gate below requires fresh evidence
generated after this file's commit.

## Gate P — package, test, and CI checks

1. `python -m pytest tests -p no:cacheprovider`,
   `python -m ruff check src tests scripts`, and
   `python scripts/check_readme_parity.py` pass with observed counts
   recorded. Existing tests may not be deleted or weakened.
2. Both sanctioned snapshot regeneration commands produce zero drift
   (`git diff --exit-code -- tests/snapshots docs/assets`).
3. `scripts/check_release_artifacts.py` passes against version `0.4.6`
   and the pinned wheel SHA-256 above; Twine validation passes; wheel and
   sdist contain `LICENSE` and `THIRD_PARTY_NOTICES.md`.
4. `scripts/release_smoke.py` against the pinned wheel reports eight
   outputs, a network-closed CSP dashboard, byte-identical repeated
   renders, and zero privacy-canary hits.
5. CI on the candidate PR head is green: `Release candidate build`,
   `Python 3.11`–`3.14`, and wheel onboarding on Ubuntu, Windows, and
   macOS with Python 3.12.

## Gate D — fresh four-role dogfood

The four roles, isolation rules, README-only constraint, and pass criteria
are exactly those of the v0.4.2 specification's "Dogfood protocol" and
"Dogfood pass criteria" sections, rerun from scratch against the pinned
wheel above. Each role uses a fresh temporary repository, virtual
environment, and `AIPROFILE_HOME`, and records commands, exit codes,
stderr, elapsed time, and friction. Prior R1 role reports do not count.
Pass requires 4/4 roles, zero installation failures, zero configuration or
privacy dead ends, zero canary hits, exact hand-derived aggregate matches,
and zero Pages publishing dead ends.

## Gate S — staging integrity

The manually dispatched `staging-preview` workflow
(`.github/workflows/staging-preview.yml`) rebuilds the candidate wheel with
the frozen `SOURCE_DATE_EPOCH`, verifies the pinned digest, installs the
exact built wheel into a fresh venv, renders the fixed synthetic
public-only fixture through the installed renderer
(`scripts/render_staging_dashboard.py`), and deploys only the staging
directory. The browser URL is:

`https://wenyuchiou.github.io/ai-profile/v0.4.6/dashboard.html`

with `staging-manifest.json` beside it. As of this freeze the workflow has
never been triggered and no Pages site is claimed to be configured or
deployed; configuration and dispatch happen only after this
pre-registration is pushed and reviewed.

Staging-manifest hash comparison — all three must hold before any browser
evidence is scored:

1. The served `staging-manifest.json` reports `package_version` `0.4.6`
   and `wheel_sha256` equal to the pinned candidate digest above.
2. The SHA-256 of the served `dashboard.html` bytes equals the manifest's
   `dashboard_sha256`.
3. An independent local run of `scripts/render_staging_dashboard.py`
   against the pinned wheel reproduces the identical `dashboard_sha256`.

The staging fixture is synthetic; the staging page is presentation and
accessibility evidence only and asserts nothing about any real profile.

## Gate B — browser matrix

All checks run against the staging URL above, on the exact bytes verified
by Gate S:

- viewports 320, 390, 768, and 1440 CSS pixels with zero document-level
  horizontal overflow at each;
- 200% zoom with zero horizontal overflow;
- light, dark, and system theme modes;
- provider filter activation by pointer AND by keyboard (Tab to the
  control, activate with Enter and with Space), with the filtered
  headline, calendar, and provider states updating correctly;
- visible focus indication on every interactive control reached by Tab;
- reduced-motion behavior honored;
- normal text contrast at least 4.5:1; large text and meaningful marks at
  least 3:1; selection never conveyed by color alone.

Every assertion above must be executed and scored against the staging
URL. Any assertion the browser target cannot execute is recorded as
UNSCORED, and any UNSCORED assertion blocks GO. Substituting a different
artifact, a local file, or a local server for the staging URL scores
nothing.

## Gate R — published-release checks

Only if promotion proceeds: publish the exact pinned bytes per
`docs/RELEASING.md`; PyPI and the GitHub Release must serve digests
matching the pinned wheel SHA-256 and the retained sdist digest; the
maintainer Profile refresh follows only after the package gates pass.
These checks are sequenced after the verdict and cannot compensate for
any failed or UNSCORED earlier gate.

## Verdict rule

The final verdict is exactly one of `GO — PUBLIC BETA`,
`GO WITH CONDITIONS`, or `NO-GO`, and may be issued only after Gates P,
D, S, and B are fully scored:

- any failed gate, any unresolved Critical or High finding, or any
  UNSCORED browser assertion forces `NO-GO`;
- every Medium finding must be fixed or explicitly accepted with owner,
  rationale, and follow-up before any `GO` form;
- `GO WITH CONDITIONS` may attach only conditions that do not touch
  Gates P, D, S, or B;
- the release may be described only as Public Beta, never Stable.

The R2 readiness report must record this file's commit hash, the exact
digests it verified, and a disposition for every finding.

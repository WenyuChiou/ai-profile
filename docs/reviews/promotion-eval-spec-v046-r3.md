# v0.4.6 Public Beta promotion re-run (R3) evaluation specification

Status: frozen before any R3 evidence
Frozen on: 2026-07-30
Target: `ai-profile-cli` 0.4.6 Public Beta

This is the complete, version-aligned promotion contract for the third
v0.4.6 evaluation. It is committed before any R3 dogfood, staging, browser,
or readiness evidence exists. After this commit the file must remain
byte-identical. Any candidate-byte change requires a new pre-registration
and a fresh run of every affected gate. Thresholds may not be weakened
within R3.

The historical v0.4.2 and v0.4.6 R2 specifications remain immutable. Their
protocol definitions are incorporated only where this file says so; no
earlier result counts toward R3.

## Candidate identity

Every R3 gate scores exactly this candidate:

- Package version: `0.4.6`
- Implementation source commit:
  `27b02083a8f17107faaebce9aa4d9021529279bf`
- Wheel: `ai_profile_cli-0.4.6-py3-none-any.whl`
- Wheel SHA-256:
  `94fe21b9ed3a763dd3ca57ababf5a1ce2a045409343d09e996cf5756a346b2a0`
- Frozen `SOURCE_DATE_EPOCH`: `1785024000`
  (`docs/reviews/promotion-candidate.json`)

Evidence from any other bytes scores nothing. A rebuild with a different
digest invalidates this specification.

## Prior evidence does not carry over

R1 and R2 ended before this candidate existed. Their dogfood, CI, staging,
browser, and readiness observations are historical context only. The R2
browser run that exposed the dark-mark contrast defect and the local
pre-check after its repair are defect-discovery evidence, not R3 gate
evidence.

## Gate P — package, test, and CI checks

1. `python -m pytest tests -p no:cacheprovider`,
   `python -m ruff check src tests scripts`, and
   `python scripts/check_readme_parity.py` pass with observed counts
   recorded. Existing tests may not be deleted or weakened.
2. Both sanctioned snapshot regeneration commands produce zero drift:
   `python tests/unit/test_render_summary.py`,
   `python tests/unit/test_heatmap_svg.py`, then
   `git diff --exit-code -- tests/snapshots docs/assets`.
3. Twine and `scripts/check_release_artifacts.py` pass against version
   `0.4.6` and the pinned wheel digest. Wheel and sdist both contain
   `LICENSE` and `THIRD_PARTY_NOTICES.md`.
4. `scripts/release_smoke.py` against the pinned wheel reports all eight
   outputs, a network-closed CSP dashboard, byte-identical repeated
   renders, and zero privacy-canary hits.
5. CI on the candidate PR head is green for the release-candidate build,
   Python 3.11–3.14, and wheel onboarding on Ubuntu, Windows, and macOS
   with Python 3.12.

## Gate D — fresh four-role dogfood

The four roles, isolation rules, README-only constraint, and pass criteria
are those of the v0.4.2 specification's dogfood protocol, rerun from
scratch against the pinned wheel. Each role uses a fresh repository, venv,
and task-specific `AIPROFILE_HOME` and records commands, exit codes,
stderr, elapsed time, and friction.

Pass requires 4/4 roles, zero installation failures, zero external
orchestrator hints, zero configuration or privacy dead ends, zero canary
hits, exact hand-derived aggregate matches, and zero Pages publishing
dead ends.

## Gate S — staging integrity

The manual-only `staging-preview` workflow rebuilds with the frozen epoch,
verifies the pinned digest, installs that wheel into a fresh venv, renders
the fixed synthetic public-only fixture through the installed package, and
deploys only the staging directory. The browser target is:

`https://wenyuchiou.github.io/ai-profile/v0.4.6/dashboard.html`

with `staging-manifest.json` beside it.

Before browser evidence is scored:

1. the served manifest reports package version `0.4.6` and the pinned wheel
   digest;
2. the served dashboard hash equals the manifest's dashboard hash; and
3. an independent local render from the pinned wheel reproduces that hash.

The fixture is synthetic and asserts nothing about a real profile.

## Gate B — browser matrix

Every assertion runs against the exact public staging bytes verified by
Gate S:

- viewports 320, 390, 768, and 1440 CSS pixels with zero document-level
  horizontal overflow;
- 200% browser-scale rendering with zero horizontal overflow; a 1440
  physical-pixel surface must expose a 720 CSS-pixel layout viewport at
  device scale 2;
- light, dark, and system theme modes;
- provider filters activated by pointer and by keyboard after Tab
  navigation, using both Enter and Space; headline, calendar, and provider
  states must update to the exact selected-provider aggregates;
- visible focus on every interactive control reached by Tab;
- `prefers-reduced-motion: reduce` honored;
- normal text contrast at least 4.5:1;
- large text and meaningful marks at least 3:1 against their actual
  adjacent computed background, including provider/share bars, evidence
  marks, provider icons, and active-calendar boundaries; and
- selection communicated by semantic state and text, not color alone.

The browser run must retain measurements and screenshots. Any assertion
the browser cannot execute is UNSCORED and blocks GO. A local file or local
server may be used only as a pre-check and scores nothing.

## Gate R — published-release checks

Only after a GO verdict: publish the exact pinned bytes according to
`docs/RELEASING.md`. PyPI and the GitHub Release must serve the pinned
wheel digest and the retained sdist digest. The maintainer Profile refresh
follows only after package gates pass.

## Verdict rule

The final verdict is exactly one of `GO — PUBLIC BETA`,
`GO WITH CONDITIONS`, or `NO-GO`, and requires Gates P, D, S, and B to be
fully scored:

- any failed gate, unresolved Critical or High finding, or UNSCORED browser
  assertion forces `NO-GO`;
- every Medium finding must be fixed or explicitly accepted with owner,
  rationale, and follow-up before a GO form;
- `GO WITH CONDITIONS` may attach only conditions outside Gates P, D, S,
  and B; and
- the release may be described only as Public Beta, never Stable or GA.

The R3 readiness report records this specification's commit, the exact
digests verified, and every finding's disposition.

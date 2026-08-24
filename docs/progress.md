# Progress — current snapshot

Concise state of the project (G2-20: history lives in
`docs/reviews/v0.1-run-log.md`; future scope lives in `docs/ROADMAP.md`,
which is authoritative).

## v0.8.1 final immutable public caller repin — commit E (codex/v081-public-caller-e)

- PR #42 (commit D `18fb08eb6bca4fac6cb4cd1058cc7641452e7bf3`) passed 8/8 checks and merged to
  `main` as `ba888908f695deb44f5166f3783be0043e1d2e2d`, upgrading `actions/download-artifact`
  to verified Node 24 v8.0.1 across all first-party workflows while keeping `ai-profile-cli==0.8.1`.
- Commit E completes the final immutable caller contract repin: repins
  `docs/templates/profile-refresh-caller.yml`, `README.md`, `README.zh-TW.md`,
  and `docs/decisions/ADR-030-automation-layer.md` from `9c246d95052264c24e7175cabd295951c5236efc`
  to immutable commit D `18fb08eb6bca4fac6cb4cd1058cc7641452e7bf3` (`ai-profile-cli==0.8.1` +
  `upload-artifact` v7.0.1 Node 24 + `download-artifact` v8.0.1 Node 24).
- `scripts/check_readme_parity.py` and `tests/unit/test_readme_parity.py` assert the
  commit D token and bilingual parity; `tests/unit/test_profile_refresh_workflow.py`
  asserts `COMMIT_D` (`18fb08eb6bca4fac6cb4cd1058cc7641452e7bf3`), verifies caller template
  and published-sha validation, and forbids stale commit B (`9c246d9`), commit A (`6a39ff4`),
  v0.8.0, and v0.7.0 pins.
- Rebuilt the unpublished `0.8.2` development candidate wheel using the exact GitHub Actions runtime
  from official actions/python-versions release 3.12.14-31661455385 (Ubuntu 24.04 x64 CPython 3.12.14
  toolcache, `build==1.4.3`, `hatchling==1.31.0` isolation, `SOURCE_DATE_EPOCH=1786320000`, clean
  `origin/main` archive plus staged diff), updating `docs/reviews/promotion-candidate.json` to the
  final candidate digest `284779ed60cf1c57fcd55b15158ab16526e7c0b26174168bbc939c84569cdbe7`.
- Maintainer Profile repin to commit D and profile-refresh execution remains outstanding.
- Local evidence: focused test suites (workflow, parity, staging preview, release contract,
  scheduler CLI, launcher, recruiter card) all PASS (171 passed, 16 skipped);
  `check_readme_parity.py` PASS; `python -m ruff check src tests scripts` clean;
  `git diff --check` clean; `check_release_artifacts.py` PASS.

## Node 24 workflow maintenance: download-artifact v8.0.1 upgrade (codex/v081-download-artifact-v8)

- Post-merge `e6a2176c3815a03df40f7039f78feb1ff6b88400` (PR #41 commit C): GitHub Profile run
  `32686342501` passed, but emitted the remaining forced-Node24 warning because all first-party
  workflows still pinned `actions/download-artifact` v4.3.0 (`d3f86a106a0bac45b974a628896c90dbdf5c8093`, Node 20).
- Upgraded `actions/download-artifact` across all four first-party workflows (`ci.yml`, `profile-refresh.yml`,
  `publish.yml`, and `staging-preview.yml`) to official latest verified immutable v8.0.1
  (`3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`, Node 24). The live Profile still pins pre-D commit
  `9c246d9`, so the warning disappears only after this change is merged and the Profile caller is
  repinned to the resulting immutable workflow commit.
- Preserved all workflow inputs, permissions, step names, artifact paths, merge behavior, secrets, package versions,
  outputs, and security/artifact semantics without drift.
- Exact-pin workflow test suites updated red-first: `tests/unit/test_profile_refresh_workflow.py` and
  `tests/unit/test_staging_preview.py` proved failing against the v4.3.0 baseline, green after upgrade.
- No README, schema, version, manifest, or renderer changes; unpublished `0.8.2` development candidate wheel
  digest `a6c64bc9d504518743e3811e9a1314310f25275db802f367e944799af1f9d81a` remains unchanged.
- Local evidence: focused test suites (workflow, parity, staging preview, release contract,
  scheduler CLI, launcher, recruiter card) all PASS (171 passed, 16 skipped);
  `check_readme_parity.py` PASS; `python -m ruff check src tests scripts` clean;
  `git diff --check` clean.

## v0.8.1 final immutable public caller repin — commit C (codex/v081-public-caller-c)

- Post-release commit B `9c246d95052264c24e7175cabd295951c5236efc` merged to `main`
  as `da4c08eb52cf6ccdb57c21894e268cc856bd599f` (PR #40), maintaining `ai-profile-cli==0.8.1`
  and upgrading `actions/upload-artifact` to verified Node 24 v7.0.1.
- Commit C completes the final immutable caller contract repin: repins
  `docs/templates/profile-refresh-caller.yml`, `README.md`, `README.zh-TW.md`,
  and `docs/decisions/ADR-030-automation-layer.md` to immutable commit B
  `9c246d95052264c24e7175cabd295951c5236efc` (`ai-profile-cli==0.8.1` + `upload-artifact` v7.0.1).
- `scripts/check_readme_parity.py` and `tests/unit/test_readme_parity.py` assert the
  commit B token and bilingual parity; `tests/unit/test_profile_refresh_workflow.py`
  asserts `COMMIT_B` (`9c246d95052264c24e7175cabd295951c5236efc`), verifies caller template
  and published-sha validation, and forbids stale commit A (`6a39ff4`), v0.8.0, and v0.7.0 pins.
- Rebuilt the unpublished `0.8.2` development candidate wheel using the exact GitHub Actions runtime
  from official actions/python-versions release 3.12.14-31661455385 (Ubuntu 24.04 x64 CPython 3.12.14
  toolcache, `build==1.4.3`, `hatchling==1.31.0` isolation, `SOURCE_DATE_EPOCH=1786320000`, clean
  `origin/main` archive plus staged diff), updating `docs/reviews/promotion-candidate.json` to the
  final candidate digest `a6c64bc9d504518743e3811e9a1314310f25275db802f367e944799af1f9d81a`.
- Local evidence: focused test suites (workflow, parity, staging preview, release contract,
  scheduler CLI, launcher, recruiter card) all PASS (171 passed, 16 skipped);
  `check_readme_parity.py` PASS; `python -m ruff check src tests scripts` clean;
  `git diff --check` clean; `check_release_artifacts.py` PASS.

## v0.8.1 public caller contract & upload-artifact v7.0.1 upgrade — commit B (codex/v081-public-caller-b)

- Post-release commit B completes the v0.8.1 hosted pin: repins the public
  caller contract to immutable commit A `6a39ff46e2716f2c30385c53419b6b25c2790ec5`,
  which merged to `main` as `8b8a543aa43281bb554daf4d0245ee63bfe8cd8c` (PR #39).
  The maintainer Profile pinned to commit A, refreshed successfully, deployed
  Pages, and a second no-change run verified idempotency at the same SHA.
- `docs/templates/profile-refresh-caller.yml` now pins `uses:` to commit A
  `6a39ff46e2716f2c30385c53419b6b25c2790ec5` and hardcodes `ai-profile-cli==0.8.1`.
  `README.md` and `README.zh-TW.md` state the commit A SHA with `ai-profile-cli==0.8.1`;
  `scripts/check_readme_parity.py` and `tests/unit/test_readme_parity.py` verify
  bilingual contract parity; `tests/unit/test_profile_refresh_workflow.py` asserts
  `COMMIT_A`, the `ai-profile-cli==0.8.1` contract, and forbids stale v0.8.0/v0.7.0
  pins.
- Upgraded `actions/upload-artifact` from v4.6.2 (`ea165f8d65b6e75b540449e92b4886f43607fa02`,
  Node 20) to official verified immutable v7.0.1 (`043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`,
  Node 24) across all four first-party workflows (`ci.yml`, `profile-refresh.yml`,
  `publish.yml`, `staging-preview.yml`), resolving the Node 20 deprecation warning
  surfaced in GitHub run 32681870707 while preserving all workflow inputs,
  permissions, and security semantics. Workflow pin test suites updated.
- Staging-preview checkout remediation: `.github/workflows/staging-preview.yml`
  build job now pins `ref: 49e574b0ce80eef14cf38a20b654d03e9a50538c` (the immutable
  v0.8.1 release commit on `main`), ensuring manual staging runs from `main` check
  out and verify the published v0.8.1 release rather than unreleased development bytes
  from moving `main` HEAD. Guarded by regression test in `tests/unit/test_staging_preview.py`.
- Wheel-digest lifecycle resolution: editing `README.md` changes `project.readme`
  and therefore wheel `METADATA`. Released v0.8.1 must stay pinned to its canonical
  published digest (`1faceac31ac7d9c3a99e3e4678bdfb725f73341e89e5847dc6a578ed8a6bbff9`)
  in `RELEASED_WHEEL_SHA256["0.8.1"]` without authorizing a second 0.8.1 wheel or
  weakening the released-digest guard. The smallest sound coherent transition is to
  advance the development version to `0.8.2` in `pyproject.toml`,
  `src/aiprofile/__init__.py`, and `SCHEDULER_VERSION` (readers accept v0.7.0–v0.8.2,
  writers emit 0.8.2; ADR-030 and architecture.md updated). `docs/reviews/promotion-candidate.json`
  authorizes the candidate wheel digest
  `483ad35b14655d275a249c680a75f830f09b3d1920a59280350c7a0cf3128fb7` for `0.8.2`
  (unpublished development candidate; independently reproduced by Codex with exact CI tooling).
- Local evidence: focused test suites (workflow, parity, staging preview, release
  contract, scheduler CLI, launcher, recruiter card) all PASS (171 passed, 16 skipped);
  `check_readme_parity.py` PASS; `python -m ruff check src tests scripts` clean;
  `git diff --check` clean.

## v0.8.1 Collaboration Pulse candidate — built and verified locally

- Branch `codex/v081-collaboration-pulse` from `6b5511d` (main, released
  v0.8.0). Summary-card-only redesign (ADR-032): the 84-cell 12-week matrix
  becomes a static pulse signature — 84 chronological oldest-to-newest 6px
  marks in 12 groups of seven with a wider structural group gap, neutral
  pulse height 12/24/36/48px over the shared total-commit bins, accent fill
  rising from the baseline to 0/25/50/75/100% of pulse height over the
  shared AI-share bins, 2px baseline ticks for no-activity dates,
  month-boundary labels retained, weekday labels and quarter rails removed,
  direct one-line legend, `<desc>` stating window/peak/encodings/scope.
  Dashboard, heatmap card, and badge unchanged; heatmap and badge snapshot
  families byte-identical; `VizStats`, ACE `0.3.0`, CLI, privacy, and the
  eight outputs untouched. Presentation-only version bump to 0.8.1;
  scheduler metadata tracks the package (readers accept v0.7.0–v0.8.1).
- Candidate wheel `ai_profile_cli-0.8.1-py3-none-any.whl`: the canonical
  digest is `1faceac31ac7d9c3a99e3e4678bdfb725f73341e89e5847dc6a578ed8a6bbff9`
  — CI's clean Ubuntu/Python 3.12 build at commit `60a0701` and an
  independent clean WSL Ubuntu clone of the same commit are byte-equal at
  `SOURCE_DATE_EPOCH=1786320000`. The earlier `d525eef3…` pin was a
  Windows-built diagnostic artifact and is REJECTED as release evidence:
  it differs in platform ZIP metadata and carries Windows CRLF bytes for
  the untouched `src/aiprofile/render/brand.py`, exactly the substitution
  `docs/RELEASING.md` forbids ("the canonical release bundle is a clean
  Ubuntu build"). PR #38 first CI run `32678706758`: Python 3.11–3.14 all
  passed; the release-candidate build failed on the wrong-platform pin
  (the artifact contract working as designed) and wheel onboarding was
  skipped pending this repin. `docs/reviews/promotion-candidate.json` now
  authorizes `1faceac3…`; the published v0.8.0 digest `9cc06f20…` joined
  `RELEASED_WHEEL_SHA256` (closing the documented post-release drift gap).
- Local evidence (2026-08-23): red-first pulse contract tests in
  `tests/unit/test_calendar_band.py` / `test_recruiter_card.py` /
  `test_signal_console.py`; summary snapshot family and README sample
  assets regenerated only via `python tests/unit/test_render_summary.py`
  with zero residual drift on rerun; Windows Python 3.14 full suite
  **981 passed, 30 skipped**; Ruff and bilingual README parity clean;
  `git diff --check` clean. Visual QA (synthetic sparse + real maintainer
  aggregate, light/dark, 830/664px, 1x/2x): `docs/reviews/v0.8.1-visual-qa.md`.
- Independent Codex staged-diff review round 1 (fingerprint `eac24546…`):
  REQUEST CHANGES — three findings (scheduler-version doc parity, stale
  commit-B status, DESIGN.md wording), all dispositioned red-first where
  testable; the visual-QA record and the review-disposition section were
  added in the same round as additional completion evidence, not reviewer
  findings; see the v0.8.1 section of
  `docs/reviews/gate-disposition.md`. Still open:
  targeted Codex recheck, green CI on the candidate commit, merge, tag,
  PyPI, staging deploy, Profile refresh.

## v0.8.0 hosted workflow pin — commits A and B merged

- Commit A (`d74a3ef`, PR #36) upgraded the hosted package contract: the
  reusable `.github/workflows/profile-refresh.yml` installs exactly
  `ai-profile-cli==0.8.0` from PyPI, and the workflow test suite pins that
  literal. PR CI run `32664943030` and main CI run `32664998531` each passed
  all eight jobs, and `d74a3ef` is an ancestor of `origin/main` (`5b60156`).
- Commit B (branch `codex/v080-hosted-pin-b`) repins the public caller
  contract to immutable commit A
  `d74a3efdf27310162fc8c54b29b8e2782ea66b46`: the caller template
  `docs/templates/profile-refresh-caller.yml`, the test-suite `COMMIT_A`
  constant, both README guides, and ADR-030 now state that SHA with
  `ai-profile-cli==0.8.0`. Historical v0.7.0 release records and plan
  evidence are unchanged. Commit B merged as PR #37: main run `32667422511`
  passed green at merge commit `6b5511d`, the v0.8.1 branch baseline. The
  maintainer Profile repository is owned by Codex, separately.
- Commit B moves the current candidate wheel digest, because the README is
  `project.readme` and therefore wheel `METADATA`. PR #37 run `32665735830`
  passed Python 3.11-3.14 but failed the release-candidate build: the build
  produced `e1f869a9ed59ab5bc3d35867bf6d0915b740bd8d6d6394713502e3c81a34d8f7`
  while `docs/reviews/promotion-candidate.json` still authorized the released
  v0.8.0 wheel. Two clean Ubuntu 24.04 git-clone builds (Python 3.12.3,
  hatchling 1.31.0, build 1.4.3, `SOURCE_DATE_EPOCH=1786320000`) reproduce
  `e1f869a9...` byte-identically at commit B, and the same command at commit A
  still reproduces `9cc06f20...`; the only differing wheel members between the
  two are `METADATA` and `RECORD`, and the only `METADATA` change is the caller
  pin paragraph. The manifest now authorizes the commit-B digest so CI builds
  what the branch actually contains.
- The published v0.8.0 wheel digest
  `9cc06f2052a642bd198fa00d728c75b72fce061dad24c51b72feddf84b07c89e` is
  unchanged everywhere it records history: the gate review, the gate
  disposition, and the manual `staging-preview.yml` pins. Those describe the
  released artifact, not the branch, so `tests/unit/test_staging_preview.py`
  now asserts the manifest digest and the workflow pin separately instead of
  for equality. The dashboard digest is still asserted equal, because it is
  renderer output and the renderers are untouched. Consequence to carry
  forward: a manual staging-preview run from `main` after commit B merges will
  rebuild `e1f869a9...` and fail its `9cc06f20...` pin, so the next candidate
  must re-pin that workflow (or read the manifest) before staging is used
  again.
- Second consequence, recorded so it is not mistaken for an oversight:
  `RELEASED_WHEEL_SHA256` in `tests/unit/test_release_workflow_contract.py`
  is the guard added after PR #34 to make post-release byte drift a test
  failure, and it deliberately does not list `0.8.0`. Listing the published
  digest there would force the manifest back onto it and permanently red the
  `ci.yml` candidate job, which rebuilds and compares against that same
  manifest. For v0.8.0 that guard was therefore inactive, and the real fix
  was the next version bump: a post-release commit that changes
  wheel-affecting files (the README is `project.readme`) should carry a new
  version rather than re-authorize the released one. The v0.8.1 bump above
  closed this gap (`9cc06f20…` now sits in `RELEASED_WHEEL_SHA256`); the
  staging-preview pin above remains a v0.8.0 published-release record.

## v0.8.0 Signal Console — released 2026-08-23 (PyPI wheel digest `9cc06f20…`)

- Branch `codex/v080-signal-console` from `63c108d` (released v0.7.2 main).
  Coordinated redesign of the dashboard, summary card, heatmap card, and
  badge (ADR-031): compact status line that labels `generated_on` as a
  snapshot, four-cell core metric strip, provider toolbar, primary commit
  map, provider/evidence sidebar that stacks below 54rem, native `<details>`
  definitions, one token system for system/light/dark, transform/opacity-only
  motion off under reduced motion. Summary: status-line header, metric
  console strip, left-aligned 52px-cell matrix, 12px floor; heatmap: shared
  header, 11px floor; badge: canvas plate with the commit-node mark.
  `DESIGN.md`, `.impeccable.md`, README (both locales), CHANGELOG, schema
  status, architecture, ADR-030 read-set, staging workflow, and candidate
  manifest updated. ACE `0.3.0`, `VizStats`, aggregation, privacy, the eight
  outputs, CLI, and the hosted workflow pin are unchanged.
- Scheduler metadata tracks the package: readers accept v0.7.0–v0.8.0
  `installed_version`; reinstall writes v0.8.0.
- Local evidence (2026-08-23): red-first `tests/unit/test_signal_console.py`
  (17 tests) plus updated dashboard/summary/heatmap/release/scheduler
  contracts; Windows Python 3.14 full suite **977 passed, 30 skipped** with
  the candidate wheel digest pinned; Ruff, bilingual README parity, and
  `git diff --check` clean; summary and heatmap/badge snapshot families and
  README sample assets regenerated only through the sanctioned commands.
  `npx impeccable detect --json` on the rendered dashboard: `[]` (the v0.7.2
  page reported layout-transition, hero-eyebrow-chip, all-caps-body,
  gpt-thin-border-wide-shadow ×2, flat-type-hierarchy). Playwright evidence:
  `docs/reviews/v0.8.0-visual-qa.md`, screenshots under
  `.ai/v080-preview/` (task keep root, expires 2026-08-24).
- Candidate wheel digest, WSL suite counts, Twine/artifact/smoke/dogfood
  results: recorded in `docs/reviews/gate-disposition.md` once the clean
  Ubuntu git-clone build completed. Subsequently released: PyPI serves the
  v0.8.0 wheel digest `9cc06f20…` (pinned as published-release evidence in
  the staging-preview workflow and release contract tests). Staging deploy
  and maintainer Profile refresh on v0.8.0 are not recorded here — see the
  ROADMAP's remaining v0.8.0 checkbox.

## v0.7.2 scheduler remote-sync candidate — released 2026-08-23

- PR #34 (`codex/scheduler-remote-sync`, `afd01c0`) lets the scheduler
  launcher fast-forward a clean Profile checkout when the configured remote
  branch has advanced as a verified descendant of the captured local parent;
  dirty, rewound, deleted, diverged, and unstable remote states still fail
  closed, and a partial checkout failure restores branch, index, and
  worktree. Its first CI run (`32648197333`) passed Python 3.11–3.14 but the
  release-candidate build failed because the manifest still authorized the
  released v0.7.1 wheel while package bytes had changed.
- This candidate bumps the runtime, scheduler metadata, staging workflow,
  changelog, ADR-030, architecture, and schema status to v0.7.2; scheduler
  readers accept v0.7.0/v0.7.1/v0.7.2 `installed_version` and reinstall
  writes v0.7.2. ACE `0.3.0`, aggregation, `VizStats`, renderers, privacy
  policy, the hosted workflow pin, and the eight output names are unchanged.
  A new contract test pins released wheel digests so a manifest can never
  again carry a published digest for a different version.
- Local evidence (2026-08-23): Windows Python 3.14 full suite **960 passed,
  30 skipped**; focused release/staging/scheduler suites **129 passed, 4
  skipped**; WSL Ubuntu Python 3.12 full suite **984 passed, 6 skipped**.
  Ruff, bilingual README parity, and `git diff --check` are clean.
- Canonical candidate wheel digest (corrected 2026-08-23): the first Ubuntu
  double build reported `551e8dd6…4a44f7` and the manifest, staging
  workflow, and staging tests pinned it. GitHub Actions run 32657558104
  (PR #34, `refs/pull/34/merge` of `63cd0ae`) built the same tree at
  `SOURCE_DATE_EPOCH=1786320000` with hatchling 1.31.0 and observed
  `4f65ef450b9637e066cc9acdfba9cb1e688007e500179cb99a41c2a62dc6708f`, so the
  candidate-build job failed and the wheel-onboarding jobs were skipped.
  Root cause: the `551e…` build ran in WSL on a copy of the Windows
  worktree, which kept CRLF bytes in the packaged sources even after file
  modes were normalized; it was never a git-bytes build. A clean git clone of
  `63cd0ae` inside WSL (no Windows filesystem copy, no uncommitted changes),
  built with the same epoch and hatchling, reproduces `4f65ef45…6708f`
  exactly, matching CI. `4f65ef45…` is the canonical v0.7.2 candidate digest;
  `551e8dd6…` is superseded and must not be pinned anywhere. The first
  clean-tree sdist was
  `a60ea8f19dc7ae0a220ac0acf4da5baf596355b5062eed9af1c0a375e39f0cd4` (not
  authoritative; the public release is). Twine, artifact/notices/checksum
  validation, and the clean-wheel refresh smoke pass.
- GitHub CI on `63cd0ae` (run 32657558104): Python 3.11–3.14 test jobs
  passed; the release-candidate build failed only on the superseded pin and
  onboarding was skipped. Still open: green CI on the repinned commit,
  independent review, merge, tag, PyPI, staging deploy, and Profile
  scheduler dogfood.

## v0.7.1 Public Beta — released and live

- v0.7.0 was published on 2026-08-10, then maintainer dogfood found that a
  real Windows Task Scheduler registration normalizes the authored task into
  a six-setting shape with `UseUnifiedSchedulingEngine=true`. The strict
  v0.7.0 ownership validator rejected that legitimate installed task.
- The v0.7.1 patch authors the observed six-setting shape directly and accepts
  only exact registered enabled/disabled forms plus the two complete COM
  round-trip variants. Registered principal normalization is bound to the
  current process-token SID. Real Windows install/status/remove dogfood passes
  and removes the temporary task. Existing v0.7.0 scheduler metadata is read
  for status and direct reinstall, then a successful reinstall rewrites it as
  v0.7.1; unrelated and future versions still fail closed. Removal now proves
  the complete native XML ownership shape before deleting a same-name task.
  ACE `0.3.0`, aggregation, `VizStats`, renderers, privacy policies, and all
  eight output names remain unchanged.
- PR #32 merged at `c88e330`; tag `v0.7.1`, PyPI, and the prerelease GitHub
  Release are live. Main CI run `31407085892` passed all eight jobs, publish
  run `31407221409` passed, and staging run `31407918920` deployed the pinned
  dashboard. The released wheel is
  `c941b547b41eccca7efdfc99bdf785c6d8c307da8bedace0a73a3d19036df005`;
  the public sdist is
  `9858657fd42fb72ac812926836896debd91b90080a8e3384b0b9c65af3bc7d9b`.
  PyPI, GitHub Release, and staging URLs returned HTTP 200.
- Current Windows evidence is **954 passed with 30 skipped**; the focused
  scheduler suites pass **143 with 5 skipped** on both the current interpreter
  and Python 3.11; WSL Python 3.12 passes **145 with 3 skipped**. The
  release-focused candidate suite passes **89**. Ruff, bilingual README
  parity, and sanctioned snapshot/sample drift are green. After the final two
  red-first migration/removal regressions, a fresh mode-correct Ubuntu double
  build at `SOURCE_DATE_EPOCH=1786320000` produced byte-identical candidate
  wheels with SHA-256
  `c941b547b41eccca7efdfc99bdf785c6d8c307da8bedace0a73a3d19036df005`.
  Twine, artifact/notices/checksum validation, and clean-wheel refresh smoke
  pass. The public release, not an out-of-tree self-digest, is the final sdist
  authority. M-01, M-03, Profile scheduler dogfood, Profile Pages, and visual
  QA are closed in
  `docs/reviews/v0.7.1-release-readiness.md` and
  `docs/reviews/v0.7.1-visual-qa.md`.

- The public-only disposable caller passed a byte-changing exact-eight run
  (`31393816068`, commit `497e741`) and a no-change run (`31394187257`);
  Pages returned HTTP 200 and matched SHA-256 `657c4a38...3eaa3`. The immutable
  workflow commit `9c4f276` is an ancestor of the release tag and resolves
  through the GitHub Contents API.
- The maintainer Profile uses the official PyPI v0.7.1 persistent scheduler on
  `main` / `origin`, 12:37 local, with one active native task. Its audited
  configuration retains 10 sources, 3 identities, and 10 `full` policies,
  excludes the Profile repository itself, and keeps SHA-256
  `77c14ce3...5795`. The first run created exact-eight commit `b06d7ea`; the
  second was a no-op. Profile PR #19 / Pages run `31409289807` and LF-hygiene
  PR #20 / Pages run `31411007440` passed. A real post-merge run at
  `2026-08-10T16:52:52Z` was a clean no-op with local and remote HEAD fixed at
  `7e14cb593`.

## v0.7.0 automation release record

- ADR-030 adds an orchestration layer without changing ACE `0.3.0`,
  aggregation semantics, `VizStats`, renderer purity, or the eight-output
  contract. Phase A (`3b57ac6`) implements fail-closed configured-repository
  refresh, logical-state-preserving dry-run, and per-home locking. Phase B (`18a17f1`)
  implements the native scheduler and exact-eight Git publication with
  per-home native identity and residual-honest rollback.
- The reusable public-only workflow is frozen at commit
  `9c4f276cb437f1866a2c1b407efe54d3790ce811`. The copyable caller at
  `f92c5c4` pins that exact commit, consumes its immutable `published-sha`,
  and serializes refresh through same-run Pages deployment. Identity emails
  enter as a secret; public repository inputs are validated before
  credential-disabled clone; raw output from workflow-owned visibility,
  clone, commit, and push subprocesses is suppressed.
- Frozen Phase C evidence: **840 passed, 21 skipped**, Ruff clean, README
  parity pass, sanctioned snapshot/sample zero drift, and substantive WSL
  workflow probes. Both independent security/code reviewers approved the
  frozen bytes. This is candidate evidence, not evidence of a live scheduled
  run, released wheel, tag, PyPI artifact, or Pages deployment.
- Phase D synchronized the English/Traditional Chinese consumer guidance,
  ADR-030, architecture, privacy, release, roadmap, and contributor contracts.
  The multi-locale gate passed; the full suite passed **845 tests with 21
  skipped**, with Ruff, README parity, and sanctioned snapshot drift checks
  green. Phase E froze the local 0.7.0 candidate at
  `SOURCE_DATE_EPOCH=1786233600`: two isolated Ubuntu builds from the same
  Git-mode source archive produced byte-identical wheel and sdist artifacts.
  The wheel is
  `1ed1c0ee2efc2167ad39554545596caae1caa1e4b8ec2dad8c418f3a821adee4`
  and the synthetic dashboard remains
  `8172a3eac4c61232a2a0331edce4435b91a124b230a37a55505b11a5ba4f4eb1`.
  Twine, artifact/checksum validation, clean-wheel refresh smoke, current and
  Python 3.11 release-contract tests, the full **847 passed / 25 skipped**
  suite, Ruff, README parity, and snapshot zero-drift all passed. At that
  checkpoint this was local candidate evidence only; later bullets record the
  cross-platform CI and committed-range review results.
- The first Ubuntu CI run exposed a private-index mode gap: Git's atomic
  `add` rewrite inherited runner `umask 022` and produced `0644` before the
  old post-command chmod. WSL reproduced that exact boundary red-first. A
  broader adversarial replay then showed that `core.sharedRepository=group`
  can rewrite the index as `0660`, and that changing the process umask during
  `add`/`write-tree` also changes repository object modes. The corrected
  boundary confines the temporary index inside a tool-owned POSIX `0700`
  directory, resets the index to `0600` after each Git operation, removes the
  directory immediately, and leaves repository object creation under its
  ambient permission policy. Ordinary and shared-repository WSL launcher
  probes passed **24/24**; current and Python 3.11 launcher suites each passed
  **19 with 5 skipped**. The exact Python 3.11 E1 suite passed **169 with 21
  skipped**, and the rebuilt candidate passed double-build byte equality,
  Twine, artifact/checksum validation, and clean-wheel refresh smoke. That
  candidate required the cross-platform CI rerun recorded below.
- Cross-platform PR gates and the committed-range independent review closed
  before publication. The later v0.7.1 release record closes PR merge, M-03,
  tag/Public Beta publication, M-01 hosted caller/Pages, and maintainer
  scheduler dogfood. The public-only Action remains limited to all-public
  inputs; the maintainer Profile continues to use the local scheduler.
- PR CI run `31358621302` passed all eight jobs, including Python 3.11–3.14
  and Ubuntu/Windows/macOS onboarding of the same candidate wheel. The first
  E3 independent committed-range review nevertheless returned **NOT READY**:
  six High findings reproduced hostile ambient Git targeting, unpushed
  ancestor publication, post-refresh byte substitution/cross-home collision,
  lost push retry, same-path/different-UID stale-cache publication, and native
  scheduler semantic drift. All six were accepted for red-first remediation;
  the changed range subsequently passed the new independent review and
  regenerated artifact/CI gates recorded below.
- E3 remediation does not change ACE `0.3.0`, aggregation, `VizStats`,
  renderers, or the eight filenames. It adds a sanitized scheduler Git
  boundary, remote-tip equality, exact rendered-byte verification, a target
  repository lock, immutable private pending-push retry, pre-mutation
  ambiguous-UID rejection, exact Windows/launchd ownership validation, and
  POSIX `0600` pending/log state. The disposable public caller/Pages E2E stays
  a post-PyPI promotion gate; merge-commit ancestry and Contents-API resolution
  of the immutable C1 pin stay pre-tag/branch-deletion gates.
- Local E3 remediation evidence: the earlier exact E1 matrix passed **216 with
  25 skipped** on both the current interpreter and Python 3.11. After the final
  destination-isolation remediations, the broader scheduler suite passed **188
  with 12 skipped** on Python 3.11, WSL passed **196 with 4 skipped**, and
  the full Windows-local suite passed **938 with 30
  skipped**. Renderer/dashboard clarity and determinism coverage passed
  **104**; Ruff, README parity, and sanctioned snapshot/sample drift checks
  are green. Canonical Ubuntu double builds produced the byte-identical
  code/README candidate wheel
  `1ed1c0ee2efc2167ad39554545596caae1caa1e4b8ec2dad8c418f3a821adee4`
  at `SOURCE_DATE_EPOCH=1786233600`. Twine,
  artifact/notices/checksum validation, and clean-wheel refresh smoke
  passed. These candidate bytes subsequently received two independent
  `APPROVE` verdicts and passed the fresh cross-platform PR CI run below.
- A post-commit security replay found two further High findings. A remote could
  rewind or delete the branch after preflight but before an ordinary push,
  allowing removed history to be reintroduced; direct and pending publication
  now bind the immutable OID to an exact expected-old parent lease and confirm
  the remote tip before success or pending-state cleanup. Separately, Windows
  Task Scheduler COM expands the authored three settings into a deterministic
  harmless/default set; ownership validation now accepts only those two exact
  canonical forms and rejects any other value or key. Real-Git rewind/advance/
  deletion/no-op-success boundary matrices and a registration-free real COM
  in-memory round-trip pin both fixes. The preceding artifact digest and CI
  evidence were revoked, then rebuilt and rerun as recorded above; fresh PR CI
  was still open at that checkpoint and is now closed. Focused H-07/H-08 red-green
  evidence covered direct and pending rewind/advance/deletion/no-op-success
  push boundaries, post-push verification, exact COM defaults and value drift,
  plus the real Windows COM in-memory round-trip.
- Final adversarial review then found two further ownership boundaries. Windows
  descendant validation compared local XML names without proving the task
  namespace, and a Git remote could expose multiple push destinations while
  verification queried only its fetch destination. The red-first fix requires
  the task namespace on every inspected descendant, captures exactly one
  symmetric fetch/push destination before refresh, binds it to a fixed alias
  in an isolated private Git context for push and verification, and stores only
  its SHA-256 commitment in pending state. The actual argv never contains the
  URL; later `insteadOf`, `pushInsteadOf`, remote-alias, or config swaps cannot
  redirect the isolated transport. Multiple/different/credential-bearing
  destinations and pending destination drift refuse before publication
  mutation. Relative local destinations are canonicalized against the Profile
  repository before capture. The private transport queries only eight exact
  credential-helper, TLS, and SSH keys; authorization headers, proxies, and URL
  rewrites are never read into the transport snapshot, ambient proxy variables
  are removed, and supported HTTPS/SSH/SCP/Git/file/local destinations cannot
  put raw URLs in argv. The final drive-relative and complete-history
  regressions reject cross-drive ambiguity plus shallow/partial clones before
  refresh or pending retry. The full Windows-local suite passed **938 with 30
  skipped**, Python 3.11 scheduler coverage passed **188 with 12 skipped**, and
  WSL passed **196 with 4 skipped**. Canonical Ubuntu double builds at the frozen epoch produced the
  byte-identical candidate wheel
  `1ed1c0ee2efc2167ad39554545596caae1caa1e4b8ec2dad8c418f3a821adee4`;
  Twine, artifact/notices/checksum validation, and clean-wheel refresh smoke
  pass; the release-focused candidate suite passes **89**. Commit
  `84837d6b434c3a7ee692c36f8a80d1755caff003` received two independent final
  `APPROVE` verdicts. PR CI run `31390314352` passed all eight required jobs;
  every Linux Python 3.11–3.14 job reported **963 passed with 5 skipped**.
  Those candidate-stage gates later closed through the v0.7.1 release and the
  live evidence recorded at the top of this file.

## Current v0.6.1 Public Beta (2026-08-05)

- The provider ledger is now the sole model/provider contribution visual in
  current Summary Card and dashboard renderers. Canonical model rows remain in
  `VizStats` and machine-readable `profile.json`; no model evidence is lost.
- This is a presentation-only patch release: ACE/public schema `0.3.0`,
  aggregation semantics, CLI behavior, privacy boundary, and the eight-output
  contract remain unchanged. v0.6.0 remains the immutable historical release.
- Released artifact: Ubuntu-authoritative wheel
  `6ca24828fbba02024904028fa8fa5f96e97a8393d3f5e16bb6ff316cff477b9f`, staging
  dashboard `8172a3eac4c61232a2a0331edce4435b91a124b230a37a55505b11a5ba4f4eb1`,
  and fixture `synthetic-two-provider-fixture-v3-provider-ledger`.
- Release evidence: tag `v0.6.1` at main merge `1be0c68`; CI run
  `30984105485`, publish run `30984290387`, and staging run `30985228475` all
  passed. The hashes and run identifiers above preserve its byte-level
  artifact evidence; the single promotion-candidate manifest now authorizes
  the v0.7.0 candidate.

## Historical v0.6.0 Public Beta (2026-08-04)

- Research and implementation slice complete on `codex/v060-evidence-ledger`:
  the flat Evidence Ledger now gives canonical model families stable
  light/dark marks and bars, while preserving non-exclusive model semantics and
  unique-commit daily geometry. ADR-028, design forensics, and visual QA are
  recorded in the review/decision documents.
- Verification: **667 passed, 4 skipped**, Ruff clean, README parity pass,
  sanctioned snapshot regeneration byte-stable, exact-wheel release smoke
  pass, and Playwright responsive/theme/auto-system checks pass. The exact
  Ubuntu-authoritative wheel was published to PyPI and the GitHub Release is
  marked prerelease; the maintainer Profile was refreshed from that wheel and
  its Pages and snake workflows passed. Final evidence is recorded in
  `docs/reviews/v0.6.0-release-readiness.md`.

## Where things stand (2026-08-01)

- **v0.1 vertical slice implemented and reviewed**: Phase 0 design
  (`08f7413`) → implementation, 165 tests green (`50b8ac3`) → summary-card
  polish (`49fdcbb`).
- **Gate 2 independent architecture review received**: GO WITH CHANGES
  (`docs/reviews/gate2-review.md`). All 20 findings adjudicated in
  `docs/reviews/gate2-disposition.md` (Criticals + Highs accepted or
  resolved; G2-11 rejected in part with recorded reason).
- **Gate 2 conformance pass COMPLETE**: design docs amended (schema,
  architecture, mvp, ADR-005/006/007/008/009, new ADR-016); ROADMAP.md,
  PRIVACY.md, LICENSE (MIT — owner decision), CONTRIBUTING.md published;
  code conformed (uid algorithm v2 with positive-remote-marker rule,
  actor-presence rename, policy-based publication labels, evidence
  population + invariants, N-ary canonical merge reduction, diagnostics
  ordinals, SHA-256 targeted error, locator validation, envelope
  serialization, static import + SVG security tests). Implementation
  conformance review: three adversarial rounds to **APPROVE** — round 1
  found two real defects (uid collision with data-loss path;
  non-associative merge), round 2 a surviving origin shape; all fixed
  with pre-fix-failing regressions. Suite: **212 passed, 0 failed**;
  ruff clean.

- **Gate-3 implementation review received and resolved** (2026-07-14):
  `docs/reviews/gate-review.md` (independent, verdict NOT READY, 23
  findings) → all 23 adjudicated ACCEPTED in
  `docs/reviews/gate-disposition.md` (M-09/M-11 via documented decisions).
  Resolved in code+design, each code fix with a pre-fix-failing
  regression:
  - C-01/C-02/H-01/M-04 → **uid algorithm v3** (injective structured
    encoding, scheme retained, github-only transport convergence,
    case-preserved local hash, last-`@` credential strip, query/fragment
    parity, `.GIT` folding) — ADR-016 rewritten;
  - C-03/C-04 → scan is config-last atomic (failures leave config
    byte-identical), alias-group uid migration with fail-closed halt and
    same-transaction old-row purge;
  - H-02 → canonical slugs are schema-owned vocabulary enforced at
    `build_event` AND independently collapsed at the privacy boundary;
  - H-03/H-05/M-10/M-12 → duplicate-source dedup to highest evidence;
    offset-aware timestamps, human-evidence rule, provenance enum
    coercion, bool review flag; pair-atomic canonical/raw merge; pairwise
    merge API removed (N-ary only);
  - H-04 → object-format preflight (catches empty SHA-256 repos) with
    path-free errors, before any mutation;
  - M-01/M-02/M-03/M-05/M-07 → provider-row validation; recursive AST
    import contract incl. dynamic imports; key-presence Human-Only
    contradiction; uid/org/salt canaries + published-output permutation
    invariance tests; bundle-atomic dist/ writes;
  - M-06/M-08/M-09/M-11/L-01/L-02 → contradiction sweep across
    mvp/schema/README/CLI-help/ADR-008/ADR-009, privacy→registry edge
    documented, `aggregate -v` scope corrected, ADR-012 pre-release
    exception, terminology sweep, historical banner on the archived run
    log.
  Suite after the pass: **240 passed, 1 skipped** (the skip is the POSIX
  case-sensitivity fixture, not runnable on Windows — documented); ruff
  clean.

- **Verification review received and resolved** (2026-07-14 evening):
  `docs/reviews/gate-review.md` (overwritten with the verification round;
  prior content preserved in git history at `de4a78a`) verified 20/23
  dispositions and produced three reproducible counterexamples — all
  accepted (`docs/reviews/gate-disposition.md`, appended section) and
  fixed with pre-fix-failing regressions:
  - **Critical**: github alias convergence now requires the documented
    `(scheme, effective-port)` endpoints (`ssh:22`/`https:443`/`git:9418`);
    the 42-combination scheme×port grid no longer collapses (verified at
    the time by an ad-hoc probe only — the committed parameterized grid
    test landed in the gate-4 round, finding L-2) — ADR-016 rule 4
    amended;
  - **Medium**: dist/ replacement stage gained best-effort rollback
    (olds moved aside, restored on failure) with a replacement-stage
    failure-injection test;
  - **Medium**: `merge_event_group` now ENFORCES its leaf-only boundary
    (at the time via a source-count heuristic — proven bypassable and
    over-broad by the gate-4 review and replaced by the explicit
    `merged` derivation marker); nested composition raises — replicated
    the reviewer's nested probe;
  - L-01 completion: the two legacy tests demonstrating non-leaf usage
    rewritten.
  Suite: **244 passed, 1 skipped**; ruff clean; e2e green.

- **Gate-4 review received and resolved** (2026-07-14 late evening):
  `docs/reviews/gate-review.md` (overwritten with round 4; prior rounds
  preserved in git history) reviewed `de4a78a..4fdd490`, verdict NOT
  READY, 8 findings (1 High, 5 Medium, 2 Low) — all accepted
  (`docs/reviews/gate-disposition.md`, gate-4 section) and fixed with
  pre-fix-failing regressions:
  - **High + M-2**: leaf-only merge boundary is now an explicit
    derivation marker (`AceEvent.merged`, envelope metadata) instead of
    the bypassable source-count heuristic — nested composition rejected
    even when sources dedup to one; schema-valid multi-source leaf
    productions merge again;
  - **M-4 + M-5**: **uid algorithm v4** — the endpoint-qualified alias
    rule now lives under an honestly bumped version (schema §7 and
    ADR-016 rewritten to match), and ports normalize to canonical
    decimal (`:0443` ≡ `:443`) before endpoint lookup/serialization;
    `canonicalize_remote` is version-neutral, `UID_ALGORITHM` is the
    single version authority;
  - **M-3 + M-6 + L-1**: export rollback attempts EVERY restore
    (failures collected; unrestorable assets keep their backup, named
    in the error), transaction artifacts gained pid-scoped names (at
    the time claimed attempt-owned — the gate-5 review showed pid =
    process-owned, fixed with per-invocation ids in round 5), and
    post-publication cleanup failure is a warning, not a false
    `RenderError`; the docstring states a best-effort guarantee;
  - **L-2**: the claimed 42-case scheme×port grid landed as a committed
    exhaustive test (at the time a looped grid — converted to true
    per-cell parametrize in round 5, finding L-02).
  Suite after the pass: **256 passed, 1 skipped**; ruff clean;
  integration/e2e green.

- **Gate-5 review received and resolved** (2026-07-15):
  `docs/reviews/gate-review.md` reviewed `4fdd490..78e2e05`, verdict
  READY AFTER MINOR FIXES (0 Critical/High, 3 Medium, 4 Low) — all 7
  accepted (`docs/reviews/gate-disposition.md`, gate-5 section), each
  behavioral fix with a pre-fix-failing regression:
  - **M-01**: the merge-purity closure claim is NARROWED to the
    sanctioned in-memory scan path and made normative — schema.md §1
    now defines derivation state (`merged`: envelope-only, never
    serialized/persisted; rehydrated events are not re-mergeable in
    v0.1; out-of-contract construction acknowledged), §8.3 states the
    guard's scope; pinned by a canonical-payload + SQLite-schema
    regression;
  - **M-02**: export transaction ids became `<pid>-<n>` (the gate-6
    review showed this is still process-owned across pid reuse — closed
    in round 6 with directory-probed suffixes); the concurrency
    contract DECLARES concurrent publication unsupported (can mix
    generations — wording corrected in round 6: nothing is actively
    rejected at runtime) instead of claiming whole-generation
    isolation; recovery-`.bak` survival regression;
  - **M-03**: port tokens are bounded before int conversion (>65535 or
    >5 digits → unusable origin → local fallback, the fail-safe
    direction) — a 5000-digit port no longer escapes as ValueError;
  - **L-01**: failed first-install retractions are named in the raised
    RenderError (no longer log-only);
  - **L-03**: envelope fields (`recorded_at`, `merged`) excluded from
    dataclass equality/hash — value equality now agrees with canonical
    event equality; semantics documented in schema.md §1;
  - **L-02/L-04**: the 42-cell grid is now genuinely per-cell
    parametrized (42 reported cases); export-test fixture deduplicated.
  Suite after the pass: **302 passed, 1 skipped**; ruff clean.

- **Gate-6 review received and resolved** (2026-07-15 morning):
  `docs/reviews/gate-review.md` reviewed `78e2e05..b899d11`, verdict
  READY AFTER MINOR FIXES (0 Critical/High, 3 Medium, 3 Low) — all 6
  accepted (`docs/reviews/gate-disposition.md`, gate-6 section), each
  behavioral fix with a pre-fix-failing regression:
  - **M-01**: export transaction suffixes are directory-probed and
    exclusively created — a reused pid replaying a dead process's
    counter can no longer clobber retained recovery artifacts; counter
    lock-protected;
  - **M-02 + M-03**: **uid algorithm v5** — port domain honestly
    versioned (ASCII decimal only, canonical decimal, 0..65535;
    violations → local fallback): gate-5's bound had changed v4 output
    without a bump, and Unicode decimal ports (`:４４３`) minted split
    non-ASCII identities; ADR-016 + schema §7 rewritten;
  - **L-01**: equality is OPERATIONAL — `recorded_at` excluded,
    `merged` participates (it decides merge admissibility; set dedup
    can never flip merge behavior) — schema §1 specifies operational
    vs canonical-payload equality;
  - **L-02**: concurrency wording aligned ("unsupported", nothing
    actively rejected); precondition surfaced in `render --help` and
    README;
  - **L-03**: the persisted-schema pin moved to the storage test suite.
  Suite after the pass: **309 passed, 1 skipped**; ruff clean.

- **Visual refinement round (gate-6 Phase 3, 2026-07-15)**: summary card
  redesigned to the owner's "Governed Intelligence Editorial" direction —
  executed by a Codex delegate under a constrained brief, review-gated by
  Claude, then audited against the dataviz design skill:
  - one hero metric (AI-attributed commits) with its share of unique
    commits stated and drawn (thin share bar); presences / active days /
    providers / unknown as a subordinate right-aligned ledger;
  - evidence + privacy pills replaced by a provenance panel: stacked
    evidence-composition bar in precedence order with a swatch legend
    (counts always text), one quiet privacy statement line;
  - evidence ramps are VALIDATOR-PASSED ordinal Primer-blue scales per
    theme (the delegate's first ramps failed the 2:1 light-end contrast
    floor at 1.64:1/1.86:1 — computed, not eyeballed); segment gaps show
    the panel surface; sparkle glyph replaced by a commit-node mark;
  - reviewer round found a real defect (remainder-sized last segment
    could go NEGATIVE for 3+ lopsided evidence categories) — fixed with
    cumulative rounding (widths >= 0 and exact-sum structurally), red
    regression from the reviewer's own reproduction; reviewer re-ran a
    3,008-case randomized adversarial search, zero violations → APPROVE;
  - all 8 snapshots regenerated via the sanctioned script and visually
    verified in a real browser (both themes; populated / aggregate-only /
    all-publishable / zero states); privacy sweep clean (only the w3.org
    xmlns matches); mvp.md section 5 + ADR-010 composition wording
    updated.
  Suite after the round: **309 passed, 1 skipped**; ruff clean.

- **Aesthetic polish round (2026-07-15, Codex delegate)**: owner-directed
  craft pass over the approved composition — 4px spacing scale swept
  through every section (hero rhythm, 24px ledger step, 28px table rows,
  panel 16/16 padding at height 104, footer/zero-state), type scale
  locked to 11/12/13/16/38 (hero up to 38px, title down to 16px, panel
  evidence label promoted to a 12px weight-600 section label), 0.2
  letter-spacing on the two section labels; zero color changes
  (validator-locked ramps untouched). Reviewer APPROVE after independent
  probes (panel fit, deliberate y=160 baseline alignment with >=225px
  x-margin, letter-spacing XML-safety); its one suggestion applied: the
  evidence-segment regression selector now anchors on the bar's own y
  coordinate, removing the implicit BAR_HEIGHT/ramp-color coupling.
  Suite: **309 passed, 1 skipped**; ruff clean.

- **README sample preview committed (2026-07-15, Codex delegate)**: the
  ROADMAP "Sample profile output" half-item landed — two sample SVGs
  under `docs/assets/` (byte-exact `render_summary` output from the
  SYNTHETIC showcase fixture, re-render-verified; privacy-swept), a
  "What it looks like" `<picture>` preview atop the README with a
  synthetic-data caption, and a drift-guard regression
  (`test_docs_sample_assets_match_current_renderer`, reviewer
  recommendation) so future card changes must regenerate the assets or
  fail loudly. Suite: **310 passed, 1 skipped**; ruff clean.

- **Gate-7 review received and resolved** (2026-07-15, committed
  `73279cd`): `docs/reviews/gate-review.md` reviewed
  `b899d11..9933308`, verdict NOT READY (1 High, 2 Medium, 2 Low) — all
  5 independently reproduced and accepted (`gate-disposition.md`,
  gate-7 section), each behavioral fix with a pre-fix-failing
  regression:
  - **H-01**: VizStats is now the ENFORCED structural privacy boundary —
    every string field pinned to a closed public vocabulary (ACE version,
    fixed all-time period, canonical slugs, schema-owned display names;
    `PROVIDER_DISPLAY` moved into schema.vocab); the reproduced
    canary-to-SVG/JSON leak fails at construction;
  - **M-01**: merge timestamp resolves by the ADR-008 strongest-leaf rule
    (was first-leaf copy — reversed inputs produced different canonical
    events); schema §8.3 states the rule;
  - **M-02**: percentages never lie at the boundaries — `<1%`/`>99%`
    endpoint labels for hero share and provider rows;
  - **L-01**: light-theme unknown evidence mark #8c959f → #6e7781
    (2.85:1 → 4.27:1); both ramps re-validated ALL PASS;
  - **L-02**: one sanctioned command now regenerates snapshots AND the
    README sample assets; CONTRIBUTING documents it.
  Suite after the pass: **323 passed, 1 skipped**; ruff clean.

- **Gate-8 review received and resolved** (2026-07-16, committed
  `e0fa569`): independent verification of `9933308..73279cd`
  (gate-review.md, preserved untouched) confirmed 4/5 gate-7 closures
  and found two gaps in the fifth — both reproduced, accepted, fixed
  red-first (`gate-disposition.md`, gate-8 section):
  - **H-01**: the validated VizStats graph is now structurally
    IMMUTABLE — exact frozen contract types enforced for every nested
    record, the tuple container, and every string leaf, before any
    duck-typed access; the reproduced mutate-after-validate leaks
    (mutable list / tuple-held mutable row / mutable period) all fail
    at construction, and post-construction mutation raises with output
    bytes pinned unchanged; the in-round review pass caught and closed
    an int-subclass __str__ variant the same way (exact int/bool);
  - **L-01**: `generated_on` is a canonical ASCII calendar date
    (ASCII fullmatch + fromisoformat + round-trip) — Unicode digits,
    trailing newline, and impossible dates rejected.
  Suite after the pass: **339 passed, 1 skipped**; ruff clean; snapshot
  regeneration byte-stable (no visual change, as required).

- **Gate-9 review received and remediated** (2026-07-18, committed as
  `d9161cb`): independent verification of `73279cd..e0fa569`
  (gate-review.md, preserved untouched) confirmed the gate-8 closures
  and found the exact-type boundary incomplete at the TOP level, plus a
  stale-status doc gap — both reproduced, accepted, fixed red-first
  (`gate-disposition.md`, gate-9 section):
  - **H-01**: `VizStats` is SEALED against subclassing —
    `__init_subclass__` raises `TypeError` at class-definition time. A
    plain subclass defeats in-method guards (override `__getattribute__`
    to substitute a private-canary row, or `__post_init__` to skip
    validation — both reproduced svg+json leaks; the review caught the
    second, stronger variant after a first-pass `_validate`-only fix);
    sealing closes the whole family at its root, with a
    `type(s) is VizStats` backstop retained. Regression added;
  - **L-01**: the gate-7/gate-8 remediation records (progress +
    disposition) corrected from "UNCOMMITTED" to their actual commit
    hashes (`73279cd`, `e0fa569`).
  Suite after the pass: **340 passed, 1 skipped**; ruff clean; snapshot
  regeneration byte-stable (no visual change).

- **Gate-10 verification passed — VizStats finding chain (gates 7-10)
  closed** (2026-07-22):
  independent verification of `e0fa569..d9161cb` (gate-review.md,
  preserved untouched and committed with this closure) returned
  **READY FOR NEXT GATE with zero findings** — the first review round
  in the chain with nothing to remediate. The reviewer replayed eight
  from-scratch subclass-bypass vectors against the seal
  (`__post_init__`-skip, `__getattribute__` substitution, deep chains,
  multiple inheritance, custom metaclass `__new__`, `types.new_class`,
  `__bases__` splice, direct `type.__new__`) — all rejected with
  `TypeError` — and confirmed the legitimate lifecycle intact
  (replace/copy/deepcopy/pickle yield exact `VizStats`) plus fresh
  privacy-sweep integration tests green. Suite: **340 passed,
  1 skipped**; ruff clean; snapshot regeneration byte-stable.
  Process note: this was the first round run through the file-based
  handoff protocol (`.ai/handoff/`, headless `codex exec` via the
  codex-delegate wrapper) — no manual copy-paste transport; one stale
  self-referential "UNCOMMITTED" note on the gate-9 bullet above was
  corrected in this closure.

- **Round A hardening + Gate-11 verification** (2026-07-22, `278c138` +
  gate-11 resolve): four ROADMAP pre-release checkboxes closed
  (owner-only permissions, worktree warning, packaged smoke script,
  cherry-pick semantics) plus the cp950-safe console-text sweep
  (repo-wide, not itself a distinct checkbox). Gate-11 external
  review (headless handoff lane): READY AFTER MINOR FIXES, one Medium -
  existing installations skipped the permission retrofit via
  init_home's early return; fixed red-first by retrofitting in
  load_config (every command's choke point, mirrors db.connect).

- **Rounds B/C + Gate-12 final verification — v0.1.0 RELEASED**
  (2026-07-22): Round B closed the last two Gate-2 §14 checkboxes
  (console stdout/stderr canary sweeps with positive controls;
  hypothesis property fuzzing, six derandomized invariant families).
  Round C: PEP 639 packaging metadata, CHANGELOG.md with the upgrade
  policy, README install section led by `pip install ai-profile` (with
  the unhyphenated-name collision warning), hand-written
  README.zh-TW.md mirror (claim-by-claim parity reviewed), AGENTS.md
  handoff-process rule. Gate-12 (final pre-release, range
  `278c138..ac21d4d`): **READY FOR RELEASE, zero findings** — suite,
  ruff, wheel metadata + twine, release smoke, chmod-failure probe,
  snapshot byte-stability, and a fresh synthetic privacy sweep all
  independently green. Released as one unit immediately following this
  commit: GitHub repo public + PyPI upload of `ai-profile 0.1.0`, tag
  `v0.1.0`.

- **Image 2.0 rounds D1+D2 + gates 13-14** (2026-07-22, `08922b7` +
  `5b01195` + closures): the card gains provider brand identity
  (vendored CC0 simple-icons marks + per-theme brand bars, ADR-017)
  and the publishable-only isometric daily calendar (ADR-018; ACE
  schema 0.1.0 -> 0.2.0 per ADR-012's minor-bump rule). Gate-13: zero
  findings. Gate-14: one Low (EOF blank line), fixed in the closure.
  Notable process lessons recorded in the reviews: a from-nothing SMIL
  entrance is invisible in static captures (two attempts removed; the
  band is fully static with a pinning regression test), and the first
  privacy canary test was confounded by the window trim (re-pinned
  in-window and re-proven by sabotage).

## Open items

- v0.4.2 was published as the immutable wheel-notice correction. Its package
  artifacts and tag remain unchanged.
- **v0.4.6 Public Beta is released and promotion-verified.** Its wheel and
  runtime are correct; its immutable sdist unintentionally contains
  non-sensitive Hypothesis cache data.
- **v0.4.7 Public Beta is released and live.** It corrects the v0.4.6 sdist,
  excludes generated/private working roots and makes the artifact contract
  reject unsafe paths, duplicate members, links, and special entries. Product
  behavior, ACE, aggregation, privacy modes, CLI, and renderers are unchanged.
- The canonical release bundle is built from a clean Ubuntu checkout with a
  manifest-frozen `SOURCE_DATE_EPOCH`; Windows and macOS smoke those retained
  bytes rather than rebuilding platform-specific ZIP metadata.
- The pinned v0.4.7 wheel digest is
  `75b896c7a1bfa462d1caa6df7025bca79650e8ad48a006272e76eb9bfb5667d8`.
  The candidate passed 4/4 README-only roles, zero privacy-canary hits, a
  public-HTTPS 13/13 browser matrix, Python 3.11–3.14, and exact-wheel
  onboarding on Ubuntu, Windows, and macOS.
- `docs/reviews/promotion-readiness-review.md` records
  **GO — PUBLIC BETA** after protected-main CI and Pages staging. The tag
  workflow, PyPI/GitHub Release byte verification, clean PyPI install, and
  maintainer Profile refresh have completed successfully. The live Profile
  dashboard passed its responsive, theme, provider-filter, and keyboard-focus
  browser smoke after deployment.
- Future import, reconciliation, richer views, GitHub API integration, and
  any configuration CLI remain deferred in ROADMAP. They are not part of
  the v0.4.8 product boundary.
- **v0.4.8 Public Beta is released and promotion-verified (2026-08-01).**
  The HR-first visual refresh (ADR-022) shipped: summary card redesigned
  as the `AI Collaboration Record` with the whole-rhythm isometric
  terrain (height = total-commit bins, hue = AI-share bins,
  provider-independent geometry; shared bin arithmetic in
  `render/_bins.py`), dashboard H1 alignment, README restructure, and
  refreshed banner/social assets. Released from `main` commit
  `b4e2178a79cf9d1437ebf46ce52d141720437762` (tag `v0.4.8`); the GitHub
  Release is marked prerelease and the PyPI classifier is Beta.
  Canonical digests — wheel
  `d8d307d4155f58f157ee817cdd628ef4c257287083aad66cf30e02f679fe47b6`,
  sdist
  `0909aa3e2efe19ec1471c1f95f373646538c6df8bb344ecabf1fac6d20065b38`,
  package dashboard
  `c8680c2812343077775c2b5c0fddae9dce32c1517bbaa4c920e056b347fdbd4f`.
  Verification: full local suite 628 passed / 4 skipped; CI Linux 631
  passed / 1 skipped; Ruff clean; README parity pass; sanctioned
  regeneration twice with zero byte drift; exact-wheel onboarding on
  Ubuntu, Windows, and macOS; release run `30717707873` passed;
  protected-main staging run `30717400004` passed and deployed the exact
  pinned dashboard bytes. Four README-only dogfood roles passed 4/4 with
  zero external hints, zero privacy-canary hits, exact hand totals, and
  eight outputs. Full record: `docs/reviews/v0.4.8-release-readiness.md`.
- **Post-v0.4.8 evidence-ledger refinement (design branch, 2026-08-04).**
  Research reviewed Nanako0129, Primer, Carbon, Radix, Geist, Vega-Lite,
  Observable Plot, Grafana, and related primary sources. The branch keeps the
  v0.4.8 data/privacy contract while separating provider metric columns,
  adding semantic section markers, and regenerating only sanctioned summary
  snapshots/assets. ADR-023 and the implementation plan document the scope.
  Independent verification is green; public patch publication remains
  conditional on a versioned artifact/CI/Pages release round. Full record:
  `docs/reviews/v0.4.9-visual-readiness.md`.
- **Structural Current visual slice (superseded design branch, 2026-08-04).**
  Independent design forensics (Nanako0129's public tools plus Primer,
  Carbon, Radix, Geist, Vega-Lite, and related systems) is recorded in
  `docs/reviews/design-reverse-engineering.md`. `DESIGN.md` and ADR-024 now
  define the semantic role tokens and evidence-first composition without
  adding runtime dependencies or a new data model. That branch's perspective
  treatment was intentionally rejected for the summary card; its rollback
  remains available until the flat replacement completes verification.
- **v0.4.9 Flat Evidence Ledger pivot (pre-release record, 2026-08-04).**
  ADR-025 replaces the summary-card perspective treatment with a 12-column by
  7-row flat daily matrix. Bars encode unique daily total-commit bins and fill
  encodes AI-share bins; provider overlap, unknown/human separation, privacy
  redaction, and the eight-file output contract remain unchanged. The branch
  was subsequently verified and released as v0.4.9; the candidate readiness
  record remains the historical pre-publication review:
  `docs/reviews/v0.4.9-flat-ledger-readiness.md`.
- **v0.4.9 Public Beta is released and promotion-verified (2026-08-04).**
  Tag `v0.4.9` and the GitHub Release are live; PyPI serves the verified
  wheel and sdist. The final Ubuntu-authoritative wheel digest is
  `f04e6c33b72072190e1cb18fbb154897c25ec7986fd316427d807c81e49fb468`.
  Main CI and the publish workflow passed, clean PyPI installation reported
  `aiprofile 0.4.9`, and the eight-output release smoke passed. Maintainer
  Profile PR #13 merged at `b991504`; its Pages deployment passed and all
  eight live outputs match the merged LF-normalized blobs. Final record:
  `docs/reviews/v0.4.9-release-readiness.md`.
- **Editorial Signal skin (pre-release candidate record, 2026-08-04).**
  A new research round compared Nanako0129's terminal-ledger composition with
  Primer, Carbon, Radix, Geist, Vega-Lite, and profile generators. The
  presentation-only candidate keeps the v0.4.9 flat Evidence Ledger, adds
  sparse quarter-window alignment rails and a two-part editorial section
  marker, and leaves ACE/schema, aggregation, privacy, CLI, and eight-output
  contracts unchanged. Research and acceptance criteria:
  `docs/reviews/design-research-2026-08-04.md`; decision:
  `docs/decisions/ADR-026-editorial-signal-skin.md`. Local exact-wheel smoke,
  privacy sweep, and browser evidence are recorded in
  `docs/reviews/v0.4.10-visual-qa.md`. Cross-platform publication and Profile
  verification were still open when that candidate record was written; the
  candidate was subsequently verified and released as v0.4.10, and the final
  evidence is the release record below.
- **v0.4.10 Public Beta is released and promotion-verified (2026-08-04).**
  Tag `v0.4.10` and the GitHub Release are live as a prerelease; PyPI serves
  the verified wheel and sdist and remains classified as Beta. The candidate
  merged to `main` as `91260bdf368dc32ecc25c6446f38f6b987047f26` via PR #21.
  The Ubuntu-authoritative wheel digest is
  `41c91d01ee761abc5a22add1c2a2fb8d3b36e309411b5db0398a7eae7824cd7a` and the
  sdist digest is
  `b327a421797c51e8b1866baff09a4612828f6bde4fb6445757e8808d980b7951`. PR CI
  run `30921682522` and publish run `30922283841` passed; an earlier publish
  attempt, run `30921090861`, failed on a digest mismatch against the frozen
  candidate manifest and was corrected by commit `b78a8da` before the
  successful publish. Clean installation of the exact PyPI wheel reported
  `aiprofile 0.4.10`, and the eight-output release smoke passed. Maintainer
  Profile PR #14 merged at `9c346fde0ebbbf0c12485f9bbacb0e486ed9d8af`
  (implementation commit `42e8ecf4571fe084fe10ee2ce1fb379de9e4022e`); Pages
  run `30924497319` and the snake run `30924498845` passed, and all eight
  live outputs are HTTP 200 and match the merged LF-normalized blobs. Final
  record: `docs/reviews/v0.4.10-release-readiness.md`.
- **The maintainer Profile refresh on public PyPI 0.4.8 is complete.**
  Profile PR #12 merged at `7f322beab1e532d906f943c62fc68e49ba21c02a`
  with the unchanged exact 11-repository full-publication scope. Profile
  Pages run `30718799030` passed; all eight published outputs are
  HTTP 200 and byte-identical to the merged git blobs; profile dashboard
  SHA-256
  `b17e996a6fb0fa8530779c59d47d5cf069154ffd8437e431d2bf7331c12ac292`.
  The Profile privacy review found zero hits across paths, names,
  organizations, e-mails, full and 12-character SHAs, 1714 commit bodies,
  1713 subjects, and 405 prompt-bearing lines.
- **v0.5.0 model-family contribution is released and promotion-verified
  (2026-08-04).** ADR-027 and the model-category plan define a closed,
  explicit-only family ledger over ACE `0.3.0`: model-family commit rows are
  non-exclusive, presence rows reconcile to AI actor presences, and missing
  models remain `Unknown` rather than Human. The release records
  `667 passed, 4 skipped`, clean Ruff, deterministic sanctioned assets,
  exact-wheel smoke, browser QA, and zero privacy-canary hits. Ubuntu CI run
  `30935669158` and publish run `30935872159` passed; the exact wheel was
  published to PyPI and the GitHub Release is a prerelease. Tag `v0.5.0` is at
  main merge `4e369c6`; wheel digest
  `dcd407fa5a570b1a47ba3c613998f681c5c992f10f18119ab4f4be457221f245`; sdist
  digest
  `24f581f9914ac0372af4e921889f79c935207852f6c66b4affe110901a5d1ed8`.
  Maintainer Profile PR #15 merged at `ead0f41`; Pages run `30937320357` and
  snake run `30937324074` passed, with all eight live outputs matching the
  merged LF-normalized blobs. Full evidence:
  `docs/reviews/v0.5.0-release-readiness.md`.

## Pointers

- Roadmap: `docs/ROADMAP.md` · Threat model: `docs/PRIVACY.md`
- Reviews: `docs/reviews/` (Gate 2 review, disposition, v0.1 run log)
- Contracts: `docs/schema.md`, `docs/architecture.md`, `docs/mvp.md`,
  `docs/decisions/`

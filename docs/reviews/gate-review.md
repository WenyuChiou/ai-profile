# ai-profile v0.7.0 gate review

Date: 2026-08-10

Review range: `cc69303..17822fe` (v0.7.0 refresh, native scheduler, public workflow, documentation, release candidate, and Ubuntu CI remediation)

Reviewer posture: independent Principal Software Engineer; verification only

## Executive summary

The v0.7.0 candidate preserves the approved ACE schema, aggregation semantics,
`VizStats` privacy boundary, renderer dependency direction, deterministic eight-
asset output contract, and Public Beta scope. Local and CI verification is
strong: the root Windows run passed **847 tests with 25 skipped**, GitHub run
`31358621302` passed all eight required jobs with **871 passed / 1 skipped** on
each Python 3.11–3.14 job, and clean-wheel onboarding passed on Ubuntu, macOS,
and Windows. The downloaded CI artifact exactly matches the pinned wheel and
sdist digests and contains both required license notices.

The candidate is nevertheless not ready to merge. Independent adversarial
probes reproduced six High-severity correctness, privacy, and automation
failures: Git repository-selection variables are inherited from the ambient
environment; a pre-existing unpushed local commit can be published with the
generated assets; staged bytes are not bound to the just-rendered generation;
a transient push failure is not retried; same-path/different-UID configuration
can publish stale cached data under the wrong policy; and native scheduler
status accepts execution-semantic drift. These are implementation blockers,
not documentation preferences.

No Critical finding was reproduced. The visual/rendering implementation did
not change in this range; sanctioned regeneration remains byte-stable. Final
browser clarity and live daily-update verification remain post-release gates,
not evidence that can close the High findings below.

## Review basis and verification evidence

| Area | Exact command or probe | Result |
|---|---|---|
| Full local suite | `python -m pytest tests -p no:cacheprovider` | **847 passed, 25 skipped** |
| Lint | `python -m ruff check src tests scripts` | **All checks passed!** |
| README parity | `python scripts/check_readme_parity.py` | **PASS** |
| Sanctioned regeneration | `python tests/unit/test_render_summary.py`; `python tests/unit/test_heatmap_svg.py`; `git diff --exit-code -- tests/snapshots docs/assets` | zero snapshot/sample drift |
| PR CI | GitHub Actions run `31358621302` | all 8 jobs passed; Python 3.11–3.14 each **871 passed, 1 skipped**; 3-platform wheel onboarding passed |
| CI artifact identity | download `release-candidate-3d2d046aa708e4bf2192f533dc13a4691a650c01`; SHA-256 | wheel `e8b568e011055c6cb8b3baaadb647cbd338bbcb82a37465c5ae46f6f41757740`; sdist `276828f9dc4ff4ba04e1ea90385d182b15f6329d618df54c3cc197d1e72f8b67` |
| Packaging | inspect wheel archive | `LICENSE` and `THIRD_PARTY_NOTICES.md` present |
| Core semantics diff | `git diff --quiet cc69303..17822fe -- src/aiprofile/aggregate.py src/aiprofile/privacy.py src/aiprofile/viz.py src/aiprofile/schema src/aiprofile/render` | unchanged |
| Private-index probe | ordinary and `core.sharedRepository=group` repos under POSIX `umask 022` | parent `0700` at rewrite boundaries; final index `0600`; caller umask and repository object modes unchanged |
| Architecture/security review | three independent read-only review tracks plus root inspection | six High findings reproduced; workflow/release track found no additional High |

## Findings

### High — H-01: ambient Git repository-selection variables are trusted

**Description:** Repository-bound Git calls in
`src/aiprofile/schedule/service.py:302` and
`src/aiprofile/schedule/launcher.py:51` inherit `GIT_DIR`, `GIT_WORK_TREE`,
`GIT_COMMON_DIR`, alternate-object, namespace, replacement-ref, and injected
Git-config variables. The private-index path copies the full environment and
overrides only `GIT_INDEX_FILE`.

**Reproduction:** A temporary target Profile and an unrelated repository were
created. With `GIT_DIR=<unrelated>/.git`, `_repository_state(...)` followed by
`_publish(...)` returned success. The unrelated remote received a target
`dist/` asset and retained the unrelated private file:

```text
captured_unrelated_head=True
result=(0, "refresh committed and pushed")
wrong_remote_received_profile_asset=True
wrong_remote_retained_private=True
```

**Impact:** A hostile or accidentally inherited environment can read, mutate,
or push the wrong repository, exposing unrelated history and violating the
configured Profile boundary.

**Recommendation:** Centralize a sanitized Git environment for every install
and launcher call. Remove repository-selection, object, namespace,
replacement-ref, shallow/graft, index, and injected-config variables; set only
the private index explicitly where required. Preserve only credential transport
needed for normal user authentication. Add hostile-environment integration
tests covering install, refresh publication, and push.

### High — H-02: an unpushed local ancestor can be published

**Description:** `src/aiprofile/schedule/launcher.py:241` creates the scheduler
commit as a child of the current local HEAD and later pushes that child without
proving the recorded remote branch equals the captured parent.

**Reproduction:** After pushing a clean baseline, a local-only commit containing
`private-canary.txt` was created. Publishing one changed generated asset
returned success; the remote history became:

```text
chore: refresh ai-profile outputs
local unrelated secret
baseline
remote_has_private_canary=True
```

**Impact:** The scheduler's claimed exact-eight publication can also publish
arbitrary unpushed history and its historical blobs.

**Recommendation:** Before any push-capable publication, resolve the actual
remote branch tip with suppressed output and require one exact 40-hex OID equal
to the captured local HEAD. Missing, ahead, behind, diverged, or unverifiable
remote state must fail closed with a path-free instruction to synchronize
manually. Do not accept allowlisted diffs in ancestor commits.

### High — H-03: mutable worktree bytes are not bound to refresh output

**Description:** After `refresh.run_refresh` returns,
`src/aiprofile/schedule/launcher.py:177` stages the then-current worktree. The
branch/OID checks do not prove those bytes are the generation returned by the
renderer/exporter. Per-home locks also do not serialize two different homes
targeting one Profile repository.

**Reproduction:** A runner wrapper changed `dist/profile.json` to
`PRIVATE-RACE-CANARY` immediately before `git add`. The launcher returned 0 and
`git show HEAD:dist/profile.json` contained the canary.

**Impact:** An editor, other automation, or second home can substitute or mix
public bytes between validation and commit, including private content.

**Recommendation:** Return an immutable expected manifest from refresh and
verify the eight private-index blob OIDs and modes against it before
`write-tree`. Add target-repository serialization or an equivalent collision
guard for different homes. Test direct boundary substitution and two-home
contention.

### High — H-04: a transient push failure can leave the public Profile stale indefinitely

**Description:** A failed push leaves the exact-eight commit as local HEAD.
The next identical refresh reaches the no-change return at
`src/aiprofile/schedule/launcher.py:305` before retrying publication.

**Reproduction:** The first run forced only `git push` to return 1; the second
used normal Git with identical generated bytes:

```text
rc1=1 local_advanced=True
rc2=0 remote_caught_up=False remote_unchanged=True
push failed (exit 1); local commit retained
refresh completed; no change
```

**Impact:** A temporary network or provider failure defeats the daily-update
promise while subsequent runs report success.

**Recommendation:** Persist the pending immutable scheduler OID privately and
retry exactly that OID only when the recorded local branch still points to it
and the expected parent/tree contract is intact. Clear pending state only after
a confirmed push; divergence must fail closed and report the local residual.

### High — H-05: same path with different repository UIDs can publish stale cached data

**Description:** `src/aiprofile/refresh.py:94` skips a repeated resolved path
before reconciling a different repository UID. Final aggregation at line 276
still consumes every UID-keyed cached row permitted by the final config.

**Reproduction:** A valid duplicate config entry was added for the same path
with UID `stale-same-path`; marker rows were inserted for that UID. Refresh
reported the duplicate as skipped, but totals rose from 3 to 4 and unknown from
2 to 3. In the privacy variant, the current path was `aggregate_only` while the
stale UID remained `full`; the public daily series exposed the stale marker
date.

**Impact:** Stale cache can double-count activity and bypass the current
physical repository's publication policy.

**Recommendation:** Reject repeated resolved paths with different UIDs as
ambiguous before scan/cache mutation, or atomically reconcile UID, apply the
most restrictive path policy, and purge stale rows. Add real and dry-run tests
for count integrity and absence of daily-date leakage.

### High — H-06: native scheduler validation accepts execution-semantic drift

**Description:** Windows status validation in
`src/aiprofile/schedule/adapters/windows.py:147` omits principal and security
fields. Launchd validation in
`src/aiprofile/schedule/adapters/launchd.py:88` accepts additional execution
keys.

**Reproduction:** A Windows task changed `UserId` and set
`RunLevel=HighestAvailable`; a launchd plist added `KeepAlive=true`. Both were
reported as installed, active, and matching the expected time.

**Impact:** Reinstall/status can trust a native job that runs under a different
identity, privilege, or frequency, contradicting ADR-030's fail-closed
native/local consistency contract.

**Recommendation:** Validate the complete owned execution/security payload.
For Windows, pin principal, logon, least-privilege run level, instance policy,
start behavior, enabled state, action context, and exact single action/trigger.
For launchd, require the exact four-key owned payload or a documented harmless
normalization allowlist. Retain post-install exact-state validation.

### Medium — M-01: real GitHub-hosted caller/Pages behavior is not yet exercised

**Description:** Static and extracted-script tests cannot validate actual
`workflow_call` context, `GITHUB_TOKEN` push, artifact transfer, or Pages
environment behavior.

**Impact:** The hosted public path could fail only after users copy it.

**Recommendation:** After PyPI publication but before Public Beta promotion,
run the copied caller against a disposable public Profile: one byte-changing
run and one no-change run, verifying exact-eight commit, immutable
`published-sha`, Pages HTTP 200, and no extra commit on the second run.

### Medium — M-02: scheduler interpreter lifetime is not documented

**Description:** Native definitions embed `sys.executable`, but the README does
not say the installation environment or virtual environment must persist.

**Impact:** Removing or moving that environment can make the OS job fail before
the application can update `last-run.log`.

**Recommendation:** Add one concise English/Traditional-Chinese note: install
from a persistent Python environment; after moving, removing, or upgrading it,
rerun `schedule install` and confirm `schedule status`.

### Medium — M-03: immutable caller pin requires merge-commit ancestry

**Description:** The caller pins `9c4f276`, which is currently reachable only
from the feature branch; repository settings also permit squash and rebase.

**Impact:** A squash/rebase merge followed by branch deletion can leave the
public template dependent on non-main PR-object retention.

**Recommendation:** Merge PR #31 with a merge commit. Before deleting the
branch, require `git merge-base --is-ancestor 9c4f276 origin/main` and verify
the workflow blob resolves through the GitHub Contents API at that SHA.

### Medium — M-04: `last-run.log` mode is broader than the documented claim

**Description:** `src/aiprofile/schedule/launcher.py:33` appends without an
explicit file mode. Under POSIX `umask 022`, the file was `0644` inside a
`0700` parent, while MVP/changelog prose claims owner-only scheduler modes.

**Impact:** The parent currently protects confidentiality, so direct exposure
is limited; the file-level claim is still false and less defense-in-depth is
present if parent permissions drift.

**Recommendation:** Create/retrofit the log as `0600` and test it, or narrow the
claim to the `0700` directory boundary.

## Verified areas without findings

- ACE schema remains `0.3.0`; unknown remains separate from Human.
- Aggregation, privacy projection, `VizStats`, schema, and renderer modules are
  unchanged; unique commits, actor presences, provider counts, active days, and
  evidence records retain their distinct units.
- Renderers still consume exact validated `VizStats` only and have no Git,
  SQLite, storage, network, inference, or clock dependency.
- The exact eight public filenames and deterministic SVG/HTML/JSON contract are
  unchanged; sanctioned regeneration is byte-stable.
- Public workflow source clones are credential-disabled and public-visibility
  checked; identity values are secret-scoped; write and Pages authorities are
  separated; actions and reusable workflow references are immutable SHA pins.
- CI artifact hashes, package/runtime version, wheel metadata, license notices,
  and the three-platform onboarding result agree.
- Current private-index confinement correctly uses a `0700` directory without
  changing caller umask or repository object modes.

## Severity summary

| Severity | Count | Status |
|---|---:|---|
| Critical | 0 | none reproduced |
| High | 6 | open; release blockers |
| Medium | 4 | open; one post-publication operational gate |
| Low | 0 | none |

## Final recommendation

**NOT READY**

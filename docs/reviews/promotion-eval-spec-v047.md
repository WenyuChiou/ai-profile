# v0.4.7 Public Beta packaging-remediation evaluation specification

Date frozen: 2026-07-30
Baseline: `0e7140f5dafcdaca77e5ba1f85c292020fc92db4` (`v0.4.6`)
Target: `ai-profile-cli` 0.4.7 Public Beta

This specification is fixed before candidate evaluation. Results may not
weaken these gates. v0.4.7 is an artifact-only remediation: the application,
ACE schema, aggregation semantics, renderers, privacy boundary, CLI behavior,
and public visual design must remain unchanged from v0.4.6.

## Candidate identity

- Version: `0.4.7`
- Wheel: `ai_profile_cli-0.4.7-py3-none-any.whl`
- Frozen `SOURCE_DATE_EPOCH`: `1785369600`
- Canonical Ubuntu wheel SHA-256:
  `75b896c7a1bfa462d1caa6df7025bca79650e8ad48a006272e76eb9bfb5667d8`
  (discovered by the first isolated fail-closed candidate build, then pinned
  before any promotion evidence was accepted).
- The dashboard SHA-256 must remain
  `17f2627e60c42a008e20af583af4cd51ca9a0814773163df5c5d1ec4982af192`.

## Required gates

1. The regression test must fail before the fix and pass afterward for
   Hypothesis, pytest, Ruff, mypy, tox, nox, virtual-environment, coverage,
   `__pycache__`, and bytecode members.
2. A build performed after the full test suite must produce an sdist with no
   generated cache member. `twine check` and the release artifact contract
   must pass for the exact retained wheel and sdist.
3. Full pytest, Ruff, sanctioned snapshot regeneration, README parity, and
   deterministic release smoke must pass.
4. Ubuntu, Windows, and macOS must install the retained candidate wheel in a
   clean environment and complete onboarding smoke.
5. The exact retained candidate must pass four README-only roles: newcomer,
   privacy, multi-provider semantics, and Profile publisher. Required result:
   4/4 complete, zero external hints, zero privacy-canary hits, and exact
   hand-derived aggregate agreement.
6. The exact staging dashboard must be served at
   `https://wenyuchiou.github.io/ai-profile/v0.4.7/dashboard.html`, match the
   pinned wheel and dashboard digests, and preserve the previously approved
   13/13 responsive, theme, keyboard, filter, accessibility, and aggregate
   checks.
7. Independent packaging/onboarding, security/privacy, maintainability, and
   completion-integrity review must report no unresolved Critical or High
   finding. Any accepted Medium must name an owner and follow-up.

## Release and live verification

The PR must merge through protected `main` with required checks. The `v0.4.7`
tag must point to that merge commit. The publish workflow must upload exactly
the retained bytes to PyPI and the GitHub Release. Live verification must
confirm:

- exact public wheel and sdist SHA-256 values;
- both notices in both artifacts;
- zero forbidden cache members in the public sdist;
- clean PyPI installation, version, quickstart, privacy canary, deterministic
  render, and expected eight outputs;
- green GitHub Actions and valid public links.

Any artifact mismatch, cache member, privacy leak, cross-platform failure,
README-only dead end, or publication mismatch forces `NO-GO`.

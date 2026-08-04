# v0.5.0 model-family promotion dogfood

Date: 2026-08-04
Candidate wheel: `ai_profile_cli-0.5.0-py3-none-any.whl`
Local Windows build SHA-256 (historical candidate evidence):
`2d67bd40b47a32125c5e609873626c1c64f92d79d4ca83a58ce608db88a41181`
Ubuntu CI authoritative SHA-256 (release pin):
`dcd407fa5a570b1a47ba3c613998f681c5c992f10f18119ab4f4be457221f245`
CI run: `30934549387`
Fixture ID: `synthetic-two-provider-fixture-v2-model-ledger`

## Scope

This round exercises the candidate artifact, not the source tree. The fixture
contains Claude, GPT, and Unknown model rows, provider rows, daily activity,
privacy totals, and the existing All AI/provider dashboard controls.

## Evidence

- `python scripts/release_smoke.py --wheel dist/ai_profile_cli-0.5.0-py3-none-any.whl --expected-version 0.5.0` passed every step: exact-wheel install, init, scan, aggregate, render, repeat render, same-date pair, profile JSON structure, eight SVG outputs, CSP, privacy canaries, and deterministic bytes.
- `python scripts/render_staging_dashboard.py --wheel ...` produced a
  manifest whose wheel digest is the candidate digest and whose dashboard
  digest is `cace8ed2b4f61affb0661e5ba3beae9de42836cc025ce8334b76b4226609110e`.
- The Ubuntu release-candidate job rebuilt the wheel at the authoritative
  release pin above; the same retained wheel bytes passed exact-wheel
  onboarding on Ubuntu, macOS, and Windows in CI run `30934549387`.
- Model rows in the fixture reconcile to 26 AI actor presences and remain
  independent of provider rows; one commit can contribute to multiple model
  categories without increasing the unique AI-commit headline.
- Unknown model evidence remains separate from Human and raw model strings are
  absent from `profile.json`, SVG, dashboard HTML, and staging output.
- The model panel is intentionally all-AI and non-exclusive; provider filters
  do not falsely claim to filter the model ledger.

## Disposition

| Finding | Severity | Disposition |
|---|---|---|
| Legacy manually constructed `VizStats` may omit `models` for compatibility | Low | Accepted for v0.5.0; production `build_viz_stats` always supplies model rows and the empty state is explicit. Tightening is a future contract change. |
| Publication and live Profile promotion | Medium | Closed: tag `v0.5.0`, PyPI, GitHub Release prerelease metadata, Profile PR #15, Pages run `30937320357`, and all eight live bytes were independently verified. |

No Critical or High dogfood finding was reproduced.

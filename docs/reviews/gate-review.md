# ai-profile v0.6.0 gate review

Date: 2026-08-04
Review range: `76c003b..58b1f21` (v0.6.0 visual release plus final release-readiness guard)
Reviewer posture: independent Principal Software Engineer; verification only

## Executive summary

The v0.6.0 implementation follows the approved architecture and MVP boundary.
The stable model-family visual key is additive: it uses canonical model rows
already present in validated `VizStats`, keeps the all-time model ledger
non-exclusive, and leaves the daily matrix's unique-commit geometry and AI
share semantics unchanged. Unknown remains separate from Human.

The static Summary Card and self-contained dashboard remain deterministic,
privacy-safe, and free of Git, SQLite, network, attribution inference, and
external font dependencies. The maintainer Profile was regenerated from the
released wheel; the retired green 3D map is no longer presented as the primary
AI activity visual.

The gate is green: **667 passed, 4 skipped**, Ruff clean, sanctioned snapshot
regeneration byte-stable, exact-wheel smoke pass, Ubuntu/Windows/macOS
onboarding pass, browser/privacy checks pass, and live PyPI/GitHub/Profile
artifacts match the recorded release evidence. Detailed evidence is in
[`v0.6.0-release-readiness.md`](v0.6.0-release-readiness.md).

## Verification evidence

| Area | Exact command/probe | Result |
|---|---|---|
| Full suite | `python -m pytest tests -p no:cacheprovider` | **667 passed, 4 skipped** |
| Lint | `python -m ruff check src tests scripts` | **All checks passed!** |
| README parity | `python scripts/check_readme_parity.py` | **PASS** |
| Summary regeneration | `python tests/unit/test_render_summary.py` twice | 8 snapshots + 2 assets; second run zero diff |
| Exact wheel smoke | `python scripts/release_smoke.py --wheel dist/ai_profile_cli-0.6.0-py3-none-any.whl --expected-version 0.6.0` | **PASS**: install, init, scan, aggregate, render, CSP, privacy canary, determinism |
| Cross-platform CI | PR #27 / run `30945358542`; Python 3.11–3.14 and Ubuntu/Windows/macOS wheel onboarding | **PASS** |
| Browser visual QA | Chromium 320/390/768/1280/1440; auto/light/dark; keyboard/focus; effective 200% | **PASS**, no page overflow |
| Model-category visual | Summary and dashboard model ledger | Claude/GPT/Unknown marks and bars present; labels and values remain textual |
| Aggregation | multi-provider/model fixture and production public aggregate | unique commits, presences, providers, active days, evidence, model rows, and unknown/human remain separate |
| Privacy/static safety | all eight Profile outputs, snapshots/assets, dashboard CSP, SVG active-content sweep | zero private paths, repo names, organizations, emails, prompts, SHAs, scripts, external network calls, or embedded objects |
| Live release | PyPI `0.6.0`, GitHub Release `v0.6.0`, Profile PR #16 / Pages run `30944387849` / snake run `30944389155` | exact digests, prerelease metadata, and HTTP 200 outputs verified |

## Findings

### Medium — Beta release metadata drift (closed)

**Description:** The first v0.6.0 GitHub Release creation did not carry the
prerelease flag, despite the project being a 0.x Public Beta. The discrepancy
was reproduced with `gh release view`, repaired before announcement, and the
publish workflow now applies `--prerelease` to `v0.*` creation/repair paths and
asserts `isPrerelease=true` afterward.

**Impact:** Without the repair, GitHub could communicate a stronger stability
claim than PyPI, the changelog, and the README.

**Recommendation:** Keep the scoped workflow guard and post-publication
metadata assertion. **Disposition: closed; current release is
`isDraft=false`, `isPrerelease=true`.**

### Low — model categories are not a dated time series (accepted)

**Description:** The model-family ledger is an all-time, non-exclusive view;
the daily matrix does not expose a Claude/GPT-by-day filter.

**Impact:** A user cannot answer a model-by-date question from v0.6.0, but
renderer-side inference would double-count or invent a dimension absent from
the validated aggregate.

**Recommendation:** Keep this honest boundary. Add model-by-day only through a
future schema/ADR aggregate with reconciliation and privacy tests.
**Disposition: accepted; no release blocker.**

No Critical or High findings remain open. No architecture, schema,
aggregation, privacy, determinism, packaging, accessibility, or OSS-onboarding
blocker was reproduced.

## Verified areas without findings

- Dependency direction is intact: storage/scan/aggregate/privacy feed the
  render layer; renderers consume validated aggregates only.
- Model colors are deterministic presentation tokens with light/dark contrast
  checks. Unknown uses a neutral explicit row; color is not the only carrier
  of meaning.
- One commit with multiple model or provider records remains one unique commit;
  non-exclusive ledger counts do not inflate the headline.
- Raw model strings, repository names/paths, prompts, commit messages,
  organizations, emails, and SHAs do not cross the public asset boundary.
- README English/Traditional Chinese parity, real Profile examples, quickstart
  wording, and dashboard links are current for v0.6.0 Public Beta.

## Severity summary

| Severity | Count | Status |
|---|---:|---|
| Critical | 0 | none |
| High | 0 | none |
| Medium | 1 | closed before final merge |
| Low | 1 | accepted by design |

## Final recommendation

**READY FOR NEXT GATE**

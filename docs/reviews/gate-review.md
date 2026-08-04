# ai-profile v0.5.0 model-family gate review

Date: 2026-08-04
Review range: `c0a5b78..working tree` on `codex/v050-model-categories`
Reviewer posture: independent Principal Software Engineer; implementation
verification with adversarial model/privacy/render probes

## Executive summary

The candidate follows the approved architecture and MVP boundary. Model-family
contribution is an additive, explicit-evidence dimension: the aggregate layer
normalizes only ACE `model`, the privacy layer emits only closed public rows,
and renderers consume validated `VizStats` without Git, SQLite, network, or
attribution inference. Provider counts, unique commits, actor presences,
active days, evidence records, and model-family rows remain separate; one
commit may contribute to more than one model family without inflating the
unique-commit headline. Unknown remains distinct from Human.

No Critical or High implementation defect was reproduced. The only open gate
is release authority: CI must rebuild and verify the candidate on Ubuntu,
Windows, and macOS before publication.

## Verification evidence

| Area | Exact command/probe | Result |
|---|---|---|
| Full suite | `python -m pytest tests -p no:cacheprovider` | 667 passed, 4 skipped |
| Lint | `python -m ruff check src tests scripts` | All checks passed |
| README parity | `python scripts/check_readme_parity.py` | PASS |
| Summary regeneration | `python tests/unit/test_render_summary.py` | exit 0; 8 snapshots + 2 assets |
| Heatmap regeneration | `python tests/unit/test_heatmap_svg.py` | exit 0; 8 snapshots + 4 assets |
| Regeneration repeat | both sanctioned scripts run twice; hashes compared | zero diff across 25 files |
| Exact wheel smoke | `python scripts/release_smoke.py --wheel dist/ai_profile_cli-0.5.0-py3-none-any.whl --expected-version 0.5.0` | PASS: install, 8 outputs, CSP, privacy, determinism |
| Packaging | `python -m build`; `twine check`; `scripts/check_release_artifacts.py` | PASS |
| Browser | bundled Chromium matrix: 320/390/768/1280/1440, light/dark, reduced motion, effective 200% | PASS; no overflow; 3 model rows |
| Privacy byte sweep | snapshots, docs assets, dist; canary/email/path/SHA patterns | 27 files, zero hits |
| Independent review | code-reviewer and silent-failure-hunter probes | APPROVE; no Critical/High |

## Findings

### Medium — publication gate remains unverified

**Description:** This review was performed before a merged PR and before the
Ubuntu-authoritative build, three-platform onboarding smoke, PyPI publication,
and live Profile refresh.

**Impact:** Local Windows artifact evidence cannot establish the exact bytes and
cross-platform installation path users will receive.

**Recommendation:** Push the reviewed branch, require green CI/staging and the
same-byte Ubuntu artifact contract, then publish and perform a clean PyPI/live
Profile verification.

### Low — legacy empty model ledger compatibility

**Description:** `VizStats` intentionally permits `models=()` for older fixtures
and callers even when AI totals are nonzero; the production privacy builder
always supplies rows.

**Impact:** A caller that bypasses the production builder could publish totals
without model-family rows.

**Recommendation:** Retain for v0.5.0 source compatibility, keep the explicit
empty-state copy, and tighten only in a future contract/schema bump.

## Verified areas without findings

- Architecture boundaries and dependency direction remain intact.
- ACE vocabulary, schema/version handling, raw model redaction, and exact-type
  `VizStats` validation are consistent.
- Aggregation uses commit author dates, preserves non-exclusive model/provider
  units, and keeps unknown/human separation.
- Summary and dashboard are deterministic, flat, static, accessible, and
  free of external resources; model rows do not alter daily terrain geometry.
- README positioning now says provider-filterable dashboard plus an all-AI
  model-family ledger; it does not claim a model filter.

## Severity summary

| Severity | Count | Status |
|---|---:|---|
| Critical | 0 | none |
| High | 0 | none |
| Medium | 1 | release CI/publication gate open |
| Low | 1 | accepted compatibility note |

## Final recommendation

**NOT READY**

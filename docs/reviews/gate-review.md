# Current Gate remediation report

Date: 2026-07-15
Remediation range: working tree on top of `9933308` (uncommitted by task
constraint — commit authorization not granted; 18 modified files + 1 new
test file, verified by `git status --short`).
Reviewer posture: remediating implementer, with two mandatory independent
gates applied — the repository code-review skill (verdict APPROVE) and the
persistent independent code-reviewer agent (verdict APPROVE after
independent reproduction of every fix).

## Executive summary

All five findings of the prior review (`b899d11..9933308`, NOT READY:
1 High, 2 Medium, 2 Low) were independently reproduced BEFORE acceptance,
accepted 5/5, and fixed with regressions that each failed against the
pre-fix code. The High finding is closed structurally: a validated
`VizStats` can no longer carry arbitrary text into SVG or JSON — every
string field is pinned to a closed public vocabulary at construction.
Both Medium correctness defects (order-dependent merge timestamps, false
endpoint percentages) are closed with narrow contract fixes, and both Low
hardening items (unknown-mark contrast, sample regeneration path) are
resolved rather than deferred.

Final suite: **323 passed, 1 skipped** (baseline 310+1; +13 net new
regressions); Ruff clean; `git diff --check` clean; the full adversarial
probe battery re-ran green. Both independent reviews returned APPROVE
with only non-blocking suggestions, all of which were applied.

## Commands and exact outputs

- Baseline (pre-edit): `python -m pytest tests -p no:cacheprovider` →
  `310 passed, 1 skipped in 24.68s`; `python -m ruff check src tests` →
  `All checks passed!`; tree clean except the review file itself.
- Final: `python -m pytest tests -p no:cacheprovider` →
  `323 passed, 1 skipped in 16.36s` (exit 0); `python -m ruff check src
  tests` → `All checks passed!`; `git diff --check` → clean.
- Palette validator (both ordinal ramps, unchanged blues, re-run for the
  record): `ALL CHECKS PASS` light (`#033d8b,#0550ae,#0969da,#218bff` on
  `#f6f8fa`) and dark (`#a5d6ff,#58a6ff,#388bfd,#1f6feb` on `#161b22`).
- Contrast (changed token): light `#6e7781` vs `#f6f8fa` = **4.27:1**
  (was `#8c959f` = 2.85:1); dark `#6e7681` vs `#161b22` = 3.77:1.
- Adversarial probes re-run green: canary-rejection ×5 (period label,
  schema version, provider slug, display name, period bounds — each a
  reproduced pre-fix leak, each now fails at construction),
  reversed-timestamp merge equality, boundary percentages
  (1/201 → `<1%`, 200/201 → `>99%`, 0/10 → `0%`, 10/10 → `100%`),
  deterministic double render ×8 state/theme pairs, byte-level privacy
  sweep over all 8 snapshots + both `docs/assets` samples (only the
  required w3.org xmlns), README sample drift guard green.

## Disposition of every prior finding

### H-01 — ACCEPTED, fixed (structural)

Reproduced first: a fully validated `VizStats` carried
`SecretPeriod-Repo`, `SecretOrg-PrivateRepo`, a fake provider slug, and a
fake schema version verbatim into both `render_summary` and
`dumps_stats`. Fix (`src/aiprofile/viz.py`): `_validate` pins every
string field — `schema_version == ACE_SCHEMA_VERSION`; period must be the
fixed v0.1 all-time contract (`None` bounds, `V01_PERIOD_LABEL`);
provider slugs must come from `CANONICAL_PROVIDERS ∪ {unrecognized}`;
display names must equal the schema-owned display for the slug.
`PROVIDER_DISPLAY` moved into `src/aiprofile/schema/vocab.py` (the schema
owns the public vocabulary — the established H-02 precedent);
`registry.py` consumes it unchanged; `privacy.py` now imports
`V01_PERIOD_LABEL` (single source). Dependency direction unchanged:
`viz → schema.vocab` pre-existed; the render/export AST fence is
untouched; no renderer sanitization was added. `docs/architecture.md` §3
now states the enforcement. Regressions: `tests/unit/test_viz_contract.py`
(6 rejection + 2 construction cases, all rejections red pre-fix).
Consequence honestly recorded: two old render fixtures that DEPENDED on
arbitrary display names (long-name truncation, XML-escape) are no longer
constructable — by design; those renderer properties are now pinned at
the `_truncate`/`_text` helper layer, and the independent reviewer
verified this preserves (and in one respect extends) the original
coverage.

### M-01 — ACCEPTED, fixed

Reproduced first: same-identity leaves with different timestamps merged
to different canonical events under reversed input
(`canonical_equal False`). Fix (`src/aiprofile/schema/event.py`):
`timestamp=resolve("timestamp")` — the same strongest-leaf canonical rule
(ADR-008) used by the other scalars; permutation purity restored.
`docs/schema.md` §8.3 states the rule, including the reviewer's note that
the final tie-break is a deterministic string comparison, not a
chronological one (cross-offset sources should normalize before merge —
unreachable in v0.1). Regression: reversed-order byte-identity plus
strongest-leaf winner assertion, red pre-fix.

### M-02 — ACCEPTED, fixed

Reproduced first: `1/201 → "0% of 201"`, `200/201 → "100% of 201"`. Fix
(`src/aiprofile/render/summary_svg.py`): `_pct_label` — exact `0%`/`100%`
only for exactly-zero/exactly-total shares; a rounding that would
fabricate an endpoint renders `<1%` / `>99%` (deterministic, compact);
applied to the hero share and the provider rows. Aggregation values
untouched; fixture snapshots unaffected (no fixture share hits an
endpoint); label and share bar communicate compatible states (verified:
2px sliver + `<1%`, 358px + `>99%`). Regressions: both surfaces,
boundaries and exact endpoints, red pre-fix.

### L-01 — ACCEPTED, fixed

Reproduced first: light-theme `evidence_unknown` `#8c959f` at 2.85:1
against the `#f6f8fa` panel. Fix (`src/aiprofile/render/themes.py`):
Primer fg-muted `#6e7781` (4.27:1), still neutral and visually
subordinate; dark theme already passed. Both ordinal ramps re-validated
ALL CHECKS PASS; a contrast pin regression (≥3:1 both themes) was red
pre-fix for light. Exactly 3 light snapshots + the light sample asset
changed (2 rects each), regenerated via the sanctioned script.

### L-02 — ACCEPTED, fixed

Confirmed first: the sanctioned script wrote only `tests/snapshots`;
CONTRIBUTING documented snapshots only. Fix: `python
tests/unit/test_render_summary.py` now also regenerates both
`docs/assets` samples from the same authoritative fixture
(`_write_sample_assets`); `CONTRIBUTING.md` documents the single command
and forbids hand-editing; the byte-exact drift guard is unchanged.

## Newly discovered findings

None retained. Two non-blocking review suggestions were applied in-round
(period-label single-sourcing; the §8.3 tie-break note). One pre-existing
observation from the independent reviewer, explicitly not introduced by
this round and not blocking: `viz.py` itself is not in the AST
dependency-scan file list (runtime isolation already covers the chain
transitively) — a candidate for a future hardening pass.

## Verified areas without findings

- Renderer/exporter isolation: fresh-interpreter probe re-run — no
  banned modules load; `aiprofile/__init__.py` holds constants only, so
  the new `viz → package-root` import creates no cycle.
- Aggregation semantics: unique commits / presences / provider commits /
  active author-local days / evidence records remain distinct; unknown
  remains distinct from human; no inference.
- Privacy on the supported path: `privacy.build_viz_stats` unchanged in
  behavior; byte-level sweeps clean across dist-shaped outputs,
  snapshots, and committed samples.
- Determinism, XML well-formedness, element allowlist, coordinate
  hygiene, minimum font size, WIDTH 830, dynamic height ordering — all
  pinned tests green with the new states included in the loops.
- MVP scope: no new features, dependencies, network code, or duplication
  entered the diff.

## Severity summary (after remediation)

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |

## Final recommendation

READY FOR NEXT GATE

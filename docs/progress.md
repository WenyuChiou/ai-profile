# Progress — ai-profile

Maintained per the UltraCode run protocol: concise engineering decisions and observable results only.

## Current phase

**v0.1 vertical slice COMPLETE** — Phase 0 committed as `08f7413`; implementation committed as `50b8ac3` (161 tests green, independent gate review APPROVE, zero P0/P1). Editable install + console entry point verified (`aiprofile 0.1.0`).

## Completed

- 2026-07-14: Read `docs/proposal.md` in full. Repo state: fresh git repo, zero commits; unborn HEAD repointed from `master` to `main`. Python 3.14.0 available.
- 2026-07-14: Landscape research fan-out launched as a background workflow — 4 web-research lanes (attribution tools / tool attribution strings / profile stats generators / git-native mechanisms) on the cheap tier, plus one strong-tier adversarial verifier for the attribution-string registry claims.

## Decisions

Recorded in `docs/decisions/` as they are finalized. Non-delegable items (architecture, ACE schema, evidence precedence, dedup, privacy boundary) are authored directly by the orchestrator.

- 2026-07-14: `docs/schema.md` (ACE v0.1) finalized. Two documented deviations from the proposal: (1) `model` and `roles` excluded from dedup identity (count integrity, ADR-007); (2) unused proposal fields (metrics, integrity, human block, branch, confidence, visibility) deferred, not included (schema.md §12).
- 2026-07-14: `docs/architecture.md` finalized — VizStats is the structural redaction boundary; render/export import-isolation is test-enforced.
- 2026-07-14: `docs/mvp.md` finalized — v0.1 = vertical slice only; proposal §31 reclassified as v0.x roadmap. Deviation: two theme assets (`summary-light/dark.svg`) + `<picture>` embedding instead of single `summary.svg`.
- 2026-07-14: ADR-001..015 accepted (Python ≥3.11 zero-dep, argparse, dataclasses, sqlite3+ordered migrations, ACE trailer convention + known-AI co-author registry, notes ns reserved, deterministic IDs, evidence precedence, aggregate_only default, pure-python SVG, no v0.1 auth, semver schema, alias registry, reachability-based rewrite handling, author-email identity).
- 2026-07-14: Feasibility probe passed on git 2.47.1 — the pinned `git log --pretty=format:'%x1e%H%x1f...%x1f%(trailers:only,unfold)'` invocation produces exactly the record/field/trailer structure ADR-005 needs (multi-group + co-author preserved in order; body excluded; empty for trailer-less commits). Second probe: the portable bare form `%(trailers:only,unfold)` is byte-identical to `%(trailers:unfold,only=true)` on 2.47.1; the bare (git ≥2.17) form is pinned.
- 2026-07-14: Phase 0 three-lens adversarial review returned REQUEST_CHANGES ×3 (privacy 8 findings, consistency 12, complexity 9). All 29 adjudicated on disk; 27 fixed, 1 skipped with reason, 1 accepted in part (ledger below). Headline fixes: unrecognized raw trailer values now collapse to a reserved `unrecognized` bucket in public outputs (was a CRITICAL leak path); `AI-Mode: Human-Only` grouping exception added (the human category was unreachable — CRITICAL); publication policy now has exactly one home (config.json; DB column and per-event privacy block removed); the scans/last-seen mechanism replaced with atomic per-repo delete-and-reinsert (ADR-014 rewritten) plus a required amend/rescan test; excluded-repo counts removed from public outputs; diagnostics hygiene pinned; registry seed lists regenerated from landscape (cline dropped, six providers + three tools added); evidence/public-private metric units pinned (events/commits); `--from/--to`, `aggregate --json`, and `manifest.json` cut from v0.1; card gains unique-commits + provider-count metrics.
  - Skipped with reason: complexity finding "cut roles/human_reviewed from the event model" — the run protocol's vertical slice explicitly requires mapping role/mode/review status (slice req 5, WP-B acceptance); storage cost is two columns, re-adding later costs a migration. Documented as a named exception in schema.md's design stance.
  - Accepted in part: "canonical event JSON gates dead code" — kept a minimal deterministic `to_dict()` (tests/debug + future export consumer), dropped the standalone full-serialization test requirement.

## Delegated tasks

| id | task | model | status | accepted? |
|---|---|---|---|---|
| wf landscape L1–L4 | web research for landscape.md | sonnet | done | accepted after adversarial verification |
| wf landscape verify | adversarial verification of registry attribution strings | fable (inherited) | done | accepted — refuted 8 research claims incl. registry-critical string errors (Devin email prefix, Copilot fixed bot IDs, five wrong "no attribution exists" verdicts: Roo Code/OpenHands/Jules/Windsurf/Amazon Q); only verifier-confirmed strings seed registry.py |
| review lens 1 | Phase 0 consistency/contradiction review | fable (inherited) | done | accepted — 12 findings, all fixed (1 CRITICAL: unreachable human-only path) |
| review lens 2 | Phase 0 privacy/leak-path review | fable (inherited) | done | accepted — 8 findings, all fixed (1 CRITICAL: raw-trailer-value leak) |
| review lens 3 | Phase 0 complexity/prematurity/slice-fit review | fable (inherited) | done | accepted — 9 findings; 7 fixed, 1 skipped w/ reason, 1 partial |
| verify round | Phase 0 fix-pass verification | fable (inherited) | done | APPROVE 22/22; 3 residual MINORs fixed |
| commit gate | code-reviewer fresh generalist pass on 21-file staged diff | fable (inherited) | done | APPROVE; 2 suggestions applied/tracked |
| wf stage1 WP-A | unit tests: ACE schema + vocab + registry | sonnet (reason: code-from-pinned-spec above haiku floor; review stays strong-tier) | done (65 tests) | accepted after orchestrator review; lane's merge-semantics flag adjudicated as intended behavior |
| wf stage1 WP-B | trailer parser implementation + tests (pinned interface) | sonnet (same reason) | done (37 tests) | accepted WITH one orchestrator override: Human-Only + any AI-Provider/AI-Tool key is now contradictory regardless of registry resolution (regression test added, confirmed failing pre-fix, green post-fix; ADR-005 wording aligned) |
| wf stage1 WP-C | SQLite migrations/connection/atomic replace + tests | sonnet (same reason) | done | accepted after orchestrator review (autocommit + explicit BEGIN correct; DDL matches architecture §6; rollback tests assert full prior-state dumps). Non-blocking note: provenance UNIQUE is vacuous for NULL source_reference — only matters for post-v0.1 incremental upserts |
| wf stage1 WP-E | SVG themes + summary renderer + snapshot tests | sonnet (same reason) | done (26 tests, after API-error retry via workflow resume) | accepted after orchestrator review: pure/deterministic, escaped, aria-labelledby, top-6+overflow, zero-state; visual check both themes via Edge-headless rasterization passed (cosmetic note: fixed-height layout leaves dead space with <6 providers — deterministic-layout tradeoff, ADR-010) |
| WP-F | fixture repos + end-to-end integration gate | sonnet (same reason) | done (9 tests) | accepted after orchestrator review — hand-derivation table independently checked. Its environment finding (home dir is a git worktree) exposed a real product bug: scanning a path INSIDE a repo silently scanned the CONTAINING repo. Orchestrator fix: `scan` now requires the repository root (`rev-parse --show-toplevel` samefile check), regression tests added (confirmed failing pre-fix) |
| WP-D | aggregation implementation + tests (pinned RepoAggregates contract) | sonnet (same reason) | done (10 tests) | accepted after orchestrator review: set-difference human/unknown semantics, mixed→ai, whole-DB version guard first, author-local date prefix, COALESCE-exact raw collection; orchestrator re-ran suite: 123 passed |

## Phase 0 readiness report (2026-07-14)

- **Verdict: GO for implementation of the first vertical slice.**
- Consistency: three-lens adversarial review (privacy / consistency /
  complexity, all initially REQUEST_CHANGES) → 29 findings adjudicated →
  fix pass → independent verification round: **APPROVE, 22/22 resolutions
  verified on disk**; 3 residual MINORs (test-number cross-ref, tool-slug
  drift, unconsumed `%cI` field) fixed same day.
- Privacy: redaction is structural (VizStats boundary) + reserved
  `unrecognized` bucket for raw strings + config-only publication policy
  (fail-closed) + pinned diagnostics hygiene + two mandatory leak tests.
- Duplication: none — non-duplication matrix in landscape.md; line-level
  attribution explicitly reused-not-rebuilt; registry seeded from
  verified formats only.
- Premature features: cut during review (manifest.json, `--from/--to`,
  `aggregate --json`, scan-state machinery, per-event privacy block,
  truncated local uids).
- Slice implementability: every work package has pinned specs; git
  trailer extraction feasibility probed on the target git version.
- Recorded uncertainties: LICENSE choice (owner's legal decision, MIT
  recommended); landscape §7 unverified-claims ledger; forward
  constraints (manual-event preservation in the scan replace step,
  dedicated secret for future published anonymous IDs).

## Tests run

- 2026-07-14 (orchestrator, after stage-1 review + parser override): full suite — 113 passed, 0 failed; ruff clean.
- 2026-07-14 (orchestrator, WP-D + WP-E landed + orchestrator-authored import-isolation test): full suite — 150 passed, 0 failed; ruff clean.
- 2026-07-14 (orchestrator, manual end-to-end): `init/scan/aggregate/render` via `python -m aiprofile` on the trailer-probe fixture — every number matched hand-derived expectations (3 scanned / 2 AI-attributed / 3 participation events — co-author correctly MERGED with same-identity trailer group / 1 unknown / 2 active days / anthropic 2·2·2, openai 1·1·1 / declared 3 + unknown 1 / all private-aggregate). Bad-path: non-repo scan exits 1 with clean GitError. Fix applied during smoke: CLI stdout separators switched to ASCII (U+00B7 mojibaked on cp950 consoles). Visual verification of both theme cards via Edge-headless render: passed.

## Unresolved issues

- LICENSE choice is the repository owner's legal decision (MIT recommended for maximal reuse); flagged, file intentionally not created.

- 2026-07-14: `docs/landscape.md` synthesized (non-duplication matrix; verified registry seed table; unverified-claims ledger). mvp.md updated with two research-driven items: bot-authored-commit blind spot (known limitation) and Assisted-by/Generated-by parsing (post-v0.1).

- 2026-07-14: Phase 0 committed to main (`08f7413`, 21 files) after the full gate (3 lenses → fixes → verification APPROVE → code-reviewer APPROVE).
- 2026-07-14: Package skeleton + all orchestrator-owned modules written directly (non-delegable core): pyproject (hatchling, zero runtime deps, pythonpath=src), errors, vocab (StrEnum), event.py (identity/validation/merge — sanity-probed: model/roles excluded from identity, merge precedence correct), registry.py (verifier-confirmed seeds only), config.py (policy home, most-restrictive, fail-closed), gitio.py (pinned %(trailers:only,unfold) invocation), viz.py (redaction-boundary type with invariant validation), privacy.py (sole VizStats constructor), scanner.py (identity filter + unknown invariant), cli.py, export.py, README. Pinned-interface stubs for delegate lanes: adapters/trailers.py (contract docstring), aggregate.py (RepoAggregates + contract). ruff clean; core semantics probe green.

- 2026-07-14 (orchestrator, final): full suite `python -m pytest tests/ -p no:cacheprovider` — **161 passed, 0 failed** (150 unit incl. import-isolation + gitio root-only regressions, 9 integration, 2 new path tests); `ruff check src/ tests/` clean.

- 2026-07-14: Final gate — independent code-reviewer on the staged 48-file diff: **APPROVE, HIGH confidence, zero P0/P1** (re-ran suite + linter itself; attribution/privacy/robustness invariants independently traced; version-parity sweep clean). P2/P3 notes: NULL-source_reference uniqueness (tracked, post-v0.1), CLI unicode punctuation on rare OEM codepages (verified non-crashing on cp950/cp1252), single-pass git log at scale (fine for v0.1).
- 2026-07-14: Implementation committed to main (`50b8ac3`, 48 files, +6568). `pip install -e ".[dev]"` + `aiprofile --version` verified.

## Next action

Post-v0.1: next smallest vertical slice = Git Notes adapter (`refs/notes/ai-collaboration`) + git-ai import mapping into the `imported` evidence tier (mvp.md §10 item 1). Also pending: repository owner's LICENSE decision (MIT recommended).

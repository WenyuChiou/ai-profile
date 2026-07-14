# Progress — ai-profile

Maintained per the UltraCode run protocol: concise engineering decisions and observable results only.

## Current phase

Phase 0 — repository and landscape assessment (in progress).

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
| review lens 1 | Phase 0 consistency/contradiction review | fable (inherited) | running | — |
| review lens 2 | Phase 0 privacy/leak-path review | fable (inherited) | running | — |
| review lens 3 | Phase 0 complexity/prematurity/slice-fit review | fable (inherited) | running | — |

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

None yet (Phase 0 is documentation; test gate specified in mvp.md §7).

## Unresolved issues

- LICENSE choice is the repository owner's legal decision (MIT recommended for maximal reuse); flagged, file intentionally not created.

- 2026-07-14: `docs/landscape.md` synthesized (non-duplication matrix; verified registry seed table; unverified-claims ledger). mvp.md updated with two research-driven items: bot-authored-commit blind spot (known limitation) and Assisted-by/Generated-by parsing (post-v0.1).

## Next action

Phase 0 review gate (3 orthogonal adversarial lenses, running) → adjudicate findings on disk → fix → readiness report → gated commit of Phase 0 docs to main.

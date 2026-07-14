# Gate 2 findings disposition

Source: `docs/reviews/gate2-review.md` (independent architecture review,
GO WITH CHANGES). Adjudicated 2026-07-14 by the maintaining orchestrator;
owner for every accepted item is the maintainer unless noted. Verdict
handling per the review's closure criteria: Criticals + G2-05 resolved in
design AND implementation; remaining Highs fixed; rejections recorded with
reasons.

Chronology statement (part of the G2-03 resolution): the v0.1 vertical
slice was designed (Phase 0, `08f7413`), implemented (`50b8ac3`), and
polished (`49fdcbb`) before this external review was received. This gate
is therefore treated as **design approval with conditions plus a
conformance pass over the existing implementation** — not as
pre-implementation certification. `docs/ROADMAP.md` is now the
authoritative phase/exit-criteria document.

| ID | Sev | Disposition | Resolution (target: this pass unless noted) |
|---|---|---|---|
| G2-01 | Critical | **Accepted** | Repository identity canonicalization becomes a versioned pure function (`uid algorithm v2`, new ADR-016): host lowercased; path case preserved except on documented case-insensitive hosts (github.com); non-default port retained; credentials stripped and rejected from identity; scp/IPv6/query/fragment pinned; collision fixtures added. Local DBs/configs migrate by rescan (uid updated per path at scan). **Round 2 (conformance review caught gaps):** local-filesystem-shaped origins (relative/drive-letter/home/UNC/absolute) now yield no remote identity and fall to the `local:` branch — the verbatim-string path collided unrelated repos sharing `../template` and, via replace-by-uid, destroyed data; scp IPv6 brackets fixed; regression fixtures confirmed failing pre-fix. **Round 3 (reviewer survivor `vendor/upstream`):** shape enumeration replaced by a positive-remote-marker rule (non-file scheme, or scp colon-before-slash) with local as the fail-safe default — failure directions are asymmetric (remote-as-local splits a uid; local-as-remote destroys data); regression fixtures again confirmed failing pre-fix. |
| G2-02 | Critical | **Accepted** | Unit renamed **AI actor presences** everywhere (schema §15, `VizStats.ai_actor_presences`, profile.json, CLI, SVG labels + footnote, README, tests). Identity model unchanged; true participation events deferred until a source supplies a stable occurrence ID (ROADMAP). |
| G2-03 | Critical | **Accepted** | `docs/ROADMAP.md` published (authoritative phases + exit criteria); `docs/progress.md` reconciled to an honest snapshot with the chronology statement above; operational run log archived to `docs/reviews/v0.1-run-log.md`. |
| G2-04 | Critical | **Accepted** | Policy-based labels replace visibility claims: `explicitly_publishable_commits` / `anonymous_aggregate_commits` / `includes_anonymous_aggregate` in the contract; card/CLI wording updated ("aggregate-only (repository identity withheld)"). "Public/private" reserved until a collector verifies visibility (ROADMAP). |
| G2-05 | High | **Accepted** | Evidence population pinned: totals cover **all ACE records** (every actor type); `VizStats.evidence.total_records` added; validation asserts category sum == population; SVG/CLI labels state it. |
| G2-06 | High | **Accepted** | Canonical, order-free merge tie-break: higher evidence precedence → source-type priority (git_trailer > git_trailer_coauthor > manual_declaration > none) → lexicographic source locator → lexicographic value. Permutation tests added. **Round 2 (conformance review falsified the first closure):** the pairwise fold was not associative for 3+ productions (values borrowed pooled ranks; reproduced end-to-end with two reordered Co-authored-by lines) — replaced with a single N-ary `merge_event_group` reduction ranking each scalar against its own leaf; source union keeps the higher evidence on key collisions; exhaustive 24-permutation test over adversarial 4-leaf sets confirmed failing pre-fix, green post-fix. |
| G2-07 | High | **Accepted** | `source_reference` constrained to an enum of recognized locators per source type (schema validation, not prose); provenance documented local-only in the schema. |
| G2-08 | High | **Accepted** | Default diagnostics use scan-local ordinals ("commit #17"), never SHAs; full SHA only under `--verbose`, which future CI/Action mode must not enable (ADR-011). |
| G2-09 | High | **Accepted** | `docs/PRIVACY.md` (threat model) documents aggregate-only as **identity redaction, not anonymity**, incl. snapshot-differencing inference; README/preview wording aligned. Optional coarse mode → ROADMAP. |
| G2-10 | High | **Resolved by owner decision** | Repository owner chose **MIT** (2026-07-14). LICENSE + CONTRIBUTING.md added; registry-evidence policy noted in CONTRIBUTING. |
| G2-11 | Medium | **Rejected in part, with reason** | `roles`/`model`/`contribution_mode`/`human_reviewed` stay: the project's governing run protocol explicitly requires mapping role/mode/review status in the first slice (its WP-B acceptance tests them); they are implemented, tested, and green — post-hoc removal is churn (migration + parser + test deletions) with no risk reduction. Named exception already recorded in schema.md's design stance. Accepted parts: `recorded_at` handled via G2-14; inactive vocabulary stays legal (trivial enum cost, forward-compat) but is presented as reserved-without-producer. Revisit at the v0.2 schema review. |
| G2-12 | Medium | **Accepted** | `repository_anonymous` rejected at config validation in v0.1 with a targeted "reserved for post-v0.1" error; docs mark it reserved vocabulary. |
| G2-13 | Medium | **Accepted** | v0.1 declares SHA-1-only: SHA-256 repositories fail with a targeted `GitError` (no silent truncation); compatibility statement added to README; fixture test skips-with-reason where `git init --object-format=sha256` is unavailable. |
| G2-14 | Medium | **Accepted** | Envelope vs payload separated: `recorded_at` is audit envelope, excluded from canonical event serialization; schema.md defines both. |
| G2-15 | Medium | **Accepted (no action now)** | Policy resolution stays in config.py until a second consumer appears; extraction noted in ROADMAP. |
| G2-16 | Medium | **Accepted** | Static AST import-contract test added alongside the runtime module-graph test. |
| G2-17 | Medium | **Accepted** | ADR-006 softened to consume-first: `refs/notes/ai-collaboration` stays reserved but nothing is written until a field cannot be represented by existing formats; roadmap item reworded to "git-ai / existing-notes import first". |
| G2-18 | Medium | **Accepted** | Metric labeled "Active AI days (author dates)" in schema/CLI/card; timezone semantics documented; offset-boundary test already exists (aggregate test 4). |
| G2-19 | Low | **Accepted** | SVG security tests: element allowlist; no `script`/`foreignObject`, no event-handler attributes, no external URLs. |
| G2-20 | Low | **Accepted** | progress.md restructured to a concise current snapshot; historical run log archived under docs/reviews/. |

Additional review-body items (not in the register):

- **Evidence precedence critique (§8: `declared > imported` not universally
  valid; origin ≠ quality)** — *Accepted in part*: ADR-008 now marks the
  total order provisional and `imported` as an ingestion-origin marker;
  re-evaluation is a blocking precondition of the first importer (ROADMAP,
  v0.2). No v0.1 behavior change (no importer exists).
- **§13 missing-before-OSS list** — LICENSE/ROADMAP/threat model/
  CONTRIBUTING land in this pass; sample profile + clean-install smoke +
  compatibility matrix are pre-release items tracked in ROADMAP (README
  gains a short compatibility statement now).
- **§14 test additions** — collision pairs, permutation, SHA-256 error,
  SVG security, AST imports land in this pass; the remaining §14 catalog
  (property-based fuzzing, canary sweeps of stdout/stderr, cherry-pick
  semantics doc) is tracked in ROADMAP as pre-release hardening.

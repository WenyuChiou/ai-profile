# Roadmap

Authoritative phase order and exit criteria (Gate 2 finding G2-03). Where
this file and older phase sketches (proposal §31/§33, mvp.md §10) differ,
this file wins.

## Gate chronology (honest record)

Phase 0 design (`08f7413`), the v0.1 vertical-slice implementation
(`50b8ac3`), and the card polish (`49fdcbb`) all preceded the independent
Gate 2 architecture review (`docs/reviews/gate2-review.md`, GO WITH
CHANGES). Gate 2 is therefore **design approval with conditions plus a
conformance pass over the existing implementation** — not
pre-implementation certification. Finding dispositions:
`docs/reviews/gate2-disposition.md`.

## v0.1 — vertical slice (implemented; Gate 2 + Gate-3 conformance complete)

Scope: docs/mvp.md. Exit criteria:

- [x] One-repo scan → trailers → ACE → SQLite → aggregate → SVG/JSON.
- [x] Test gate green (unit + integration + snapshots).
- [x] Gate 2 accepted findings applied in design AND code: uid algorithm
      v2 (ADR-016, incl. round-2 local-path-origin guard), actor-presence
      naming, policy-based publication labels, evidence population,
      canonical N-ary merge reduction (round-2 rework after the pairwise
      fold was falsified), constrained provenance locators, SHA-free
      default diagnostics, SHA-256 targeted error, `repository_anonymous`
      rejection, envelope vs payload serialization, static import test,
      SVG security tests.
- [x] Implementation conformance review against the amended design
      (Gate 2 next action #4) — three adversarial rounds by one persistent
      reviewer: round 1 REQUEST CHANGES (uid local-path collision with a
      replace-by-uid data-loss path; non-associative pairwise merge),
      round 2 caught a surviving bare-relative origin (`vendor/upstream`),
      round 3 **APPROVE** (positive-remote-marker rule structurally
      mirrors git's own disambiguation; reviewer could not construct a
      further dangerous-direction counterexample). Every fix shipped with
      a regression test confirmed failing pre-fix.
- [x] Gate-3 implementation review (`docs/reviews/gate-review.md`, NOT
      READY, 23 findings) resolved: all 23 accepted
      (`docs/reviews/gate-disposition.md`), fixed with pre-fix-failing
      regressions — headline: **uid algorithm v3** (injective; supersedes
      v2 above), config-last atomic scans, alias-group migration,
      schema-owned canonical vocabulary with independent privacy-boundary
      collapse, pair-atomic merge. Persistent-reviewer verdict at the
      time: APPROVE — **superseded by the two later rounds below**, which
      each found real survivors in this round's fixes.
- [x] Verification review round (2026-07-14 evening; NOT READY, 3
      reproducible counterexamples against the Gate-3 fixes — headline:
      uid v3's github-alias branch collapsed all 42 scheme×port
      combinations) resolved: all accepted and fixed with pre-fix-failing
      regressions (`docs/reviews/gate-disposition.md`, appended section).
- [x] Gate-4 review round (2026-07-14 late evening; NOT READY, 8
      findings — headline: the leaf-only merge guard was bypassable via
      source dedup, and the endpoint-qualified uid change had shipped
      without its mandatory version bump) resolved: all 8 accepted and
      fixed — explicit `merged` derivation marker, **uid algorithm v4**
      (honest bump + decimal port normalization), pid-scoped export
      transaction files (later found process-owned, not attempt-owned;
      corrected in gate-5) with best-effort-stated rollback, the real
      42-case grid test committed (`docs/reviews/gate-disposition.md`,
      gate-4 section). Lesson recorded: the uid algorithm has NOT been
      adversarially validated "with no survivor" — three consecutive
      external rounds each falsified the previous round's closure claim.
- [x] Gate-5 review round (2026-07-15; READY AFTER MINOR FIXES, 0
      Critical/High, 3 Medium, 4 Low — first round with no High+
      finding) resolved: all 7 accepted and fixed — merge-purity claim
      narrowed to the sanctioned in-memory path and made normative in
      schema.md, per-invocation export transaction ids with an honest
      no-concurrency contract, bounded port validation (5000-digit
      probe), retraction failures in the raised error, envelope fields
      excluded from equality, true per-cell 42-grid parametrization
      (`docs/reviews/gate-disposition.md`, gate-5 section).
- [x] Gate-6 review round (2026-07-15; READY AFTER MINOR FIXES, 0
      Critical/High, 3 Medium, 3 Low) resolved: all 6 accepted and
      fixed — directory-probed exclusive export transaction suffixes
      (pid-reuse debris safe), **uid algorithm v5** (ASCII-decimal
      bounded port domain, honestly versioned after gate-5's bound
      changed v4 output unversioned), operational equality (`merged`
      participates; audit metadata excluded), concurrency wording
      aligned + user-facing precondition, storage pin relocated
      (`docs/reviews/gate-disposition.md`, gate-6 section).

## v0.1 OSS release (after conformance)

Exit criteria:

- [x] LICENSE (MIT, owner decision 2026-07-14) + CONTRIBUTING.md.
- [x] Threat model (`docs/PRIVACY.md`).
- [x] Sample profile output (committed example, docs/assets/).
- [x] clean-install/packaged smoke test — `scripts/release_smoke.py`
      (standalone release-time tooling, deliberately outside the
      network-free pytest suite; run green 2026-07-21).
- Pre-release hardening tests from Gate 2 §14 not landed in the
  conformance pass:
  - [ ] property-based unit-invariant fuzzing (next hardening pass).
  - [ ] canary sweeps over stdout/stderr/logs, not only dist/ (next
        hardening pass).
  - [x] cherry-pick cross-repository counting documented+tested
        (schema.md §8.4 + `tests/integration/test_cherry_pick.py`,
        2026-07-21).
  - [x] owner-only file permissions where supported (0o700 home /
        0o600 config+db, POSIX-enforced, documented Windows no-op,
        2026-07-21).
  - [x] warn when `AIPROFILE_HOME` is inside a git worktree
        (2026-07-21).
- [ ] Packaged release (not editable-install-only) + upgrade policy note.

## v0.2 — import and reconciliation

Preconditions before any importer ships:

- ADR-008 evidence-precedence re-evaluation (`imported` is origin, not
  quality; conflict surfacing vs total order).
- Actor-presence semantics unchanged; true participation events require a
  source-provided stable occurrence ID (G2-02).

Scope: git-ai / existing-notes import (consume-first, ADR-006);
`aiprofile reconcile` + `mixed` producer (scan replace step must preserve
manual events — schema.md §14); bot-authored/human-co-authored identity
inclusion (spoofing fixtures required); v0.2 schema review revisits the
G2-11 field set and `repository_anonymous`.

## v0.3 — views and periods

Provider breakdown / evidence / publication cards and calendars (reusing
the summary card's token system); period filters (author-local-date
boundary rule, schema.md §15); dedicated `privacy-preview` with per-repo
views; optional coarse aggregation mode (rounding/thresholds — G2-09);
`purge` helper; policy-resolver extraction when the second consumer
appears (G2-15). An `aiprofile doctor`-style diagnostic listing
stale/unresolvable alias config entries (gate-3 reviewer suggestion —
improves the C-03 fail-closed UX without weakening it).

## v0.4+ — GitHub integration

Public-API discovery wrapping the official REST/GraphQL API (mature
client or `gh api`; never ad hoc auth/pagination/rate-limit code —
Gate 2 §7); verified-visibility labels become possible here (G2-04);
fine-grained PAT posture per ADR-011; reusable Action (+ manifest.json)
with CI log hygiene enforced; incremental scanning once a measured
threshold justifies it (architecture §11).

## Explicit non-goals (any version)

Line-level attribution (git-ai's domain), AI code detection / style
inference, hosted dashboards, generic GitHub stats, prompt/transcript
storage.

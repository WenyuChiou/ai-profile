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

## v0.1 — vertical slice (implemented; Gate 2 conformance in progress)

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

## v0.1 OSS release (after conformance)

Exit criteria:

- [x] LICENSE (MIT, owner decision 2026-07-14) + CONTRIBUTING.md.
- [x] Threat model (`docs/PRIVACY.md`).
- [ ] Sample profile output (committed example) + clean-install smoke test.
- [ ] Pre-release hardening tests from Gate 2 §14 not landed in the
      conformance pass: property-based unit-invariant fuzzing; canary
      sweeps over stdout/stderr/logs (not only dist/); cherry-pick
      cross-repository counting documented+tested; owner-only file
      permissions where supported; warn when `AIPROFILE_HOME` is inside a
      git worktree.
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
appears (G2-15).

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

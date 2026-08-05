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
- Pre-release hardening tests from Gate 2 §14:
  - [x] property-based unit-invariant fuzzing (Round B, 2026-07-22).
  - [x] canary sweeps over stdout/stderr/logs and published artifacts
        (Round B, expanded by the packaged smoke).
  - [x] cherry-pick cross-repository counting documented+tested
        (schema.md §8.4 + `tests/integration/test_cherry_pick.py`,
        2026-07-21).
  - [x] owner-only file permissions where supported (0o700 home /
        0o600 config+db, POSIX-enforced, documented Windows no-op,
        2026-07-21).
  - [x] warn when `AIPROFILE_HOME` is inside a git worktree
        (2026-07-21).
- [x] Packaged release + upgrade policy — `ai-profile-cli` is live on
      PyPI. v0.4.2 adds an exact-artifact contract, clean-wheel smoke,
      third-party-notice regression, and three-platform onboarding CI.

## Future capability milestone — import and reconciliation

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

## Future capability milestone — richer views and periods

Provider breakdown / evidence / publication cards and calendars (reusing
the summary card's token system); period filters (author-local-date
boundary rule, schema.md §15); dedicated `privacy-preview` with per-repo
views; optional coarse aggregation mode (rounding/thresholds — G2-09);
`purge` helper; policy-resolver extraction when the second consumer
appears (G2-15). An `aiprofile doctor`-style diagnostic remains deferred.
Public Beta promotion does not add configuration or policy CLI commands;
README-only dogfood determines whether that work becomes a separately
designed v0.5.0 plan.

## v0.4 — self-contained interactive dashboard

- [x] Generate one deterministic `dashboard.html` from validated
      `VizStats`, with no framework, external assets, network calls, or
      telemetry (ADR-021).
- [x] Switch between all-provider and one-provider views using existing
      unique-commit, actor-presence, active-day, and daily aggregate units.
- [x] Keep evidence visibly global (“All ACE records”) rather than
      pretending provider-scoped evidence exists.
- [x] Responsive light/dark presentation, keyboard-operable filters,
      visible focus, reduced-motion support, and mobile overflow checks.
- [x] Preserve the static SVG README strategy; link to the generated HTML
      when users want interaction.

## v0.4.8 — HR-first visual refresh (released 2026-08-01, Public Beta)

- [x] Summary card redesigned as the recruiter-first `AI Collaboration
      Record` (ADR-022): hero + share, secondary ledger, prominent
      12-week isometric collaboration terrain (bar height = total-commit
      bins, fill = AI-share bins, provider-independent geometry),
      non-exclusive provider ledger, compact evidence rail.
- [x] Dashboard headline and summary type system aligned with the shared
      editorial-tech direction; README example simplified to the Summary
      Card with the heatmap moved to "What gets generated".
- [x] Release round (canonical Ubuntu build, frozen candidate digest,
      dogfood rerun, promotion review) per docs/RELEASING.md — completed
      2026-08-01. Released as Public Beta from `main` commit `b4e2178`
      (tag `v0.4.8`; GitHub Release marked prerelease, PyPI classifier
      Beta). Readiness record:
      `docs/reviews/v0.4.8-release-readiness.md`.

## v0.4.9 — Flat Evidence Ledger Public Beta (released 2026-08-04)

- [x] Evidence-ledger alignment (ADR-023): separate provider count and
      percentage columns, keep section markers semantic, and preserve the
      existing renderer/data/privacy contract.
- [x] Flat Evidence Ledger visual contract (ADR-025): document semantic roles,
      local fallback typography, the evidence-first composition grammar, and
      the no-gradient/no-network/no-inference boundary in `DESIGN.md`.
- [x] Replace the perspective daily treatment with a deterministic flat
      matrix and neutral dashboard section markers; the matrix preserves daily
      height/share and provider/commit aggregation semantics.
- [x] Complete the independent visual, accessibility, privacy, and artifact
      review; candidate artifact identity is frozen in
      `docs/reviews/promotion-candidate.json`; the readiness record is
      `docs/reviews/v0.4.9-flat-ledger-readiness.md`.
- [x] Complete the PR/CI, immutable artifact publication, clean-install smoke,
      and maintainer Profile refresh. Tag `v0.4.9` is live at commit
      `876bab3`; final release evidence is recorded in
      `docs/reviews/v0.4.9-release-readiness.md`.

## v0.4.10 — Editorial Signal Public Beta (released 2026-08-04)

- [x] Keep the flat 12-week Evidence Ledger and add sparse editorial
      alignment rails plus the shared two-part section marker (ADR-026).
- [x] Re-run local renderer, dashboard, privacy, determinism, packaging, and
      browser gates. Pre-publication candidate evidence:
      `docs/reviews/v0.4.10-visual-qa.md`.
- [x] Run the cross-platform release workflow and publish the exact artifact.
      Released as Public Beta from `main` merge commit `91260bd` (PR #21,
      tag `v0.4.10`; the GitHub Release is marked prerelease and the PyPI
      classifier is Beta). Publish run `30922283841` and PR CI run
      `30921682522` passed; the canonical wheel digest is
      `41c91d01ee761abc5a22add1c2a2fb8d3b36e309411b5db0398a7eae7824cd7a`.
      Final release evidence:
      `docs/reviews/v0.4.10-release-readiness.md`.
- [x] Regenerate the maintainer Profile from the exact public artifact after
      the release workflow and Pages checks pass. Profile PR #14 merged at
      `9c346fd`; Pages run `30924497319` and the snake run `30924498845`
      passed, and all eight live outputs match the merged LF-normalized
      blobs.

## v0.5.0 — Explicit model-family contribution (released 2026-08-04, Public Beta)

- [x] Implement ADR-027's closed model-family aggregate as ACE/public contract
      `0.3.0`; keep `0.1.x` and `0.2.x` stored events readable.
- [x] Reconcile model-family attributed commits, actor presences, active days,
      provider rows, unique commits, evidence records, and unknown/human
      separation on synthetic and real-profile fixtures.
- [x] Publish only schema-owned family labels (`unknown` remains separate;
      raw model strings stay local-only); no style/provider/tool inference.
- [x] Add the compact model ledger to the summary SVG and dashboard without
      changing the flat daily terrain or claiming model-by-day filtering.
- [x] Complete the independent cross-platform and publication gates. The
      Ubuntu-authoritative wheel passed exact-wheel onboarding on Ubuntu,
      macOS, and Windows; PyPI and GitHub Release publication completed from
      tag `v0.5.0` at main merge `4e369c6` (GitHub Release is prerelease; PyPI
      classifier remains Beta). Final evidence:
      `docs/reviews/v0.5.0-release-readiness.md`.
- [x] Refresh the maintainer Profile from that exact public artifact. Profile
      PR #15 merged at `ead0f41`; Pages run `30937320357` and the snake run
      `30937324074` passed, and all eight live outputs match the merged
      LF-normalized blobs.

## v0.6.0 — Stable model-family visual key (released 2026-08-04, Public Beta)

- [x] Add a stable, contrast-checked category mark and bar palette for the
      canonical model families in the Summary Card and self-contained
      dashboard. Unknown remains a neutral, explicit row.
- [x] Keep the daily matrix semantically unchanged: column height is unique
      daily commit volume and fill is daily AI share. The model ledger is an
      all-time, non-exclusive view; no model-by-day inference or filter is
      exposed without a validated cross-dimension aggregate.
- [x] Preserve the ACE schema, aggregation units, privacy boundary, CLI, and
      eight-output contract. No external fonts, network calls, animation,
      gradients, or 3D surface were introduced.
- [x] Publish the exact candidate from main merge `76c003b` as tag `v0.6.0`.
      The Ubuntu-authoritative wheel SHA-256 is
      `7ea7b3db484615d5f361d2ba0a237819a94757065b47464efb1d8058bf0ba789`;
      final evidence is recorded in
      `docs/reviews/v0.6.0-release-readiness.md`.
- [x] Refresh the maintainer Profile from the released wheel. Profile PR #16
      merged at `ca12bdd`; Pages run `30944387849` and the snake run
      `30944389155` passed, and all eight live outputs returned HTTP 200.

The v0.6.0 model visual is a historical release surface. ADR-029 now keeps
the model-family aggregate in ACE/profile data while making the provider ledger
the sole model/provider contribution visual in current SVG and dashboard
renderers.

## v0.6.1 - Provider-ledger-only visual correction (2026-08-05, Public Beta candidate)

- [x] Remove the duplicate model-family presentation from the Summary Card and
      self-contained dashboard while retaining canonical model evidence in
      `VizStats` and machine-readable `profile.json`.
- [x] Preserve ACE/public schema `0.3.0`, aggregation units, CLI behavior,
      privacy boundary, and the eight-output contract. No new model-by-date
      inference or schema field is introduced.
- [x] Use a patch version because the published v0.6.0 candidate is immutable;
      freeze the v0.6.1 candidate in `docs/reviews/promotion-candidate.json`
      with the Ubuntu-authoritative wheel digest
      `6ca24828fbba02024904028fa8fa5f96e97a8393d3f5e16bb6ff316cff477b9f` and
      staging dashboard digest
      `8172a3eac4c61232a2a0331edce4435b91a124b230a37a55505b11a5ba4f4eb1`.

## Future capability milestone — GitHub integration

Public-API discovery wrapping the official REST/GraphQL API (mature
client or `gh api`; never ad hoc auth/pagination/rate-limit code —
Gate 2 §7); verified-visibility labels become possible here (G2-04);
fine-grained PAT posture per ADR-011; reusable Action (+ manifest.json)
with CI log hygiene enforced; incremental scanning once a measured
threshold justifies it (architecture §11).

## Explicit non-goals (any version)

Line-level attribution (git-ai's domain), AI code detection / style
inference, a hosted dashboard **service** or analytics backend, generic
GitHub stats, prompt/transcript storage.

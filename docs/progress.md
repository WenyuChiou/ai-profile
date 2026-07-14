# Progress — current snapshot

Concise state of the project (G2-20: history lives in
`docs/reviews/v0.1-run-log.md`; future scope lives in `docs/ROADMAP.md`,
which is authoritative).

## Where things stand (2026-07-14)

- **v0.1 vertical slice implemented and reviewed**: Phase 0 design
  (`08f7413`) → implementation, 165 tests green (`50b8ac3`) → summary-card
  polish (`49fdcbb`).
- **Gate 2 independent architecture review received**: GO WITH CHANGES
  (`docs/reviews/gate2-review.md`). All 20 findings adjudicated in
  `docs/reviews/gate2-disposition.md` (Criticals + Highs accepted or
  resolved; G2-11 rejected in part with recorded reason).
- **Gate 2 conformance pass COMPLETE**: design docs amended (schema,
  architecture, mvp, ADR-005/006/007/008/009, new ADR-016); ROADMAP.md,
  PRIVACY.md, LICENSE (MIT — owner decision), CONTRIBUTING.md published;
  code conformed (uid algorithm v2 with positive-remote-marker rule,
  actor-presence rename, policy-based publication labels, evidence
  population + invariants, N-ary canonical merge reduction, diagnostics
  ordinals, SHA-256 targeted error, locator validation, envelope
  serialization, static import + SVG security tests). Implementation
  conformance review: three adversarial rounds to **APPROVE** — round 1
  found two real defects (uid collision with data-loss path;
  non-associative merge), round 2 a surviving origin shape; all fixed
  with pre-fix-failing regressions. Suite: **212 passed, 0 failed**;
  ruff clean.

## Open items

- Pre-OSS-release items tracked in ROADMAP (sample profile, hardening
  tests, packaged release).

## Pointers

- Roadmap: `docs/ROADMAP.md` · Threat model: `docs/PRIVACY.md`
- Reviews: `docs/reviews/` (Gate 2 review, disposition, v0.1 run log)
- Contracts: `docs/schema.md`, `docs/architecture.md`, `docs/mvp.md`,
  `docs/decisions/`

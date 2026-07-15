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

- **Gate-3 implementation review received and resolved** (2026-07-14):
  `docs/reviews/gate-review.md` (independent, verdict NOT READY, 23
  findings) → all 23 adjudicated ACCEPTED in
  `docs/reviews/gate-disposition.md` (M-09/M-11 via documented decisions).
  Resolved in code+design, each code fix with a pre-fix-failing
  regression:
  - C-01/C-02/H-01/M-04 → **uid algorithm v3** (injective structured
    encoding, scheme retained, github-only transport convergence,
    case-preserved local hash, last-`@` credential strip, query/fragment
    parity, `.GIT` folding) — ADR-016 rewritten;
  - C-03/C-04 → scan is config-last atomic (failures leave config
    byte-identical), alias-group uid migration with fail-closed halt and
    same-transaction old-row purge;
  - H-02 → canonical slugs are schema-owned vocabulary enforced at
    `build_event` AND independently collapsed at the privacy boundary;
  - H-03/H-05/M-10/M-12 → duplicate-source dedup to highest evidence;
    offset-aware timestamps, human-evidence rule, provenance enum
    coercion, bool review flag; pair-atomic canonical/raw merge; pairwise
    merge API removed (N-ary only);
  - H-04 → object-format preflight (catches empty SHA-256 repos) with
    path-free errors, before any mutation;
  - M-01/M-02/M-03/M-05/M-07 → provider-row validation; recursive AST
    import contract incl. dynamic imports; key-presence Human-Only
    contradiction; uid/org/salt canaries + published-output permutation
    invariance tests; bundle-atomic dist/ writes;
  - M-06/M-08/M-09/M-11/L-01/L-02 → contradiction sweep across
    mvp/schema/README/CLI-help/ADR-008/ADR-009, privacy→registry edge
    documented, `aggregate -v` scope corrected, ADR-012 pre-release
    exception, terminology sweep, historical banner on the archived run
    log.
  Suite after the pass: **240 passed, 1 skipped** (the skip is the POSIX
  case-sensitivity fixture, not runnable on Windows — documented); ruff
  clean.

- **Verification review received and resolved** (2026-07-14 evening):
  `docs/reviews/gate-review.md` (overwritten with the verification round;
  prior content preserved in git history at `de4a78a`) verified 20/23
  dispositions and produced three reproducible counterexamples — all
  accepted (`docs/reviews/gate-disposition.md`, appended section) and
  fixed with pre-fix-failing regressions:
  - **Critical**: github alias convergence now requires the documented
    `(scheme, effective-port)` endpoints (`ssh:22`/`https:443`/`git:9418`);
    the 42-combination scheme×port grid no longer collapses (verified at
    the time by an ad-hoc probe only — the committed parameterized grid
    test landed in the gate-4 round, finding L-2) — ADR-016 rule 4
    amended;
  - **Medium**: dist/ replacement stage gained best-effort rollback
    (olds moved aside, restored on failure) with a replacement-stage
    failure-injection test;
  - **Medium**: `merge_event_group` now ENFORCES its leaf-only boundary
    (at the time via a source-count heuristic — proven bypassable and
    over-broad by the gate-4 review and replaced by the explicit
    `merged` derivation marker); nested composition raises — replicated
    the reviewer's nested probe;
  - L-01 completion: the two legacy tests demonstrating non-leaf usage
    rewritten.
  Suite: **244 passed, 1 skipped**; ruff clean; e2e green.

- **Gate-4 review received and resolved** (2026-07-14 late evening):
  `docs/reviews/gate-review.md` (overwritten with round 4; prior rounds
  preserved in git history) reviewed `de4a78a..4fdd490`, verdict NOT
  READY, 8 findings (1 High, 5 Medium, 2 Low) — all accepted
  (`docs/reviews/gate-disposition.md`, gate-4 section) and fixed with
  pre-fix-failing regressions:
  - **High + M-2**: leaf-only merge boundary is now an explicit
    derivation marker (`AceEvent.merged`, envelope metadata) instead of
    the bypassable source-count heuristic — nested composition rejected
    even when sources dedup to one; schema-valid multi-source leaf
    productions merge again;
  - **M-4 + M-5**: **uid algorithm v4** — the endpoint-qualified alias
    rule now lives under an honestly bumped version (schema §7 and
    ADR-016 rewritten to match), and ports normalize to canonical
    decimal (`:0443` ≡ `:443`) before endpoint lookup/serialization;
    `canonicalize_remote` is version-neutral, `UID_ALGORITHM` is the
    single version authority;
  - **M-3 + M-6 + L-1**: export rollback attempts EVERY restore
    (failures collected; unrestorable assets keep their backup, named
    in the error), transaction artifacts are attempt-owned
    (`<target>.<pid>.tmp/.bak` — user `.bak` files survive, concurrent
    renders can't consume each other's files), and post-publication
    cleanup failure is a warning, not a false `RenderError`; the
    docstring now states the honest best-effort guarantee;
  - **L-2**: the claimed 42-case scheme×port grid is now a real
    committed parameterized test computing expected equivalence classes
    from the rule.
  Suite after the pass: **256 passed, 1 skipped**; ruff clean;
  integration/e2e green.

## Open items

- Pre-OSS-release items tracked in ROADMAP (sample profile, hardening
  tests, packaged release).

## Pointers

- Roadmap: `docs/ROADMAP.md` · Threat model: `docs/PRIVACY.md`
- Reviews: `docs/reviews/` (Gate 2 review, disposition, v0.1 run log)
- Contracts: `docs/schema.md`, `docs/architecture.md`, `docs/mvp.md`,
  `docs/decisions/`

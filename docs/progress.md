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
    in the error), transaction artifacts gained pid-scoped names (at
    the time claimed attempt-owned — the gate-5 review showed pid =
    process-owned, fixed with per-invocation ids in round 5), and
    post-publication cleanup failure is a warning, not a false
    `RenderError`; the docstring states a best-effort guarantee;
  - **L-2**: the claimed 42-case scheme×port grid landed as a committed
    exhaustive test (at the time a looped grid — converted to true
    per-cell parametrize in round 5, finding L-02).
  Suite after the pass: **256 passed, 1 skipped**; ruff clean;
  integration/e2e green.

- **Gate-5 review received and resolved** (2026-07-15):
  `docs/reviews/gate-review.md` reviewed `4fdd490..78e2e05`, verdict
  READY AFTER MINOR FIXES (0 Critical/High, 3 Medium, 4 Low) — all 7
  accepted (`docs/reviews/gate-disposition.md`, gate-5 section), each
  behavioral fix with a pre-fix-failing regression:
  - **M-01**: the merge-purity closure claim is NARROWED to the
    sanctioned in-memory scan path and made normative — schema.md §1
    now defines derivation state (`merged`: envelope-only, never
    serialized/persisted; rehydrated events are not re-mergeable in
    v0.1; out-of-contract construction acknowledged), §8.3 states the
    guard's scope; pinned by a canonical-payload + SQLite-schema
    regression;
  - **M-02**: export transaction ids became `<pid>-<n>` (the gate-6
    review showed this is still process-owned across pid reuse — closed
    in round 6 with directory-probed suffixes); the concurrency
    contract DECLARES concurrent publication unsupported (can mix
    generations — wording corrected in round 6: nothing is actively
    rejected at runtime) instead of claiming whole-generation
    isolation; recovery-`.bak` survival regression;
  - **M-03**: port tokens are bounded before int conversion (>65535 or
    >5 digits → unusable origin → local fallback, the fail-safe
    direction) — a 5000-digit port no longer escapes as ValueError;
  - **L-01**: failed first-install retractions are named in the raised
    RenderError (no longer log-only);
  - **L-03**: envelope fields (`recorded_at`, `merged`) excluded from
    dataclass equality/hash — value equality now agrees with canonical
    event equality; semantics documented in schema.md §1;
  - **L-02/L-04**: the 42-cell grid is now genuinely per-cell
    parametrized (42 reported cases); export-test fixture deduplicated.
  Suite after the pass: **302 passed, 1 skipped**; ruff clean.

- **Gate-6 review received and resolved** (2026-07-15 morning):
  `docs/reviews/gate-review.md` reviewed `78e2e05..b899d11`, verdict
  READY AFTER MINOR FIXES (0 Critical/High, 3 Medium, 3 Low) — all 6
  accepted (`docs/reviews/gate-disposition.md`, gate-6 section), each
  behavioral fix with a pre-fix-failing regression:
  - **M-01**: export transaction suffixes are directory-probed and
    exclusively created — a reused pid replaying a dead process's
    counter can no longer clobber retained recovery artifacts; counter
    lock-protected;
  - **M-02 + M-03**: **uid algorithm v5** — port domain honestly
    versioned (ASCII decimal only, canonical decimal, 0..65535;
    violations → local fallback): gate-5's bound had changed v4 output
    without a bump, and Unicode decimal ports (`:４４３`) minted split
    non-ASCII identities; ADR-016 + schema §7 rewritten;
  - **L-01**: equality is OPERATIONAL — `recorded_at` excluded,
    `merged` participates (it decides merge admissibility; set dedup
    can never flip merge behavior) — schema §1 specifies operational
    vs canonical-payload equality;
  - **L-02**: concurrency wording aligned ("unsupported", nothing
    actively rejected); precondition surfaced in `render --help` and
    README;
  - **L-03**: the persisted-schema pin moved to the storage test suite.
  Suite after the pass: **309 passed, 1 skipped**; ruff clean.

- **Visual refinement round (gate-6 Phase 3, 2026-07-15)**: summary card
  redesigned to the owner's "Governed Intelligence Editorial" direction —
  executed by a Codex delegate under a constrained brief, review-gated by
  Claude, then audited against the dataviz design skill:
  - one hero metric (AI-attributed commits) with its share of unique
    commits stated and drawn (thin share bar); presences / active days /
    providers / unknown as a subordinate right-aligned ledger;
  - evidence + privacy pills replaced by a provenance panel: stacked
    evidence-composition bar in precedence order with a swatch legend
    (counts always text), one quiet privacy statement line;
  - evidence ramps are VALIDATOR-PASSED ordinal Primer-blue scales per
    theme (the delegate's first ramps failed the 2:1 light-end contrast
    floor at 1.64:1/1.86:1 — computed, not eyeballed); segment gaps show
    the panel surface; sparkle glyph replaced by a commit-node mark;
  - reviewer round found a real defect (remainder-sized last segment
    could go NEGATIVE for 3+ lopsided evidence categories) — fixed with
    cumulative rounding (widths >= 0 and exact-sum structurally), red
    regression from the reviewer's own reproduction; reviewer re-ran a
    3,008-case randomized adversarial search, zero violations → APPROVE;
  - all 8 snapshots regenerated via the sanctioned script and visually
    verified in a real browser (both themes; populated / aggregate-only /
    all-publishable / zero states); privacy sweep clean (only the w3.org
    xmlns matches); mvp.md section 5 + ADR-010 composition wording
    updated.
  Suite after the round: **309 passed, 1 skipped**; ruff clean.

- **Aesthetic polish round (2026-07-15, Codex delegate)**: owner-directed
  craft pass over the approved composition — 4px spacing scale swept
  through every section (hero rhythm, 24px ledger step, 28px table rows,
  panel 16/16 padding at height 104, footer/zero-state), type scale
  locked to 11/12/13/16/38 (hero up to 38px, title down to 16px, panel
  evidence label promoted to a 12px weight-600 section label), 0.2
  letter-spacing on the two section labels; zero color changes
  (validator-locked ramps untouched). Reviewer APPROVE after independent
  probes (panel fit, deliberate y=160 baseline alignment with >=225px
  x-margin, letter-spacing XML-safety); its one suggestion applied: the
  evidence-segment regression selector now anchors on the bar's own y
  coordinate, removing the implicit BAR_HEIGHT/ramp-color coupling.
  Suite: **309 passed, 1 skipped**; ruff clean.

## Open items

- Pre-OSS-release items tracked in ROADMAP (sample profile, hardening
  tests, packaged release).

## Pointers

- Roadmap: `docs/ROADMAP.md` · Threat model: `docs/PRIVACY.md`
- Reviews: `docs/reviews/` (Gate 2 review, disposition, v0.1 run log)
- Contracts: `docs/schema.md`, `docs/architecture.md`, `docs/mvp.md`,
  `docs/decisions/`

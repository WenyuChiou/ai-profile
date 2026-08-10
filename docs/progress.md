# Progress — current snapshot

Concise state of the project (G2-20: history lives in
`docs/reviews/v0.1-run-log.md`; future scope lives in `docs/ROADMAP.md`,
which is authoritative).

## v0.7.0 automation candidate — local evidence only (not released)

- ADR-030 adds an orchestration layer without changing ACE `0.3.0`,
  aggregation semantics, `VizStats`, renderer purity, or the eight-output
  contract. Phase A (`3b57ac6`) implements fail-closed configured-repository
  refresh, logical-state-preserving dry-run, and per-home locking. Phase B (`18a17f1`)
  implements the native scheduler and exact-eight Git publication with
  per-home native identity and residual-honest rollback.
- The reusable public-only workflow is frozen at commit
  `9c4f276cb437f1866a2c1b407efe54d3790ce811`. The copyable caller at
  `f92c5c4` pins that exact commit, consumes its immutable `published-sha`,
  and serializes refresh through same-run Pages deployment. Identity emails
  enter as a secret; public repository inputs are validated before
  credential-disabled clone; raw output from workflow-owned visibility,
  clone, commit, and push subprocesses is suppressed.
- Frozen Phase C evidence: **840 passed, 21 skipped**, Ruff clean, README
  parity pass, sanctioned snapshot/sample zero drift, and substantive WSL
  workflow probes. Both independent security/code reviewers approved the
  frozen bytes. This is candidate evidence, not evidence of a live scheduled
  run, released wheel, tag, PyPI artifact, or Pages deployment.
- Phase D synchronized the English/Traditional Chinese consumer guidance,
  ADR-030, architecture, privacy, release, roadmap, and contributor contracts.
  The multi-locale gate passed; the full suite passed **845 tests with 21
  skipped**, with Ruff, README parity, and sanctioned snapshot drift checks
  green. Phase E froze the local 0.7.0 candidate at
  `SOURCE_DATE_EPOCH=1786233600`: two isolated Ubuntu builds from the same
  Git-mode source archive produced byte-identical wheel and sdist artifacts.
  The wheel is
  `9d8b39a5d25f9100c671fda8a7945c6403ac67ead161b16bbe17e26d4bac3523`
  and the synthetic dashboard remains
  `8172a3eac4c61232a2a0331edce4435b91a124b230a37a55505b11a5ba4f4eb1`.
  Twine, artifact/checksum validation, clean-wheel refresh smoke, current and
  Python 3.11 release-contract tests, the full **847 passed / 21 skipped**
  suite, Ruff, README parity, and snapshot zero-drift all passed. This is
  local candidate evidence only, not published or cross-platform CI evidence.
- Release remains blocked on Phase E cross-platform PR gates, the committed-
  range independent review, the v0.7.0 tag/Public Beta publication, and
  post-release maintainer dogfood. The maintainer Profile will use the local
  scheduler because its configured set includes an `aggregate_only` source;
  it will not be migrated to the public-only Action.

## Current v0.6.1 Public Beta (2026-08-05)

- The provider ledger is now the sole model/provider contribution visual in
  current Summary Card and dashboard renderers. Canonical model rows remain in
  `VizStats` and machine-readable `profile.json`; no model evidence is lost.
- This is a presentation-only patch release: ACE/public schema `0.3.0`,
  aggregation semantics, CLI behavior, privacy boundary, and the eight-output
  contract remain unchanged. v0.6.0 remains the immutable historical release.
- Released artifact: Ubuntu-authoritative wheel
  `6ca24828fbba02024904028fa8fa5f96e97a8393d3f5e16bb6ff316cff477b9f`, staging
  dashboard `8172a3eac4c61232a2a0331edce4435b91a124b230a37a55505b11a5ba4f4eb1`,
  and fixture `synthetic-two-provider-fixture-v3-provider-ledger`.
- Release evidence: tag `v0.6.1` at main merge `1be0c68`; CI run
  `30984105485`, publish run `30984290387`, and staging run `30985228475` all
  passed. The hashes and run identifiers above preserve its byte-level
  artifact evidence; the single promotion-candidate manifest now authorizes
  the v0.7.0 candidate.

## Historical v0.6.0 Public Beta (2026-08-04)

- Research and implementation slice complete on `codex/v060-evidence-ledger`:
  the flat Evidence Ledger now gives canonical model families stable
  light/dark marks and bars, while preserving non-exclusive model semantics and
  unique-commit daily geometry. ADR-028, design forensics, and visual QA are
  recorded in the review/decision documents.
- Verification: **667 passed, 4 skipped**, Ruff clean, README parity pass,
  sanctioned snapshot regeneration byte-stable, exact-wheel release smoke
  pass, and Playwright responsive/theme/auto-system checks pass. The exact
  Ubuntu-authoritative wheel was published to PyPI and the GitHub Release is
  marked prerelease; the maintainer Profile was refreshed from that wheel and
  its Pages and snake workflows passed. Final evidence is recorded in
  `docs/reviews/v0.6.0-release-readiness.md`.

## Where things stand (2026-08-01)

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

- **README sample preview committed (2026-07-15, Codex delegate)**: the
  ROADMAP "Sample profile output" half-item landed — two sample SVGs
  under `docs/assets/` (byte-exact `render_summary` output from the
  SYNTHETIC showcase fixture, re-render-verified; privacy-swept), a
  "What it looks like" `<picture>` preview atop the README with a
  synthetic-data caption, and a drift-guard regression
  (`test_docs_sample_assets_match_current_renderer`, reviewer
  recommendation) so future card changes must regenerate the assets or
  fail loudly. Suite: **310 passed, 1 skipped**; ruff clean.

- **Gate-7 review received and resolved** (2026-07-15, committed
  `73279cd`): `docs/reviews/gate-review.md` reviewed
  `b899d11..9933308`, verdict NOT READY (1 High, 2 Medium, 2 Low) — all
  5 independently reproduced and accepted (`gate-disposition.md`,
  gate-7 section), each behavioral fix with a pre-fix-failing
  regression:
  - **H-01**: VizStats is now the ENFORCED structural privacy boundary —
    every string field pinned to a closed public vocabulary (ACE version,
    fixed all-time period, canonical slugs, schema-owned display names;
    `PROVIDER_DISPLAY` moved into schema.vocab); the reproduced
    canary-to-SVG/JSON leak fails at construction;
  - **M-01**: merge timestamp resolves by the ADR-008 strongest-leaf rule
    (was first-leaf copy — reversed inputs produced different canonical
    events); schema §8.3 states the rule;
  - **M-02**: percentages never lie at the boundaries — `<1%`/`>99%`
    endpoint labels for hero share and provider rows;
  - **L-01**: light-theme unknown evidence mark #8c959f → #6e7781
    (2.85:1 → 4.27:1); both ramps re-validated ALL PASS;
  - **L-02**: one sanctioned command now regenerates snapshots AND the
    README sample assets; CONTRIBUTING documents it.
  Suite after the pass: **323 passed, 1 skipped**; ruff clean.

- **Gate-8 review received and resolved** (2026-07-16, committed
  `e0fa569`): independent verification of `9933308..73279cd`
  (gate-review.md, preserved untouched) confirmed 4/5 gate-7 closures
  and found two gaps in the fifth — both reproduced, accepted, fixed
  red-first (`gate-disposition.md`, gate-8 section):
  - **H-01**: the validated VizStats graph is now structurally
    IMMUTABLE — exact frozen contract types enforced for every nested
    record, the tuple container, and every string leaf, before any
    duck-typed access; the reproduced mutate-after-validate leaks
    (mutable list / tuple-held mutable row / mutable period) all fail
    at construction, and post-construction mutation raises with output
    bytes pinned unchanged; the in-round review pass caught and closed
    an int-subclass __str__ variant the same way (exact int/bool);
  - **L-01**: `generated_on` is a canonical ASCII calendar date
    (ASCII fullmatch + fromisoformat + round-trip) — Unicode digits,
    trailing newline, and impossible dates rejected.
  Suite after the pass: **339 passed, 1 skipped**; ruff clean; snapshot
  regeneration byte-stable (no visual change, as required).

- **Gate-9 review received and remediated** (2026-07-18, committed as
  `d9161cb`): independent verification of `73279cd..e0fa569`
  (gate-review.md, preserved untouched) confirmed the gate-8 closures
  and found the exact-type boundary incomplete at the TOP level, plus a
  stale-status doc gap — both reproduced, accepted, fixed red-first
  (`gate-disposition.md`, gate-9 section):
  - **H-01**: `VizStats` is SEALED against subclassing —
    `__init_subclass__` raises `TypeError` at class-definition time. A
    plain subclass defeats in-method guards (override `__getattribute__`
    to substitute a private-canary row, or `__post_init__` to skip
    validation — both reproduced svg+json leaks; the review caught the
    second, stronger variant after a first-pass `_validate`-only fix);
    sealing closes the whole family at its root, with a
    `type(s) is VizStats` backstop retained. Regression added;
  - **L-01**: the gate-7/gate-8 remediation records (progress +
    disposition) corrected from "UNCOMMITTED" to their actual commit
    hashes (`73279cd`, `e0fa569`).
  Suite after the pass: **340 passed, 1 skipped**; ruff clean; snapshot
  regeneration byte-stable (no visual change).

- **Gate-10 verification passed — VizStats finding chain (gates 7-10)
  closed** (2026-07-22):
  independent verification of `e0fa569..d9161cb` (gate-review.md,
  preserved untouched and committed with this closure) returned
  **READY FOR NEXT GATE with zero findings** — the first review round
  in the chain with nothing to remediate. The reviewer replayed eight
  from-scratch subclass-bypass vectors against the seal
  (`__post_init__`-skip, `__getattribute__` substitution, deep chains,
  multiple inheritance, custom metaclass `__new__`, `types.new_class`,
  `__bases__` splice, direct `type.__new__`) — all rejected with
  `TypeError` — and confirmed the legitimate lifecycle intact
  (replace/copy/deepcopy/pickle yield exact `VizStats`) plus fresh
  privacy-sweep integration tests green. Suite: **340 passed,
  1 skipped**; ruff clean; snapshot regeneration byte-stable.
  Process note: this was the first round run through the file-based
  handoff protocol (`.ai/handoff/`, headless `codex exec` via the
  codex-delegate wrapper) — no manual copy-paste transport; one stale
  self-referential "UNCOMMITTED" note on the gate-9 bullet above was
  corrected in this closure.

- **Round A hardening + Gate-11 verification** (2026-07-22, `278c138` +
  gate-11 resolve): four ROADMAP pre-release checkboxes closed
  (owner-only permissions, worktree warning, packaged smoke script,
  cherry-pick semantics) plus the cp950-safe console-text sweep
  (repo-wide, not itself a distinct checkbox). Gate-11 external
  review (headless handoff lane): READY AFTER MINOR FIXES, one Medium -
  existing installations skipped the permission retrofit via
  init_home's early return; fixed red-first by retrofitting in
  load_config (every command's choke point, mirrors db.connect).

- **Rounds B/C + Gate-12 final verification — v0.1.0 RELEASED**
  (2026-07-22): Round B closed the last two Gate-2 §14 checkboxes
  (console stdout/stderr canary sweeps with positive controls;
  hypothesis property fuzzing, six derandomized invariant families).
  Round C: PEP 639 packaging metadata, CHANGELOG.md with the upgrade
  policy, README install section led by `pip install ai-profile` (with
  the unhyphenated-name collision warning), hand-written
  README.zh-TW.md mirror (claim-by-claim parity reviewed), AGENTS.md
  handoff-process rule. Gate-12 (final pre-release, range
  `278c138..ac21d4d`): **READY FOR RELEASE, zero findings** — suite,
  ruff, wheel metadata + twine, release smoke, chmod-failure probe,
  snapshot byte-stability, and a fresh synthetic privacy sweep all
  independently green. Released as one unit immediately following this
  commit: GitHub repo public + PyPI upload of `ai-profile 0.1.0`, tag
  `v0.1.0`.

- **Image 2.0 rounds D1+D2 + gates 13-14** (2026-07-22, `08922b7` +
  `5b01195` + closures): the card gains provider brand identity
  (vendored CC0 simple-icons marks + per-theme brand bars, ADR-017)
  and the publishable-only isometric daily calendar (ADR-018; ACE
  schema 0.1.0 -> 0.2.0 per ADR-012's minor-bump rule). Gate-13: zero
  findings. Gate-14: one Low (EOF blank line), fixed in the closure.
  Notable process lessons recorded in the reviews: a from-nothing SMIL
  entrance is invisible in static captures (two attempts removed; the
  band is fully static with a pinning regression test), and the first
  privacy canary test was confounded by the window trim (re-pinned
  in-window and re-proven by sabotage).

## Open items

- v0.4.2 was published as the immutable wheel-notice correction. Its package
  artifacts and tag remain unchanged.
- **v0.4.6 Public Beta is released and promotion-verified.** Its wheel and
  runtime are correct; its immutable sdist unintentionally contains
  non-sensitive Hypothesis cache data.
- **v0.4.7 Public Beta is released and live.** It corrects the v0.4.6 sdist,
  excludes generated/private working roots and makes the artifact contract
  reject unsafe paths, duplicate members, links, and special entries. Product
  behavior, ACE, aggregation, privacy modes, CLI, and renderers are unchanged.
- The canonical release bundle is built from a clean Ubuntu checkout with a
  manifest-frozen `SOURCE_DATE_EPOCH`; Windows and macOS smoke those retained
  bytes rather than rebuilding platform-specific ZIP metadata.
- The pinned v0.4.7 wheel digest is
  `75b896c7a1bfa462d1caa6df7025bca79650e8ad48a006272e76eb9bfb5667d8`.
  The candidate passed 4/4 README-only roles, zero privacy-canary hits, a
  public-HTTPS 13/13 browser matrix, Python 3.11–3.14, and exact-wheel
  onboarding on Ubuntu, Windows, and macOS.
- `docs/reviews/promotion-readiness-review.md` records
  **GO — PUBLIC BETA** after protected-main CI and Pages staging. The tag
  workflow, PyPI/GitHub Release byte verification, clean PyPI install, and
  maintainer Profile refresh have completed successfully. The live Profile
  dashboard passed its responsive, theme, provider-filter, and keyboard-focus
  browser smoke after deployment.
- Future import, reconciliation, richer views, GitHub API integration, and
  any configuration CLI remain deferred in ROADMAP. They are not part of
  the v0.4.8 product boundary.
- **v0.4.8 Public Beta is released and promotion-verified (2026-08-01).**
  The HR-first visual refresh (ADR-022) shipped: summary card redesigned
  as the `AI Collaboration Record` with the whole-rhythm isometric
  terrain (height = total-commit bins, hue = AI-share bins,
  provider-independent geometry; shared bin arithmetic in
  `render/_bins.py`), dashboard H1 alignment, README restructure, and
  refreshed banner/social assets. Released from `main` commit
  `b4e2178a79cf9d1437ebf46ce52d141720437762` (tag `v0.4.8`); the GitHub
  Release is marked prerelease and the PyPI classifier is Beta.
  Canonical digests — wheel
  `d8d307d4155f58f157ee817cdd628ef4c257287083aad66cf30e02f679fe47b6`,
  sdist
  `0909aa3e2efe19ec1471c1f95f373646538c6df8bb344ecabf1fac6d20065b38`,
  package dashboard
  `c8680c2812343077775c2b5c0fddae9dce32c1517bbaa4c920e056b347fdbd4f`.
  Verification: full local suite 628 passed / 4 skipped; CI Linux 631
  passed / 1 skipped; Ruff clean; README parity pass; sanctioned
  regeneration twice with zero byte drift; exact-wheel onboarding on
  Ubuntu, Windows, and macOS; release run `30717707873` passed;
  protected-main staging run `30717400004` passed and deployed the exact
  pinned dashboard bytes. Four README-only dogfood roles passed 4/4 with
  zero external hints, zero privacy-canary hits, exact hand totals, and
  eight outputs. Full record: `docs/reviews/v0.4.8-release-readiness.md`.
- **Post-v0.4.8 evidence-ledger refinement (design branch, 2026-08-04).**
  Research reviewed Nanako0129, Primer, Carbon, Radix, Geist, Vega-Lite,
  Observable Plot, Grafana, and related primary sources. The branch keeps the
  v0.4.8 data/privacy contract while separating provider metric columns,
  adding semantic section markers, and regenerating only sanctioned summary
  snapshots/assets. ADR-023 and the implementation plan document the scope.
  Independent verification is green; public patch publication remains
  conditional on a versioned artifact/CI/Pages release round. Full record:
  `docs/reviews/v0.4.9-visual-readiness.md`.
- **Structural Current visual slice (superseded design branch, 2026-08-04).**
  Independent design forensics (Nanako0129's public tools plus Primer,
  Carbon, Radix, Geist, Vega-Lite, and related systems) is recorded in
  `docs/reviews/design-reverse-engineering.md`. `DESIGN.md` and ADR-024 now
  define the semantic role tokens and evidence-first composition without
  adding runtime dependencies or a new data model. That branch's perspective
  treatment was intentionally rejected for the summary card; its rollback
  remains available until the flat replacement completes verification.
- **v0.4.9 Flat Evidence Ledger pivot (pre-release record, 2026-08-04).**
  ADR-025 replaces the summary-card perspective treatment with a 12-column by
  7-row flat daily matrix. Bars encode unique daily total-commit bins and fill
  encodes AI-share bins; provider overlap, unknown/human separation, privacy
  redaction, and the eight-file output contract remain unchanged. The branch
  was subsequently verified and released as v0.4.9; the candidate readiness
  record remains the historical pre-publication review:
  `docs/reviews/v0.4.9-flat-ledger-readiness.md`.
- **v0.4.9 Public Beta is released and promotion-verified (2026-08-04).**
  Tag `v0.4.9` and the GitHub Release are live; PyPI serves the verified
  wheel and sdist. The final Ubuntu-authoritative wheel digest is
  `f04e6c33b72072190e1cb18fbb154897c25ec7986fd316427d807c81e49fb468`.
  Main CI and the publish workflow passed, clean PyPI installation reported
  `aiprofile 0.4.9`, and the eight-output release smoke passed. Maintainer
  Profile PR #13 merged at `b991504`; its Pages deployment passed and all
  eight live outputs match the merged LF-normalized blobs. Final record:
  `docs/reviews/v0.4.9-release-readiness.md`.
- **Editorial Signal skin (pre-release candidate record, 2026-08-04).**
  A new research round compared Nanako0129's terminal-ledger composition with
  Primer, Carbon, Radix, Geist, Vega-Lite, and profile generators. The
  presentation-only candidate keeps the v0.4.9 flat Evidence Ledger, adds
  sparse quarter-window alignment rails and a two-part editorial section
  marker, and leaves ACE/schema, aggregation, privacy, CLI, and eight-output
  contracts unchanged. Research and acceptance criteria:
  `docs/reviews/design-research-2026-08-04.md`; decision:
  `docs/decisions/ADR-026-editorial-signal-skin.md`. Local exact-wheel smoke,
  privacy sweep, and browser evidence are recorded in
  `docs/reviews/v0.4.10-visual-qa.md`. Cross-platform publication and Profile
  verification were still open when that candidate record was written; the
  candidate was subsequently verified and released as v0.4.10, and the final
  evidence is the release record below.
- **v0.4.10 Public Beta is released and promotion-verified (2026-08-04).**
  Tag `v0.4.10` and the GitHub Release are live as a prerelease; PyPI serves
  the verified wheel and sdist and remains classified as Beta. The candidate
  merged to `main` as `91260bdf368dc32ecc25c6446f38f6b987047f26` via PR #21.
  The Ubuntu-authoritative wheel digest is
  `41c91d01ee761abc5a22add1c2a2fb8d3b36e309411b5db0398a7eae7824cd7a` and the
  sdist digest is
  `b327a421797c51e8b1866baff09a4612828f6bde4fb6445757e8808d980b7951`. PR CI
  run `30921682522` and publish run `30922283841` passed; an earlier publish
  attempt, run `30921090861`, failed on a digest mismatch against the frozen
  candidate manifest and was corrected by commit `b78a8da` before the
  successful publish. Clean installation of the exact PyPI wheel reported
  `aiprofile 0.4.10`, and the eight-output release smoke passed. Maintainer
  Profile PR #14 merged at `9c346fde0ebbbf0c12485f9bbacb0e486ed9d8af`
  (implementation commit `42e8ecf4571fe084fe10ee2ce1fb379de9e4022e`); Pages
  run `30924497319` and the snake run `30924498845` passed, and all eight
  live outputs are HTTP 200 and match the merged LF-normalized blobs. Final
  record: `docs/reviews/v0.4.10-release-readiness.md`.
- **The maintainer Profile refresh on public PyPI 0.4.8 is complete.**
  Profile PR #12 merged at `7f322beab1e532d906f943c62fc68e49ba21c02a`
  with the unchanged exact 11-repository full-publication scope. Profile
  Pages run `30718799030` passed; all eight published outputs are
  HTTP 200 and byte-identical to the merged git blobs; profile dashboard
  SHA-256
  `b17e996a6fb0fa8530779c59d47d5cf069154ffd8437e431d2bf7331c12ac292`.
  The Profile privacy review found zero hits across paths, names,
  organizations, e-mails, full and 12-character SHAs, 1714 commit bodies,
  1713 subjects, and 405 prompt-bearing lines.
- **v0.5.0 model-family contribution is released and promotion-verified
  (2026-08-04).** ADR-027 and the model-category plan define a closed,
  explicit-only family ledger over ACE `0.3.0`: model-family commit rows are
  non-exclusive, presence rows reconcile to AI actor presences, and missing
  models remain `Unknown` rather than Human. The release records
  `667 passed, 4 skipped`, clean Ruff, deterministic sanctioned assets,
  exact-wheel smoke, browser QA, and zero privacy-canary hits. Ubuntu CI run
  `30935669158` and publish run `30935872159` passed; the exact wheel was
  published to PyPI and the GitHub Release is a prerelease. Tag `v0.5.0` is at
  main merge `4e369c6`; wheel digest
  `dcd407fa5a570b1a47ba3c613998f681c5c992f10f18119ab4f4be457221f245`; sdist
  digest
  `24f581f9914ac0372af4e921889f79c935207852f6c66b4affe110901a5d1ed8`.
  Maintainer Profile PR #15 merged at `ead0f41`; Pages run `30937320357` and
  snake run `30937324074` passed, with all eight live outputs matching the
  merged LF-normalized blobs. Full evidence:
  `docs/reviews/v0.5.0-release-readiness.md`.

## Pointers

- Roadmap: `docs/ROADMAP.md` · Threat model: `docs/PRIVACY.md`
- Reviews: `docs/reviews/` (Gate 2 review, disposition, v0.1 run log)
- Contracts: `docs/schema.md`, `docs/architecture.md`, `docs/mvp.md`,
  `docs/decisions/`

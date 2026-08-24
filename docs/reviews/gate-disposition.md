# Gate implementation-review findings disposition

Source: `docs/reviews/gate-review.md` (independent implementation review of
`49fdcbb..5d57016`, verdict NOT READY). Adjudicated 2026-07-14 by the
maintaining orchestrator. **All 23 findings accepted** — none could be
refuted on technical grounds; two (M-09, M-11) resolve through documented
decisions rather than code, recorded below. Every accepted code fix ships
with a regression test confirmed failing pre-fix, in the same commit.

## Critical

| ID | Disposition | Technical justification + resolution |
|---|---|---|
| C-01 | **Accepted** | Correct: `host_<port>` string concatenation is non-injective (literal-underscore hosts collide with port encodings), and global scheme erasure wrongly asserts that SSH and HTTPS namespaces address the same repository on arbitrary self-hosted services — only documented alias-convergent hosts may merge transports. Resolution: **uid algorithm v3** — structured, self-delimiting canonical form `scheme://host[:port]/path` (port always explicit when the scheme has a known default; `://` and `:` delimiters cannot be forged by host/port components), with scheme/port dropped ONLY for documented alias-convergent hosts (v3 list: github.com, whose ssh/https/git endpoints address one namespace on standard ports). Injective by parse-back; collision fixtures added (underscore-host vs port pair, ssh-vs-https same host, IPv6, delimiters). |
| C-02 | **Accepted** | Correct: lowercasing resolved local paths merges case-distinct directories on case-sensitive filesystems; declared macOS/Linux support makes this a real distinct-repo merge → replace-by-uid data loss. `Path.resolve()` already canonicalizes case on case-insensitive filesystems (Windows returns on-disk casing), so dropping `.lower()` preserves convergence there while restoring the safe split on POSIX. Resolution: v3 local uid hashes the case-preserved resolved path; POSIX-semantics fixture added (case-distinct dirs → distinct uids). |
| C-03 | **Accepted** | Correct: per-path uid upsert breaks the alias group during v-migration — a `full` clone migrating alone stops aliasing its `excluded` sibling, and most-restrictive resolution silently loses. Resolution: at scan time, when an entry's uid changes, ALL config entries holding the old uid are re-derived in the same operation (their paths must resolve; otherwise **halt fail-closed** with a targeted ConfigError naming the stale entries); the old uid's database rows are purged inside the same scan transaction (no orphan/phantom rows). Conflicting-policy duplicate-clone fixtures added. |
| C-04 | **Accepted** | Correct: persisting config (uid + `--full` elevation) before enumeration/storage means any later failure leaves policy elevated over stale cached data — reachable from the supported CLI path. Resolution: scan is reordered into config-last commit order — preflight (repo root, identities, object format) → in-memory config mutation → enumeration/parse/build → atomic DB replacement (including C-03 purge) → only then `save_config`. A failure at any earlier step leaves the on-disk config byte-identical; if the DB commit succeeds and the config write fails, the new uid is unconfigured and therefore excluded (fail-closed direction). Failure-injection tests added at the enumeration and storage boundaries incl. `--full` over pre-existing cache. |

## High

| ID | Disposition | Technical justification + resolution |
|---|---|---|
| H-01 | **Accepted** | Correct: `split("@", 1)` keeps everything after the FIRST `@`, so multi-`@` userinfo leaks a secret fragment into the uid (probe: `en@host...`). RFC 3986 authority parsing puts the host after the LAST `@`. Resolution: `rpartition("@")`; adversarial multi-`@` / empty-host tests added. |
| H-02 | **Accepted** | Correct, and it invalidates the "structurally unrepresentable" claim: canonical `provider` was an unconstrained string trusted end-to-end. Resolution (both ends, defense in depth): canonical provider/tool slug sets become schema-owned vocabulary (`vocab.CANONICAL_PROVIDERS/_TOOLS` — schema.md §10 already lists them; schema stays stdlib-only); `build_event` rejects non-canonical values; `privacy.build_viz_stats` independently collapses any non-canonical provider key into the `unrecognized` bucket before display resolution; registry asserts its outputs ⊆ vocabulary. Canary tests inject sensitive strings into canonical and raw fields and sweep dist/. |
| H-03 | **Accepted** | Correct: stable sort on `(type, reference)` preserves caller order for duplicate keys with different evidence → two canonical serializations of one evidence multiset, plus a schema/storage contract mismatch (SQLite would reject what the schema accepted). Resolution: `build_event` deduplicates sources by key keeping the highest evidence (the same rule group-merge already uses); reversed-input regression added. |
| H-04 | **Accepted** | Correct on both counts: 64-hex detection never fires on an empty SHA-256 repo, and the error text embedded the repo path. Resolution: `git rev-parse --show-object-format` preflight (before any mutation, per C-04's ordering) rejecting non-sha1 with a **path-free** message; empty and non-empty SHA-256 fixtures assert the error and zero config/DB mutation. |
| H-05 | **Accepted** | All four probes verified: `fromisoformat` accepts date-only strings (naive midnight); `human` was only constrained on identity fields, not evidence; raw strings in `ProvenanceSource` blew up later as `AttributeError`; `human_reviewed` was untyped. Resolution: offset-aware datetime required (tzinfo check) for `timestamp` and `recorded_at`; `human` requires `declared` evidence from a non-`none` source; per-source enum coercion through the schema's own `_coerce`; `human_reviewed` must be `bool | None`. Negative contract tests per rule. |

## Medium

| ID | Disposition | Technical justification + resolution |
|---|---|---|
| M-01 | **Accepted** | Row-level counts were omitted from validation — probe built a valid VizStats with negative rows. Fix: provider-row fields join the non-negative-int check; malformed-row test. |
| M-02 | **Accepted** | Hard-coded file list, no dynamic-import detection, and `aiprofile.schema` missing from the denylist (the dependency table forbids render→schema directly). Fix: recursive module discovery for render/ + export, denylist extended (schema/adapters/config/privacy/aggregate), `importlib.import_module`/`__import__` call detection. |
| M-03 | **Accepted** | Empty-valued `AI-Provider:`/`AI-Tool:` lines lost key-presence before the Human-Only contradiction check — ADR-005 keys the rule on PRESENCE. Fix: per-group presence tracking independent of non-empty value storage; contradiction fires on presence; empty/whitespace fixtures. |
| M-04 | **Accepted** | scp forms skipped query/fragment stripping; `.GIT` escaped the suffix strip before github case-folding. Fix inside v3: one component pipeline for all syntaxes; for case-insensitive hosts the path folds BEFORE suffix stripping. Parity fixtures. |
| M-05 | **Accepted** | The privacy sweep never asserted the uid or a remote-org string; permutation coverage stopped at canonical events; empty-SHA-256 and migration cases were absent. Fix: fixture repo gains a distinctive private-org origin (uid + org swept in dist/), scan→aggregate permutation test (reordered trailer lines → identical published totals), plus the C-03/C-04/H-04 fixtures. |
| M-06 | **Accepted** | Each cited contradiction verified in-tree. Fix: contract-term sweep — mvp.md diagnostics wording (ordinals), schema.md residual "free-form" phrasing, README + CLI `--full` help ("explicitly publishable", not "public"), ADR-008 consequence line vs its provisional-order bullet, ADR-009 `repository_anonymous` wording (reserved/rejected), historical banner prepended to the archived run log. (ROADMAP conformance-status row was already corrected post-review-snapshot; re-verified.) |
| M-07 | **Accepted** | Sequential writes leave mixed-generation dist/ on partial failure. Fix: write all three assets to same-directory temp files, then `os.replace` each only after the full bundle is built; failure-injection test. |
| M-08 | **Accepted** | The privacy→registry import is real and undocumented, and registry fallback behavior became publication behavior (H-02's enabler). Fix: architecture dependency table amended with the edge, constrained to display-name resolution AFTER the canonical-slug collapse; noted in ADR-009. |
| M-09 | **Accepted (documented decision, no code)** | The MVP promised skipped-author counts at `aggregate -v`, but they are scan-run diagnostics; persisting them would add storage surface for a convenience readout — scope the promise, don't grow the cache. mvp.md §3 amended: skipped-author counts are reported by `scan` (already true); `aggregate -v` reports unrecognized values + excluded count. |
| M-10 | **Accepted** | Verified: independent per-scalar resolution can pair `model` from one leaf with `model_raw` from another — a provenance statement no source made. This is a defect in ADR-008's approved per-scalar design. Fix: `(canonical, raw)` pairs resolve atomically from one winning leaf (rank, then pair-tuple value tie-break); ADR-008 + schema §8.3 amended; pair-integrity regression (failing pre-fix) + permutation rerun. |
| M-11 | **Accepted (ADR exception, no version bump)** | The renames do violate ADR-012's letter, but no tagged release or external consumer exists and ACE 0.1.0 has never been published. Bumping to 0.2.0 now would burn a version on a contract that is still pre-freeze. Resolution: ADR-012 gains an explicit pre-release clause — the 0.1.0 contract is a moving target until the first tagged release, at which point schema+contract freeze and the normal bump rule binds; ROADMAP release checklist gains "freeze schema/viz contract at tag". |
| M-12 | **Accepted** | A public pairwise API whose docstring warns against its own use is an attractive nuisance; a shipped test demonstrated the forbidden fold. Fix: `merge_events` removed from the public schema surface (group API is the only exported merge); tests rewritten against `merge_event_group`. |

## Low

| ID | Disposition | Technical justification + resolution |
|---|---|---|
| L-01 | **Accepted** | Terminology sweep: CLI "events stored" → "records stored"; aggregate docstring "level -> events" → records; first-write-era comments updated; forbidden-fold demonstrations removed with M-12. |
| L-02 | **Accepted (wording only)** | Open OSS items remain correctly listed in ROADMAP; progress.md wording re-checked to avoid release-ready implications until the checklist is independently verified. |


---

## Verification-review round (gate-review.md, 2026-07-14 19:54; NOT READY)

An independent verification review of `5d57016..de4a78a` confirmed 20/23
dispositions and produced three reproducible counterexamples. All
adjudicated **accepted**; each fix shipped with a regression test
confirmed failing pre-fix.

| Finding | Disposition | Technical justification + resolution |
|---|---|---|
| Critical — github alias collapses all schemes/ports (contradicts C-01 closure) | **Accepted** | Correct: the alias branch switched on host alone, so `ftp://github.com:444/...` and 41 other combinations collapsed into the documented namespace — ADR-016's own "standard ports" restriction was unenforced. Fix: convergence now requires `(scheme, effective_port)` in the documented endpoint set (`ssh:22`, `https:443`, `git:9418`); everything else on an alias host keeps structured identity (safe split). ADR-016 rule 4 amended; collision grid regression added. |
| Medium — replacement stage not bundle-atomic (contradicts M-07 closure) | **Accepted** | Correct: three sequential `os.replace` calls had no rollback, and the shipped test only injected failure BEFORE replacement. Fix: olds are moved aside to `.bak` before replacement; a replacement-stage failure restores every already-replaced target before re-raising (best-effort rollback — a simultaneous restore failure remains the documented residual). Replacement-stage failure-injection regression added. |
| Medium — exported N-ary merge unsafe under composition | **Accepted** | Correct: `merge_event_group` could not distinguish leaves from merged results, so nested composition re-ranked values against pooled provenance. Fix: the leaf-only boundary is ENFORCED — every input to a multi-event reduction must carry exactly one provenance source (the definition of a leaf production); nested/merged inputs raise `SchemaValidationError`. Regression: nested three-leaf composition rejected; flat reduction unchanged. |
| L-01 partial — a shipped test still demonstrated incremental accumulation | **Accepted** | The old permutation test folded a merged result back into the API. Rewritten to a flat N-ary reduction per permutation; the union-mechanics test likewise rewritten to leaf-only inputs. |


---

## Gate-4 review round (gate-review.md, 2026-07-14 22:15; NOT READY)

An independent review of `de4a78a..4fdd490` reproduced five
counterexamples against the previous round's fixes. All 8 findings
adjudicated **accepted**; every code fix shipped with a regression test
confirmed failing pre-fix (red-first), and the reviewer's probes were
replicated locally.

| Finding | Disposition | Technical justification + resolution |
|---|---|---|
| High — leaf-only merge guard bypassable via source dedup | **Accepted** | Correct: `len(sources) == 1` is a property of the DEDUPLICATED provenance set, not of derivation — two leaves sharing one provenance key merge into a single-source result that the guard re-admits, and the reviewer's nested probe reproduced divergent model selection (nested `zeta` vs flat `alpha`). Fix: leaf status is now an explicit derivation marker — `AceEvent.merged` (envelope metadata, like `recorded_at`: excluded from canonical payload and identity), set by `merge_event_group` on every multi-input reduction and checked on every input. Regression: same-key different-evidence leaves → nested rejected, flat picks `alpha`. |
| M-2 — schema-valid multi-source leaf productions rejected | **Accepted** | Correct: the same source-count heuristic narrowed the approved contract — `build_event` validates one-OR-MORE sources and schema §8 keeps source union for future imports. The `merged` marker makes merge-state validation independent of source count; a two-source built event now merges. Regression added. |
| M-3 — rollback stops at first restore failure; docstring overclaims | **Accepted** | Correct: the restore loop re-raised on the first `OSError`, abandoning every later asset, while the public docstring still promised "previous generation fully intact". Fix: every restore is attempted (failures collected); an unrestorable asset keeps its `.bak` as recovery data and is NAMED in the raised error; retractions are likewise per-item guarded. Docstring rewritten to the honest best-effort contract (worst case: mix limited to unrestorable assets, recovery data on disk). Regression: injected install-failure + restore-failure → other assets restored, failed asset's backup retained, `RenderError` raised. |
| M-4 — uid rules changed without an algorithm version bump; schema §7 stale | **Accepted** | Correct: the endpoint-qualified alias rule changed canonical output for existing github origins while `UID_ALGORITHM` stayed `"v3"` — violating ADR-016's own "any rule change bumps the version" rule, so one `remote:v3:` prefix named two algorithms across commits. Fix: `UID_ALGORITHM = "v4"`; `canonicalize_remote_v3` renamed version-neutral `canonicalize_remote` (the constant is the single version authority); schema.md §7 rewritten to the endpoint-qualified rule + v4 prefixes; ADR-016 status/decision updated to v4 with the bump rationale recorded. Existing v3 uids migrate opportunistically on rescan via the established alias-group migration (fail-closed), same as v2→v3. Version regression pins `UID_ALGORITHM == "v4"`. |
| M-5 — leading-zero ports split identities | **Accepted** | Correct: effective ports compared as strings, so `:0443`/`:00022`/`:09418` split from their documented decimal endpoints — a safe split, but a violation of stable canonical identity. Fix: ports normalize to canonical decimal (`str(int(port))` — the port pattern admits digits only) before default resolution, endpoint lookup, and structured serialization; folded into the v4 bump. Leading-zero fixtures for all three documented transports + a non-alias host. |
| M-6 — fixed `.bak`/`.tmp` names clobber user files and race concurrent renders | **Accepted** | Correct: `os.replace` onto a deterministic `<target>.bak` destroyed a pre-existing user backup (reproduced), and two concurrent renders shared transaction filenames. Fix: attempt-owned artifact names — `<target>.<pid>.tmp` / `<target>.<pid>.bak`; a render only ever creates, consumes, and deletes its own. Concurrent renders into one directory are documented as unserialized (each publishes a whole generation; which one wins is undefined). Regression: user `summary-light.svg.bak` sentinel survives a successful render byte-identical. |
| L-1 — backup-cleanup failure reported as publication failure | **Accepted** | Correct: `.bak` unlinks sat inside the operation-level `OSError` handler, so a cleanup failure AFTER all targets were installed raised `RenderError` on a successful publish. Fix: publication success is the install of the last target; cleanup failures downgrade to a logged warning (debris named) and the written paths are returned. Regression: injected `.bak` unlink failure → no raise, new content live. |
| L-2 — claimed 42-case grid test not committed | **Accepted** | Correct: the previous round's disposition claimed grid replication but committed only sampled endpoints — which is WHY the M-5 split survived a green suite. Fix: the full parameterized 6-scheme × 7-port grid is now a committed test computing each cell's expected equivalence class from the rule itself (documented endpoints → alias identity with path folding; default-port resolution within scheme; structured identity otherwise), plus leading-zero and path-case variants. |


---

## Gate-5 review round (gate-review.md, 2026-07-15; READY AFTER MINOR FIXES)

An independent review of `4fdd490..78e2e05` confirmed all eight gate-4
code fixes and produced three new adversarial reproductions (forged
`merged` flag, 5000-digit port, failed first-install retraction) plus
four accuracy findings. All 7 findings adjudicated **accepted**; every
behavioral fix shipped with a regression confirmed failing pre-fix.

| Finding | Disposition | Technical justification + resolution |
|---|---|---|
| M-01 — merge-purity boundary conventional, non-durable, absent from normative schema | **Accepted (documentation-scope, per the reviewer's own alternative)** | Correct: `merged` was defined nowhere in schema.md (the declared source of truth), is not serialized or persisted, and an out-of-contract `dataclasses.replace` probe reproduced the nested/flat divergence — the boundary is conventional, and the closure claim was stronger than the event contract. Resolution takes the reviewer's first option: the closure claim is NARROWED to the sanctioned in-memory scan path, now normatively documented — schema.md §1 defines derivation state (default, lifecycle, envelope semantics, non-persistence) and §8.3 states the leaf-only guard's scope; a future round-trip/import boundary must first give derivation state an enforceable persisted representation. Pinning regression added: `merged` absent from canonical payload AND from the SQLite `events` schema. |
| M-02 — artifacts process-owned, not attempt-owned; concurrent whole-generation claim false | **Accepted** | Correct on both counts: a pid identifies a process (same-process re-entrant calls shared names; pid reuse could collide with crash debris), and three independent target replacements cannot guarantee generation atomicity under concurrent writers — the "each publishes a whole generation" claim was wrong. Fix: per-invocation transaction id (`<target>.<pid>-<n>.tmp/.bak`, process-lifetime counter), and the contract now explicitly DECLARES concurrent publication unsupported (can mix generations; no runtime guard — wording corrected per gate-6 L-02) instead of claiming isolation. Regression: a retained recovery `.bak` from a failed render survives a later successful render in the same process byte-identical (failed pre-fix: pid-only names consumed then deleted it). |
| L-01 — failed first-install retraction absent from the raised error | **Accepted** | Correct: retraction failure was log-only, so a programmatic caller inspecting the exception could not discover the surviving partial asset. Fix: retraction failures are collected separately from restore failures and both are named in the RenderError ("could not retract … the partial new content remains published"). Regression: first-ever render + install failure + retraction failure → error names the surviving asset. |
| M-03 — oversized ports escape the error contract | **Accepted** | Correct: the URL regex admits unbounded digits and `int()` on a 5,000-digit token raises Python's conversion-limit ValueError outside `AiProfileError` handling. Fix: the port token is bounded BEFORE conversion (strip leading zeros; >5 digits or >65535 → the origin is not a usable remote endpoint → `None`, falling back to local identity — the established fail-safe direction: a bad split, never a collision or a crash). Regressions: 5000-digit port, 65536, 8-digit port → None; 65535 and 10-zero-padded 443 remain usable. |
| L-02 — the "parameterized" 42-grid is one looped test | **Accepted** | Correct: functional coverage existed but the first failing cell would abort the rest, and the evidence record overstated the form. Fix: stacked `pytest.mark.parametrize` — 42 individually reported cases with meaningful ids (`[scheme-port-N]`); disposition/progress wording now matches reality. |
| L-03 — `merged` changes dataclass equality while canonical payloads are identical | **Accepted** | Correct, and the inconsistency predates the marker: `recorded_at` had the same defect. Fix: BOTH envelope fields are `field(compare=False)` — dataclass equality/hash now agree with canonical event equality, and schema.md §1 specifies the envelope equality semantics. Regression: `merge_event_group([leaf, leaf])` equals the leaf (equal hash, byte-identical canonical JSON); a `recorded_at`-stamped twin likewise. |
| L-04 — triplicated VizStats fixture in export tests | **Accepted** | Mechanical: `_zero_stats()` hoisted above first use; both older tests now call it. No behavioral change. |


---

## Gate-6 review round (gate-review.md, 2026-07-15 06:39; READY AFTER MINOR FIXES)

An independent review of `78e2e05..b899d11` confirmed the gate-5
closures and produced three adversarial reproductions (pid-reuse
recovery loss, Unicode-port identity split, equality
non-substitutability). All 6 findings adjudicated **accepted**; every
behavioral fix shipped with a regression confirmed failing pre-fix.

| Finding | Disposition | Technical justification + resolution |
|---|---|---|
| M-01 — transaction ids collide after pid reuse | **Accepted** | Correct: the counter restarts with the process, so a reused pid replays a dead process's names and the reviewer's probe destroyed a retained recovery `.bak`. Fix: `_transaction_suffix` probes the output directory and skips any suffix with surviving artifacts (a dead process cannot race), staging files are created with exclusive `open(..., "x")` semantics, and the counter is lock-protected (no reliance on CPython bytecode atomicity, per the 3.11+ interpreter-neutral packaging). Regression: counter reset to 1 with pre-seeded `<target>.<pid>-1.bak` recovery data → survives a successful render byte-identical. |
| M-02 — bounded-port rejection changed v4 without a bump; ADR stale | **Accepted** | Correct, and it is the same violation class this project already accepted twice (gate-4 M-4): `:65536` produced structured remote-v4 identity at 78e2e05 and local fallback at b899d11 under one label. Fix: **uid algorithm v5** — the full port-domain rule (ASCII decimal only, canonical decimal, 0..65535, violations → local fallback) honestly versioned; ADR-016 status/rule 3 rewritten with the v5 definition and migration note (opportunistic rescan migration, fail-closed, as with every prior bump); schema.md §7 updated; version pinned by regression. |
| M-03 — Unicode decimal ports not canonicalized | **Accepted** | Correct: the regex's `\d` and `int()` both accept full-width/Arabic-Indic decimals, and gate-5's rewrite dropped the `str(int(port))` reassignment, so `:４４３` minted a split non-ASCII structured identity. Fix (folded into v5): port tokens must be ASCII decimal (`isascii() and isdigit()`) — RFC 3986 defines ports as ASCII DIGIT, so exotic spellings are an unusable origin shape → local fallback (fail-safe split), never a silent convergence. Regressions: full-width 443/22/2222 and Arabic-Indic 0443 → None. |
| L-01 — equal AceEvents behave differently in the merge API | **Accepted** | Correct: gate-5's `compare=False` on `merged` made a leaf and a reduced event interchangeable in sets while `merge_event_group` accepts one and rejects the other — the reviewer's probe showed insertion order deciding merge success. Resolution per the reviewer's recommendation: equality is now OPERATIONAL — `recorded_at` (pure audit) stays excluded, `merged` (decides merge admissibility) PARTICIPATES in eq/hash; schema.md §1 specifies operational vs canonical-payload equality explicitly. The gate-5 equality test is rewritten to the approved semantics with a substitutability regression (set dedup can never flip merge behavior). |
| L-02 — concurrent-render rejection described but not enforced or exposed | **Accepted** | Correct: no runtime guard exists; "rejects" in the round-5 records overstated the docstring's "unsupported". Fix: wording aligned to "declares unsupported" in progress.md and the round-5 disposition row (annotated, not silently rewritten); the precondition is now user-facing — `aiprofile render --help` description and the README quickstart state one-render-per-directory. No runtime guard added (a lock file is new machinery the MVP does not need; the honest contract is the reviewer's stated alternative). |
| L-03 — schema tests reach into the storage layer | **Accepted** | Correct: the persisted-schema half of the gate-5 pin belongs with storage tests. Fix: `PRAGMA table_info` assertion moved to `tests/unit/test_storage.py`; the schema-event suite keeps only the canonical-payload assertions with a pointer comment. |


---

## Gate-7 review round (gate-review.md, 2026-07-15; NOT READY)

An independent review of `b899d11..9933308` confirmed all gate-6
closures and the visual work, then produced three reproduced defects and
two hardening items. All 5 findings adjudicated **accepted** after
independent reproduction; every behavioral fix shipped with a regression
confirmed failing pre-fix. Remediation committed as `73279cd` (gate-7
disposition below records the same round).

| Finding | Disposition | Technical justification + resolution |
|---|---|---|
| H-01 — VizStats is not the structural boundary the architecture claims | **Accepted** | Reproduced: a validated instance carried canary strings (`SecretPeriod-Repo`, `SecretOrg-PrivateRepo`, a fake slug, a fake schema version) verbatim into BOTH render_summary and dumps_stats — the boundary was constructor convention, not structure. Fix (centralized in the contract, no renderer sanitization): `VizStats.__post_init__` pins every string field to a closed public vocabulary — schema_version must equal the supported ACE version; the period must be the fixed v0.1 all-time contract (None bounds, "All time"); provider slugs must come from `CANONICAL_PROVIDERS` ∪ {unrecognized}; display names must equal the schema-owned display for the slug. `PROVIDER_DISPLAY` moved from registry into `schema.vocab` (the schema owns the public vocabulary — H-02 precedent), registry consumes it; dependency direction unchanged (viz→vocab existed; render still imports viz/themes/errors only). architecture.md §3 now states the enforcement. Regressions: 6 rejection cases + 2 construction cases (`test_viz_contract.py`), each rejection a reproduced pre-fix leak. Consequence honestly recorded: the two renderer-robustness fixtures that DEPENDED on arbitrary display names (long-name truncation, XML-escape) can no longer be constructed — by design; those properties are now pinned at the `_truncate`/`_text` helper layer, and the construction-rejection tests are the stronger replacement. |
| M-01 — same-identity leaves with different timestamps break permutation purity | **Accepted** | Reproduced: reversed input orders produced different canonical events (timestamp copied from `first`). Timestamp is not in event identity, so the disagreement is legal input. Fix: `timestamp=resolve("timestamp")` — the SAME strongest-leaf canonical rule (ADR-008) as every other scalar; schema.md §8.3 states the rule. Regression: same identity, different timestamps, different sources → both orders byte-identical, winner = strongest leaf (trailer over coauthor at equal evidence). |
| M-02 — whole-number rounding states false endpoint percentages | **Accepted** | Reproduced: 1/201 rendered "0% of 201", 200/201 rendered "100% of 201" — both contradicting the count and share bar. Fix: `_pct_label` — exact 0%/100% only for exactly-zero/exactly-total shares; rounding that would fabricate an endpoint renders `<1%` / `>99%` (deterministic, compact); applied to the hero share AND provider rows. No aggregation change. Regressions: boundary + exact-endpoint cases for both surfaces. Fixture snapshots unaffected (no fixture share hits an endpoint). |
| L-01 — light-theme unknown evidence mark below 3:1 | **Accepted** | Reproduced: `#8c959f` at 2.85:1 vs the `#f6f8fa` panel. Fix: Primer fg-muted `#6e7781` (4.27:1) — still visually subordinate, still neutral vs the blue ramp; dark theme already passed (3.77:1). Full evidence system re-validated: both ordinal ramps ALL CHECKS PASS, both unknown marks ≥3:1; contrast pin regression added (was red for light). Snapshots + the light sample asset regenerated via the sanctioned script. |
| L-02 — sample regeneration path undocumented | **Accepted** | Confirmed: the sanctioned script wrote only tests/snapshots; CONTRIBUTING documented snapshots only, so contributors had to hand-build docs/assets. Fix: `python tests/unit/test_render_summary.py` now regenerates snapshots AND both README sample assets from the same authoritative fixture (`_write_sample_assets`); CONTRIBUTING.md documents the single command and forbids hand-editing; the byte-exact drift guard stays. |


---

## Gate-8 review round (gate-review.md, 2026-07-16; NOT READY)

An independent verification review of `9933308..73279cd` confirmed four
of five gate-7 dispositions closed and produced two reproduced gaps in
the fifth (the H-01 boundary work). Both adjudicated **accepted** after
independent reproduction; both fixed red-first. Remediation committed
as `e0fa569`. The review artifact itself is preserved untouched in
gate-review.md.

| Finding | Disposition | Technical justification + resolution |
|---|---|---|
| H-01 — the validated VizStats graph is not structurally immutable | **Accepted** | Reproduced all three bypasses: a mutable list passed for the tuple-annotated providers field; a tuple holding a mutable duck-typed row passed; a mutable period-like object passed — and post-construction mutation of the latter two published private strings through BOTH render_summary and dumps_stats. Root cause: `_validate` checked VALUES via duck-typed attribute access but never the declared runtime TYPES, and frozen semantics only covered the outer dataclass. Fix (strict rejection — option 1, the smallest architecture-consistent choice, matching the schema layer's rejection-over-coercion philosophy): `_require_exact` enforces `type(x) is` the exact frozen contract type for the COMPLETE graph (Period, Totals, EvidenceTotals, PrivacySplit, tuple container, every ProviderRow) BEFORE any duck-typed access, plus exact-`str` checks on every string leaf (schema_version, period.label, generated_on, slugs, display names — a str subclass can emit render-time text validation never saw). `isinstance` deliberately avoided: subclasses can be mutable or dynamic. After validation the whole graph is frozen dataclasses, tuples, and plain immutable leaves — mutation raises FrozenInstanceError and output bytes cannot change (pinned). Regressions: 8 new cases, each pre-fix-failing bypass or pin; no renderer sanitization; enforcement stays centralized in VizStats. The in-round code-review pass then found (and reproduced: svg_leak=True) a surviving variant — an int SUBCLASS overriding __str__ passed `isinstance` and lied at render time — closed the same way: counts require exact int (which also rejects bool), the privacy flag exact bool; 4 more pre-fix-failing regressions. |
| L-01 — generated_on accepts non-canonical and invalid dates | **Accepted** | Reproduced all five: full-width digits, Arabic-Indic digits, trailing newline, 2026-99-99, and invalid leap 2025-02-29 all constructed. Root cause: Unicode-aware `\d` + `.match()` with `$` checks shape, not the contract. Fix: ASCII `[0-9]` pattern with `fullmatch` (kills Unicode digits and the newline artifact) + `datetime.date.fromisoformat` + canonical round-trip equality (kills impossible dates and non-canonical forms). Regressions: 7 rejection params (each pre-fix-failing) + leap-day/production-date acceptance. |


---

## Gate-9 review round (gate-review.md, 2026-07-18; NOT READY)

An independent verification of `73279cd..e0fa569` confirmed the gate-8
closures but found the exact-type work incomplete at the TOP level, plus
a documentation-integrity gap. Both findings independently reproduced,
both accepted, H-01 fixed red-first. The review artifact is preserved
untouched in gate-review.md.

| Finding | Disposition | Technical justification + resolution |
|---|---|---|
| H-01 — a VizStats subclass can inject private text after validation | **Accepted** | Reproduced: an ordinary subclass (`EvilStats(VizStats)`) inherits the validating constructor, passes `__post_init__` with a legitimate graph while a class flag is False, then its overridden `__getattribute__` returns a different exact `ProviderRow` (private canary) for `providers` once the flag flips — svg_leak AND json_leak both True, using no `object.__setattr__`/ctypes/pickle. Gate-8's exact NESTED checks could not catch it: they run while the subclass is still honest. Root cause: no guard required `type(s) is VizStats`. A first-pass fix that checked type inside `_validate` was INCOMPLETE — the gate-9 verification review reproduced a stronger variant: a subclass overriding `__post_init__` to `pass` never calls `_validate` at all and leaks from construction (an ordinary, documented dataclass extension point, not a low-level bypass). Final fix: `VizStats.__init_subclass__` raises `TypeError` at class-definition time, sealing the entire family (deferred-`__getattribute__` substitution, `__post_init__`-skip, deep chains, any future dunder override) at its root; a `type(s) is VizStats` backstop remains inside validation for exotic metaclass-created instances. Confirmed no legitimate subclass exists and replace/copy/pickle all yield exact `VizStats`, so sealing breaks nothing. Regression: subclass DEFINITION (both variants) raises `TypeError`. architecture.md §3 updated to "sealed against subclassing". |
| L-01 — remediation status records contradict committed state | **Accepted** | Correct: `progress.md` and this file described the gate-7 and gate-8 remediations as "UNCOMMITTED pending authorization" while both are in history (`73279cd`, `e0fa569`). Fix: both records now state the actual commit hashes and "resolved/committed"; the fact that each independent review predated its fix is preserved, and the review artifact's original findings/recommendation are untouched. (The gate-7 record was equally stale and corrected in the same pass, for a consistent audit trail.) |

---

## Gate-10 review round (gate-review.md, 2026-07-22; READY FOR NEXT GATE — zero findings)

An independent verification of `e0fa569..d9161cb` (the gate-9
remediation) returned **zero findings** at every severity — the first
clean round in the chain. The reviewer's own from-scratch bypass replay
(eight subclass vectors, all `TypeError` at class-definition time),
lifecycle checks (replace/copy/deepcopy/pickle -> exact `VizStats`),
fresh-repo privacy sweeps, full suite (340 passed, 1 skipped), ruff,
and byte-stable snapshot regeneration all passed. No remediation
required; the VizStats structural-immutability finding chain (gates
7-10) is closed. Further gate rounds are expected before OSS release
(pre-release hardening/packaging, progress.md Open items). The review
artifact is preserved untouched in gate-review.md and committed with
this closure, restoring the commit-alongside-resolution convention that
gate-9 had deferred.

Process note: this round ran through the file-based handoff protocol
(brief at `.ai/handoff/001_gate9_remediation_verification.to_codex.md`,
reply at the sibling `.to_fable.md`, headless `codex exec` via the
codex-delegate wrapper) instead of manual copy-paste between apps. The
gate-8 review text, which gate-9 deliberately left uncommitted and this
round's report overwrote, is preserved verbatim in the local (ignored)
snapshot `.ai/handoff/000_gate8_review_snapshot.to_fable.md`.

Second independent confirmation: a parallel Codex-app round (run by the
owner over the same `e0fa569..d9161cb` range, written 2026-07-21 21:27
local — after this closure was committed) independently returned the
same verdict: READY FOR NEXT GATE, no findings at any severity. Its
report is preserved verbatim as `gate9-second-opinion.md`; the headless
round's report remains the canonical `gate-review.md` record. Two
transports, two sessions, one clean verdict.

---

## Gate-11 review round (gate-review.md, 2026-07-22; READY AFTER MINOR FIXES)

Independent verification of `77ed004..278c138` (pre-release hardening
round A) via the headless handoff lane (brief 003). One Medium finding,
reproduced by the reviewer and accepted; fixed red-first.

| Finding | Disposition | Technical justification + resolution |
|---|---|---|
| M-01 - existing installations never receive the permission retrofit | **Accepted** | Reproduced: `init_home()` returns `load_config(home), False` BEFORE any chmod when config.json already exists (`created False`, `chmod_calls []`), so a user whose AIPROFILE_HOME predates the hardening keeps default-permission files forever unless they delete and re-init. Fix: `load_config` now calls `_restrict_to_owner(home, 0o700)` + `_restrict_to_owner(config_path, 0o600)` on every load - the choke point every command (init early-return, scan, aggregate, render) passes through, mirroring `db.connect`'s restrict-on-every-call design. Cheap, idempotent, and reaches upgraded users on their first post-upgrade command. Regression: `test_load_config_retrofits_owner_only_permissions` (pre-existing config written WITHOUT init_home, chmod recorder) - proven red against the pre-fix code (observed `calls == []`), green after. |

---

## Gate-12 review round (gate-review.md, 2026-07-22; READY FOR RELEASE - final gate)

Independent final pre-release verification of `278c138..ac21d4d` (the
gate-11 resolution, Round B console-sweep + property-fuzzing tests, and
Round C packaging/CHANGELOG/bilingual-README) via the headless handoff
lane (brief 004). **Zero findings at every severity.** The reviewer
independently: re-ran the full suite (364 passed, 4 skipped) and ruff;
ran both new Round B test files twice (hypothesis determinism); built
the wheel and verified PEP 639 metadata + twine check on both
artifacts; ran the release smoke script end-to-end (PASS, clean
scratch); probed the gate-11 retrofit under injected chmod failure
(warns, never raises); regenerated snapshots (byte-stable); and ran a
fresh synthetic-repo privacy byte-sweep (9 canaries, leaks: []).

The v0.1 release gate chain closes here: gates 2 through 12, eleven
independent adversarial rounds, the final round with zero findings.
The review artifact is committed verbatim with this release closure.

---

## Gate-13 review round (gate-review.md, 2026-07-22; READY FOR NEXT GATE - zero findings)

Independent verification of `1d63814..08922b7` (Image 2.0 round D1,
provider brand identity) via the headless handoff lane (brief 005).
Zero findings at every severity. The reviewer independently: re-ran the
suite (375 passed, 4 skipped), ruff, the targeted privacy battery (30
passed), snapshot determinism (twice, clean), and the release smoke
script; probed contrast ratios (all >=3:1), XML-attribute safety of all
five glyph paths, fallback purity (0 path elements for non-branded
slugs), and confirmed `viz.py` has an empty diff across the range.
Honest limitation recorded in the review: the reviewer's sandbox could
not reach raw.githubusercontent.com to re-diff the vendored path data
against the pinned upstream commit; it corroborated version/license/
slug-presence via public npm/CDN metadata instead. That exact
byte-level diff was independently performed against commit f7cc400 by
the internal review during the round (all five identical), so the
provenance claim is covered by one direct and one corroborating check.
The review artifact is committed verbatim with this closure.

---

## Gate-14 review round (gate-review.md, 2026-07-22; READY AFTER MINOR FIXES)

Independent verification of `383792f..5b01195` (Image 2.0 round D2, the
publishable-only isometric calendar) via the headless handoff lane
(brief 006). One Low finding, fixed in this closure.

The reviewer independently: re-ran the suite (421 passed, 4 skipped),
ruff, the calendar/render test set (53), and twice-clean snapshot
regeneration; built a live two-repo CLI scenario (one full, one
aggregate-only, IN-window canary date) and byte-swept dist/ - the
aggregate-only date was absent from every output with the full repo's
date as positive control; probed the VizStats daily battery, the
substr-vs-date() SQL timezone behavior, the static-render claim (zero
animate markup), and the schema-version compatibility pair (0.1 stored
events aggregate; fabricated 0.3 refuses).

| Finding | Disposition | Resolution |
|---|---|---|
| L-01 - new blank line at EOF (tests/unit/test_calendar_band.py:440; git diff --check fails) | **Accepted** | Trailing blank line removed; `git diff --check` clean; suite re-run green. |

---

## Gate-15 review round (gate-review.md, 2026-07-23; NOT READY)

Independent verification of `ea5f37d..d2c1147` (round D3) via the
headless handoff lane (brief 008). One High finding - and the probe
that found it exposed a LATENT V0.1-ERA BUG, not just a D3 gap.

| Finding | Disposition | Technical justification + resolution |
|---|---|---|
| H-01 - display-name trailer forms do not resolve (AI-Provider: Kimi/Qwen/Grok/GLM/Llama -> None) | **Accepted** | Reproduced, and widened on investigation: the alias table only ever carried company-slug spellings, so the D1-era display names failed identically (Claude/Gemini/Copilot -> None since v0.1 - masked because the README example uses the company form "Anthropic"). Users declare the PRODUCT name they know; this defeated the declaration tier's entire purpose for the most likely spellings. Fix: PROVIDER_ALIASES now derives an entry from EVERY schema-owned display name (PROVIDER_DISPLAY -> lowercased display -> slug), closing the class permanently for future providers, plus common spacing/punctuation variants (Mistral AI, Meta AI, x.ai, Z.ai, Moonshot AI; Amazon Q arrives via the derivation). Regressions proven red pre-fix: test_display_name_trailer_forms_resolve_to_canonical_slugs (iterates the whole display map) + test_common_provider_name_variants_resolve. |

Also recorded from the review: the reviewer's sandbox could not reach
raw.githubusercontent.com to byte-diff the 8 vendored icon paths (the
same network limitation as gate-13); that diff was performed directly
by the internal review round (8/8 identical) and independently
reproduced via the vendoring script - one direct plus one
corroborating check, per the gate-13 precedent.

---

## Gate-16 review round (gate-review.md, 2026-07-23; READY, zero findings)

Independent re-verification of `d2c1147..66bc3e9` (gate-15 resolution)
via the headless handoff lane (brief 009). The reviewer re-ran the
gate-15 probe verbatim plus widened checks: 15 direct aliases, all 21
schema-owned display names, 23 pre-existing alias keys unchanged, no
collisions, and a synthetic `AI-Provider: Kimi` commit rendered
end-to-end as `moonshot`/`Kimi` with the vendored Moonshot mark and no
public-output privacy canary leaks. Suite 444 passed / 4 skipped;
ruff clean. Severity: Critical 0, High 0, Medium 0, Low 0.

No findings to disposition. **Round D3 is closed.**

Process disclosure (same class as the gate-14 note): while this review
ran, the working tree carried uncommitted doc-only edits (README user-
audit fixes + new `.github/workflows/ci.yml`). The review target -
`src/aiprofile/registry.py` and its tests at `66bc3e9` - was untouched
and committed; the reviewer's suite/probes ran against that committed
code. The doc edits ship separately with their own review round.

---

## Gate-17 review round (gate-review.md, 2026-07-23; READY, one Low)

Independent verification of `bd0e3ce..1864d65` (rounds D5 + D4) via the
headless handoff lane (brief 010). The reviewer re-ran the pinned lobe
vendoring command independently (2 vendored, 0 skipped - provenance
confirmed from upstream), and ran adversarial probes across in-process
privacy, CLI end-to-end canary assets (all seven dist files), the
DayCell contract battery, share/volume bin math at the exact quarter
boundaries, badge honesty rounding, and Monday-anchored grid alignment.
Suite 491 passed / 4 skipped; ruff clean.
Severity: Critical 0, High 0, Medium 0, Low 1.

| Finding | Disposition | Resolution |
|---|---|---|
| L-01 - stale comment: summary_svg.py:171 claimed CAL_WINDOW_DAYS "matches viz.DAILY_WINDOW_DAYS exactly", untrue since the D4 window widened to 365 | **Accepted** | Comment rewritten to describe the band's own newest-anchored 84-day slice of the wider series; suite re-run green. |

**Rounds D5 and D4 are closed.**

---

## v0.7.0 Gate E3 review round (2026-08-10; NOT READY)

Independent verification of `cc69303..17822fe` reproduced six High and four
Medium findings after the first all-green cross-platform candidate run. No
schema, aggregation, `VizStats`, renderer, or exact-eight change is part of
the accepted remediation.

| Finding | Disposition | Resolution |
|---|---|---|
| H-01 — scheduler Git calls trust ambient repository-selection state | **Accepted** | One centralized environment boundary removes ambient repository/object/namespace/replacement/shallow/index/tracing/injected-config variables from install and launcher Git calls. Only explicit private-index state and ordinary credential transports remain. Shallow and partial clones are rejected before refresh or pending retry because the isolated private Git directory requires complete local history. Hostile-environment install and end-to-end launcher regressions pin the boundary. |
| H-02 — an unpushed local ancestor can reach the remote | **Accepted** | Before any push-capable refresh, suppressed `ls-remote` output must yield one exact recorded-branch OID equal to captured local `HEAD`. Missing/ahead/behind/diverged/unverifiable state stops before refresh or Git mutation with a fixed path-free message. Publication additionally requires one fetch URL and the same single push URL, captures that destination before refresh, resolves relative local paths from the Profile repository (including same-drive Windows drive-relative paths while rejecting cross-drive ambiguity), and binds it to a fixed alias in an isolated private Git context; actual push/query argv never contains the URL, and multiple/different/credential-bearing destinations plus later `insteadOf`/`pushInsteadOf`/remote-alias/config swaps fail closed or cannot redirect the isolated transport. Eight exact credential-helper/TLS/SSH keys are queried individually and frozen; authorization headers, Git-config/ambient proxies, and URL rewrites are never queried or forwarded. The actual immutable-OID push uses an exact expected-old lease tied to that same parent, then re-queries the isolated captured destination before clearing pending state; rewind, advance, deletion, config swap, or an unverified reported success at the push boundary fails closed. |
| H-03 — staged worktree bytes are not bound to refresh; homes can collide | **Accepted** | Refresh returns a private in-memory SHA-256 commitment for the exact eight rendered bytes. The private-index modes/paths/raw blob bytes must match it before `write-tree`; binary reads prevent Windows newline normalization from weakening the commitment. A lock in the target Git common directory serializes different homes targeting one Profile. This adds no public manifest or output. |
| H-04 — failed push is not retried | **Accepted** | Push-capable publication writes a `0600` POSIX immutable commit/parent/tree/branch/remote pending record with a SHA-256 commitment of the captured destination (never its URL) before the forward ref CAS, with atomic replacement as its final fallible step. If a process dies before CAS, a later run may complete that exact CAS only while both local and remote still equal the recorded parent and the current single destination matches the commitment. If CAS completed, retry repairs and verifies the exact-eight real index before pushing the recorded OID. Confirmed success clears the record; destination/config divergence or repair failure keeps it, refuses push, and reports every possible index/ref/pending residual. |
| H-05 — same path/different UID can publish stale cached rows | **Accepted** | Planning resolves the entire config first and rejects a resolved path mapped to different UIDs before real/dry scan, cache access, or output mutation. Real/dry regressions retain stale canary rows and prove home/output bytes remain unchanged and path/name-free. |
| H-06 — native status accepts execution-semantic drift | **Accepted** | Windows status now proves the task-schema namespace of every inspected descendant, tool principal, interactive token, least-privilege run level, single daily trigger/action, exact local `2000-01-01T<HH:MM>:00` boundary, action context, and either the exact three authored settings or the exact harmless/default settings emitted by a real in-memory Task Scheduler COM round-trip. Launchd requires its exact four-key owned payload. Missing/foreign namespaces, altered privilege/identity/date/timezone/frequency, value drift, or any unrecognized execution key is unverifiable and blocks mutation. |
| M-01 — no real hosted caller/Pages E2E | **Accepted as post-PyPI promotion gate** | Static tests cannot replace hosted behavior. `docs/RELEASING.md` now requires a disposable public Profile byte-changing run plus a no-change run, exact-eight commit, immutable `published-sha`, Pages HTTP 200, and no second commit before Public Beta promotion. |
| M-02 — scheduler interpreter lifetime undocumented | **Accepted** | English and Traditional Chinese README guidance now says the installing interpreter/venv path must persist and instructs users to reinstall plus confirm status after moving, removing, or upgrading it. |
| M-03 — immutable caller pin depends on merge ancestry | **Accepted as pre-tag gate** | v0.7.0 must merge with a merge commit. Before branch deletion/tagging, the runbook requires `merge-base --is-ancestor` for full C1 SHA `9c4f276...` against `origin/main` and GitHub Contents-API resolution of the pinned workflow blob. |
| M-04 — `last-run.log` is `0644` under umask 022 | **Accepted** | The launcher creates/retrofits the log at `0600` on POSIX inside the existing `0700` scheduler directory, rejects linked/non-regular scheduler state before reading or changing modes, and keeps the closed path-free vocabulary. POSIX regressions cover umask 022 plus file/directory links without mutating external targets. |

The review's **NOT READY** verdict remains current until the remediation range,
rebuilt artifacts, cross-platform CI, and second independent review complete.

---

## Gate-18 review round (gate-review.md, 2026-07-23; READY AFTER MINOR FIXES)

Independent verification of `b70f3a5..63f00c6` (round D6 aesthetic
pass) via the headless handoff lane (brief 011). The reviewer verified
the range is genuinely renderer-only (byte-compared badge/empty
snapshots against the pre-range tree), probed the color math for
bg/track collisions (none), confirmed grid positions identical to the
previous range, and ran the end-to-end seven-asset privacy canary.
Suite 493 passed / 4 skipped; ruff clean.
Severity: Critical 0, High 0, Medium 0, Low 2.

| Finding | Disposition | Resolution |
|---|---|---|
| L-01 - _cell_rects recomputed the fill formula inline instead of calling _cell_fill, contradicting the round's single-color-source claim | **Accepted** | Day cells now call _cell_fill directly; snapshots unchanged (byte-neutral refactor - the two paths were provably identical, now structurally so). |
| L-02 - stale fill-opacity wording in the module docstring and _cell_rects docstring | **Accepted** | Both rewritten to describe the solid background-mix encoding. |

**Round D6 is closed.**

---

## v0.7.2 candidate self-verification (2026-08-23; CANDIDATE — awaiting CI and independent review)

Scope: the uncommitted v0.7.2 release diff on `codex/scheduler-remote-sync`
(version bump, scheduler metadata read-set, staging workflow and manifest
repin, changelog/ADR/architecture/schema status). Verified by the Fable
implementer only; no Codex round has reviewed this range yet. GitHub run
32657558104 on `63cd0ae` (PR #34) passed the Python 3.11–3.14 test jobs and
failed only the release-candidate build, on the superseded `551e…` wheel pin
corrected below; CI on the repinned commit is still pending.

| Check | Result |
|---|---|
| Windows Python 3.14 full suite | 960 passed, 30 skipped |
| Windows focused release/staging/scheduler suites | 129 passed, 4 skipped |
| WSL Ubuntu Python 3.12 full suite | 984 passed, 6 skipped |
| Ruff (`src tests scripts`), README parity, `git diff --check` | clean |
| Ubuntu double build, `SOURCE_DATE_EPOCH=1786320000`, hatchling 1.31.0 | first build reported `551e8dd6…4a44f7`, but it was a WSL build of a copied Windows worktree that retained CRLF bytes — superseded. GitHub run 32657558104 on `refs/pull/34/merge` and a clean WSL git clone of `63cd0ae` both produce `4f65ef45…6708f`; manifest/workflow/test pins now carry `4f65ef45…` |
| Twine, `check_release_artifacts.py --expected-wheel-sha256`, `release_smoke.py` | PASS |
| Regression coverage | `test_candidate_manifest_is_the_v0_7_2_candidate_not_a_released_digest`, `test_scheduler_metadata_version_tracks_the_package_version`, v0.7.0/v0.7.1 migration test |

Disposition: **candidate only**. Release gates (PR CI on the bumped commit,
independent review, merge, tag, publish, dogfood) remain open.

---

## v0.8.0 Signal Console candidate self-verification (2026-08-23; CANDIDATE — awaiting CI and independent review)

Scope: the v0.8.0 candidate on `codex/v080-signal-console` from `63c108d`
(ADR-031): coordinated dashboard / summary / heatmap / badge redesign,
red-first `tests/unit/test_signal_console.py` plus updated renderer,
release, staging, and scheduler contracts, sanctioned snapshot and README
asset regeneration, `DESIGN.md`, `.impeccable.md`, docs, version bump to
0.8.0, scheduler metadata read-set, candidate manifest and staging pins.
Verified by the Fable implementer only; no Codex round has reviewed this
range yet and no GitHub CI has run on it.

| Check | Result |
|---|---|
| Red-first contract | `test_signal_console.py` 17 tests + updated dashboard/recruiter/summary/model/release/staging/scheduler tests failed against the v0.7.2 renderers (31 failures), pass after implementation |
| Windows Python 3.14 full suite | 977 passed, 30 skipped |
| WSL Ubuntu Python 3.12 full suite (clean git clone) | 1001 passed, 6 skipped |
| Ruff (`src tests scripts`), README parity, `git diff --check` | clean (Windows and WSL) |
| Sanctioned snapshot commands | summary and heatmap/badge families + 6 README sample assets regenerated; rerun in the WSL clone produces zero drift |
| `npx impeccable detect --json` (impeccable 3.6.0) on the rendered dashboard | `[]`; the v0.7.2 dashboard from the same fixture reported 6 findings (layout-transition, hero-eyebrow-chip, all-caps-body, gpt-thin-border-wide-shadow ×2, flat-type-hierarchy) |
| Browser QA (Playwright 1.58 / Chromium) | 1440×900, 1024×768, 768×1024, 390×844, 320×568, 195×600 in light + dark with `data-theme="auto"`: zero horizontal overflow, min rendered font 13px, zero network requests; 390 first viewport holds metrics + commit map; filter/theme/tooltip/keyboard/disclosure/reduced-motion/zero-state interactions pass — `docs/reviews/v0.8.0-visual-qa.md` |
| Clean Ubuntu git-clone build, `SOURCE_DATE_EPOCH=1786320000`, hatchling 1.31.0, build 1.4.3 | two builds byte-identical: wheel `9cc06f2052a642bd198fa00d728c75b72fce061dad24c51b72feddf84b07c89e`, reproduced again from a clean clone of the final candidate commit. The sdist digest is deliberately not recorded here: this file ships inside the sdist, so any pre-recorded sdist digest self-invalidates; the wheel is the authorized artifact and the publish workflow checksums its own pair |
| Twine, `check_release_artifacts.py --expected-wheel-sha256`, `release_smoke.py` | PASS on Ubuntu (build host) and on Windows consuming the same wheel bytes |
| Frozen four-role dogfood against the exact wheel | newcomer, privacy (full / aggregate_only / excluded, 0 canary hits), multi-provider (1 unique commit, 2 presences, human and unknown separate), publisher (exact eight, byte-identical double refresh, faithful dry-run, CSP, snapshot label): 4/4 PASS — scripted by the implementer in isolated WSL venvs/homes/repos, not independent role agents |
| Regression coverage | `test_signal_console.py`, `test_dashboard_html.py`, `test_recruiter_card.py`, `test_render_summary.py` (12px floor), `test_model_renderers.py`, `test_release_workflow_contract.py` (v0.8.0 notes, released-digest guard now covers 0.7.2), `test_staging_preview.py`, `test_schedule_cli.py` / `test_launcher.py` (v0.8.0 metadata) |

Post-review note: the independent code-reviewer round returned APPROVE with
two non-blocking suggestions (an SVG-namespace clarifying comment in the
dashboard script; a progress.md phrasing fix). Both were applied as the
reviewer's own explicit same-session suggestions; because the comment changes
dashboard and wheel bytes, the dashboard digest
(`b9c7208ee1bece4a0a6cd39ea1b569a55ed30a78d14d85cdb74ee52b89b4cc48`) and the
wheel/sdist digests above were re-derived from a fresh clean-clone double
build, and Twine, artifact, smoke, and the four-role dogfood were rerun
against the final wheel — all PASS. The final committed tree was rebuilt from
its own clean clone and reproduces the pinned wheel digest.

Disposition: **candidate only**. Release gates (PR CI on the candidate
commit, independent review, merge, tag, publish, staging deploy, Profile
refresh) remain open.

## v0.8.1 Collaboration Pulse candidate self-verification + Codex staged-diff review (2026-08-23; CANDIDATE)

Scope: the v0.8.1 candidate on `codex/v081-collaboration-pulse` from
`6b5511d` (ADR-032): summary-card-only Collaboration Pulse redesign,
red-first pulse contract tests, version bump to 0.8.1, scheduler metadata
read-set, candidate manifest repin, released-digest guard closure for
0.8.0, docs (ADR-032, DESIGN.md, .impeccable.md, READMEs, CHANGELOG,
ROADMAP, progress, schema status, ADR-030/architecture scheduler-version
parity). Dashboard, heatmap, and badge renderers untouched.

| Check | Result |
|---|---|
| Red-first contract | rewritten `test_calendar_band.py` + updated `test_recruiter_card.py` / `test_signal_console.py` written against the v0.8.0 renderer (import/geometry failures), pass after implementation; scheduler-docs parity test written red against the stale ADR-030/architecture statements, green after the doc fix |
| Windows Python 3.14 full suite | 981 passed, 30 skipped |
| Ruff (`src tests scripts`), README parity, `git diff --check` | clean |
| Sanctioned snapshot command | summary family + 2 README sample assets via `python tests/unit/test_render_summary.py`; rerun produces zero drift; heatmap/badge snapshots byte-identical; `summary_zero_*` byte-identical |
| Visual QA | `docs/reviews/v0.8.1-visual-qa.md` — synthetic sparse and real maintainer aggregate, light/dark, 830/664px, 1x/2x, all clear |
| Deterministic build, `SOURCE_DATE_EPOCH=1786320000` | canonical clean Ubuntu builds byte-identical at commit `60a0701`: CI run `32678706758` and an independent clean WSL Ubuntu clone both produce wheel `1faceac31ac7d9c3a99e3e4678bdfb725f73341e89e5847dc6a578ed8a6bbff9`, now pinned in `docs/reviews/promotion-candidate.json`. The earlier Windows-built `d525eef3…` was a diagnostic artifact only and is rejected per `docs/RELEASING.md` (platform ZIP metadata + CRLF bytes for untouched `brand.py` differ; never substitute a Windows-built wheel). PR #38 first run: Python 3.11–3.14 green, release-candidate build red on the wrong-platform pin (contract working as designed), wheel onboarding skipped pending the repin. The published v0.8.0 digest `9cc06f20…` sits in `RELEASED_WHEEL_SHA256` |

Independent Codex staged-diff review, round 1 (fingerprint
`eac245469b0a3240baffb640559fb65e29547cb8`): **REQUEST CHANGES**, three
findings, dispositioned as follows:

1. Version parity — ADR-030 and architecture.md still stated the v0.8.0
   scheduler write contract. FIXED red-first:
   `test_scheduler_version_docs_state_the_current_contract` (derived from
   the `service` constants) failed on the stale docs, both docs updated
   (read v0.7.0–v0.8.0 plus current, emit v0.8.1), test green. Hosted
   `profile-refresh.yml` / staging-preview published-v0.8.0 pins untouched.
2. progress.md stale "commit B in review" — FIXED: PR #37 recorded merged
   at `6b5511d` with green main run `32667422511`; historical digest
   explanation preserved; the "next version bump" consequence paragraphs
   now note v0.8.1 closed the released-digest gap.
3. DESIGN.md extension points still said "flat daily timeline" — FIXED:
   now names the Collaboration Pulse helpers.

Additional completion evidence recorded in the same round (not reviewer
findings): `docs/reviews/v0.8.1-visual-qa.md` (synthetic + captured real
local aggregate; screenshots kept out of the repository) and this
review-disposition section itself.

Disposition: **candidate only**. Awaiting targeted Codex recheck of the
updated staged diff, then green CI on the candidate commit, merge, tag,
publish, staging deploy, and Profile refresh.

## v0.8.1 hosted pin commit B: public caller contract & upload-artifact v7.0.1 (2026-08-23; CANDIDATE)

Scope: the postrelease commit B on `codex/v081-public-caller-b` from
`8b8a543` (main, merged PR #39 commit A `6a39ff4`):
- Public caller contract repinned to immutable commit A `6a39ff46e2716f2c30385c53419b6b25c2790ec5`
  with `ai-profile-cli==0.8.1`: `docs/templates/profile-refresh-caller.yml`, `README.md`,
  `README.zh-TW.md`, `scripts/check_readme_parity.py`, `tests/unit/test_readme_parity.py`,
  `tests/unit/test_profile_refresh_workflow.py`, and `docs/decisions/ADR-030-automation-layer.md`.
- `actions/upload-artifact` upgraded from v4.6.2 (`ea165f8d65b6e75b540449e92b4886f43607fa02`,
  Node 20) to verified immutable v7.0.1 (`043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`,
  Node 24) across all four first-party workflows (`ci.yml`, `profile-refresh.yml`,
  `publish.yml`, `staging-preview.yml`), preserving inputs, permissions, and semantics.
- Staging-preview checkout remediation: `.github/workflows/staging-preview.yml`
  build job checkout pinned to immutable v0.8.1 release commit `49e574b0ce80eef14cf38a20b654d03e9a50538c`
  on `main`, ensuring manual staging runs from `main` check out and verify the published v0.8.1
  release rather than unreleased development bytes from moving `main` HEAD. Guarded by
  `test_workflow_build_checks_out_the_immutable_v0_8_1_release_commit` in `tests/unit/test_staging_preview.py`.
- Wheel-digest lifecycle resolved: released v0.8.1 wheel digest (`1faceac31ac7d9c3a99e3e4678bdfb725f73341e89e5847dc6a578ed8a6bbff9`)
  remains permanently guarded in `RELEASED_WHEEL_SHA256["0.8.1"]`. Transitioned development
  version to `0.8.2` in `pyproject.toml`, `src/aiprofile/__init__.py`, `SCHEDULER_VERSION`
  (readers accept v0.7.0–v0.8.2, writers emit 0.8.2; ADR-030 and architecture.md updated),
  and `docs/reviews/promotion-candidate.json` authorizes candidate wheel
  `483ad35b14655d275a249c680a75f830f09b3d1920a59280350c7a0cf3128fb7` (development only).

Codex staged-diff review blocker disposition:
- Review blocker 1: Staging preview checkout on `main` was unpinned, which would build from moving
  `main` HEAD and fail the v0.8.1 artifact verification once `0.8.2` development commits land.
  FIXED: Staging checkout pinned to `49e574b0ce80eef14cf38a20b654d03e9a50538c` with regression test.
- Review blocker 2: Candidate manifest wheel digest required updating for the final candidate bundle.
  FIXED: `promotion-candidate.json` updated to `483ad35b14655d275a249c680a75f830f09b3d1920a59280350c7a0cf3128fb7`
  (independently reproduced by Codex with exact CI tooling; second CI-exact WSL reproduction completed: Python 3.12.13, build==1.4.3, hatchling==1.31.0 isolation, SOURCE_DATE_EPOCH=1786320000; wheel SHA256 `483ad35b14655d275a249c680a75f830f09b3d1920a59280350c7a0cf3128fb7`; check_release_artifacts PASS).

| Check | Result |
|---|---|
| Red-first contract tests & regressions | 10 tests proven failing red against baseline, green after implementation |
| Windows Python 3.14 full suite | 983 passed, 30 skipped in 462.21s |
| Focused test suite (workflow, parity, staging, release contract, scheduler CLI, launcher, recruiter card) | 171 passed, 16 skipped (Windows Python 3.14) |
| Parity check | `python scripts/check_readme_parity.py` -> PASS |
| Ruff & diff checks | `python -m ruff check src tests scripts` clean; `git diff --check` clean |
| Canonical wheel reproduction | Codex completed second CI-exact WSL reproduction: Python 3.12.13, build==1.4.3, hatchling==1.31.0 isolation, SOURCE_DATE_EPOCH=1786320000; wheel SHA256 `483ad35b14655d275a249c680a75f830f09b3d1920a59280350c7a0cf3128fb7`; check_release_artifacts PASS |

Disposition: **staged for Codex independent review**.

## v0.8.1 hosted pin commit C: immutable public caller repin to commit B (2026-08-23; CANDIDATE)

Scope: the postrelease commit C on `codex/v081-public-caller-c` from
`da4c08e` (main, merged PR #40 commit B `9c246d9`):
- Public caller contract repinned to immutable commit B `9c246d95052264c24e7175cabd295951c5236efc`
  with `ai-profile-cli==0.8.1` and `actions/upload-artifact` v7.0.1 (Node 24): `docs/templates/profile-refresh-caller.yml`,
  `README.md`, `README.zh-TW.md`, `scripts/check_readme_parity.py`, `tests/unit/test_readme_parity.py`,
  `tests/unit/test_profile_refresh_workflow.py`, and `docs/decisions/ADR-030-automation-layer.md`.
- Stale commit-A pin assertions removed from the live contract (`COMMIT_B = "9c246d95052264c24e7175cabd295951c5236efc"`,
  forbids `6a39ff4` in caller template) while historical evidence is retained.
- Candidate manifest `docs/reviews/promotion-candidate.json` updated to the final rebuilt candidate wheel digest
  `a6c64bc9d504518743e3811e9a1314310f25275db802f367e944799af1f9d81a` for unpublished `0.8.2` development candidate
  (reproduced by Codex using the exact GitHub Actions runtime from official actions/python-versions release 3.12.14-31661455385:
  Ubuntu 24.04 x64 CPython 3.12.14 toolcache, `build==1.4.3`, `hatchling==1.31.0` isolation, `SOURCE_DATE_EPOCH=1786320000`,
  clean origin/main archive plus staged diff; `check_release_artifacts.py` PASS).

| Check | Result |
|---|---|
| Red-first contract tests & regressions | 6 tests proven failing red against baseline, green after implementation |
| Focused test suite (workflow, parity, staging, release contract, scheduler CLI, launcher, recruiter card) | 171 passed, 16 skipped (Windows Python 3.14) |
| Parity check | `python scripts/check_readme_parity.py` -> PASS |
| Ruff & diff checks | `python -m ruff check src tests scripts` clean; `git diff --check` clean |
| Canonical wheel reproduction | Codex reproduced from final staged source using exact GitHub Actions runtime from official actions/python-versions release 3.12.14-31661455385: Ubuntu 24.04 x64 CPython 3.12.14 toolcache, build==1.4.3, hatchling==1.31.0 isolation, SOURCE_DATE_EPOCH=1786320000, clean origin/main archive plus staged diff; wheel SHA256 `a6c64bc9d504518743e3811e9a1314310f25275db802f367e944799af1f9d81a`; check_release_artifacts PASS |

Disposition: **staged for Codex independent review**.

## Node 24 workflow maintenance: actions/download-artifact v8.0.1 upgrade (2026-08-23; CANDIDATE)

Scope: workflow maintenance on branch `codex/v081-download-artifact-v8` from
`e6a2176` (main, merged PR #41 commit C `cb967d9`):
- GitHub Profile run `32686342501` passed, but emitted the remaining forced-Node24 warning
  because all first-party workflows still pinned `actions/download-artifact` v4.3.0 (`d3f86a106a0bac45b974a628896c90dbdf5c8093`, Node 20).
- Upgraded `actions/download-artifact` from v4.3.0 (`d3f86a106a0bac45b974a628896c90dbdf5c8093`) to official verified immutable
  v8.0.1 (`3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`, Node 24) across all four first-party workflows:
  `.github/workflows/ci.yml`, `.github/workflows/profile-refresh.yml`, `.github/workflows/publish.yml`, and `.github/workflows/staging-preview.yml`.
- Maintained exact workflow contracts without altering names, paths, merge behavior, permissions, inputs, secrets,
  package versions, outputs, or artifact semantics.
- Updated exact-pin tests red-first: `tests/unit/test_profile_refresh_workflow.py` (`DOWNLOAD_ARTIFACT_PIN`) and
  `tests/unit/test_staging_preview.py` (`test_workflow_uses_only_the_pinned_action_shas`) failed against baseline, green after pin updates.
- No changes made to `README.md`, `README.zh-TW.md`, schema, version, renderers, or candidate manifest;
  the unpublished `0.8.2` development candidate wheel digest `a6c64bc9d504518743e3811e9a1314310f25275db802f367e944799af1f9d81a` remains unchanged.
- Post-merge Profile and public-caller repin remains outstanding: the live Profile caller currently pins pre-D commit `9c246d9`, so the remaining Node 20 deprecation warning disappears only after this change is merged and the Profile caller is repinned to the resulting immutable workflow commit.

| Check | Result |
|---|---|
| Red-first contract tests & regressions | 2 tests proven failing red against baseline, green after implementation |
| Focused test suite (workflow, parity, staging, release contract, scheduler CLI, launcher, recruiter card) | 171 passed, 16 skipped (Windows Python 3.14) |
| Parity check | `python scripts/check_readme_parity.py` -> PASS |
| Ruff & diff checks | `python -m ruff check src tests scripts` clean; `git diff --check` clean |
| Candidate manifest parity | `promotion-candidate.json` digest `a6c64bc9...` untouched; `test_release_workflow_contract.py` PASS |

Disposition: **staged for Codex independent review** (post-merge Profile and public-caller repin to the resulting immutable workflow commit remains outstanding).

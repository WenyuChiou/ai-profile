# Current Gate Implementation Review

Review date: 2026-07-14  
Reviewer posture: independent Principal Software Engineer  
Reviewed Gate range: `49fdcbb79268e4bc161825abdda7dc499fc95871..5d57016802269f2cbea13023657b8f89b50e453f`

## Scope and method

This review verifies the completed Gate 2 conformance work against the
repository's amended architecture, ACE schema, MVP boundary, ADRs, Gate 2
review/disposition, privacy model, roadmap, and OSS guidance. It is an
implementation-conformance review, not a redesign.

Evidence used:

- full static review of the 4,467-line Gate diff;
- direct inspection of current source, tests, design documents, and project
  guidance;
- two independent static passes for architecture, security, performance,
  code quality, requirements compliance, and bugs;
- fresh execution of the full test suite and linter;
- focused runtime probes for repository-UID collisions, credential handling,
  UID migration, schema validation, merge determinism, and privacy leakage.

Fresh verification results:

```text
python -m pytest tests/ -p no:cacheprovider
212 passed in 25.41s

python -m ruff check src tests
All checks passed!
```

The environment emitted third-party compatibility warnings for Requests and
Pydantic on Python 3.14; they did not fail the repository's suite.

Green tests do not establish Gate readiness. The focused probes below
reproduced multiple load-bearing counterexamples outside the present fixture
set.

## Executive assessment

The implementation follows the intended modular-monolith shape and preserves
the MVP's local Git -> ACE -> SQLite -> aggregate -> privacy projection ->
SVG/JSON flow. The actor-presence rename, evidence-population invariant,
policy-based publication labels, N-ary scanner merge, SHA-free ordinary parse
warnings, renderer isolation intent, OSS license, threat model, roadmap, and
contributor guidance are all substantive improvements.

The current Gate cannot close. Repository identity v2 still permits distinct
repositories to share a UID, which feeds a replace-by-UID storage operation and
a UID-keyed publication policy. A partial v1-to-v2 migration can also bypass an
existing `excluded` clone policy. Separately, the privacy boundary accepts an
arbitrary canonical provider slug and publishes it verbatim, contradicting the
claim that private organization/repository strings are structurally
unrepresentable.

These are not theoretical style concerns. Direct probes reproduced the port
collision, credential retention, policy split, invalid human event acceptance,
non-canonical source ordering, invented canonical/raw model pair, and provider
string leakage into SVG.

## Conformance summary

| Review area | Result | Summary |
|---|---|---|
| Architecture consistency | Fail | Overall layers are sound, but the approved repository-identity design is unsafe, cross-store scan atomicity is absent, renderer dependency enforcement is incomplete, and one dependency edge is undocumented. |
| Schema consistency | Fail | Canonical merge, provenance validation, timestamps, human evidence, and schema versioning do not fully follow the normative contract. |
| Aggregation correctness | Partial | Commit/presence/evidence units are substantially improved; malformed-but-accepted schema values and provider rows can still corrupt or leak through aggregates. |
| Privacy and security | Fail | UID collisions/policy migration and arbitrary provider publication violate load-bearing privacy guarantees. |
| Test coverage | Partial | 212 tests pass, but critical collision, migration, privacy-canary, empty-SHA-256, and contract-version cases are absent. |
| Code quality | Partial | Code is readable and lint-clean; unsafe duplicate APIs, incomplete validators, stale comments, and mixed-generation writes remain. |
| Unnecessary complexity | Partial | No large framework excess; the pairwise merge API and duplicated/superseded contract wording add avoidable risk. |
| Duplicated functionality | Pass | No Git AI line-attribution, Git Notes transport, GitHub API client, or generic profile-statistics functionality was reimplemented in this Gate. |
| OSS readiness | Partial | MIT license, contribution guide, roadmap, and threat model now exist; package/release hardening and documentation consistency remain incomplete. |

## Critical findings

### C-01: Remote UID v2 is not injective

**Description**  
`src/aiprofile/gitio.py:219` serializes a non-default port as
`host_<port>`, while the scheme and default port are discarded globally.
Distinct origins can therefore share an identity:

```text
https://example.com:8443/o/r  -> example.com_8443/o/r
https://example.com_8443/o/r  -> example.com_8443/o/r

ssh://git.example:22/o/r      -> git.example/o/r
https://git.example:443/o/r   -> git.example/o/r
```

The second pair is unsafe for arbitrary self-hosted services because SSH and
HTTPS namespaces are not guaranteed to address the same repository. The code
implements ADR-016's approved `host_<port>` and scheme-removal rules; this is a
newly discovered defect in the approved design, not code divergence from it.

**Impact**  
Scanning the second repository can replace the first repository's commits and
events because `repositories.repository_uid` is unique and scans delete and
reinsert by UID. Publication policy is also keyed by UID, so one repository's
policy can govern the other. This is silent data loss, count corruption, and a
privacy-policy boundary failure.

**Recommendation**  
Replace the string concatenation with an injective, versioned encoding of a
structured tuple. Retain scheme/port by default; permit cross-transport alias
convergence only for explicitly documented hosts. Bump the UID algorithm and
add collision-pair fixtures covering literal underscore hosts, non-default
ports, schemes, IPv6, and delimiters.

### C-02: Originless local repositories collide on case-sensitive filesystems

**Description**  
`src/aiprofile/gitio.py:232` lowercases every resolved local path before
hashing. On a case-sensitive filesystem, `/work/Repo` and `/work/repo` are
distinct repositories but receive the same `local:v2` UID. This faithfully
implements ADR-016's approved lowercased-local-path rule; the rule itself is
unsafe on supported case-sensitive platforms.

**Impact**  
The second scan replaces the first repository's stored history and couples
their publication policies. The project declares macOS/Linux compatibility,
so Windows-only case assumptions are not acceptable. This survives the Gate's
claim that UID v2 closes distinct-repository merge paths.

**Recommendation**  
Use filesystem/platform-aware normalization that preserves case whenever
identity is uncertain; a safe split is preferable to a destructive merge.
Bump the UID algorithm and add a POSIX case-distinct fixture.

### C-03: Partial UID migration can weaken the most-restrictive policy

**Description**  
Migration is “rescan each path.” `config.upsert_repository()` updates only the
rescanned path's UID. If two clone entries share an old v1 UID with `full` and
`excluded` policies, rescanning only the `full` clone moves it to v2 while the
`excluded` clone remains on v1. The most-restrictive resolution no longer sees
them as aliases. A direct probe produced:

```text
remote:v2:host/o/r -> full
remote:v1:host/o/r -> excluded
```

The old v1 database row is also retained as an orphan rather than reconciled.

**Impact**  
Previously excluded activity can become publishable during a partial upgrade.
The cache retains stale private repository metadata and reports a phantom
excluded repository. This violates fail-closed policy resolution.

**Recommendation**  
Perform an explicit UID migration before scanning: migrate all config entries
sharing the old UID together, reconcile/delete the old database row in the
same controlled operation, and halt fail-closed if aliases cannot be resolved.
Add conflicting-policy duplicate-clone and seeded-v1 database fixtures.

### C-04: Config and database updates are not one successful scan operation

**Description**  
`scanner.scan_repository()` saves config—including UID and `--full` policy—
before Git enumeration and before the atomic SQLite replacement. Any later Git,
schema, or storage failure leaves config changed while database state remains
old. This is directly reachable through the supported `scan --full` command.

**Impact**  
An unsuccessful scan can elevate publication policy and immediately make
pre-existing cached data publishable, hide old data by changing the UID, or
leave config/database identities inconsistent. This violates fail-closed scan
semantics on a supported user path.

**Recommendation**  
Stage config changes in memory, complete enumeration/validation/storage first,
then persist config with a recoverable commit protocol. At minimum, restore the
prior config on failure and add failure-injection tests at enumeration and
storage boundaries, including `--full` over pre-existing cached data.

## High findings

### H-01: Credential stripping can retain secret fragments in repository UID

**Description**  
`src/aiprofile/gitio.py:184-186` splits URL userinfo at the first `@`. For
`https://user:tok@en@host.example/o/r`, canonicalization produced
`en@host.example/o/r`.

**Impact**  
Credential fragments enter the UID and are persisted in config/SQLite. The
same repository no longer converges with its credential-free URL, and ADR-016's
“credentials never enter identity” guarantee is false.

**Recommendation**  
Parse the authority structurally, reject malformed/multiple-userinfo forms, and
ensure no userinfo substring can enter the canonical tuple. Add adversarial
multiple-`@`, percent-encoded, empty-host, and malformed-authority tests.

### H-02: Arbitrary provider strings cross the structural privacy boundary

**Description**  
`schema.build_event()` accepts any non-null canonical `provider` string.
`privacy.build_viz_stats()` treats every non-null key as canonical, and
`registry.provider_display()` returns an unknown slug verbatim. A focused probe
using `private-org-secret` as the provider produced that exact value in both
`VizStats` and the rendered SVG. The normal trailer adapter does not generate
this state, but malformed cache/library input or a future adapter can.

**Impact**  
The privacy boundary is not structurally safe against malformed internal data:
a private organization/repository-like string can be published verbatim.

**Recommendation**  
Validate canonical provider/tool slugs against the registry at the schema
boundary and independently collapse every unknown/non-registry provider to
`unrecognized` inside the privacy boundary. Add privacy-canary tests that
inject sensitive strings into canonical and raw fields.

### H-03: Duplicate provenance keys make canonical JSON order-dependent

**Description**  
`build_event()` sorts sources only by `(source_type, source_reference)`.
Duplicate keys with different evidence levels retain caller order because the
sort is stable. Reversing the same two sources changed `canonical_json()` in a
direct probe. The event is accepted by schema construction but cannot be stored
because SQLite enforces uniqueness on that key.

**Impact**  
The same evidence multiset has multiple canonical serializations, violating
determinism and creating a schema/storage contract mismatch.

**Recommendation**  
At construction, either reject duplicate provenance keys or reduce them to the
strongest evidence using the same deterministic rule as group merge. Include
evidence in the canonical ordering and add reversed-input tests.

### H-04: SHA-256 rejection is incomplete and leaks paths by default

**Description**  
SHA-256 detection relies on seeing a 64-character commit ID. An empty SHA-256
repository returns no records and is accepted. The default non-empty-repository
error also embeds the full repository path, contradicting the new threat
model's default-diagnostic guarantee.

**Impact**  
Unsupported empty repositories are accepted, and private path components can
enter ordinary captured logs. Cross-store mutation consequences are classified
separately in C-04.

**Recommendation**  
Run `git rev-parse --show-object-format` before any config/database mutation.
Reject unsupported formats with a path-free default error and optional verbose
detail. Test empty and non-empty SHA-256 repositories and assert zero config/DB
mutation on failure.

### H-05: The schema constructor does not enforce its normative contract

**Description**  
Focused probes and static inspection found that `build_event()`:

- accepts a date-only activity timestamp (`2026-07-14`) without a time/offset;
- accepts a `human` event backed by `none`/`unknown` evidence;
- raises `AttributeError` rather than `SchemaValidationError` for invalid
  provenance enum strings;
- does not require `human_reviewed` to be `bool | None`.

**Impact**  
Invalid ACE records cross the advertised validated boundary and can distort
human/evidence/day aggregates or fail later in storage with the wrong error
type.

**Recommendation**  
Validate/coerce provenance enums, require offset-aware datetimes for activity
timestamps, enforce declared evidence plus a declaration source for humans,
and reject non-boolean review values. Add negative contract tests for each rule.

## Medium findings

### M-01: `VizStats` does not validate provider-row numeric fields

**Description**  
`viz._validate()` checks top-level counts but omits
`ProviderRow.attributed_commits`, `actor_presences`, and `active_days`. A probe
constructed a valid `VizStats` containing `attributed_commits=-1` and
`active_days=-2`.

**Impact**  
Negative/non-integer provider metrics can cross the renderer/export contract
despite the “validated aggregates only” guarantee.

**Recommendation**  
Validate every provider-row count as a non-negative integer and add malformed
contract tests.

### M-02: Renderer dependency enforcement is incomplete

**Description**  
The new AST test examines only four hard-coded files and only `Import` and
`ImportFrom`. It omits `aiprofile.schema` from the denylist even though the
architecture forbids that edge, and does not detect `importlib.import_module()`
or `__import__()`.

**Impact**  
A new renderer or lazy import can reach schema/storage/Git while the claimed
architecture gate remains green.

**Recommendation**  
Recursively discover renderer/export modules and enforce the documented import
allowlist, including dynamic import calls where statically resolvable. Exercise
public render/export functions in the runtime isolation probe.

### M-03: Empty AI identity keys bypass the Human-Only contradiction rule

**Description**  
The trailer parser discards empty-valued `AI-Provider:`/`AI-Tool:` lines before
grouping. Both `AI-Provider:` + `AI-Mode: Human-Only` and `AI-Tool:` + that mode
were accepted as clean human declarations with no warning.

**Impact**  
This contradicts ADR-005's key-presence rule and can classify a malformed,
contradictory declaration as human.

**Recommendation**  
Track recognized key presence separately from non-empty value parsing; reject
and warn on Human-Only plus any provider/tool key. Add empty/whitespace fixtures.

### M-04: Remote alias normalization is internally inconsistent

**Description**  
SCP-form origins do not strip query/fragment text while URL-form origins do.
For GitHub, `.GIT` is not stripped before host-specific path case folding, so
`Repo.GIT` and `repo.git` split. These contradict ADR-016's convergence rules.

**Impact**  
Equivalent clones can receive different UIDs, double-count activity, and retain
duplicate policy/config entries. This is a safe-split rather than a destructive
merge, but it still corrupts profile totals.

**Recommendation**  
Apply one component-normalization pipeline to every supported syntax and add
SCP query/fragment parity and mixed-case suffix fixtures.

### M-05: Mandatory privacy and permutation tests are incomplete

**Description**  
The privacy integration test does not sweep the actual repository UID or a
distinctive remote organization value. Merge permutation coverage proves
canonical event output but not scanner-to-storage-to-aggregate invariance. The
empty SHA-256 case and UID migration policy cases are absent.

**Impact**  
The Gate records stronger acceptance coverage than the suite implements,
allowing the reproduced privacy/correctness failures to coexist with 212 green
tests.

**Recommendation**  
Add end-to-end canaries for every upstream field and output channel, aggregate
permutation tests, empty/non-empty object-format tests, and v1/v2 conflicting-
clone migration tests. Assert the counterexamples fail before fixes.

### M-06: Normative guidance still contradicts the implemented Gate contract

**Description**  
Current guidance contains several conflicts:

- `docs/mvp.md` still says default warnings include commit SHA;
- `docs/schema.md` still calls `source_reference` free-form;
- `README.md` and CLI help still describe `--full` as public counting;
- `docs/ROADMAP.md` says conformance is in progress while progress/disposition
  say complete;
- ADR-008 says the first importer needs no re-ranking debate while making
  precedence re-evaluation a blocker;
- ADR-009 still describes `repository_anonymous` as accepted while config now
  rejects it;
- the archived run log retains current-looking obsolete metric/license status.

**Impact**  
Contributors following authoritative documents can reintroduce privacy wording,
locator, evidence, or policy behavior that the Gate intended to remove.

**Recommendation**  
Perform a contract-term sweep across README, architecture, schema, MVP, ADRs,
roadmap, CLI help, and historical records. Mark immutable historical statements
as historical rather than silently presenting them as current.

### M-07: Asset publication is not bundle-atomic

**Description**  
`export.write_outputs()` overwrites two SVGs and JSON sequentially. A failure on
the second or third write leaves mixed generations in `dist/`.

**Impact**  
A subsequent README publish can combine statistics from different scans even
though render returned an error.

**Recommendation**  
Write every asset to same-directory temporary files, close/flush all writes,
then replace targets only after the complete bundle succeeds. Add failure-
injection coverage.

### M-08: Implementation contains an undocumented dependency edge

**Description**  
`privacy.py` imports `registry.provider_display`, while the finalized module map
lists `privacy -> aggregate, viz, config, errors` only.

**Impact**  
The redaction boundary depends on normalization/catalog internals without an
approved architectural edge. This contributed to H-02 because registry fallback
behavior became publication behavior.

**Recommendation**  
Make canonical display resolution an explicit sanitized input/contract, or amend
the architecture with a privacy-safe registry interface and enforce it in the
dependency test.

### M-09: The verbose aggregate contract omits skipped-author counts

**Description**  
The MVP says `aggregate -v` reports skipped-author counts, unrecognized raw
providers, and excluded repositories. Only the latter two are available after
the scan; skipped-author counts are not persisted.

**Impact**  
The CLI does not conform to its documented MVP, and users cannot diagnose stale
identity configuration from later aggregate runs as promised.

**Recommendation**  
Either persist a local-only last-scan diagnostic outside `VizStats` or amend the
MVP to make skipped-author counts scan-only.

### M-10: The approved per-scalar merge rule can invent canonical/raw pairs

**Description**  
`merge_event_group()` follows ADR-008 by resolving each scalar independently,
including `provider`/`provider_raw`, `model`/`model_raw`, and `tool`/`tool_raw`.
Equal-ranked leaves `(model="alpha", model_raw="alpha")` and
`(model="beta", model_raw="Beta")` merged to
`(model="alpha", model_raw="Beta")`, a pair no source asserted. This follows
the approved per-scalar design; it is a newly exposed provenance-quality flaw,
not scanner nonconformance.

**Impact**  
Canonical data can associate a raw value with the wrong normalized value. The
current renderer does not expose model data, limiting v0.1 reachability, but
future imports/exports could misstate provenance.

**Recommendation**  
Revise ADR-008 so canonical/raw pairs resolve from one winning leaf, then add
pair-integrity and permutation tests before any consumer exposes these fields.

### M-11: Pre-release visualization contract changes lack a version decision

**Description**  
The Gate renames totals, provider, evidence, and privacy fields in
`profile.json`, while `ACE_SCHEMA_VERSION` remains `0.1.0`. ADR-012 says the
visualization contract changes only with a schema-version bump. No tagged public
release exists, so external compatibility breakage is not established, but the
repository's own versioning rule is unresolved before release.

**Impact**  
Generated old/new fixtures or early consumers cannot distinguish incompatible
0.1.0 documents, and the project risks publishing its first release with an
ambiguous contract history.

**Recommendation**  
Before release, either bump the contract/schema version and document the
pre-release migration or record an explicit ADR exception. Consider a separate
visualization-contract version if ACE and public JSON evolve independently.

### M-12: The exported pairwise merge API documents unsafe accumulation

**Description**  
`merge_events()` remains exported even though its docstring says incremental
folding of three or more productions is not associative. The scanner correctly
uses `merge_event_group()`, so the supported CLI path is safe, but a newly added
test demonstrates the forbidden fold with a benign fixture.

**Impact**  
Library users and maintainers can copy an unsafe pattern and reintroduce the
order-dependent merge bug outside the scanner.

**Recommendation**  
Export the N-ary API as the supported accumulation interface. Remove/private the
pairwise helper or reject merged inputs, and rewrite the misleading test around
the supported N-ary operation.

## Low findings

### L-01: Gate terminology remains stale in code comments and tests

**Description**  
Examples include `evidence_records` documented as “level -> events,” CLI output
that says “events stored,” and tests/comments that describe the superseded
first-write merge semantics or demonstrate forbidden pairwise folding.

**Impact**  
The code remains functional, but future maintainers can mix ACE records, actor
presences, and true participation events—the exact ambiguity the Gate intended
to remove.

**Recommendation**  
Complete a terminology sweep and make tests demonstrate only supported APIs.

### L-02: OSS release readiness is correctly incomplete but should not be
reported as shipped

**Description**  
LICENSE, CONTRIBUTING, ROADMAP, and PRIVACY now exist. The roadmap still lists
sample output, clean-install/package smoke, permissions/symlink/worktree
hardening, canary output sweeps, and packaged-release/upgrade guidance as open.

**Impact**  
The repository is substantially more understandable and legally reusable, but
it is not yet a complete OSS release artifact by its own exit criteria.

**Recommendation**  
Keep these items explicit in the next Gate and avoid release-ready language
until they are independently verified.

## Positive verification

- The runtime remains a small, readable modular monolith with zero declared
  runtime dependencies.
- Renderers consume `VizStats`; no renderer currently scans Git or SQLite or
  recalculates attribution.
- Unique commits, AI actor presences, provider-attributed commits, active author
  dates, and all-ACE-record evidence totals are separately represented.
- Unknown remains separate from human in the normal scanner path; no source-
  style inference exists.
- Publication labels in `VizStats`, JSON, CLI output, and SVG are policy-based
  rather than visibility claims, apart from the stale onboarding/help wording
  noted above.
- The scanner uses the N-ary merge API for actual trailer productions.
- SQLite queries are parameterized, Git subprocess invocation does not use a
  shell, and SVG text is escaped.
- Existing Git AI/Git Notes/GitHub-profile functionality is referenced or
  deferred rather than duplicated.
- The full suite and linter pass freshly, with the exact results stated above.

## Gate conclusion

The current Gate contains multiple silent data-loss and privacy-policy failure
paths in the mechanism introduced to close those exact risks. It also has a
reproducible public-output privacy leak and incompatible JSON contract changes
without versioning. These require design-conformant implementation fixes and
new failing-before-fix regression tests before the Gate can be accepted.

**NOT READY**

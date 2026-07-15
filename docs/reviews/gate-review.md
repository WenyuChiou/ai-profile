# Current Gate implementation review

Date: 2026-07-15
Review range: `4fdd49016431200b7390c144f9023cc8e700521b..78e2e05519bc0de784790121a421f5fb0b4144d1`
Reviewer posture: independent implementation verification; no design or implementation changes made.

## Executive summary

The Gate makes several correct, tested improvements: UID v4 is honestly versioned, documented GitHub endpoints are separated from nonstandard scheme/port combinations, leading-zero ports normalize, valid multi-source leaves are accepted, nested reductions produced through the sanctioned API are rejected, rollback continues after a restore failure, user-owned `.bak` files survive, and cleanup failure no longer reports a successful publication as failed.

The Gate nevertheless cannot close as submitted. Its principal correctness fix depends on a caller-controlled `merged` boolean that is absent from both the normative schema and persisted/canonical event representations. An adversarial probe outside the sanctioned constructor path reset that public dataclass field and reproduced the previously known nested-versus-flat divergence (`zeta` versus `alpha`), demonstrating that the claimed boundary is conventional rather than representational. The export disposition also overstates isolation: PID-derived filenames are process-owned rather than attempt-owned, and the unlocked three-target publication sequence cannot guarantee a whole generation under concurrent writers. Additional reproduced failures exist for oversized numeric ports and first-render rollback when retraction itself fails.

No evidence was found that this Gate introduces Git AI/Git Notes/GitHub API/profile-statistics duplication, changes aggregation units, weakens the `unknown` versus `human` distinction, permits renderers to read Git or SQLite, or leaks repository identity through validated `VizStats`. Those areas remain consistent with the approved MVP.

## Review basis and verification performed

- Read the repository guidance and current design set, including the architecture, ACE schema, MVP, privacy threat model, roadmap/progress, landscape/non-duplication analysis, all ADRs, prior Gate reports/dispositions, README, contributing guide, packaging configuration, implementation, and tests.
- Inspected the complete pinned diff and traced each Gate-4 disposition to code, documentation, and regression coverage.
- Ran `pytest -o addopts= -q`: `256 passed, 1 skipped in 22.52s`.
- Ran `ruff check .`: `All checks passed!`.
- Re-ran focused adversarial probes for merge purity, oversized ports, and export rollback failure. The merge probe reproduced grouping-dependent output after `dataclasses.replace(result, merged=False)`; the port probe raised an uncaught `ValueError`; the rollback probe left `summary-light.svg` installed while the raised error reported only the later install failure.
- Reviewed renderer/import boundaries, aggregation units, privacy canaries, deterministic SVG/JSON coverage, rewritten-history coverage, malformed trailers, unknown commits, and fixture repositories.

## Findings

### M-01 — Medium — The merge-purity boundary is conventional, non-durable, and absent from the normative schema

**Description:** `AceEvent.merged` is the sole guard that distinguishes a leaf from a prior N-ary reduction (`src/aiprofile/schema/event.py:68-82, 327, 424`). It is a caller-controlled field on the publicly exported dataclass, is omitted by `to_dict()`/`canonical_json()`, and is not stored by the SQLite event insert or schema (`src/aiprofile/storage/store.py:143-168`; `src/aiprofile/storage/migrations.py:38-57`). `docs/schema.md`, despite declaring itself the source of truth, does not define this merge-controlling envelope state, its default, its equality semantics, or its lifecycle. The code comment explicitly declares raw reconstruction and `dataclasses.replace` out of contract, and no supported v0.1 CLI path rehydrates a stored event and merges it again. However, a direct adversarial probe outside that sanctioned path reset the field and reproduced the prior counterexample: nested selected `zeta`, while the flat reduction selected `alpha`.

**Impact:** The current scanner's sanctioned in-memory path is protected, but the Gate's unconditional closure claim is stronger than its event contract. A contributor implementing a schema round-trip, persistence reader, or future adapter has no normative way to preserve the marker and can reopen grouping-dependent attribution.

**Recommendation:** Narrow the closure claim to the sanctioned in-memory scanner path or make derivation state part of an enforceable, documented representation before future round-trip/import boundaries use this API. Add a regression for whichever public boundary is approved.

### M-02 — Medium — Export artifacts are not attempt-owned and concurrent whole-generation publication is not guaranteed

**Description:** `write_outputs()` documents `<target>.<pid>.tmp/.bak` as attempt-owned and states that each concurrent render publishes a whole generation (`src/aiprofile/export.py:35-47`). A PID identifies a process, not a call: same-process concurrent/re-entrant calls share paths, and PID reuse can collide with crash debris. More fundamentally, three public targets are moved/replaced independently with no output-directory serialization or generation-level atomic switch (`src/aiprofile/export.py:58-104`). A writer's rollback can restore over another writer's newly published target, yielding SVG and JSON from different generations.

**Impact:** The M-6 disposition and progress record overclaim closure. Concurrent library calls can clobber transaction files, and concurrent CLI processes can publish a mixed generation or undo another successful writer.

**Recommendation:** Use a true per-invocation transaction identity and either serialize publication per output directory or narrow the contract to explicitly reject concurrent writers. Add deterministic interleaving tests before claiming isolation or whole-generation publication.

### L-01 — Low — Failed first-render retraction is absent from the raised error

**Description:** During rollback, failure to unlink a first-ever installed target is logged (`src/aiprofile/export.py:74-86`) but is not added to `unrestored`, so the raised `RenderError` reports only the original install failure. The direct probe started with no outputs, failed installation of `summary-dark.svg`, and then failed retraction of the already installed `summary-light.svg`; the asset remained. The default warning did name `summary-light.svg`, but a programmatic caller inspecting only the exception cannot discover the partial publication.

**Impact:** This requires two filesystem failures and is visible in normal logs, so operational likelihood is low. The exception contract is still incomplete, and suppressed/redirected logging can hide the surviving partial asset.

**Recommendation:** Track and report failed retractions separately from failed restores, state the resulting partial-publication condition precisely, and add a regression that injects failure into first-install rollback.

### M-03 — Medium — Oversized numeric ports escape the UID canonicalization error contract

**Description:** The URL parser accepts an unbounded `\d+` port and `_canonical_identity()` normalizes it with `str(int(port))` (`src/aiprofile/gitio.py:231, 263-267`). A direct probe using a 5,000-digit port raised Python's integer-string conversion `ValueError` rather than returning a canonical identity/`None` or a project error.

**Impact:** A repository with a malformed or adversarial origin can abort scanning outside the normal `AiProfileError` handling path. The full 42-cell scheme/port test and leading-zero tests do not cover invalid-size ports.

**Recommendation:** Bound and validate the decimal port token before conversion, translate rejection into the established failure contract, and add oversized-port coverage.

### L-02 — Low — The claimed parameterized 42-case UID grid is one looped test

**Description:** The disposition and progress record call the scheme-by-port grid parameterized (`docs/reviews/gate-disposition.md:90`; `docs/progress.md:73, 112-113`), but `tests/unit/test_gitio_uid.py:392-412` is one test with nested loops. It evaluates all 42 cells, but the first failure aborts the rest and pytest cannot report cell-specific cases.

**Impact:** Functional coverage exists, so correctness risk is low; however, the evidence record is inaccurate and failures are less diagnosable than claimed.

**Recommendation:** Either use actual parameter cases with meaningful IDs or correct the documentation to call it a looped exhaustive grid.

### L-03 — Low — Internal derivation metadata changes dataclass equality while canonical payloads remain identical

**Description:** `merged` is excluded from canonical serialization but remains a normal dataclass comparison/hash field. A leaf and `merge_event_group([leaf, leaf])` can have byte-identical canonical JSON while comparing unequal and producing different hashes solely because the latter has `merged=True`.

**Impact:** Sets, caches, tests, and future deduplication code can disagree with canonical event equality, increasing maintenance risk around an already subtle boundary.

**Recommendation:** Specify equality semantics for envelope metadata and align dataclass comparison/hash behavior with the normative event-value contract.

### L-04 — Low — Export tests duplicate the same `VizStats` fixture construction

**Description:** `tests/unit/test_export_atomic.py` adds `_zero_stats()` but two earlier tests still construct the same full zero-valued `VizStats` inline (`lines 14-46, 67-100, 127-146`).

**Impact:** Future visualization-contract changes require synchronized edits at three sites and make failure-injection tests noisier than necessary.

**Recommendation:** Reuse the existing helper throughout the module when the Gate findings are corrected.

## Verified areas without findings

### Architecture and MVP consistency

- Collection, schema, storage, aggregation, privacy, visualization, rendering, and export boundaries remain recognizable and dependency direction is inward toward validated contracts.
- Renderers consume `VizStats` and pre-rendered strings only; static import coverage prevents Git/SQLite/config access from rendering/export layers.
- The diff does not add GitHub networking, Git Notes ingestion/writing, Git AI line attribution, hosted services, extra cards, period filtering, or other post-v0.1 scope.

### Aggregation correctness

- Unique commits, AI-attributed commits, actor presences, provider-attributed commits, active author-local days, and evidence records remain separately named and computed.
- One multi-AI commit can contribute one unique commit and multiple actor presences without conflating the measures; provider commit rows use per-provider distinct-commit sets.
- Evidence counts remain record-based and validated against their own population.
- Rewritten-history replacement and duplicate-scan idempotence tests pass.

### Privacy and security

- `unknown` remains distinct from explicitly declared `human`; there is no source-style inference.
- `VizStats` cannot represent repository UID/name/path, organization, prompt, commit SHA/message, email, raw provider/trailer value, or sub-date timestamp.
- Excluded repositories fail closed, aggregate-only outputs retain counts without identity, and unrecognized raw provider values collapse before the public boundary.
- SVG security allowlists, deterministic snapshots, and byte-level leak canaries pass. v0.1 still contains no GitHub authentication or network code.

### Non-duplication and OSS readiness

- The implementation consumes Git trailers and deliberately defers Git AI/Git Notes interoperability; it does not reproduce line-level attribution, GitHub API clients, generic profile statistics, contribution graphs, or third-party README-stat generators.
- README, contributing guidance, privacy threat model, ADRs, and roadmap provide a coherent contributor entry point.
- The roadmap honestly leaves packaged-install smoke testing, sample output, permissions/symlink hardening, broader diagnostic canaries, and release packaging open; those are release-readiness items rather than unacknowledged Gate completions.

## Severity summary

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 3 |
| Low | 4 |

## Final recommendation

READY AFTER MINOR FIXES

# Gate implementation verification review

Date: 2026-07-14

Reviewer role: independent Principal Software Engineer

Reviewed range: `5d57016..de4a78a`
Review scope: verify the 23 claims in `docs/reviews/gate-disposition.md`, then independently probe UID v3 and merge purity. This is a verification review, not a redesign.

## Executive summary

The Gate materially improves architecture conformance, schema validation, privacy defense in depth, scan failure ordering, and regression coverage. Twenty of the 23 disposition items are supported by the current implementation and tests. Two claims are contradicted by reproducible failure injection, and one is only partially resolved.

The blocking defect is in UID v3. ADR-016 limits GitHub transport convergence to documented transports on standard ports, but the implementation discards every scheme and every port whenever the host is `github.com`. A 42-case probe covering six schemes and seven port variants collapsed all inputs to one UID. This reintroduces the exact class of distinct-repository collision that UID v3 was intended to eliminate; because repository UID is also the storage replacement and publication-policy key, the impact includes count corruption, cache replacement, and policy aliasing.

Two non-blocking-but-real defects also remain. The three-file output operation is not bundle-atomic when a target replacement fails after an earlier replacement succeeded. In addition, the N-ary merge is deterministic and input-pure for leaf events, but its public type signature permits a merged result to be supplied as a new input; that nested composition can produce a different canonical event than a single N-ary reduction over the same leaves.

Fresh repository verification completed successfully: 241 tests passed, one documented POSIX case-sensitivity test was skipped on Windows, and Ruff reported no violations. Green tests do not invalidate the three counterexamples because the relevant boundaries are not covered by the committed tests.

## Review method and evidence

- Read the repository guidance and current normative design: architecture, schema, MVP, privacy model, roadmap, progress ledger, relevant ADRs, contribution guidance, and the 23-item disposition.
- Inspected the complete pinned diff and the current implementation at `de4a78a`.
- Mapped every disposition item to its production change, regression test, and governing design statement.
- Ran the full test and lint gates.
- Ran independent adversarial probes rather than trusting the disposition or prior reviewer report.

Fresh commands and results:

```text
python -m pytest tests -p no:cacheprovider
241 passed, 1 skipped in 26.37s

python -m ruff check src tests
All checks passed!
```

The skip is `test_c02_case_distinct_local_repos_split_on_posix`, which is intentionally unavailable on Windows. Static inspection confirms that the implementation removed unconditional lowercasing from the local UID hash input, but this environment did not execute the POSIX filesystem behavior.

Independent probes:

- UID targeted grid: six schemes (`https`, `http`, `ssh`, `git`, `ftp`, custom) × seven ports (absent, 22, 80, 443, 9418, 444, 2222). All 42 `github.com/Owner/Repo.git` inputs canonicalized to `github.com/owner/repo`.
- Merge leaf purity: 300 randomly generated leaf sets, 30 shuffled orders per set (9,000 reductions). Canonical output was permutation-invariant and input objects remained unchanged.
- Merge composition: a three-leaf nested reduction produced a different `model`, `contribution_mode`, and canonical JSON from the direct N-ary reduction by trial 11.
- Output failure injection: forcing the second `os.replace` to fail left `summary-light.svg` new while `summary-dark.svg` and `profile.json` remained old.

## Disposition verification matrix

| ID | Status | Verification result |
|---|---|---|
| C-01 | Contradicted | Structured encoding fixes the v2 underscore/port and arbitrary-host scheme collisions, but the GitHub exception ignores all schemes and ports. UID v3 is therefore not injective under its own ADR semantics. |
| C-02 | Verified with platform limitation | Local hashing uses the case-preserved resolved path. The POSIX execution test is skipped on Windows; code inspection supports the claim. |
| C-03 | Verified | Alias-group entries are re-derived together, unresolved siblings halt before persistence, and old UID rows are purged in the scan transaction. Focused regression tests cover migration, exclusion, purge, and unresolved siblings. |
| C-04 | Verified | Enumeration and storage failures leave the on-disk config unchanged; config persistence occurs after the database transaction. The database-first/config-last failure direction remains fail-closed because an unconfigured UID is excluded. |
| H-01 | Verified | URL and scp userinfo are stripped with `rpartition("@")`; multi-`@` tests and direct probes remove the complete credential prefix. |
| H-02 | Verified | Provider/tool canonical vocabularies are schema-owned; `build_event` rejects arbitrary canonical values and `build_viz_stats` independently collapses non-canonical provider keys to `unrecognized`. |
| H-03 | Verified | Duplicate provenance keys deduplicate to the highest evidence level before canonical sorting; reversed input produces identical canonical JSON. |
| H-04 | Verified | Object-format preflight covers empty SHA-256 repositories, runs before scan mutation, and emits a path-free default error. |
| H-05 | Verified | Offset-aware timestamps, human evidence, source enum coercion, and boolean/null `human_reviewed` constraints are implemented and negatively tested. |
| M-01 | Verified | Provider-row counts are included in non-negative integer validation. |
| M-02 | Verified | Render/export modules are recursively discovered for AST checks; forbidden imports and dynamic-import calls are checked. Runtime isolation remains a separate module-graph test. |
| M-03 | Verified | Trailer key presence is tracked independently of value presence, so empty provider/tool keys still contradict `Human-Only`. |
| M-04 | Verified for the stated cases | Query/fragment handling is shared across URL/scp forms and GitHub path folding precedes `.git` stripping. The broader GitHub scheme/port collision is reported under C-01. |
| M-05 | Verified | Dist canaries now include UID, salt, and remote organization values; scanner-to-publication trailer-order invariance is tested. |
| M-06 | Verified | The cited MVP/schema/README/CLI/ADR/run-log terminology conflicts were corrected in the reviewed range. |
| M-07 | Contradicted | Assets are built in temporary files first, but sequential target replacement is not transactionally atomic. A replacement-stage failure leaves a mixed generation. |
| M-08 | Verified | The privacy-to-registry dependency is documented and limited to display-name resolution after canonical-slug collapse. |
| M-09 | Verified as a documented decision | MVP wording now places skipped-author counts in scan diagnostics and keeps `aggregate -v` limited to persisted local detail. No new cache surface was added. |
| M-10 | Verified for leaf N-ary reduction | Canonical/raw pairs are selected atomically from one winning leaf. Direct leaf-set permutation probing found no mixed pairs or order dependence. |
| M-11 | Verified as a documented decision | ADR-012 records the pre-first-tag exception and the release roadmap retains the contract-freeze requirement. |
| M-12 | Verified | The named pairwise API was removed, the group API is the only exported merge, and the scanner performs one N-ary call. The separately reported nested-composition defect is a newly discovered boundary weakness rather than a contradiction of this disposition. |
| L-01 | Partially verified | The terminology changes consistently use “records” and the old pairwise API is gone, but `test_merge_is_permutation_invariant` still demonstrates incremental accumulation by feeding a `merge_event_group` result back into the same API. The claimed removal of forbidden-fold demonstrations is incomplete. |
| L-02 | Verified | Roadmap and progress documents continue to list the remaining OSS-release work and do not claim release readiness. |

## Architecture and MVP assessment

Architecture remains a disciplined modular monolith. The dependency direction is consistent with the approved design: Git access is isolated in collection, schema remains standard-library-only, storage does not import policy or Git, and render/export consume validated visualization data rather than events or SQLite. The Gate does not introduce unnecessary framework abstractions or duplicate Git/GitHub statistics functionality.

Schema and aggregation behavior are substantially aligned with the approved contracts. Unknown remains distinct from human; unique commits, AI actor presences, provider-attributed commits, active days, and evidence records retain separate units. No new double-counting path was found. Pair-atomic leaf merging closes the prior canonical/raw fabrication defect.

Privacy defense in depth improved: arbitrary provider keys are collapsed at the publication boundary, path-free SHA-256 diagnostics are tested, and additional repository/org/salt canaries are swept from public assets. The UID collision is nevertheless privacy-relevant because UID is the publication-policy join key. Two distinct configured repositories can be forced into one policy/storage identity even though their content never appears directly in `VizStats`.

The MVP boundary remains appropriately narrow. No GitHub API, Git Notes importer, generic profile-statistics generator, hosted service, or source-style attribution logic was added. OSS readiness is still incomplete exactly where the roadmap says it is: clean-install/sample output, additional hardening, packaged release, and upgrade guidance remain open.

## Findings

### Critical — UID v3 collapses non-standard GitHub schemes and ports

**Description:** `src/aiprofile/gitio.py:253-263` switches solely on `host in _ALIAS_CONVERGENT_HOSTS` and then returns `host/path`, discarding both `scheme` and `port`. ADR-016 limits convergence to GitHub's documented SSH/HTTPS/Git endpoints on standard ports. The implementation also accepts `ftp`, arbitrary custom schemes, and every explicit non-standard port as the same identity. Examples that collide are `https://github.com/o/r`, `https://github.com:444/o/r`, `ssh://github.com:2222/o/r`, and `ftp://github.com/o/r`.

**Impact:** Distinct repository origins can share a UID. Since UID keys atomic scan replacement and most-restrictive publication policy, this can replace cached repository data, corrupt aggregate counts, and apply one repository's publication policy to another. It directly falsifies the Gate's “UID v3 is injective” completion claim.

**Recommendation:** Before advancing the Gate, constrain the alias branch to an explicit set of allowed `(scheme, effective_port)` combinations and make all other combinations retain structured scheme/port identity or fail safely. Add collision tests for non-standard GitHub ports and unsupported schemes, not only arbitrary-host transport splits.

### Medium — Three-file publication is not bundle-atomic

**Description:** `src/aiprofile/export.py:33-38` completes all temporary writes and then performs three sequential `os.replace` calls. There is no rollback if replacement two or three fails. The existing regression in `tests/unit/test_export_atomic.py` injects failure during JSON serialization, before any target replacement; it does not exercise the replacement stage. Injecting failure on the second replacement produced a mixed output generation.

**Impact:** A disk, permission, antivirus, or filesystem error can leave README assets internally inconsistent: one SVG may display new counts while the other SVG and JSON expose old counts. This is a correctness and publication-integrity failure, though it does not itself expose raw private fields.

**Recommendation:** Correct the Gate claim and add replacement-stage failure tests. Require the output path to preserve the documented no-mixed-generation behavior before describing independent file replacements as bundle-atomic.

### Medium — The exported N-ary merge remains unsafe under composition

**Description:** `merge_event_group` correctly reduces a complete set of leaf events, but `src/aiprofile/schema/event.py:290-396` cannot distinguish a leaf from a previously merged event. Feeding `merge_event_group([merge_event_group([a, b]), c])` can re-rank values against pooled provenance and produce different canonical data than `merge_event_group([a, b, c])`. The direct scanner path is correct, and the independent leaf-only permutation probe passed; this is a newly discovered exported-API boundary weakness.

**Impact:** Current scanner aggregation is not affected. A future adapter, importer, reconciliation path, or external library caller can naturally accumulate through the only exported merge function and silently obtain order/grouping-dependent model, mode, or review fields. This recreates the semantic hazard M-12 intended to remove.

**Recommendation:** Enforce the documented leaf-only boundary at the exported merge API and add a regression asserting that nested use is rejected for adversarial three-leaf inputs.

## Strengths verified

- Config-last scanning closes the prior reachable publication-policy elevation path.
- Alias-group migration is fail-closed and purges superseded cache identities transactionally.
- Schema-owned provider/tool vocabulary plus an independent privacy collapse is strong defense in depth.
- Direct leaf N-ary merging is deterministic, pair-atomic, and input-pure under the tested adversarial set.
- Aggregation units remain explicitly separated and no count-mixing regression was found.
- Render/export dependency isolation and public-output canary coverage are materially stronger.
- The change reuses Git, SQLite, and existing registry/rendering boundaries rather than duplicating Git AI, Git Notes, GitHub API, or generic README-statistics systems.
- The roadmap honestly retains unfinished OSS-release work.

## Required changes before the next Gate

1. Close the GitHub non-standard scheme/port UID collision and add adversarial tests.
2. Resolve or accurately downgrade the bundle-atomic publication guarantee, with replacement-stage failure coverage.
3. Enforce the documented leaf-only merge boundary so nested grouping cannot change canonical output.
4. Re-run the full suite, UID collision grid, nested-merge probe, and output replacement failure probe after the fixes.

## Final recommendation

**NOT READY**

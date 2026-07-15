# Current Gate implementation review

Date: 2026-07-14

Reviewer role: independent Principal Software Engineer

Reviewed range: `de4a78a..4fdd490`

Gate intent: close the three counterexamples from the preceding verification review: UID v3 endpoint collisions, mixed-generation output publication, and unsafe nested merge composition.

## Executive summary

This Gate is directionally correct but does not close the merge counterexample. It defines a leaf as an event with exactly one deduplicated provenance source. A merged result can still have one source when its inputs share a provenance key, so nested composition remains accepted and can produce different canonical data from a flat reduction. The same heuristic rejects legitimate unmerged events containing multiple sources, despite the approved schema permitting them.

The GitHub endpoint change follows amended ADR-016 by restricting transport convergence to the documented scheme/effective-port set while retaining the ADR's alias-host path-folding rule. This review does not challenge that approved equivalence rule. Two conformance gaps remain: the algorithm changed without the required version bump, and numerically equivalent ports with leading zeroes split identities.

The export rollback handles the originally demonstrated replacement failure when every rollback operation succeeds. It does not provide the absolute no-mixed-generation guarantee still claimed by its docstring and progress documents: a failure during rollback stops restoration and can leave new, missing, and backup assets together. Fixed backup names introduce an additional clobber/concurrency risk.

The broader architecture remains aligned with the approved MVP. No dependency-direction regression, aggregation-unit mixing, public-field leakage through `VizStats`, unnecessary external duplication, or performance regression was found. The implementation remains a narrow local-first trailer-to-SQLite-to-aggregate-to-static-assets vertical slice.

## Verification evidence

The review read the current architecture, schema, MVP, privacy model, roadmap, progress ledger, disposition record, ADR-016, contribution guidance, the complete pinned diff, and the affected production/tests. Static review used independent architecture, security, performance, code-quality, requirements, and bug lenses. Findings below were retained only after direct code inspection or runtime reproduction.

Fresh repository verification:

```text
python -m pytest tests -p no:cacheprovider
245 passed, 1 skipped in 22.99s

python -m ruff check src tests
All checks passed!
```

The skip is the documented POSIX case-sensitive filesystem fixture, unavailable on Windows. The test process also emitted environment warnings about the locally installed Requests dependency combination and Pydantic v1 compatibility on Python 3.14; neither warning came from this project or failed the suite.

Independent counterexamples:

- Merging a declared `git_trailer/ai-provider` leaf with no model and an imported leaf on the same key carrying model `zeta` deduplicates the result to one source. That result passes the new leaf guard; nested reduction against a declared co-author leaf carrying `alpha` selected `zeta`, while the flat three-leaf reduction selected `alpha`.
- A schema-valid event constructed with two provenance sources is rejected when passed to a multi-event merge.
- Injecting failure during replacement and again during the first restore left the light SVG new, the dark SVG missing, the JSON old, and two `.bak` files.
- A successful render destroyed a pre-existing `summary-light.svg.bak` sentinel.
- Injecting backup-cleanup failure raised `RenderError` after all three new outputs were already live.

## Findings summary

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 1 |
| Medium | 5 |
| Low | 2 |

## Findings

### High — The leaf-only merge guard is bypassable

**Description:** `src/aiprofile/schema/event.py:305-332` infers leaf status from `len(event.sources) == 1`. Source union deduplicates by `(source_type, source_reference)`, so two leaves sharing one provenance key can merge into a non-leaf event that still has exactly one source. That result is accepted by a later merge. A reproduced three-leaf case produced different canonical models for nested and flat reductions.

**Impact:** Library callers and future adapters can still obtain grouping-dependent model, mode, or review values. The current scanner uses a flat reduction and is not directly affected, but the exported schema API does not enforce the completion claim made by this Gate.

**Recommendation:** Enforce leaf status independently of the cardinality of the deduplicated semantic provenance set. Add a regression using same-key, different-evidence leaves that proves nested input is rejected.

### Medium — Valid multi-source productions are rejected

**Description:** The same source-count guard rejects an independently constructed event containing two valid provenance sources. `build_event` accepts and validates one-or-more sources, and `docs/schema.md` retains source union for future notes, Git AI, and manual imports; the approved contract does not define a leaf as exactly one source.

**Impact:** The implementation narrows the schema/API without an approved contract change. Future import and reconciliation work can fail on valid data, and current library callers receive `SchemaValidationError` for schema-conformant inputs.

**Recommendation:** Preserve the approved multi-source event contract and make merge-state validation independent of source count. Add a valid multi-source production regression.

### Medium — Rollback failure still leaves mixed or missing public assets

**Description:** `src/aiprofile/export.py:51-67` restores backups sequentially and stops on the first rollback `OSError`. The public docstring still says a mid-bundle failure leaves the previous generation fully intact, while the implementation comment acknowledges that a mix can remain. The added tests make the initial replacement fail but allow every rollback operation to succeed.

**Impact:** A persistent lock, permission error, antivirus race, or filesystem fault can leave a new SVG, a missing SVG, an old JSON file, and backup files together. Static hosting or a README can then expose an inconsistent generation despite the command reporting failure.

**Recommendation:** Align the public contract with the behavior actually guaranteed and add failure injection within rollback itself. The Gate must not claim no mixed generations unless restoration failure is handled and verified.

### Medium — UID behavior changed without changing its algorithm version

**Description:** The Gate changes canonical UID output for existing GitHub origin strings while leaving `UID_ALGORITHM = "v3"`. Both the code comment and `docs/schema.md:213-214` state that any canonicalization rule change bumps the algorithm version. The normative schema also still describes every alias-host origin as `host/case-folded-path`, omitting the new endpoint-qualified structured fallback.

**Impact:** The same `remote:v3:` prefix now names different algorithms in `de4a78a` and `4fdd490`. Persisted configuration can migrate only opportunistically on rescan, and future maintainers have contradictory authoritative rules.

**Recommendation:** Apply the repository's versioning rule or record an explicit pre-release exception for UID algorithms, and update the normative schema to match the endpoint-qualified ADR.

### Medium — Numerically equivalent standard ports split identities

**Description:** Effective ports are compared as strings. `:0443`, `:00022`, and `:09418` are not normalized to decimal before endpoint lookup, so they split from the equivalent documented endpoints `443`, `22`, and `9418`.

**Impact:** Equivalent clones can receive different UIDs, weakening deduplication and most-restrictive policy resolution and permitting duplicate aggregate counts. This is a safe split rather than a destructive collision, but it violates stable canonical identity.

**Recommendation:** Canonicalize numeric ports before endpoint comparison and structured serialization. Add leading-zero fixtures for each supported transport.

### Medium — Fixed backup names can overwrite recovery data

**Description:** `write_outputs` uses deterministic `<target>.bak` names with `os.replace`, which overwrites any existing backup. A reproduced successful render destroyed a pre-existing backup sentinel. Concurrent render processes also share the same `.tmp` and `.bak` names and can consume or delete each other's transaction files.

**Impact:** A retry after a failed rollback can destroy the remaining recoverable generation. Concurrent CLI invocations can restore the wrong generation or lose local files in the output directory.

**Recommendation:** Ensure each publication attempt owns and cleans only its own staging/backup artifacts, and define serialization behavior for concurrent publication to one output directory.

### Low — Cleanup failure reports a false publication failure

**Description:** Backup deletion occurs after all new targets are installed but remains inside the operation-level `OSError` handler. If a `.bak` unlink fails, the function raises `RenderError` even though the new generation is already fully published.

**Impact:** Callers receive an inaccurate failure result and may retry a successful publication. Backup debris can also remain without a distinct cleanup diagnostic.

**Recommendation:** Separate post-publication cleanup status from publication failure and add cleanup-failure coverage.

### Low — The claimed 42-case UID regression is not present

**Description:** `tests/unit/test_gitio_uid.py` checks a small set of documented and unsupported endpoints, not the stated six-scheme-by-seven-port grid. It only proves selected unsupported values differ from the canonical alias; it does not assert uniqueness among unsupported structured identities or vary their path case.

**Impact:** The test and progress ledger overstate coverage. The suite remained green despite the reproduced leading-zero equivalent-port split, and the documented 42-case cross-grid is not committed.

**Recommendation:** Replace the claim or implement the full parameterized grid with explicit equivalence classes, pairwise uniqueness expectations, normalized-port cases, and path-case variants that verify the ADR-approved convergence rule.

## Architecture and MVP assessment

- Architecture boundaries remain consistent: scanner owns orchestration, schema owns event validation/merge rules, storage remains below scanner, privacy remains the redaction boundary, and render/export consume `VizStats` rather than Git or SQLite.
- Aggregation units remain separated: unique commits, actor presences, provider-attributed commits, active days, and evidence records are not conflated. Unknown remains distinct from human.
- No new public privacy field, raw-value leak, or implementation divergence from ADR-016's approved path-folding rule was found.
- No GitHub API, Git Notes importer, generic profile-statistics generator, hosted service, or source-style inference was introduced. The Gate does not duplicate Git AI or generic README SVG/statistics projects.
- Runtime cost remains bounded and appropriate for v0.1. The new endpoint lookup is constant time; rollback handles three fixed assets; merge validation adds one linear pass.
- OSS release work remains incomplete as documented: sample output, clean-install/package smoke testing, additional hardening, packaged release, and upgrade policy are still open.

## Strengths

- The allowed endpoint set closes the previously demonstrated cross-scheme/port collapse for the sampled cases.
- The original replacement-stage failure now restores the prior generation when rollback succeeds.
- Legacy tests no longer demonstrate the prohibited incremental fold.
- Full tests and lint are green, with the platform-specific skip disclosed.
- No unnecessary abstraction or dependency was introduced.

## Required changes before advancing

1. Replace the source-count leaf heuristic with a boundary consistent with schema-valid multi-source events.
2. Reconcile export guarantees with rollback failure behavior and protect backup ownership.
3. Resolve UID version/schema drift and normalize numeric ports.
4. Add the missing adversarial identity coverage and re-run the full suite plus the direct UID, merge, rollback, cleanup, and backup-clobber probes.

## Final recommendation

**NOT READY**

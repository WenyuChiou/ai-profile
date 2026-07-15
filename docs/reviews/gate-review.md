# Current Gate implementation review

Date: 2026-07-15
Review range: `78e2e05519bc0de784790121a421f5fb0b4144d1..b899d1188fac306f25ab2d0c0e796dcc6f645769`
Reviewer posture: independent Principal Software Engineer; verification only, with no implementation or design changes.

## Executive summary

Gate 5 correctly closes most findings from the preceding review. The ACE schema now states the deliberately narrow lifetime of merge derivation state; sanctioned scanner reductions remain flat and deterministic; failed first-install retractions are reported; envelope equality behavior is explicit; the 42-cell UID grid is genuinely parameterized; and export fixtures are less duplicated. Architecture, aggregation, privacy, renderer isolation, MVP scope, and non-duplication remain consistent with the approved design.

Three correctness gaps prevent unconditional advancement. First, `<pid>-<process-counter>` transaction names repeat after process restart and PID reuse, so a later render can overwrite the recovery artifact that this Gate claims is attempt-owned. Second, rejecting ports above 65535 changes versioned repository identity behavior while retaining the `v4` algorithm label and leaving ADR-016 stale. Third, Unicode decimal ports pass `\d` and `int()` but are not rewritten to ASCII decimal, splitting endpoints equivalent to `:443`. Direct adversarial probes reproduced the artifact loss and Unicode UID split.

The remaining findings are bounded and do not compromise the validated aggregation or public-data boundary. They require targeted corrections and regressions rather than an architectural redesign.

## Review basis and verification evidence

- Read the repository guidance and current project design, including architecture, schema, MVP, privacy model, roadmap/progress, landscape, relevant ADRs, prior Gate reviews/dispositions, README, contribution guidance, implementation, and tests.
- Inspected the complete pinned 909-line diff through two independent static passes for each of architecture, security, performance, code quality, requirements compliance, and bugs.
- Ran `pytest -o addopts= -q`: `302 passed, 1 skipped in 24.60s`.
- Ran `ruff check .`: `All checks passed!`.
- Reproduced PID-reuse recovery loss by resetting the process counter while holding the PID constant: `summary-light.svg.4242-1.bak` contained `OLD-L` after the failed attempt and was absent after the simulated replacement process rendered.
- Reproduced Unicode-port splitting: ASCII `443` canonicalized to `github.com/o/r`, while full-width `４４３` and Arabic-Indic `٠٤٤٣` remained non-ASCII structured identities.
- Reproduced equality non-substitutability: a leaf and reduced event compared and hashed equal, but set insertion order selected an accepted leaf or a merge-rejected reduced event.

## Findings

### M-01 — Medium — Export transaction identifiers still collide after PID reuse

**Description:** `src/aiprofile/export.py:19-24, 43-58` defines an attempt identifier as `<pid>-<process-lifetime counter>`. The counter prevents collisions between calls in one live CPython process, but it restarts at `1` in every new process. If a hard-killed process leaves `summary-light.svg.<pid>-1.bak` and the OS later assigns the same PID to another process, its first render generates the same name. The direct probe simulated this lifecycle and showed the retained recovery backup was overwritten and deleted. The added regression covers sequential calls only within one process. The comment also relies on CPython counter atomicity even though `pyproject.toml` supports Python 3.11+ without restricting the interpreter.

**Impact:** A rare but explicitly in-scope crash-recovery sequence can destroy the only copy of previous public content. The disposition and docstring claim that later attempts never touch one another's artifacts, so the implementation does not meet the Gate's ownership contract.

**Recommendation:** Use a process-lifetime-independent per-invocation identifier with exclusive creation semantics, and add a regression that pre-seeds stale transaction artifacts independently of the current process counter.

### M-02 — Medium — Bounded-port rejection changes UID v4 without a version bump or ADR update

**Description:** `src/aiprofile/gitio.py:264-276` now returns `None` for ports above 65535. In the parent revision, `https://host:65536/o/r` produced a structured remote-v4 identity; this Gate makes `repository_uid()` fall back to a salted local-v4 identity. `UID_ALGORITHM` remains `v4`, while `docs/decisions/ADR-016-repository-identity-canonicalization.md` still defines v4 as endpoint qualification plus decimal normalization and states that rule changes require a version bump. The ADR does not define the new valid-port domain or fallback behavior.

**Impact:** The same `v4` label denotes different canonicalization algorithms across commits. Existing configuration can migrate opportunistically to a different UID without a version signal, undermining the version-directed reconciliation discipline used to protect deduplication and publication policy. The change is a safe split rather than a destructive collision, but it is still contract and migration drift.

**Recommendation:** Reconcile the change with ADR-016's versioning rule: either bump the UID algorithm and cover migration, or formally define and justify an input-domain exception before claiming v4 is unchanged. Update the normative schema and tests consistently.

### M-03 — Medium — Unicode decimal ports are not canonicalized to ASCII

**Description:** The URL regex at `src/aiprofile/gitio.py:231` uses Unicode-aware `\d+`. Python's `int()` accepts full-width and Arabic-Indic decimal digits, but `_canonical_identity()` strips only ASCII `0` and no longer assigns `str(int(port))` back to `port` (`lines 264-273`). Consequently, `https://github.com:４４３/o/r` remains `https://github.com:４４３/o/r` rather than converging with the documented ASCII endpoint `https://github.com:443/o/r`. The new tests cover ASCII ports only.

**Impact:** Equivalent remote endpoints can receive distinct repository UIDs, splitting counts and most-restrictive publication-policy resolution across clones. This is the same safe-split class that versioned canonicalization is intended to make deterministic.

**Recommendation:** Restrict accepted port syntax to ASCII digits or convert the bounded numeric value back to canonical ASCII decimal, then add cross-script digit-equivalence or rejection regressions.

### L-01 — Low — Equal AceEvent values can behave differently in the merge API

**Description:** `recorded_at` and `merged` now use `field(compare=False)` in `src/aiprofile/schema/event.py:66-89`. Excluding audit time aligns value equality with canonical JSON, but excluding `merged` makes a leaf and a reduced event compare and hash equal even though `merge_event_group()` accepts the former and rejects the latter. The direct set probe showed insertion order determines which equal representative survives and therefore whether the subsequent merge succeeds.

**Impact:** The current scanner does not put events through this pattern, so v0.1 runtime risk is low. Public library callers, caches, or future adapter code can nevertheless observe non-substitutable equal objects, making the sets/caches rationale misleading and increasing maintenance risk around the merge boundary.

**Recommendation:** Specify operational versus canonical-payload equality explicitly and avoid making control-flow-distinct leaf/reduced values interchangeable in Python collections. Add a substitutability regression for the approved semantics.

### L-02 — Low — Concurrent-render rejection is described but not exposed or enforced

**Description:** `docs/progress.md` and `docs/reviews/gate-disposition.md` say the concurrency contract rejects concurrent publication. Production code does not detect or reject overlap; the internal `write_outputs()` docstring only states that it is unsupported and can mix generations. The public `aiprofile render` help and README do not expose the one-writer-per-output-directory precondition.

**Impact:** The implementation's honest internal warning is an improvement, but CLI users can still invoke overlapping renders without seeing the known mixed-generation risk. The Gate evidence overstates runtime enforcement.

**Recommendation:** Use consistent “unsupported” wording unless an actual guard is implemented, and surface the precondition in user-facing render documentation/help.

### L-03 — Low — Schema tests reach into the storage migration layer

**Description:** `tests/unit/test_schema_event.py:829-862` combines canonical-payload assertions with `sqlite3`, `storage.db.migrate`, and `PRAGMA table_info(events)`. This places a persistence-schema contract in the event-model unit suite rather than the existing storage/migration tests.

**Impact:** Future persistence changes can fail in a surprising module and increase coupling between otherwise clear schema and storage test boundaries. There is no production defect.

**Recommendation:** Keep payload assertions in the schema-event suite and place the no-`merged`-column contract with storage/migration tests.

## Verified areas without findings

### Architecture and MVP consistency

- The scanner remains the only orchestration path; schema owns event construction and merge behavior; storage remains below the scanner; privacy owns `VizStats`; render/export do not scan Git or access SQLite.
- Narrowing merge-state protection to the sanctioned in-memory scanner path is explicit in the normative schema and does not silently promise unsupported rehydration behavior.
- No new GitHub networking, Git Notes reader/writer, Git AI line attribution, hosted service, extra card, period filter, or other post-v0.1 feature was introduced.

### Aggregation correctness

- Unique commits, AI-attributed commits, actor presences, provider-attributed commits, active author-local days, and evidence records remain separately named and computed.
- Multi-AI commits continue to count once as a unique commit and once per distinct actor presence; provider rows use distinct commits per provider.
- Unknown records remain distinct from explicit human declarations, and no source-code-style inference exists.
- Duplicate-scan idempotence and rewritten-history fixtures pass.

### Privacy and security

- Validated `VizStats` remains structurally unable to represent repository names/uids/paths, organization names, prompts, commit messages/SHAs, emails, raw trailer values, or sub-date timestamps.
- Excluded repositories fail closed; aggregate-only mode publishes counts without repository identity; unrecognized provider values collapse before the public boundary.
- Deterministic SVG/JSON, SVG allowlist, privacy canary, malformed-trailer, unknown-commit, and fixture-repository tests pass.
- v0.1 continues to contain no GitHub authentication, token handling, telemetry, or network client.

### Non-duplication and OSS readiness

- The Gate does not reproduce Git AI, Git Notes, GitHub API clients, generic profile-statistics generators, README SVG frameworks, or contribution-graph tools.
- README, contributing guidance, privacy threat model, design docs, and ADRs remain sufficient for contributor orientation.
- Sample output, packaged-install smoke testing, permissions/symlink hardening, broader diagnostic canaries, and release packaging remain honestly open in the roadmap rather than being claimed complete.

## Severity summary

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 3 |
| Low | 3 |

## Final recommendation

READY AFTER MINOR FIXES

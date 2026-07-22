# Gate-9 remediation verification review

Date: 2026-07-21

Review range: `e0fa569446d66b9de57416bcf10d7d1429de02d4..d9161cb4c5f4ef67d0fb9d71a9f197a14e80ab4d`

Reviewer posture: independent Principal Software Engineer; verification only. No production code, test code, or approved design document was changed during this review.

## Executive summary

The gate-9 remediation is verified. `VizStats` is sealed against ordinary subclassing at class-definition time, and its retained exact-top-level-type validation backstop is consistent with the privacy-boundary contract. I independently exercised eight construction or mutation routes; none yielded a subclass capable of reaching rendering or export with a private canary.

Legitimate `VizStats` lifecycle operations remain exact and functional. The privacy builder and a fresh synthetic Git-repository CLI sweep produced public assets with no private repository, organization, UID, or salt data. The gate-7 vocabulary and gate-8 exact-graph protections remain enforced, sanctioned snapshot/sample regeneration is byte-stable, and gate-7/gate-8 remediation records name their actual commits.

No findings.

## Review basis and verification evidence

Reviewed repository guidance (`AGENTS.md`), `README.md`, `CONTRIBUTING.md`, the gate-9 handoff brief, architecture section 3, `docs/progress.md`, gate-9 in `docs/reviews/gate-disposition.md`, the complete target diff, `src/aiprofile/viz.py`, and `tests/unit/test_viz_contract.py`.

`HEAD` has later documentation-only commits (`AGENTS.md`, progress/disposition/review artifacts); `git diff --name-status d9161cb..HEAD` showed no later production or test-code change. Findings therefore assess the immutable requested range.

Commands and observed results:

- `git diff --check e0fa569..d9161cb` -> exit 0; no whitespace errors.
- `python -m pytest tests -p no:cacheprovider` -> exit 0; `340 passed, 1 skipped in 37.66s`. The command emitted unrelated installed-package compatibility warnings from `requests` and `langsmith` after the passing result.
- `python -m ruff check src tests` -> exit 0; `All checks passed!`.
- `python tests/unit/test_render_summary.py` -> exit 0; wrote 8 snapshot files and 2 sample assets. `git diff --exit-code -- tests/snapshots docs/assets` -> exit 0, and `git status --short` remained empty before this report was written.
- `python -m pytest tests/integration/test_end_to_end.py::test_privacy_leak_remote_org_and_uid_canaries -p no:cacheprovider` -> exit 0; `1 passed in 4.38s`. This is a fresh real-Git/CLI fixture which scans a remote containing organization/repository canaries, renders assets, and byte-sweeps the public output for the organization, repository, derived UID, and salt.
- `rg -n -i -C 2 "UNCOMMITTED" docs/progress.md docs/reviews/gate-disposition.md` -> gate-7 and gate-8 state records name `73279cd` and `e0fa569`; remaining matches only quote the old stale term in the disposition explanation or describe a later gate-9 record correction.

### Independent bypass replay

A from-scratch inline Python probe attempted each required route against the reviewed code:

- A `VizStats` subclass overriding `__post_init__` to skip validation -> `TypeError` at class definition.
- A subclass overriding `__getattribute__` for render-time private-row substitution -> `TypeError` at class definition.
- A deep subclass chain -> the first descendant raised `TypeError`; no chain could form.
- Multiple inheritance -> `TypeError` at class definition.
- A custom metaclass whose `__new__` calls `type.__new__` -> `TypeError` at class definition.
- `types.new_class` -> `TypeError` at class definition.
- A `__bases__` splice -> `TypeError` from CPython before a usable subclass exists (the `VizStats` deallocator differs from `object`).
- Direct `type.__new__(type, name, (VizStats,), namespace)` -> `TypeError` at class definition.

The probe asserted that no construction survived. Consequently no subclass existed to pass a private canary to `render_summary`, `dumps_stats`, or `write_outputs`.

The same independent probe also verified:

- `dataclasses.replace`, `copy.copy`, `copy.deepcopy`, and pickle round-trip each yield an exact `VizStats`, preserve equality, and render/export the same bytes as the original valid value.
- Gate-7 free-text period and display-name canaries raise `RenderError` before renderer/exporter use.
- Gate-8 mutable provider-container plus `str` and `int` subclass inputs raise `RenderError` before renderer/exporter use.
- A direct `privacy.build_viz_stats` construction with private UID/path/raw-provider canaries produces an exact `VizStats`; both theme SVGs and JSON contain none of the canary bytes.

## Findings

No Critical, High, Medium, or Low findings.

## Verified areas without findings

- `src/aiprofile/viz.py:100` seals ordinary subclasses in `VizStats.__init_subclass__`; `src/aiprofile/viz.py:139` retains exact-type validation as a defense-in-depth backstop.
- The architecture documentation accurately limits its promise to ordinary Python mutation and subclassing, explicitly excluding deliberate low-level fabrication such as `object.__setattr__`, ctypes, and pickle surgery.
- Valid object lifecycle behavior and the supported `privacy.build_viz_stats` path remain intact.
- Gate-7 vocabulary and gate-8 structural-exactness defenses still reject their prior bypass classes.
- Render snapshots and committed README sample assets regenerate byte-identically using the sanctioned command.
- The focused synthetic-repository integration sweep confirms generated public assets do not disclose private identifiers.
- Gate-7 and gate-8 audit records no longer make the stale claim that their remediations are uncommitted.

## Severity summary

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |

## Final recommendation

READY FOR NEXT GATE

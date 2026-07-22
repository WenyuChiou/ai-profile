# Gate 9 remediation verification review

Date: 2026-07-22

Review range: `e0fa569446d66b9de57416bcf10d7d1429de02d4..d9161cb4c5f4ef67d0fb9d71a9f197a14e80ab4d`

Reviewer posture: independent Principal Software Engineer; verification only. No production code, test code, architecture, schema, or MVP design was changed during this review. This report overwrites the prior uncommitted gate review artifact per repository convention.

## Executive summary

The gate-9 remediation is verified. `VizStats` is now sealed against ordinary subclassing at class-definition time, and the retained `type(s) is VizStats` validation backstop is consistent with the privacy-boundary contract. I could not produce a surviving ordinary subclass through `__post_init__` skipping, `__getattribute__` substitution, deep subclassing, multiple inheritance, custom metaclass `__new__`, `types.new_class`, `__bases__` splicing, or direct `type.__new__`.

The legitimate construction paths still work: `dataclasses.replace`, `copy.copy`, `copy.deepcopy`, `pickle` round-trip, and `privacy.build_viz_stats` all yield exact `VizStats` objects and publish only redacted public vocabulary. Gate-7 vocabulary checks and gate-8 exact-type checks still reject private canaries. Gate-7 and gate-8 remediation records now name their actual commit hashes (`73279cd`, `e0fa569`) instead of wrongly stating "UNCOMMITTED".

No findings.

## Review basis and verification evidence

Reviewed repository guidance; `README.md`; `CONTRIBUTING.md`; the handoff brief; the code-review skill instructions; `docs/reviews/gate-disposition.md` gate-9 section; `docs/architecture.md` section 3; `docs/progress.md`; the complete `e0fa569..d9161cb` diff; `src/aiprofile/viz.py`; and `tests/unit/test_viz_contract.py`.

Commands and observed results:

- `git status --short --branch` -> `## main` and ` M docs/reviews/gate-review.md` before writing this replacement report, matching the handoff note that the prior review artifact was deliberately uncommitted.
- `git log --oneline --decorate -5` -> `6801ce9` at `HEAD`, with `d9161cb` immediately below it and `e0fa569` below that. The later `6801ce9` commit is doc-only and outside the review range.
- `git diff --stat e0fa569..d9161cb` -> 5 files changed, 108 insertions, 15 deletions: `docs/architecture.md`, `docs/progress.md`, `docs/reviews/gate-disposition.md`, `src/aiprofile/viz.py`, `tests/unit/test_viz_contract.py`.
- `python -m pytest tests -p no:cacheprovider` -> `340 passed, 1 skipped in 24.65s` (exit 0). The run emitted unrelated global-environment warnings from `requests` and `langsmith`; no project test failed.
- `python -m ruff check src tests` -> `All checks passed!` (exit 0).
- `python tests/unit/test_render_summary.py` -> `Wrote 8 snapshot files` and `Wrote 2 sample assets`; subsequent `git status --short` showed only `M docs/reviews/gate-review.md`; `git diff --check` returned exit 0.
- `python -m pytest tests/integration/test_end_to_end.py::test_privacy_leak tests/integration/test_end_to_end.py::test_privacy_leak_remote_org_and_uid_canaries -p no:cacheprovider` -> `2 passed in 3.69s` (exit 0), independently re-running the fresh synthetic-repo public-output privacy sweeps.
- `rg -n "Gate-7|Gate-8|UNCOMMITTED|73279cd|e0fa569" docs\progress.md docs\reviews\gate-disposition.md` -> gate-7 and gate-8 records name `73279cd` and `e0fa569`; remaining `UNCOMMITTED` references are the current gate-9 state and the quoted stale wording corrected by L-01.

### Bypass replay results

I ran a from-scratch Python adversarial probe against the checked-out code. Results:

- `type("SkipPostInit", (VizStats,), {"__post_init__": lambda self: None})` -> `TypeError`.
- `type("SwapProviders", (VizStats,), {"__getattribute__": ...})` -> `TypeError`.
- Deep-chain setup via `type("BaseEvil", (VizStats,), {})` -> `TypeError` before a chain can be formed.
- Multiple inheritance via `type("MultiEvil", (Mixin, VizStats), {})` -> `TypeError`.
- Custom metaclass `Meta("MetaEvil", (VizStats,), {})` whose `__new__` calls `type.__new__` -> `TypeError`.
- `types.new_class("NewClassEvil", (VizStats,))` -> `TypeError`.
- `Placeholder.__bases__ = (VizStats,)` -> `TypeError` (`__bases__` assignment rejected by CPython before a usable subclass exists).
- `type.__new__(type, "DirectTypeNewEvil", (VizStats,), {})` -> `TypeError`.
- `dataclasses.replace(s, generated_on="2026-07-16")`, `copy.copy(s)`, `copy.deepcopy(s)`, and `pickle.loads(pickle.dumps(s))` -> exact `VizStats`; rendered SVG/JSON contained no private canary.
- Gate-7 vocabulary replay with `ProviderRow("anthropic", private_canary, ...)` -> `RenderError` before rendering/export.
- Gate-8 exact-container replay with a list-valued `providers` container -> `RenderError` before rendering/export.
- `privacy.build_viz_stats` replay with a noncanonical provider key and raw private provider canary -> public output contained `Unrecognized`, not the private key or raw canary.

An earlier hand-written e2e script timed out before producing usable evidence, so I did not count it as verification evidence. The focused integration privacy tests above provide the repeatable fresh-repo sweep evidence.

## Findings

No Critical, High, Medium, or Low findings.

## Verified areas without findings

- `VizStats.__init_subclass__` closes the ordinary subclass family at class-definition time, including the `__post_init__`-skip and `__getattribute__`-substitution variants that motivated gate-9.
- `_validate` still keeps an exact top-level `type(s) is VizStats` defense-in-depth backstop.
- The architecture prose is no stronger than the implementation: it claims protection against ordinary assignment, duck-typed construction, and subclassing, while explicitly excluding deliberate low-level fabrication such as `object.__setattr__`, ctypes, and pickle surgery.
- The legitimate object lifecycle remains intact: replace/copy/deepcopy/pickle produce exact `VizStats`.
- The supported `privacy.build_viz_stats` pipeline still strips identity and collapses noncanonical provider keys to `unrecognized` before display.
- Gate-7 vocabulary rejection and gate-8 structural exact-type rejection still work.
- Snapshot and README sample regeneration is byte-stable.
- Fresh synthetic repository privacy sweeps pass.
- Gate-7 and gate-8 audit records no longer carry wrongly stale "UNCOMMITTED" status.

## Severity summary

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

## Final recommendation

READY FOR NEXT GATE

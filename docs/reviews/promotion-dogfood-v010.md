# v0.10.0 attribution reliability dogfood

Date: 2026-09-24. Candidate: the Ubuntu CI-retained
`ai_profile_cli-0.10.0-py3-none-any.whl`, SHA-256
`f928f3cea716f80b005b1e126af8b774bbc63b6f9886b54cdb2748454ef4da4e`.
The same digest is frozen in `promotion-candidate.json`; it is not a floating
package lookup. The pre-registered acceptance criteria are in
`promotion-eval-spec-v010.md`.

## Independent README-only roles

Each role received only the English and Traditional Chinese READMEs, the
retained wheel, and a bounded objective. Each installed the wheel into a
fresh virtual environment and used its own synthetic Git repository and
`AIPROFILE_HOME`. No role inspected source or tests, edited this repository,
contacted GitHub, or synchronized private attestations.

| Role | Result | Observed evidence |
| --- | --- | --- |
| Newcomer | PASS | 2 scanned, 1 AI-attributed, 1 Unattributed, 1 actor presence; exactly eight assets and zero byte changes on repeat refresh |
| Privacy-sensitive user | PASS | Unmarked commit stayed Unattributed; one individually confirmed private reconciliation became 1 AI-attributed commit after rescan and refresh; exact eight assets with zero private path/email/SHA/canary hits |
| Overlapping-provider user | PASS | 4 scanned, 2 unique AI commits, 3 actor presences, 2 Unattributed; 15/15 oracle checks; ambiguous organization and review prose did not become AI evidence |
| Profile publisher | PASS | Eight non-empty local publication assets, five working README targets, restrictive self-contained dashboard CSP, no network dependency or private identifier, byte-identical repeat refresh |

The coordinator independently parsed all four `profile.json` files and
verified every eight-file output set. It repeated a fixed-string scan for the
privacy fixture's canary, private email and full SHA with zero public-asset
hits, and independently compared the publisher's eight baseline and refreshed
SHA-256 digests with zero differences. Raw fixtures and ledgers remain only in
the marked disposable scratch root; this report contains no private fixture
identity or per-commit declaration.

## Exact-wheel Git workflow probe

A separate isolated installation of that same wheel exercised real Git hooks:
an opt-in mark inserted normalized AI trailers into one commit; `doctor`
reported no pending mark afterward. Changing the staged tree after marking
blocked the commit without consuming the mark. `clear` then allowed an
unmarked commit, and `pr-check` rejected a proposed squash message that would
lose explicit source evidence. These are opt-in commit-time checks, not an
AI-usage detector or a local daily schedule.

## Scope, limitations, and remaining gates

All four roles passed. One publisher fixture shell command quoted literal
newlines, producing an `Unrecognized` synthetic provider label; that fixture
was used only to check asset publication, while the overlap role separately
verified canonical provider rows. An initial hash helper and baseline-copy
attempt were discarded; only corrected, repeatable hash checks support the
determinism verdict. Each role's home was within an enclosing worktree and
the CLI displayed its intended privacy warning; no home data entered outputs.

Before merge, Windows Python 3.14 reported **1038 passed, 31 skipped**;
Ruff, bilingual README parity, sanctioned snapshot/sample regeneration with
zero byte drift, installed-wheel artifact/smoke checks, and GitHub's eight
candidate CI jobs passed. This dogfood does not substitute for the separate
post-PyPI hosted caller/Pages E2E or live maintainer Profile verification.

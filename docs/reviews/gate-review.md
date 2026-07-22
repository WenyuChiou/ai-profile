# Gate 11 round A hardening verification review

Date: 2026-07-22

Review range: `77ed004..278c138`

Reviewer posture: independent Principal Software Engineer; verification only. No production code, test code, schema, or design code was changed during this review. This report overwrites the prior gate review artifact per repository convention.

## Executive summary

The round A hardening is mostly verified: required tests and lint are green, the packaged smoke passes, worktree detection is a pure path walk, the cp950 ASCII guards work against scratch-copy mutations, cherry-pick counting is documented and independently reproduced, and public-output privacy canaries still pass.

One Medium finding remains: the owner-only permission retrofit is not applied when `AIPROFILE_HOME/config.json` already exists. That means an already-initialized home can pass through `aiprofile init`, `aggregate`, or `render` without chmodding either the home directory or `config.json`, despite the new docs claiming owner-only local storage hardening.

## Findings

| Severity | Issue | Location |
|---|---|---|
| Medium | Existing `AIPROFILE_HOME` instances skip the permission retrofit because `init_home()` returns before any chmod path runs when `config.json` exists. | `src/aiprofile/config.py:85` |

### Medium: existing homes skip chmod retrofit

`init_home()` exits immediately on an existing `config.json`, so the new `home.mkdir(..., mode=0o700)`, `_restrict_to_owner(home, 0o700)`, and `save_config()` tmp-file chmod path are all skipped for already-initialized users. `scan` eventually calls `save_config()` and will retrofit then, but `init`, `aggregate`, and `render` can leave pre-hardening `AIPROFILE_HOME` and `config.json` permissions unchanged. That contradicts the hardening claim in the handoff and the implemented-hardening wording in `docs/PRIVACY.md`.

Reproduction probe:

```text
created False
chmod_calls []
```

The probe created a valid existing `home/config.json`, patched `os.chmod` to record calls, then ran `init_home(home, [])`. No chmod was attempted.

Suggested fix: on the existing-config path, call `_restrict_to_owner(home, 0o700)` before loading, and either restrict `config_path(home)` directly after successful load or route through a small helper that validates then chmods the existing config file. Keep chmod failure warning/non-raising semantics.

## Review basis

Reviewed `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, the handoff brief, the full `77ed004..278c138` diff, changed implementation/test files, `docs/ROADMAP.md`, the `docs/PRIVACY.md` delta, `docs/schema.md` section 8.4, and `docs/decisions/ADR-007-deterministic-event-ids.md`.

## Verification evidence

Commands and observed results:

- `git status --porcelain=v1` before verification: clean.
- `git diff --stat 77ed004..278c138`: 17 files changed, 1027 insertions, 36 deletions.
- `python -m pytest tests -p no:cacheprovider`: `354 passed, 4 skipped in 36.64s` (exit 0). The run emitted unrelated global-environment warnings from `requests` and `langsmith`.
- `python -m ruff check src tests scripts`: `All checks passed!` (exit 0).
- Fake-POSIX chmod failure probe for `config.init_home`, `config.save_config`, and `storage.connect`: each emitted `warning: could not restrict permissions on ...` to stderr and did not raise.
- Existing-home chmod probe: `created False`, `chmod_calls []` (finding above).
- Worktree probe: `.git` directory, `.git` file, and deep nesting all returned `True`; `subprocess.run` was patched to raise and was never called. Symlinked-parent probe was skipped because this Windows process lacks symlink privilege (`WinError 1314`).
- Independent AST scanner over `cli.py` string constants: 0 non-ASCII offenders.
- Independent AST scanner over repo-wide Python raise-string constants: 0 non-ASCII offenders.
- Scratch-copy mutation with a non-ASCII character in `cli.py`: `test_all_cli_string_literals_are_ascii` failed as expected.
- Scratch-copy mutation with a non-ASCII character in a raised config exception: `test_all_raised_exception_messages_are_ascii` failed as expected.
- `python scripts/release_smoke.py`: all steps passed; result `PASS - all steps green`. Install mode was `pip install --no-build-isolation` because `hatchling` was importable in this interpreter.
- Release-smoke cleanup: the current run removed its scratch directory. Two older `aiprofile-release-smoke-*` directories were already present under `%TEMP%` and remained.
- `python tests/unit/test_render_summary.py`: wrote 8 snapshot files and 2 sample assets; subsequent `git status --porcelain=v1` and `git diff -- tests/snapshots docs/assets` showed no byte drift.
- `python -m pytest tests/integration/test_end_to_end.py::test_privacy_leak tests/integration/test_end_to_end.py::test_privacy_leak_remote_org_and_uid_canaries -p no:cacheprovider`: `2 passed in 8.09s` (exit 0).
- Independent cherry-pick replay: source AI commit SHA `7de2af53e87ddf88261db461b5d3861e5619e0b7`, cherry-picked SHA `ed848c5f3c5a08c0af6bf62d206ca91b59516f15`, two distinct repository UIDs, totals `commits_scanned=4`, `ai_attributed_commits=2`, `ai_actor_presences=2`, `unknown_commits=2`, `human_declared_commits=0`; Anthropic provider `attributed_commits=2`, `actor_presences=2`.

## Verified areas without findings

- New homes get `home.mkdir(..., mode=0o700)` plus best-effort `_restrict_to_owner(home, 0o700)`.
- `config.json` writes restrict the temporary file before `os.replace()`.
- `aiprofile.db` is chmodded on every successful `connect()`.
- POSIX chmod failures warn to stderr and do not break init/config/db creation.
- Windows behavior is documented as a chmod no-op.
- `aiprofile init` warns when `AIPROFILE_HOME` is inside a git work tree.
- `_is_inside_git_worktree()` recognizes `.git` as either a directory or file and does not spawn git.
- CLI user-facing string constants and raised exception messages are ASCII-clean under the committed AST guards.
- `render/summary_svg.py` UTF-8 SVG template content was left outside the console-text hardening scope.
- Cherry-picked commits with distinct SHAs are counted once per repository/commit identity, consistent with schema section 8.4 and ADR-007.
- `.gitignore`, README, ROADMAP, and privacy-doc updates match the stated hardening direction, subject to the existing-home chmod gap above.
- Public-output privacy leak tests remain green.

## Severity summary

- Critical: 0
- High: 0
- Medium: 1
- Low: 0

## Final recommendation

READY AFTER MINOR FIXES

# Gate 12 final pre-release verification review

Date: 2026-07-22

Review range: `278c138..ac21d4d`

Reviewer posture: independent Principal Software Engineer; verification only. No production code, test code, schema, or design code was changed during this review. This report overwrites the prior gate review artifact per repository convention.

## Executive summary

The final pre-release range is verified. The gate-11 permission retrofit now runs through `load_config()` for pre-existing installations and remains non-fatal on chmod failure. The Round B tests are non-vacuous and deterministic in isolation, the full suite and lint are green, package metadata passes build/twine checks, release smoke passes, snapshot/sample generation is byte-stable, and a fresh synthetic end-to-end privacy byte sweep found no canary leaks.

No release-blocking or minor findings were found.

## Findings

| Severity | Issue | Location |
|---|---|---|
| None | No findings. | n/a |

## Review basis

Reviewed `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, the handoff brief, the full `278c138..ac21d4d` diff, changed implementation/test/docs files, `docs/decisions/ADR-012-schema-versioning.md`, `docs/decisions/ADR-004-sqlite-access-and-migrations.md`, `src/aiprofile/aggregate.py`, `src/aiprofile/storage/db.py`, and `src/aiprofile/storage/migrations.py`.

## Verification evidence

Commands and observed results:

- `git status --porcelain=v1` before verification: clean.
- `git log --oneline --decorate -5`: HEAD was `ac21d4d (HEAD -> main, origin/main) Round C: packaging metadata, CHANGELOG + upgrade policy, bilingual README`.
- `git diff --stat 278c138..ac21d4d`: 12 files changed, 1052 insertions, 51 deletions.
- `git diff --name-only 278c138..ac21d4d`: `AGENTS.md`, `CHANGELOG.md`, `README.md`, `README.zh-TW.md`, `docs/progress.md`, `docs/reviews/gate-disposition.md`, `docs/reviews/gate-review.md`, `pyproject.toml`, `src/aiprofile/config.py`, `tests/integration/test_console_privacy.py`, `tests/unit/test_config.py`, `tests/unit/test_properties.py`.
- `python -m pytest tests/integration/test_console_privacy.py tests/unit/test_properties.py -p no:cacheprovider`: `9 passed in 6.55s` (exit 0). The run emitted unrelated global-environment warnings from `requests` and `langsmith`.
- Re-run of the same isolation command: `9 passed in 6.34s` (exit 0), supporting the Hypothesis determinism claim.
- `python -m pytest tests -p no:cacheprovider`: `364 passed, 4 skipped in 25.84s` (exit 0). The run emitted the same unrelated global-environment warnings.
- `python -m ruff check src tests scripts`: `All checks passed!` (exit 0).
- `python -m build --no-isolation`: successfully built `ai_profile-0.1.0.tar.gz` and `ai_profile-0.1.0-py3-none-any.whl`.
- Wheel `METADATA` inspection: `Metadata-Version: 2.4`, `Name: ai-profile`, `Version: 0.1.0`, `License-Expression: MIT`, `License-File: LICENSE`, and four `Project-URL` entries (`Homepage`, `Repository`, `Issues`, `Changelog`).
- `python -m twine check dist/*`: both wheel and sdist `PASSED`. Generated `dist/` artifacts were removed afterward; `dist exists: False`.
- `python scripts/release_smoke.py`: `RESULT: PASS - all steps green`. Its current scratch directory was removed. Two older `aiprofile-release-smoke-*` directories from 2026-07-21 were already present under `%TEMP%` and remained; they were not created by this run.
- `%TEMP%` cleanup check for release smoke: current scratch `aiprofile-release-smoke-hgasnzpz` was absent; pre-existing directories were `aiprofile-release-smoke-maa517v9` and `aiprofile-release-smoke-rdv1mxu4`.
- Chmod failure probe for pre-existing config: `load_config()` returned `loaded identities: ['u@example.com']` after attempted chmod calls for `(home, 0o700)` and `(home/config.json, 0o600)` both raised `OSError`.
- `python tests/unit/test_render_summary.py`: wrote 8 snapshot files and 2 sample assets; subsequent `git status --porcelain=v1` stayed clean.
- Fresh synthetic-repo end-to-end privacy sweep: created a temporary repo with canary repo name, remote org/repo/URL, author email, raw unrecognized provider, commit message, salt, and commit SHA; ran `init`, `scan`, and `render`; byte-swept `profile.json`, `summary-dark.svg`, and `summary-light.svg`; checked 9 forbidden canaries; `leaks: []`.

## Verified areas without findings

- Gate-11 retrofit: `load_config()` now chmods both the existing home directory and existing `config.json`, covering upgraded installations that skip `init_home()` creation.
- Chmod errors remain best-effort and non-fatal.
- Round B console privacy sweeps are not vacuous: default-mode tests assert the deliberate repo-display exception, verbose scan asserts SHA/local-detail output, and verbose aggregate asserts raw unrecognized provider output.
- Round B property tests use `derandomize=True`, bounded examples, and ASCII-only generated strings.
- Changelog upgrade-policy claims match ADR-004's forward-only migration runner and ADR-012's incompatible `major.minor` aggregation refusal.
- README.zh-TW.md spot check: install/name-collision and privacy-model sections mirror the English README's high-risk claims, including the hyphenated PyPI name, `aggregate_only` default, public-output exclusions, raw unrecognized provider visibility only via `aggregate -v`, aggregate-only non-anonymity caveat, and dotfiles warning.
- Packaging metadata is release-ready for the checked wheel.
- Snapshot/sample assets are byte-stable.

## Severity summary

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

## Final recommendation

READY FOR RELEASE

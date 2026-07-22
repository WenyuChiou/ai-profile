# Gate 13 brand identity verification review

Date: 2026-07-22

Review range: `1d63814..08922b7`

Reviewer posture: independent Principal Software Engineer; verification only. No production code, test code, schema, or design code was changed during this review. This report overwrites the prior gate review artifact per repository convention.

## Executive summary

The round D1 brand identity layer is ready for the next gate. The renderer now selects branded glyph tiles only from the canonical public provider slug, keeps fallback providers on neutral letter tiles, leaves `VizStats` untouched, and preserves the privacy boundary. Full suite, lint, targeted privacy tests, snapshot/sample regeneration, and a fresh synthetic release smoke all passed.

One evidence limitation: this environment could not connect from the local shell to `raw.githubusercontent.com`, so I could not independently byte-diff the vendored `d=` attributes against the exact pinned upstream commit from the command line. Browser-searchable public metadata did corroborate `simple-icons` package version `16.27.0`, CC0-1.0 licensing, and CDN presence of relevant icon slugs, but not the exact pinned-commit path bytes.

## Findings

| Severity | Issue | Location |
|---|---|---|
| None | No findings. | n/a |

## Review basis

Reviewed `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, the handoff brief, `.ai/round_d1_brand_identity_spec.md`, the full `1d63814..08922b7` diff, `docs/decisions/ADR-017-provider-brand-glyphs.md`, `src/aiprofile/render/brand.py`, `src/aiprofile/render/summary_svg.py`, `src/aiprofile/render/themes.py`, `src/aiprofile/schema/vocab.py`, `src/aiprofile/viz.py`, `tests/unit/test_brand.py`, `tests/unit/test_render_summary.py`, `tests/unit/test_dependency_isolation.py`, and the privacy/render/export integration tests.

External source checks:

- `https://www.npmjs.com/package/simple-icons`: public package metadata showed version `16.27.0` and license `CC0-1.0`.
- `https://cdn.jsdelivr.net/npm/simple-icons/`: public CDN listing showed `simple-icons@16.27.0`, `LICENSE.md`, and package files.
- `https://cdn.jsdelivr.net/npm/simple-icons/icons/`: public CDN icon listing showed relevant slugs including `googlegemini.svg`, `cursor.svg`, and `windsurf.svg`.
- `https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md`: GitHub-rendered license page showed `CC0 1.0 Universal`.

## Verification evidence

Commands and observed results:

- `git status --porcelain=v1` before verification: clean.
- `git diff --stat 1d63814..08922b7`: 14 files changed, 887 insertions, 66 deletions.
- `git diff --name-only 1d63814..08922b7`: `docs/architecture.md`, 2 docs sample assets, `docs/decisions/ADR-017-provider-brand-glyphs.md`, `src/aiprofile/render/brand.py`, `src/aiprofile/render/summary_svg.py`, 6 SVG snapshots, and 2 unit test files.
- `git diff 1d63814..08922b7 -- src/aiprofile/viz.py`: empty.
- `python -m pytest tests -p no:cacheprovider`: `375 passed, 4 skipped in 25.90s` (exit 0). The run emitted unrelated global-environment warnings from `requests` and `langsmith`.
- `python -m ruff check src tests scripts`: `All checks passed!` (exit 0).
- `python -m pytest tests/integration/test_end_to_end.py::test_privacy_leak tests/integration/test_end_to_end.py::test_privacy_leak_remote_org_and_uid_canaries tests/integration/test_console_privacy.py tests/unit/test_viz_contract.py -p no:cacheprovider`: `30 passed in 6.19s` (exit 0). The run emitted the same unrelated global-environment warnings.
- `python tests/unit/test_render_summary.py; git status --porcelain=v1; python tests/unit/test_render_summary.py; git status --porcelain=v1`: each run wrote 8 snapshot files and 2 sample assets; both subsequent status checks produced no output, confirming byte-stable regenerated artifacts.
- `python scripts/release_smoke.py`: all steps passed, including throwaway venv install, synthetic trailer repo, `init`, `scan`, `aggregate`, `render`, `profile.json` structural sanity, SVG well-formedness, and canary byte-sweep of dist outputs; final line `RESULT: PASS - all steps green`.
- `git diff --check 1d63814..08922b7`: no output (exit 0).
- `rg -n "#[0-9A-Fa-f]{6}" src/aiprofile/render/summary_svg.py src/aiprofile/render/brand.py src/aiprofile/render/themes.py`: no hex literals in `summary_svg.py`; hex values are confined to token/data modules (`themes.py`, `brand.py`) and comments.
- `rg -n "BRAND|get\\(row\\.provider\\)|row\\.display_name|provider_raw|tool_raw|repository|remote|sha|email" src/aiprofile/render src/aiprofile/viz.py`: renderer branch point is `BRAND.get(row.provider)` in `summary_svg.py`; private/raw-value terms do not appear in render modules except public explanatory text.
- `Invoke-WebRequest` probes to `https://raw.githubusercontent.com/simple-icons/simple-icons/f7cc40071c00ca767e6f5532fb99bfbc25efb8fe/{icons/claude.svg,icons/googlegemini.svg,icons/githubcopilot.svg,LICENSE.md}`: all failed with `Unable to connect to the remote server`.

Independent Python probe over brand/render behavior:

```text
CONTRAST anthropic light=4.213 dark=6.757
CONTRAST google light=3.221 dark=3.883
CONTRAST github light=14.394 dark=10.318
CONTRAST cursor light=15.300 dark=10.503
PATH_SAFETY checked=5 unsafe=0
FALLBACK_PATHS checked=aider,amazon,cognition,openai,openhands,roo-code,unrecognized path_elements=0
BRANDED_PATHS checked=anthropic,cursor,github,google,windsurf path_elements_each=1
```

## Verified areas without findings

- Brand rendering depends on the canonical provider slug, not raw provider strings or repository-local values: `summary_svg._glyph_tile_svg()` uses `BRAND.get(row.provider)` for branded tiles and the validated public display name only for neutral fallback lettering.
- `VizStats` remains the privacy boundary and is unchanged in the review range.
- The mirrored render-layer vocabulary is backed by drift tests against the real schema constants.
- Fallback providers (`openai`, `amazon`, `aider`, `roo-code`, `openhands`, `cognition`) and the reserved `unrecognized` row render without `<path>` elements.
- XML safety is covered both by unit tests and an independent probe: vendored paths are ASCII and contain no `"`, `&`, `<`, `>`, newline, tab, or carriage return characters.
- SVG active-content checks still cover the newly allowed `<path>` element: no event-handler attributes, no `href`, no external references, no `<script>`, no `foreignObject`.
- WCAG contrast for sampled brand foreground/tint pairs cleared 3:1 in both themes using an independent luminance implementation.
- The nominative-use/trademark posture is appropriately modest. ADR-017 says the glyphs identify providers/tools and do not imply endorsement; it also records the Simple Icons trademark caveat indirectly via fallback and source policy. I did not find overclaiming in the project docs.

## Severity summary

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

## Final recommendation

READY FOR NEXT GATE

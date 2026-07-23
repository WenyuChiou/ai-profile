# Gate 15 D3 provider ecosystem verification review

Date: 2026-07-23

Review range: `ea5f37d..d2c1147`

Reviewer posture: independent Principal Software Engineer; verification only. No
production code, test code, schema, or design code was changed during this
review. This report overwrites the prior gate review artifact per repository
convention.

## Executive summary

The round D3 implementation is not ready for the next gate. The suite and lint
pass, co-author auto-match isolation holds, slug-form declarations flow through
parse -> ACE -> aggregate -> VizStats -> render, and privacy canaries stayed out
of public SVG/JSON. However, the owner-facing product display names documented by
the round spec and ADR-019 do not all resolve as `AI-Provider:` values.

Specifically, `AI-Provider: Kimi`, `AI-Provider: Qwen`, `AI-Provider: Grok`,
`AI-Provider: GLM`, and `AI-Provider: Llama` produce canonical-null AI specs
instead of the intended canonical slugs `moonshot`, `alibaba`, `xai`, `zhipu`,
and `meta`. Those rows would publish as `Unrecognized` rather than the D3 brand
identities.

## Findings

| Severity | Issue | Location |
|---|---|---|
| High | Product-identity provider declarations do not resolve for five D3 providers. ADR-019 says display names follow product identity, and the handoff explicitly required synthetic `AI-Provider: Kimi` / `DeepSeek` / etc. to resolve end-to-end. `PROVIDER_ALIASES` only includes company/canonical slug spellings for `moonshot`, `alibaba`, `xai`, `zhipu`, and `meta`, so user-written product-name trailers become canonical-null. | `src/aiprofile/registry.py:42` |

## Details

### High: product display aliases missing from declaration tier

`PROVIDER_DISPLAY` maps the public identities as `moonshot -> Kimi`,
`alibaba -> Qwen`, `xai -> Grok`, `zhipu -> GLM`, and `meta -> Llama`
(`src/aiprofile/schema/vocab.py:128`). The round spec also lists these display
names as the declaration-tier vocabulary (`.ai/round_d3_provider_ecosystem_spec.md:25`).
But `PROVIDER_ALIASES` only accepts raw canonical/company spellings:

```text
moonshot -> moonshot
alibaba -> alibaba
xai -> xai
zhipu -> zhipu
meta -> meta
```

Independent parser probe:

```text
display_alias_results
Amp->'amp' expected 'amp'
Replit->'replit' expected 'replit'
Kimi->None expected 'moonshot'
DeepSeek->'deepseek' expected 'deepseek'
Qwen->None expected 'alibaba'
Mistral->'mistral' expected 'mistral'
Grok->None expected 'xai'
GLM->None expected 'zhipu'
Ollama->'ollama' expected 'ollama'
Llama->None expected 'meta'
```

This is not just a naming preference. It changes public behavior: a user who
follows the product-identity naming model documented by ADR-019 gets
`provider=None, provider_raw=<product name>`, which the privacy boundary
collapses into the reserved `Unrecognized` public bucket.

Suggested fix: add declaration-tier provider aliases for the product display
spellings, at minimum:

```python
"kimi": "moonshot",
"qwen": "alibaba",
"grok": "xai",
"glm": "zhipu",
"llama": "meta",
```

Then add a test that parses `AI-Provider: <display>` for all ten D3 display
names and asserts the canonical slug, not only `normalize_provider(slug)`.

## Review basis

Reviewed `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, the handoff brief,
`.ai/round_d3_provider_ecosystem_spec.md`, commit `d2c1147`'s body,
`docs/decisions/ADR-017-provider-brand-glyphs.md`,
`docs/decisions/ADR-019-two-tier-provider-vocabulary.md`, `docs/schema.md`,
`src/aiprofile/schema/vocab.py`, `src/aiprofile/registry.py`,
`src/aiprofile/adapters/trailers.py`, `src/aiprofile/scanner.py`,
`src/aiprofile/schema/event.py`, `src/aiprofile/aggregate.py`,
`src/aiprofile/privacy.py`, `src/aiprofile/viz.py`,
`src/aiprofile/render/brand.py`, `src/aiprofile/render/summary_svg.py`,
`scripts/vendor_brand_icons.py`, and the D3-adjacent tests.

## Verification evidence

Commands and observed results:

- `git status --short` before verification: clean.
- `git diff --stat ea5f37d..d2c1147`: 19 files changed, 2151 insertions, 527 deletions.
- `git diff --name-only ea5f37d..d2c1147`: `CHANGELOG.md`, social preview assets, summary sample assets, ADR-017, ADR-019, `docs/schema.md`, `scripts/vendor_brand_icons.py`, registry/vocab/render code, snapshots, and D3 unit tests.
- `python -m pytest tests -p no:cacheprovider`: `442 passed, 4 skipped in 23.69s` (exit 0). The run emitted unrelated global-environment warnings from `requests` and `langsmith`.
- `python -m ruff check src tests scripts`: `All checks passed!` (exit 0).
- `python -m pytest tests/unit/test_calendar_band.py tests/unit/test_render_summary.py tests/unit/test_brand.py tests/unit/test_vocab_registry.py -p no:cacheprovider`: `100 passed in 0.33s` (exit 0), with the same unrelated warnings.
- `python tests/unit/test_render_summary.py`: wrote 8 snapshot files and 2 sample assets; `git status --short` stayed clean.
- `python tests/unit/test_render_summary.py` again: wrote the same 8 snapshot files and 2 sample assets; targeted tests stayed green.
- `python scripts/vendor_brand_icons.py --help`: exit 0, CLI help rendered.
- `python -m pytest --collect-only -q | Select-String -Pattern 'vendor_brand_icons|scripts'`: no output, confirming the vendoring script is not collected by pytest.
- `Invoke-WebRequest` to `https://raw.githubusercontent.com/simple-icons/simple-icons/f7cc40071c00ca767e6f5532fb99bfbc25efb8fe/icons/mistralai.svg`: failed with `Unable to connect to the remote server`; upstream byte-diff could not be independently repeated under this sandbox's network restriction.

Independent two-tier isolation probe:

```text
coauthor_intersection {'amp'}
amp [('amp', 'amp')]
fabricated co-author emails for replit/moonshot/deepseek/alibaba/mistral/xai/zhipu/ollama/meta: zero specs
```

Independent slug-form declaration, aggregation, render, and privacy probe:

```text
slug amp [('amp', 'amp')]
slug replit [('replit', 'replit')]
slug moonshot [('moonshot', 'moonshot')]
slug deepseek [('deepseek', 'deepseek')]
slug alibaba [('alibaba', 'alibaba')]
slug mistral [('mistral', 'mistral')]
slug xai [('xai', 'xai')]
slug zhipu [('zhipu', 'zhipu')]
slug ollama [('ollama', 'ollama')]
slug meta [('meta', 'meta')]
local_details {'excluded_repositories': 0, 'unrecognized_provider_values': ['SECRET_VENDOR_CANARY']}
providers ['alibaba', 'amp', 'deepseek', 'meta', 'mistral', 'moonshot', 'ollama', 'replit', 'unrecognized', 'xai', 'zhipu']
svg_more_line True
canary_presence {'PRIVATE_REPO_CANARY': (False, False), 'C:/PRIVATE/PATH/CANARY': (False, False), 'SECRET_REPO_CANARY': (False, False), 'C:/SECRET/PATH/CANARY': (False, False), 'SECRET_VENDOR_CANARY': (False, False)}
legend ((1, '1'), (4, '2-4'), (7, '5-7'), (8, '8+'))
months ((4, 'Jun'), (8, 'Jul'))
```

Independent contrast recomputation:

```text
mistral light 3.07 dark 4.13 fg/tint #F04805/#F6E6DF #FA520F/#472315
replit light 3.15 dark 4.12 fg/tint #DE5A06/#F6E8DF #F26207/#472815
moonshot light 17.62 dark 3.16 fg/tint #000000/#EBEBEB #7A7A7A/#2E2E2E
deepseek light 3.16 dark 4.58 fg/tint #4377FE/#DFE6F6 #5786FE/#152347
```

## Verified areas without findings

- Adding declaration-tier aliases did not expand auto-match: `match_coauthor`
  only consults `COAUTHOR_IDENTITIES`, and the D3 intersection is exactly
  `{'amp'}`.
- `amp@ampcode.com` resolves to provider/tool `amp` / `amp`; fabricated
  co-author emails for the nine declaration-tier-only providers produced no
  specs.
- Slug-form declarations (`AI-Provider: moonshot`, etc.) parse, build ACE
  events, aggregate, enter `VizStats`, and serialize in public JSON.
- Public SVG/JSON omitted repository-name, path, and raw unrecognized-provider
  canaries; local-only details retained the raw unrecognized value.
- Calendar legend bins are derived from `CAL_CAP_COMMITS=8` as `1`, `2-4`,
  `5-7`, `8+`.
- Month labels are data-anchored from `stats.daily`; no clock read was found in
  the month-label path.
- Empty-daily rendering remains byte-stable across the sanctioned snapshot
  regeneration command.
- `scripts/vendor_brand_icons.py` is manually run, deterministic in structure,
  does not read environment secrets, and is outside pytest collection.
- ADR-019's six-tool-slug accounting is accurate: `amp`, `replit-agent`,
  `kimi-code`, `qwen-code`, `vibe-code`, and `ollama`.

## Severity summary

- Critical: 0
- High: 1
- Medium: 0
- Low: 0

## Final recommendation

NOT READY

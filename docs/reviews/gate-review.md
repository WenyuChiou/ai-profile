# Gate 16 display-alias resolution verification review

Date: 2026-07-23

Review range: `d2c1147..66bc3e9`

Reviewer posture: independent Principal Software Engineer; verification only.
No production code, test code, schema, or design code was changed during this
review. This report overwrites the prior gate review artifact per repository
convention.

## Executive summary

The gate-15 H-01 resolution is ready for the next gate. The fix derives
provider aliases from every schema-owned display name and adds the expected
manual spelling variants, closing both the D3 product-name gap and the latent
v0.1-era display-name bug for Claude/Gemini/Copilot/Devin.

Full suite and lint are clean. Independent probes confirmed the old
Kimi/Qwen/Grok/GLM/Llama failure now resolves, the v0.1-era names resolve, the
variant spellings resolve, pre-existing aliases did not change targets, and an
end-to-end `AI-Provider: Kimi` commit publishes as canonical `moonshot` with
display `Kimi` and the vendored Moonshot/Kimi mark while preserving the privacy
boundary.

## Findings

| Severity | Issue | Location |
|---|---|---|
| None | No correctness, privacy, rendering, or alias-regression findings in this range. | n/a |

## Review basis

Reviewed `README.md`, `CONTRIBUTING.md`, the handoff brief, `docs/schema.md`,
the `d2c1147..66bc3e9` diff, `src/aiprofile/registry.py`,
`src/aiprofile/schema/vocab.py`, `src/aiprofile/adapters/trailers.py`,
`src/aiprofile/privacy.py`, `src/aiprofile/render/brand.py`, and
`tests/unit/test_vocab_registry.py`.

## Verification evidence

Commands and observed results:

- `git status --short`: clean before verification.
- `git rev-parse HEAD`: `66bc3e957ea59be483dc2b4046c84c936797eec5`.
- `git diff --stat d2c1147..66bc3e9`: 4 files changed, 210 insertions, 82 deletions.
- `git diff --name-only d2c1147..66bc3e9`: `docs/reviews/gate-disposition.md`, `docs/reviews/gate-review.md`, `src/aiprofile/registry.py`, `tests/unit/test_vocab_registry.py`.
- `python -m pytest tests -p no:cacheprovider`: `444 passed, 4 skipped in 25.03s` (exit 0). The run emitted unrelated global-environment warnings from `requests` and `langsmith`.
- `python -m ruff check src tests`: `All checks passed!` (exit 0).

Independent alias and collision probe:

```text
direct_probe_count: 15
display_names_checked: 21
pre_existing_aliases_checked: 23
alias_collisions: {}
```

The direct probe covered the gate-15 adversarial product names
`Kimi`, `Qwen`, `Grok`, `GLM`, and `Llama`; the v0.1-era display names
`Claude`, `Gemini`, `Copilot`, and `Devin`; and the requested variants
`Mistral AI`, `Meta AI`, `x.ai`, `Z.ai`, `Moonshot AI`, and `Amazon Q`.
All normalized to the expected canonical slugs.

Independent end-to-end Kimi probe:

```text
e2e_provider: moonshot/Kimi
e2e_mark: BRAND[moonshot] path present in summary-light.svg
privacy_sweep: profile.json + light/dark SVG contained no repo/home/email/filename canaries
```

The synthetic repository contained one commit with:

```text
AI-Provider: Kimi
```

After `init -> scan --full -> aggregate -> render`, `profile.json` ranked the
single provider row as:

```json
{
  "provider": "moonshot",
  "display_name": "Kimi",
  "attributed_commits": 1,
  "actor_presences": 1,
  "active_days": 1
}
```

The same probe verified `provider_count == 1`, `ai_attributed_commits == 1`,
and the privacy split as one explicitly publishable commit with no anonymous
aggregate commits. The rendered light SVG contained the `Kimi` label and the
vendored `BRAND["moonshot"]` path fragment; public JSON/SVG outputs did not
contain repository path, home path, fixture email, or filename canaries.

## Verified areas without findings

- `PROVIDER_ALIASES.update({display.lower(): slug ...})` covers every
  schema-owned display name, so future display vocabulary additions cannot miss
  the alias table by omission.
- The manual variants add only new spellings; no pre-existing alias key changed
  canonical slug.
- `Amazon Q` is covered by display-name derivation, matching the implementation
  comment.
- The fix does not touch `COAUTHOR_IDENTITIES`; declaration-tier display
  aliases do not expand auto-match behavior.
- The existing VizStats privacy boundary and renderer brand path handle the new
  canonical result without special cases.

## Severity summary

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

## Final recommendation

READY FOR NEXT GATE

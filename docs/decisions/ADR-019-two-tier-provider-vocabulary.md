# ADR-019: Two-tier provider vocabulary (round D3)

Status: accepted (2026-07-23)

## Context

ADR-013 seeded `registry.py` from a single evidence bar: "registry seeds
come only from claims confirmed by the landscape verification lane"
(`docs/landscape.md` §2.1). That bar conflated two different questions
into one gate:

1. Can a *hand-written* `AI-Provider:`/`AI-Tool:` trailer for this
   provider resolve to a canonical slug at all (declaration)?
2. Can this repo *automatically* attribute a commit to this provider from
   a co-author email alone, with no human declaration (auto-match)?

Round D3's planning research (Codex co-planning reply
`.ai/handoff/007_d3_provider_ecosystem_planning.to_fable.md`) surveyed
ten additional AI coding ecosystems — Amp, Replit Agent, Moonshot/Kimi,
DeepSeek, Alibaba/Qwen, Mistral, xAI/Grok, Zhipu/GLM, Ollama, Meta/Llama
— against the single ADR-013 bar and found only one (Amp) meets it:
Amp's official manual documents `amp.git.commit.coauthor.enabled`
defaulting to true and adding `Co-authored-by: Amp <amp@ampcode.com>` to
agent commits (<https://ampcode.com/manual>). The other nine are real,
material coding-tool/model ecosystems with WEAK-or-NONE evidence for a
*stable git attribution string* under the single bar (see the 007
reply's evidence-grading table for the per-provider citations), which
would have kept every hand-written `AI-Provider: DeepSeek` (etc.) trailer
from resolving — `provider_raw` would be preserved, but canonical
`provider` would stay `null` — purely because no repo has yet been
caught auto-emitting that string, not because a human declaring it is
untrustworthy.

## Decision

Split the single bar into two tiers, matching the two questions above:

- **DECLARATION tier** (`schema.vocab.CANONICAL_PROVIDERS` /
  `CANONICAL_TOOLS` membership + `PROVIDER_DISPLAY` entry +
  `registry.PROVIDER_ALIASES` / `TOOL_ALIASES` entries + a `brand.py`
  mark or letter-tile fallback): accepts a provider once it is a real,
  identifiable AI coding ecosystem, so a human's explicit
  `AI-Provider:`/`AI-Tool:` trailer for it normalizes to a canonical slug
  and renders with a display name and brand mark. This tier carries NO
  claim that the provider's tooling auto-attributes its own commits.
- **AUTO-MATCH tier** (`registry.COAUTHOR_IDENTITIES`): unchanged,
  strictly evidence-gated exactly as ADR-013 specified — a commit is
  attributed to this provider from a `Co-authored-by:` email alone, with
  no human declaration, only when an official source documents a stable
  co-author identity or noreply address.

Every provider in the auto-match tier is necessarily also in the
declaration tier (you cannot auto-match into a slug that is not
canonical), but not every declaration-tier provider needs an auto-match
identity. Declaration-tier membership is explicitly **not** a claim that
the named provider auto-attributes its own commits — it is only a claim
that this repo recognizes the name.

### Owner rulings on the five open questions (007 reply, "Risks and open
questions for owner")

1. **Backend-model providers (DeepSeek/Ollama/Meta):** YES in the
   vocabulary (declaration tier) — a user who explicitly writes
   `AI-Provider: DeepSeek` after using it as a backend model behind
   another tool is making a legible, honest declaration; the two-tier
   split is exactly what makes this safe (no auto-match is implied). NO
   auto-match tier for any of the three.
2. **Replit:** vocabulary entry + tool slug `replit-agent` (Replit's own
   docs confirm Agent Checkpoints create automatic Git commits stored in
   Git: <https://docs.replit.com/learn/projects-and-artifacts/version-control>).
   NO co-author identity until a stable one is documented — the 007
   research found strong evidence for "creates commits" but no stable
   trailer/co-author string to auto-match on.
3. **Amp:** its own provider slug `amp` (not folded under `sourcegraph`)
   — the public attribution string Amp's own tooling emits is `Amp`
   itself, matching the existing product-identity precedent (see ruling
   4) rather than the parent company name.
4. **Display names follow PRODUCT identity**, continuing the existing
   `google` -> `Gemini` precedent: `moonshot` -> `Kimi`, `alibaba` ->
   `Qwen`, `xai` -> `Grok`, `zhipu` -> `GLM`. Schema *slugs* stay
   provider/company-oriented (`moonshot`, not `kimi`); only the
   PUBLIC display name follows the product name users actually
   recognize.
5. **Icon extraction:** a new mechanical script,
   `scripts/vendor_brand_icons.py`, extracts brand data from a pinned
   simple-icons commit (title/slug/hex/path) and emits `BrandSpec` stubs
   plus a WCAG contrast report, rather than hand-typing path data (the
   007 reply's own open question 5, and the failure mode ADR-017 already
   guards against: no hand-drawn marks, ever). Scoped to a follow-up
   round's file set, not this one.

### Evidence summary (citing the 007 reply's links)

| slug | display | tier(s) | evidence | citation |
|---|---|---|---|---|
| `amp` | Amp | declaration + auto-match | STRONG: official co-author trailer, on by default | <https://ampcode.com/manual> |
| `replit` | Replit | declaration | STRONG for automatic Git commits, no stable co-author id | <https://docs.replit.com/learn/projects-and-artifacts/version-control> |
| `moonshot` | Kimi | declaration | WEAK: coding CLI/IDE tool, no attribution signal | <https://www.kimi.com/code/docs/en/> |
| `deepseek` | DeepSeek | declaration | NONE for auto-match: backend-model API, not a git-attributing tool | <https://api-docs.deepseek.com/guides/function_calling/> |
| `alibaba` | Qwen | declaration | WEAK: commit-message generation is not attribution | <https://qwenlm.github.io/qwen-code-docs/en/users/features/commands/> |
| `mistral` | Mistral | declaration | WEAK: Vibe Code can read/write files and open PRs, no co-author id | <https://docs.mistral.ai/vibe/code/overview> |
| `xai` | Grok | declaration | WEAK: coding agent/model, no attribution signal | <https://docs.x.ai/developers/models/grok-code-fast-1> |
| `zhipu` | GLM | declaration | WEAK: coding-agent use, no official attribution signal found | (007 reply, no single authoritative URL) |
| `ollama` | Ollama | declaration | NONE for auto-match: local model runtime, not a git-attributing actor | (007 reply) |
| `meta` | Llama | declaration | NONE for auto-match: Code Llama is a coding model, not a git-attributing tool | <https://ai.meta.com/blog/code-llama-large-language-model-coding/> |

## Consequences

- `PROVIDER_ALIASES`/`TOOL_ALIASES` (declaration tier) grow by ten
  providers and six new tool slugs (`amp`, `replit-agent`, `kimi-code`,
  `qwen-code`, `vibe-code`, `ollama` - the last being the only tool
  slug spelled identically to its provider slug; `deepseek`/`xai`/
  `zhipu`/`meta` add no tool slug per the spec table) so their trailers
  resolve; `COAUTHOR_IDENTITIES`
  (auto-match tier) grows by exactly one (`amp@ampcode.com`).
  `tests/unit/test_vocab_registry.py` pins both: every new slug resolves
  a display name, `amp` auto-matches via `match_coauthor`, and a
  declaration-tier slug with no registry identity (e.g. `deepseek`) does
  not auto-match any co-author email.
- `render/brand.py`'s hand-mirrored `_CANONICAL_PROVIDERS_MIRROR`
  (ADR-017's isolation workaround) is temporarily stale-by-subset the
  moment `CANONICAL_PROVIDERS` grows — harmless on its own (the mirror
  only asserts `BRAND` keys are a *subset* of it), but
  `tests/unit/test_brand.py`'s mirror-vs-real-vocab cross-check would
  fail without a matching literal update. Per this round's spec-approved
  resolution, that one literal in `brand.py` is updated alongside this
  ADR; no new `BrandSpec` marks are added here (that is round D3's icon
  lane, script-driven per ruling 5).
- `docs/schema.md` §10's inline provider/tool enumeration (the schema's
  own duplicate of the vocab, kept for human readability) is updated in
  the same commit so it does not silently drift from `vocab.py`.
- The ADR-013 "seeded only from landscape-verified claims" sentence now
  describes the auto-match tier specifically; the declaration tier has
  its own, deliberately lower bar (a real, identifiable ecosystem) that
  this ADR — not ADR-013 — owns going forward. A future provider that
  clears only "real ecosystem" joins the declaration tier by editing
  `vocab.py` + `registry.py` aliases + this evidence table; clearing the
  auto-match bar additionally needs a `COAUTHOR_IDENTITIES` entry cited
  to a primary source, unchanged from ADR-013.

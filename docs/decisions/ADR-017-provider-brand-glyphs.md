# ADR-017: Provider brand identity glyphs (round D1)

Status: accepted (2026-07-22)

## Context

The summary card's provider table (`render/summary_svg.py`, ADR-010) drew
every row with the same square commit-node mark and a uniform accent bar —
correct and accessible, but generic: nothing in the card visually
distinguished "Claude" from "OpenAI" from "Amazon Q" beyond the text label.
Owner direction for round D1 (`.ai/round_d1_brand_identity_spec.md`) was to
add recognizability — provider logos and per-provider identity — while
keeping every hard invariant this repo already enforces: `VizStats`
untouched, deterministic static data only, zero runtime dependencies, no
network at render time, ASCII-only new string constants, and the renderer
consuming theme/brand tokens rather than hard-coded colors.

This ADR narrows one clause of ADR-010 ("Icons are pure inline geometry ...
never provider logos or emoji") to the **header** commit-node mark only.
Provider *rows* now carry real vendored brand marks per this decision; the
header glyph is unchanged.

## Decision

### Vendored glyph table: `src/aiprofile/render/brand.py`

- `BRAND: dict[slug, BrandSpec]`, `BrandSpec` a frozen dataclass:
  `path` (single 24x24-viewBox SVG path string), `light_fg`, `light_tint`,
  `dark_fg`, `dark_tint` (flat hex literals — no runtime alpha, no
  gradients, never the brand's own multi-color treatment).
- `assert set(BRAND) <= CANONICAL_PROVIDERS` at import time. Because
  `render/*` may not import `aiprofile.schema` (architecture.md section 2
  — enforced by both a runtime module-graph probe and a static AST sweep,
  `tests/unit/test_dependency_isolation.py`), the assertion runs against a
  hand-mirrored local copy, `_CANONICAL_PROVIDERS_MIRROR`.
  `tests/unit/test_brand.py` (not subject to the isolation boundary) cross-
  checks that mirror — and `summary_svg.py`'s own
  `_UNRECOGNIZED_PROVIDER` mirror — against the real schema constants, so
  drift between the render-layer copies and the schema fails a test
  instead of silently going stale.

### Source, license, and provenance (recorded verbatim from the vendor stage)

Source: [simple-icons](https://github.com/simple-icons/simple-icons),
package version 16.27.0, commit
`f7cc40071c00ca767e6f5532fb99bfbc25efb8fe` on `master` (consulted
2026-07-22 via the public raw.githubusercontent.com mirror and the GitHub
REST API — no network access happens at render time or at any other point
in this repo's code paths; `brand.py` is the vendored, static result of
that one-time lookup, committed like any other source file).

License: **CC0-1.0** (Creative Commons Zero v1.0 Universal), verified by
reading `LICENSE.md` at that commit — a public-domain dedication, so no
permission is required to vendor the path data verbatim. Attribution is
recorded in `brand.py`'s module docstring anyway as good practice, matching
the round D1 spec's requirement.

### Nominative-use rationale

Each vendored mark is used only to visually identify the provider or tool
whose AI activity a row/tile represents — never to imply that Anthropic,
Google, GitHub, Cursor, or Windsurf endorses `aiprofile` or any particular
generated card. Path geometry is vendored verbatim (no redrawing, no
simplification); only the fill color is recolored per theme as one of four
precomputed flat hexes per provider — never a runtime blend, never the
brand's own multi-color treatment where one exists.

### Slug -> mark mapping

Follows the card's **public display identity**
(`schema.vocab.PROVIDER_DISPLAY`), per the spec's instruction to vendor the
mark users actually recognize rather than the upstream company name:

| canonical slug | `PROVIDER_DISPLAY` | simple-icons title | `icons/` slug |
|---|---|---|---|
| `anthropic` | "Claude" | "Claude" | `claude` |
| `google` | "Gemini" | "Google Gemini" | `googlegemini` |
| `github` | "Copilot" | "GitHub Copilot" | `githubcopilot` |
| `cursor` | "Cursor" | "Cursor" | `cursor` |
| `windsurf` | "Windsurf" | "Windsurf" | `windsurf` |

### Fallback policy (first-class, not an afterthought)

`PROVIDER_DISPLAY` currently has eleven entries; only five have a vendored
mark. The other six — `openai`, `amazon`, `aider`, `roo-code`, `openhands`,
`cognition` — have **no reliable simple-icons mark** as of the commit
above. This was verified, not assumed: an exact/near-title search against
the full upstream data set (`data/simple-icons.json`) plus direct 404
probes against the `icons/` directory for the obvious slug candidates
(`openai`, `chatgpt`, `gpt`, `amazonq`, `amazonwebservices`, `aws`,
`devin`, `cognition`, `cognitionlabs`, `aider`, `roocode`, `rooai`,
`openhands`, `opendevin`) — every candidate 404'd. simple-icons appears to
have never carried an OpenAI- or Amazon-family mark, and has nothing for
Aider, Roo Code, OpenHands, or Devin/Cognition either.

These six, and the reserved `unrecognized` bucket row, render through a
**neutral letter-tile fallback** instead of an invented or approximated
glyph:

- Tile fill: `theme.chip_bg` (the same token the evidence panel uses for
  its neutral surface — never a brand-tinted color, since there is no
  brand to tint towards).
- Glyph: the first letter of the row's display name, uppercase, 11px,
  weight 600, centered, fill `theme.muted` — or `"?"` for the
  `unrecognized` bucket specifically (it has no display-name letter that
  would mean anything).
- Bar fill for a fallback row: `theme.bar_fill` (the existing card-wide
  blue) — unchanged from pre-D1 behavior, since there is no brand color to
  promote it to.

A provider gaining a real mark later is a `brand.py` diff only (add a
`BrandSpec` entry) — `summary_svg.py` requires no change, since branded vs.
fallback is decided per-row from `BRAND.get(row.provider)`.

### Provider row lockup (`summary_svg.py`)

- A 20x20, `rx=4` glyph tile sits at `x=24` (the row's old name start),
  vertically centered in the 28px row. Tile fill: brand `tint` (branded)
  or `theme.chip_bg` (fallback).
- The glyph itself draws at 14x14, centered inside the tile, via
  `<path d="..." fill="{fg}" transform="translate(gx,gy) scale(14/24)"/>`
  — a plain static transform on vendored path data, not a template engine
  and not `svgwrite` (ADR-010's constraint continues to apply: pure string
  composition).
- The provider name shifts from `x=24` to `x=52` (tile + 8px gap);
  `NAME_WIDTH` shrinks from 150 to 122 (the same 28px the name moved).
  `BAR_X`, `COUNT_X`, and `ROW_HEIGHT` are unchanged — minimal geometry
  churn, per the spec.
- Bar fill for a **branded** row is the brand FG hex for the active theme
  (replacing the uniform `theme.bar_fill`, provider rows only). The hero
  metric, share bar, and evidence ramp keep the existing blue — structural
  color stays separate from brand color, exactly as the spec requires.
- `<path>` joined the SVG security allowlist
  (`tests/unit/test_render_summary.py::_ALLOWED_SVG_TAGS`) alongside
  `rect`/`line`/`text`/`tspan`/`polygon` — still governed by the same
  checks: no `on*` handlers, no `href`, no external references, no
  `<script>`, no `foreignObject`.

### Contrast

Every `(fg, tint)` pair clears **3:1** against its own tint, in both
themes (the evidence-ramp precedent, gate-7 L-01) — verified in
`tests/unit/test_brand.py` by computing WCAG relative-luminance contrast
ratios over every `BrandSpec`, not by eyeballing hex values. The three
monochrome-branded marks (GitHub Copilot, Cursor, Windsurf all ship an
official hex at or near `#000000`) and Anthropic's mid-lightness orange
(which fell just under 3:1 against its own light-theme pastel) needed a
same-hue, contrast-adjusted shade instead of the literal brand hex — the
standard treatment for a monochrome mark on a dark surface is to lighten
it, which is what `dark_fg` does for all three. `light_fg` for those three
is a same-hue darkened shade for the same reason on a light tint.
Windsurf's `light_fg` is the exception that proves the rule: its literal
near-black brand hex (`#0B100F`, a near-black with a faint teal cast) is
already dark enough to clear 3:1 on any light pastel, so it is kept
verbatim there.

The tint itself must also be **distinguishable from the theme card
background** (spec requirement) — checked separately in
`tests/unit/test_brand.py` (not folded into the 3:1 check, since a subtle
pastel wash against a white/near-black card is a different, much lower
bar than a foreground mark against its own tile).

## Consequences

- The provider table is now visually scannable by brand at a glance for
  the five vendored providers; the other six (and the Unrecognized bucket)
  keep a clean, honest neutral tile rather than a fabricated glyph.
- `brand.py` adds one new file to the render package's dependency graph;
  `summary_svg.py` now imports it (`from .render.brand import BRAND,
  BrandSpec`) — permitted under architecture.md section 2's `render →`
  edge (a sibling render-package module, not a schema/storage/gitio
  import), and covered by the same isolation tests as every other
  `render/*` file (both discover files by globbing the package directory,
  not a hard-coded list).
- Adding a provider's mark later touches only `brand.py` (one new
  `BrandSpec` entry, contrast-checked by the existing test) — no
  `summary_svg.py` change, no schema change, no ADR bump required unless
  the *mapping policy itself* changes (e.g. switching which mark a slug
  maps to).
- **Non-goals** (explicit, per the spec): no remote fetching of icons at
  any time — everything is vendored at authoring time and committed like
  source; no per-user or per-repo theme customization of brand colors —
  the four hexes per provider are fixed, not configurable; no redrawing or
  simplifying of vendored path geometry — verbatim path data only; no
  glyphs invented for providers simple-icons does not carry — the letter
  fallback is permanent for those slugs until (if ever) a real mark
  appears upstream.

## D3 addendum: mechanical vendoring tool + eight declaration-tier marks

Status: accepted (2026-07-23), per `.ai/round_d3_provider_ecosystem_spec.md`
item 5 (owner ruling: "Icon extraction script: YES —
`scripts/vendor_brand_icons.py`, mechanical extraction from a pinned
simple-icons commit, emits `BrandSpec` stubs + WCAG contrast report; no
hand-typed path data").

### The vendoring tool

`scripts/vendor_brand_icons.py` is a standalone, manually-run release tool
(not pytest-collected — same discipline as `scripts/release_smoke.py`: it
lives outside `tests/`, the sole `testpaths` root). Given a pinned
simple-icons commit SHA and a repeatable `--map canonical-slug:icon-slug`
argument, it:

1. Fetches `data/simple-icons.json` (title → hex) and, per mapping entry,
   `icons/<icon-slug>.svg` from the public `raw.githubusercontent.com`
   mirror at the pinned ref only.
2. Extracts `<title>` and the sole `<path d="...">` mechanically (regex
   over the fetched SVG text — never hand-typed path data) and verifies
   exactly one `<path>` element; a 404 or a multi-path icon is **skipped
   and reported**, never faked with an approximated glyph.
3. Looks the brand hex up by exact `<title>` match against
   `data/simple-icons.json` (this simple-icons schema version carries no
   `slug` field, so title is the mechanical join key actually present in
   both documents).
4. Derives `(fg, tint)` per theme from the brand hex: the tint is a
   same-hue HSL wash of the brand color (high lightness for the light
   theme, low lightness for the dark theme, saturation capped so highly
   saturated brand hues don't produce a shouty chip); `fg` is the **literal
   brand hex** wherever it already clears WCAG ≥3:1 against that derived
   tint, otherwise a same-hue, lightness-walked shade (darkened toward the
   light tint, lightened toward the dark tint) is substituted via a fixed,
   deterministic step scan — the same "adjust a monochrome mark's fg, never
   the tint" treatment the D1 GitHub Copilot/Cursor/Windsurf entries used
   by hand.
5. Prints ready-to-paste `BrandSpec(...)` stubs plus a WCAG contrast table
   (fg-vs-tint ≥3:1, tint-vs-card ≥1.1, both themes) for every icon
   attempted.

Deterministic given the pinned ref: no random sampling, no hand-tuned
"looks nicer" adjustment — same ref + mapping always reproduces the same
stubs.

### Pinned ref and provenance

Source: simple-icons (https://github.com/simple-icons/simple-icons),
package version **16.27.0**, commit
`f7cc40071c00ca767e6f5532fb99bfbc25efb8fe` — verified as `master`'s current
HEAD via the GitHub REST API on 2026-07-23 (the planning reply's cited SHA,
`44a643f819e3c71aba635d15f132c33c5cc3d000`, does not match what `master`
actually resolves to at extraction time and was not used); this is the
*same* commit D1 already vendored from (`master` had not advanced between
the two lookups), so both rounds vendor from one consistent snapshot.
`package.json`'s `version` field at that commit reads `16.27.0`;
`LICENSE.md` at that commit is CC0-1.0, confirmed exactly as D1 recorded.

### Mapping and mechanical verification (all 8 present, single-path, at the pinned ref)

| canonical slug | `PROVIDER_DISPLAY` | simple-icons title | `icons/` slug | brand hex |
|---|---|---|---|---|
| `moonshot` | Kimi | "KIMI" | `kimi` | `#000000` |
| `deepseek` | DeepSeek | "DeepSeek" | `deepseek` | `#5786FE` |
| `alibaba` | Qwen | "QWen" | `qwen` | `#6950EF` |
| `mistral` | Mistral | "Mistral AI" | `mistralai` | `#FA520F` |
| `ollama` | Ollama | "Ollama" | `ollama` | `#000000` |
| `replit` | Replit | "Replit" | `replit` | `#F26207` |
| `zhipu` | GLM | "Z.ai" | `zdotai` | `#2D2D2D` |
| `meta` | Llama | "Meta AI" | `metaai` | `#9844FF` |

Every one of the 8 mapped icons existed at the pinned ref and carried
exactly one `<path>` element — no skips this round. Post-write
verification (the D1 discipline: never trust the paste, diff it): each
`BrandSpec.path` string committed to `brand.py` was independently
byte-diffed against a fresh fetch of `icons/<slug>.svg` at the pinned ref
after pasting — all 8 are byte-identical to upstream.

`amp` and `xai` (also declaration-tier per ADR-019) get **no** `BrandSpec`
entry — not a vendoring failure, an explicit owner ruling
(`round_d3_provider_ecosystem_spec.md`: "NO icons exist for amp / xai →
letter tiles (never hand-draw)"); simple-icons was never probed for them,
since the spec states up front no mark exists. Both render through the
existing D1 letter-tile fallback path (`BRAND.get(row.provider)` returns
`None`, `summary_svg.py` requires no change) — pinned by
`tests/unit/test_brand.py::test_round_d3_amp_and_xai_have_no_mark_by_owner_ruling`.

### Color derivation and WCAG contrast (D3 run)

Same rule as D1 (§ "Contrast" above), computed mechanically rather than by
hand this round. `moonshot` and `ollama` both carry the official brand hex
`#000000` (monochrome, like D1's GitHub Copilot/Cursor/Windsurf): the
literal hex is kept for `light_fg` (`#000000` on a light pastel clears
3:1 with enormous headroom — 17.62:1 measured), and a lightness-walked
same-hue (achromatic) shade (`#7A7A7A`) is substituted for `dark_fg`,
exactly the "lighten a monochrome mark for the dark surface" treatment D1
established. `zhipu`'s `#2D2D2D` is dark but not pure black; its
`light_fg` clears at the literal hex (11.55:1) and its `dark_fg` needed the
same lightening treatment. The other five providers' brand hexes cleared
3:1 on both derived tints without adjustment and are kept literal in all
four fields. Full measured ratios (script output, reproduced verbatim):

```
slug       theme  fg-vs-tint  tint-vs-card  fg       tint
-------------------------------------------------------------
alibaba    light        4.04          1.30  #6950EF  #E3DFF6   OK
alibaba    dark         3.19          1.13  #6950EF  #1D1547   OK
deepseek   light        3.16          1.25  #4377FE  #DFE6F6   OK
deepseek   dark         4.58          1.23  #5786FE  #152347   OK
meta       light        3.55          1.28  #9844FF  #E9DFF6   OK
meta       dark         3.54          1.17  #9844FF  #2B1547   OK
mistral    light        3.07          1.21  #F04805  #F6E6DF   OK
mistral    dark         4.13          1.37  #FA520F  #472315   OK
moonshot   light       17.62          1.19  #000000  #EBEBEB   OK
moonshot   dark         3.16          1.39  #7A7A7A  #2E2E2E   OK
ollama     light       17.62          1.19  #000000  #EBEBEB   OK
ollama     dark         3.16          1.39  #7A7A7A  #2E2E2E   OK
replit     light        3.15          1.20  #DE5A06  #F6E8DF   OK
replit     dark         4.12          1.43  #F26207  #472815   OK
zhipu      light       11.55          1.19  #2D2D2D  #EBEBEB   OK
zhipu      dark         3.16          1.39  #7A7A7A  #2E2E2E   OK
```

`tests/unit/test_brand.py`'s existing parametrized contrast tests
(`test_brand_fg_meets_3_to_1_contrast_against_its_own_tint`,
`test_brand_tint_distinguishable_from_theme_card_background`) iterate
`BRAND.items()` generically, so they picked up all 8 new entries without
any test edit; two new tests were added only to pin the round's two
provenance decisions themselves (which slugs got vendored, which two were
deliberately skipped) against future silent drift.

### Consequences (D3)

- `BRAND` grows from 5 to 13 entries; `brand.py`'s
  `_CANONICAL_PROVIDERS_MIRROR` already carried all 21 D3-round canonical
  slugs (landed with the vocabulary change, ADR-019) and needed no further
  edit for this pass — only the `BRAND` dict and module docstring changed.
- No `summary_svg.py` change (per the original ADR's stated consequence:
  adding a mark is a `brand.py`-only diff).
- `scripts/vendor_brand_icons.py` is now the sanctioned path for any future
  vendoring pass — a maintainer should never hand-type path data or
  hand-pick fg/tint hexes again; if a provider gains a mark later, run the
  script against a freshly pinned ref and paste its output.

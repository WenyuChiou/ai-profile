"""Vendored provider brand glyph data (round D1 brand identity spec,
``.ai/round_d1_brand_identity_spec.md``; ADR-017 records the decision).
Round D3 (``.ai/round_d3_provider_ecosystem_spec.md``) adds eight more
declaration-tier marks via the mechanical vendoring tool
``scripts/vendor_brand_icons.py``; ADR-017's D3 addendum records that pass.

Source: simple-icons (https://github.com/simple-icons/simple-icons),
package version 16.27.0, commit f7cc40071c00ca767e6f5532fb99bfbc25efb8fe on
``master`` (consulted 2026-07-22 for round D1 and re-verified unchanged at
2026-07-23 for round D3 - `master` had not advanced between the two
lookups - via the public raw.githubusercontent.com mirror and the GitHub
REST API; no network access happens at render time; this module is the
vendored, static result of those lookups).
License: CC0-1.0 (Creative Commons Zero v1.0 Universal), verified by
reading ``LICENSE.md`` at that commit - a public-domain dedication, so no
permission is required to vendor the path data verbatim. Attribution is
recorded here anyway as good practice, matching the spec's requirement.

Icon names used (exact "title" field in simple-icons' data set) mapped to
the CARD's public display identity (schema.vocab.PROVIDER_DISPLAY), per
the spec's instruction to vendor the mark users actually recognize:

    canonical slug   PROVIDER_DISPLAY   simple-icons title   icons/ slug
    ---------------  -----------------  --------------------  -----------
    anthropic        "Claude"           "Claude"               claude
    google            "Gemini"          "Google Gemini"        googlegemini
    github            "Copilot"         "GitHub Copilot"       githubcopilot
    cursor            "Cursor"          "Cursor"               cursor
    windsurf          "Windsurf"        "Windsurf"             windsurf
    moonshot          "Kimi"            "KIMI"                 kimi
    deepseek          "DeepSeek"        "DeepSeek"              deepseek
    alibaba           "Qwen"            "QWen"                  qwen
    mistral           "Mistral"         "Mistral AI"            mistralai
    ollama            "Ollama"          "Ollama"                ollama
    replit            "Replit"          "Replit"                replit
    zhipu             "GLM"             "Z.ai"                  zdotai
    meta              "Llama"           "Meta AI"               metaai

Nominative-use rationale: each mark is used only to visually identify the
provider or tool whose AI activity a row/tile represents - never to imply
that Anthropic, Google, GitHub, Cursor, Windsurf, Moonshot, DeepSeek,
Alibaba, Mistral, Ollama, Replit, Z.ai, or Meta endorses aiprofile or any
particular generated card. Path geometry is vendored verbatim (no
redrawing); only the fill color is recolored per theme, as flat precomputed
hexes (see below) - never the brand's own multi-color treatment where it
has one, and never a runtime blend.

Providers with NO reliable simple-icons mark as of the commit above -
checked by exact/near title match against the full upstream data set
(data/simple-icons.json) plus direct 404 probes against the icons/
directory for the obvious slug candidates (openai, chatgpt, gpt, amazonq,
amazonwebservices, aws, devin, cognition, cognitionlabs, aider, roocode,
rooai, openhands, opendevin - every one 404'd; simple-icons appears to have
never carried OpenAI- or Amazon-family marks, and has nothing for Aider,
Roo Code, OpenHands, or Devin/Cognition either): openai, amazon, aider,
roo-code, openhands, cognition. Round D3 adds two more to this honest-
fallback list on the owner's explicit ruling, not a vendoring failure: amp
and xai have no simple-icons mark at all (never probed as slug candidates
by ``vendor_brand_icons.py`` - the round D3 spec calls them out by name as
letter-tile-only). These eight (six from D1, two from D3) render via the
neutral letter-tile fallback in summary_svg.py (theme.chip_bg +
theme.muted, first letter of PROVIDER_DISPLAY), never an invented glyph -
see ADR-017's fallback policy.

Color derivation (every pair WCAG-contrast-verified in the round D1 design
session; ratios recorded in the round's handoff reply, not duplicated as a
runtime dependency here): for each provider, ``light_tint``/``dark_tint``
are a flat pastel / deep-muted rendition of the brand hue (HSL-derived,
same hue as the source hex, high lightness for light-theme tint, low
lightness for dark-theme tint) - never the brand hex verbatim, since the
brand hex is tuned to look right on a plain white/black background, not as
a tinted chip fill. ``light_fg``/``dark_fg`` are the brand hex itself where
it already clears >=3:1 against that theme's tint; where it does not
(monochrome near-black brand marks - GitHub Copilot, Cursor, Windsurf all
ship an official hex of #000000 or near-black, which fails 3:1 against any
tint dark enough to read as "dark theme" - and Anthropic's mid-lightness
orange fell just under 3:1 against its own light-theme pastel), a
same-hue, contrast-adjusted shade is used instead (the standard treatment
for a monochrome mark on a dark surface is to lighten it, which is what
happens here). No alpha, no runtime blending - every value below is a flat
hex literal.

Isolation note (architecture.md section 2,
tests/unit/test_dependency_isolation.py): ``aiprofile.render.*`` may not
import ``aiprofile.schema`` (or any other storage/registry/schema root) -
enforced by a static AST sweep over every file in this package, not just a
runtime check, so even a function-local import would fail it. The round D1
spec calls for `` assert set(BRAND) <= CANONICAL_PROVIDERS`` at import
time, but that identifier lives in ``aiprofile.schema.vocab`` and importing
it here would trip the isolation sweep. This module instead asserts BRAND's
keys against a local, hand-mirrored copy of that frozenset
(``_CANONICAL_PROVIDERS_MIRROR`` below) - a typo'd or stale BRAND key still
fails fast at import time, which is the assertion's actual purpose, but the
mirror can drift from the real ``CANONICAL_PROVIDERS`` if that enum ever
changes without a matching edit here. That drift is caught by
``tests/unit/test_brand.py`` (mirror == the real vocab constant, checked
from test code where the schema import is allowed), so a vocab change
without a matching edit here fails the suite rather than shipping.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrandSpec:
    """One vendored provider glyph: 24x24 viewBox path data plus the four
    per-theme flat hex colors used to render its tile (fg = glyph fill,
    tint = tile background)."""

    path: str
    light_fg: str
    light_tint: str
    dark_fg: str
    dark_tint: str


# Mirrors aiprofile.schema.vocab.CANONICAL_PROVIDERS verbatim (see the
# isolation note above for why this is a literal copy rather than an
# import). Keep in sync by hand if that frozenset ever changes.
_CANONICAL_PROVIDERS_MIRROR = frozenset(
    {
        "anthropic",
        "openai",
        "google",
        "github",
        "amazon",
        "cursor",
        "aider",
        "roo-code",
        "openhands",
        "windsurf",
        "cognition",
        "amp",
        "replit",
        "moonshot",
        "deepseek",
        "alibaba",
        "mistral",
        "xai",
        "zhipu",
        "ollama",
        "meta",
    }
)


BRAND: dict[str, BrandSpec] = {
    "anthropic": BrandSpec(
        path=(
            "m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.072"
            "9-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608"
            " 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.103"
            "2-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.007"
            "8.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.14"
            "57-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-."
            "0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4"
            "147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.7"
            "06.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.06"
            "68.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.651"
            "4-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.347"
            "8-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794"
            " 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.04"
            "25.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079."
            "4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 "
            "2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468"
            "-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-"
            ".6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156."
            "3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9"
            "004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.412"
            "8.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062"
            "-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9064-"
            "1.3114Z"
        ),
        light_fg="#B74C2A",
        light_tint="#F6E5DF",
        dark_fg="#E2A28D",
        dark_tint="#3C231B",
    ),
    "google": BrandSpec(
        path=(
            "M11.04 19.32Q12 21.51 12 24q0-2.49.93-4.68.96-2.19 2.58-3.81t3.81-2.55Q21.51 12 24"
            " 12q-2.49 0-4.68-.93a12.3 12.3 0 0 1-3.81-2.58 12.3 12.3 0 0 1-2.58-3.81Q12 2.49 1"
            "2 0q0 2.49-.96 4.68-.93 2.19-2.55 3.81a12.3 12.3 0 0 1-3.81 2.58Q2.49 12 0 12q2.49"
            " 0 4.68.96 2.19.93 3.81 2.55t2.55 3.81"
        ),
        # Literal official hex both themes (module rule: keep the brand
        # hex where it already clears 3:1 - it does: 3.22 on the light
        # tint, 3.88 on the dark tint).
        light_fg="#8E75B2",
        light_tint="#ECE6F4",
        dark_fg="#8E75B2",
        dark_tint="#2B203C",
    ),
    "github": BrandSpec(
        path=(
            "M23.922 16.997C23.061 18.492 18.063 22.02 12 22.02 5.937 22.02.939 18.492.078 16.9"
            "97A.641.641 0 0 1 0 16.741v-2.869a.883.883 0 0 1 .053-.22c.372-.935 1.347-2.292 2."
            "605-2.656.167-.429.414-1.055.644-1.517a10.098 10.098 0 0 1-.052-1.086c0-1.331.282-"
            "2.499 1.132-3.368.397-.406.89-.717 1.474-.952C7.255 2.937 9.248 1.98 11.978 1.98c2"
            ".731 0 4.767.957 6.166 2.093.584.235 1.077.546 1.474.952.85.869 1.132 2.037 1.132 "
            "3.368 0 .368-.014.733-.052 1.086.23.462.477 1.088.644 1.517 1.258.364 2.233 1.721 "
            "2.605 2.656a.841.841 0 0 1 .053.22v2.869a.641.641 0 0 1-.078.256Zm-11.75-5.992h-.3"
            "44a4.359 4.359 0 0 1-.355.508c-.77.947-1.918 1.492-3.508 1.492-1.725 0-2.989-.359-"
            "3.782-1.259a2.137 2.137 0 0 1-.085-.104L4 11.746v6.585c1.435.779 4.514 2.179 8 2.1"
            "79 3.486 0 6.565-1.4 8-2.179v-6.585l-.098-.104s-.033.045-.085.104c-.793.9-2.057 1."
            "259-3.782 1.259-1.59 0-2.738-.545-3.508-1.492a4.359 4.359 0 0 1-.355-.508Zm2.328 3"
            ".25c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1-.549 0-1-.451-1-1v-2c0-.549.451-1 1-1Zm-"
            "5 0c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1-.549 0-1-.451-1-1v-2c0-.549.451-1 1-1Zm3"
            ".313-6.185c.136 1.057.403 1.913.878 2.497.442.544 1.134.938 2.344.938 1.573 0 2.29"
            "2-.337 2.657-.751.384-.435.558-1.15.558-2.361 0-1.14-.243-1.847-.705-2.319-.477-.4"
            "88-1.319-.862-2.824-1.025-1.487-.161-2.192.138-2.533.529-.269.307-.437.808-.438 1."
            "578v.021c0 .265.021.562.063.893Zm-1.626 0c.042-.331.063-.628.063-.894v-.02c-.001-."
            "77-.169-1.271-.438-1.578-.341-.391-1.046-.69-2.533-.529-1.505.163-2.347.537-2.824 "
            "1.025-.462.472-.705 1.179-.705 2.319 0 1.211.175 1.926.558 2.361.365.414 1.084.751"
            " 2.657.751 1.21 0 1.902-.394 2.344-.938.475-.584.742-1.44.878-2.497Z"
        ),
        light_fg="#1B1F24",
        light_tint="#EEEFF1",
        dark_fg="#E3E5E8",
        dark_tint="#2E3138",
    ),
    "cursor": BrandSpec(
        path=(
            "M11.503.131 1.891 5.678a.84.84 0 0 0-.42.726v11.188c0 .3.162.575.42.724l9.609 5.55"
            "a1 1 0 0 0 .998 0l9.61-5.55a.84.84 0 0 0 .42-.724V6.404a.84.84 0 0 0-.42-.726L12.4"
            "97.131a1.01 1.01 0 0 0-.996 0M2.657 6.338h18.55c.263 0 .43.287.297.515L12.23 22.91"
            "8c-.062.107-.229.064-.229-.06V12.335a.59.59 0 0 0-.295-.51l-9.11-5.257c-.109-.063-"
            ".064-.23.061-.23"
        ),
        light_fg="#17171A",
        light_tint="#EEEDEC",
        dark_fg="#E7E6E4",
        dark_tint="#33302E",
    ),
    "windsurf": BrandSpec(
        path=(
            "M23.55 5.067c-1.2038-.002-2.1806.973-2.1806 2.1765v4.8676c0 .972-.8035 1.7594-1.75"
            "97 1.7594-.568 0-1.1352-.286-1.4718-.7659l-4.9713-7.1003c-.4125-.5896-1.0837-.941-"
            "1.8103-.941-1.1334 0-2.1533.9635-2.1533 2.153v4.8957c0 .972-.7969 1.7594-1.7596 1."
            "7594-.57 0-1.1363-.286-1.4728-.7658L.4076 5.1598C.2822 4.9798 0 5.0688 0 5.2882v4."
            "2452c0 .2147.0656.4228.1884.599l5.4748 7.8183c.3234.462.8006.8052 1.3509.9298 1.37"
            "71.313 2.6446-.747 2.6446-2.0977v-4.893c0-.972.7875-1.7593 1.7596-1.7593h.003a1.79"
            "8 1.798 0 0 1 1.4718.7658l4.9723 7.0994c.4135.5905 1.05.941 1.8093.941 1.1587 0 2."
            "1515-.9645 2.1515-2.153v-4.8948c0-.972.7875-1.7594 1.7596-1.7594h.194a.22.22 0 0 0"
            " .2204-.2202v-4.622a.22.22 0 0 0-.2203-.2203Z"
        ),
        light_fg="#0B100F",
        light_tint="#E3F2EF",
        dark_fg="#97D8CB",
        dark_tint="#1E3833",
    ),
    # --- Round D3 additions below (scripts/vendor_brand_icons.py output,
    # pinned ref f7cc40071c00ca767e6f5532fb99bfbc25efb8fe, pasted verbatim
    # from the script's printed stubs; contrast table reproduced in
    # ADR-017's D3 addendum) ---
    "alibaba": BrandSpec(
        path=(
            "M23.919 14.545 20.817 9.17l1.47-2.544a.56.56 0 0 0 0-.566l-1.633-2.83a.57.57 0 0 0"
            "-.49-.283h-6.207L12.487.402a.57.57 0 0 0-.49-.284H8.732a.56.56 0 0 0-.49.284L5.139"
            " 5.775h-2.94a.56.56 0 0 0-.49.284L.077 8.887a.56.56 0 0 0 0 .567L3.18 14.83l-1.47 "
            "2.545a.56.56 0 0 0 0 .566l1.634 2.83a.57.57 0 0 0 .49.283h6.205l1.47 2.545a.57.57 "
            "0 0 0 .49.284h3.266a.57.57 0 0 0 .49-.284l3.104-5.375h2.94a.57.57 0 0 0 .49-.283l1"
            ".634-2.828a.55.55 0 0 0-.004-.568M8.733.686l1.634 2.828-1.634 2.828H21.8L20.164 9."
            "17H7.425L5.63 6.06Zm1.306 19.801-6.205-.002 1.634-2.83h3.265L2.201 6.344h3.267q3.1"
            "82 5.517 6.367 11.032zm10.124-5.66L18.53 12l-6.532 11.315-1.634-2.83c2.129-3.673 4"
            ".25-7.351 6.373-11.028h3.592l3.102 5.374z"
        ),
        light_fg="#6950EF",
        light_tint="#E3DFF6",
        dark_fg="#6950EF",
        dark_tint="#1D1547",
    ),  # 'QWen' (icons/qwen.svg), brand #6950EF
    "deepseek": BrandSpec(
        path=(
            "M23.748 4.651c-.254-.124-.364.113-.512.233-.051.04-.094.09-.137.137-.372.397-.806."
            "657-1.373.626-.829-.046-1.537.214-2.163.848-.133-.782-.575-1.248-1.247-1.548-.352-"
            ".155-.708-.311-.955-.65-.172-.24-.219-.509-.305-.774-.055-.16-.11-.323-.293-.35-.2"
            "-.031-.278.136-.356.276-.313.572-.434 1.202-.422 1.84.027 1.436.633 2.58 1.838 3.3"
            "93.137.094.172.187.129.323-.082.28-.18.553-.266.833-.055.179-.137.218-.328.14a5.5 "
            "5.5 0 0 1-1.737-1.179c-.857-.828-1.631-1.743-2.597-2.46a12 12 0 0 0-.689-.47c-.985"
            "-.957.13-1.743.387-1.836.27-.098.094-.433-.778-.428-.872.003-1.67.295-2.687.685a3 "
            "3 0 0 1-.465.136 9.6 9.6 0 0 0-2.883-.101c-1.885.21-3.39 1.1-4.497 2.622C.082 8.77"
            "6-.231 10.854.152 13.02c.403 2.284 1.568 4.175 3.36 5.653 1.857 1.533 3.997 2.284 "
            "6.438 2.14 1.482-.085 3.132-.284 4.994-1.86.47.234.962.328 1.78.398.629.058 1.235-"
            ".031 1.705-.129.735-.155.684-.836.418-.961-2.155-1.004-1.682-.595-2.112-.926 1.095"
            "-1.295 2.768-3.598 3.284-6.733.05-.346.115-.834.108-1.114-.004-.171.035-.238.23-.2"
            "57a4.2 4.2 0 0 0 1.545-.475c1.397-.763 1.96-2.016 2.093-3.517.02-.23-.004-.467-.24"
            "7-.588M11.58 18.168c-2.088-1.642-3.101-2.183-3.52-2.16-.39.024-.32.472-.234.763.09"
            ".288.207.487.371.74.114.167.192.416-.113.603-.673.416-1.842-.14-1.897-.168-1.361-."
            "801-2.5-1.86-3.301-3.306-.775-1.393-1.225-2.888-1.299-4.482-.02-.385.094-.522.477-"
            ".592a4.7 4.7 0 0 1 1.53-.038c2.131.311 3.946 1.264 5.467 2.774.868.86 1.525 1.887 "
            "2.202 2.89.72 1.066 1.494 2.082 2.48 2.915.348.291.626.513.892.677-.802.09-2.14.10"
            "9-3.055-.615zm1.001-6.44a.306.306 0 0 1 .415-.287.3.3 0 0 1 .113.074.3.3 0 0 1 .08"
            "6.214c0 .17-.136.307-.308.307a.303.303 0 0 1-.306-.307m3.11 1.596c-.2.081-.4.151-."
            "591.16a1.25 1.25 0 0 1-.798-.254c-.274-.23-.47-.358-.551-.758a1.7 1.7 0 0 1 .015-."
            "588c.07-.327-.007-.537-.238-.727-.188-.156-.426-.199-.689-.199a.6.6 0 0 1-.254-.07"
            "8.253.253 0 0 1-.114-.358 1 1 0 0 1 .192-.21c.356-.202.767-.136 1.146.016.352.144."
            "618.408 1.001.782.392.451.462.576.685.915.176.264.336.536.446.848.066.194-.02.353-"
            ".25.45"
        ),
        light_fg="#4377FE",
        light_tint="#DFE6F6",
        dark_fg="#5786FE",
        dark_tint="#152347",
    ),  # 'DeepSeek' (icons/deepseek.svg), brand #5786FE
    "meta": BrandSpec(
        path=(
            "M10.73.032c-1.333 0-2.032 1.016-2.032 2.285 0 2.223 2.127 4.953 4.318 4.953 1.301 "
            "0 2-.953 2-2.254 0-2.254-2.095-4.984-4.286-4.984m8.413 2.984c-1.968 0-3.397 2.73-3"
            ".397 4.825 0 1.556.794 3.016 2.254 3.016 2 0 3.365-2.762 3.365-4.794 0-1.523-.762-"
            "3.047-2.222-3.047M4.857 4.159c-1.968 0-3.778 1.016-3.778 2.54 0 1.65 2.16 2.793 4."
            "254 2.793 1.873 0 3.778-.92 3.778-2.508 0-1.682-2.159-2.825-4.254-2.825m-.222 6.47"
            "6C2.413 10.635 0 13.175 0 15.397c0 1.301.825 2.159 2.095 2.159 2.19 0 4.603-2.508 "
            "4.603-4.794 0-1.27-.761-2.127-2.063-2.127m16.667.698c-2.223 0-5.016 1.62-5.016 3.6"
            "51 0 1.238 1.047 2.19 2.698 2.19 2.159 0 5.016-1.587 5.016-3.682 0-1.302-1.08-2.15"
            "9-2.698-2.159M7.619 16c-1.524 0-2.38 1.746-2.38 3.429 0 2.063 1.269 4.54 3.047 4.5"
            "4 1.524 0 2.38-1.81 2.38-3.461C10.667 18.57 9.46 16 7.62 16m6.571 1.016c-1.333 0-2"
            ".476.667-2.476 2.032 0 2.095 2.667 4.063 4.92 4.063 1.366 0 2.54-.73 2.54-2.063 0-"
            "2.032-2.698-4.032-4.984-4.032"
        ),
        light_fg="#9844FF",
        light_tint="#E9DFF6",
        dark_fg="#9844FF",
        dark_tint="#2B1547",
    ),  # 'Meta AI' (icons/metaai.svg), brand #9844FF
    "mistral": BrandSpec(
        path=(
            "M17.143 3.429v3.428h-3.429v3.429h-3.428V6.857H6.857V3.43H3.43v13.714H0v3.428h10.28"
            "6v-3.428H6.857v-3.429h3.429v3.429h3.429v-3.429h3.428v3.429h-3.428v3.428H24v-3.428h"
            "-3.43V3.429z"
        ),
        light_fg="#F04805",
        light_tint="#F6E6DF",
        dark_fg="#FA520F",
        dark_tint="#472315",
    ),  # 'Mistral AI' (icons/mistralai.svg), brand #FA520F
    "moonshot": BrandSpec(
        path=(
            "M21.765.351C22.998.351 24 1.353 24 2.586S22.998 4.82 21.765 4.82h-1.974c-.15 0-.26"
            "-.12-.26-.26V2.586A2.237 2.237 0 0 1 21.765.35M9.41 13.388l8.447-8.377c.16-.16.07-"
            ".471-.14-.471h-4.55s-.1.02-.14.06l-9.099 9.029c-.14.14-.35.02-.35-.21V4.81c0-.15-."
            "1-.27-.221-.27H.22c-.12 0-.22.12-.22.27v18.57c0 .15.1.27.22.27h3.137c.12 0 .22-.12"
            ".22-.27v-3.79c0-.08.03-.16.08-.21l2.826-2.796c.07-.07.16-.08.241-.03l7.546 5.551a8"
            ".9 8.9 0 0 0 4.018 1.493c.12.01.23-.11.23-.27V19.76c0-.14-.08-.25-.19-.26a5.8 5.8 "
            "0 0 1-2.355-.942l-6.533-4.73c-.14-.09-.15-.32-.03-.441"
        ),
        light_fg="#000000",
        light_tint="#EBEBEB",
        dark_fg="#7A7A7A",
        dark_tint="#2E2E2E",
    ),  # 'KIMI' (icons/kimi.svg), brand #000000
    "ollama": BrandSpec(
        path=(
            "M16.361 10.26a.894.894 0 0 0-.558.47l-.072.148.001.207c0 .193.004.217.059.353.076."
            "193.152.312.291.448.24.238.51.3.872.205a.86.86 0 0 0 .517-.436.752.752 0 0 0 .08-."
            "498c-.064-.453-.33-.782-.724-.897a1.06 1.06 0 0 0-.466 0zm-9.203.005c-.305.096-.53"
            "3.32-.65.639a1.187 1.187 0 0 0-.06.52c.057.309.31.59.598.667.362.095.632.033.872-."
            "205.14-.136.215-.255.291-.448.055-.136.059-.16.059-.353l.001-.207-.072-.148a.894.8"
            "94 0 0 0-.565-.472 1.02 1.02 0 0 0-.474.007Zm4.184 2c-.131.071-.223.25-.195.383.03"
            "1.143.157.288.353.407.105.063.112.072.117.136.004.038-.01.146-.029.243-.02.094-.03"
            "6.194-.036.222.002.074.07.195.143.253.064.052.076.054.255.059.164.005.198.001.264-"
            ".03.169-.082.212-.234.15-.525-.052-.243-.042-.28.087-.355.137-.08.281-.219.324-.31"
            "4a.365.365 0 0 0-.175-.48.394.394 0 0 0-.181-.033c-.126 0-.207.03-.355.124l-.085.0"
            "53-.053-.032c-.219-.13-.259-.145-.391-.143a.396.396 0 0 0-.193.032zm.39-2.195c-.37"
            "3.036-.475.05-.654.086-.291.06-.68.195-.951.328-.94.46-1.589 1.226-1.787 2.114-.04"
            ".176-.045.234-.045.53 0 .294.005.357.043.524.264 1.16 1.332 2.017 2.714 2.173.3.03"
            "3 1.596.033 1.896 0 1.11-.125 2.064-.727 2.493-1.571.114-.226.169-.372.22-.602.039"
            "-.167.044-.23.044-.523 0-.297-.005-.355-.045-.531-.288-1.29-1.539-2.304-3.072-2.49"
            "7a6.873 6.873 0 0 0-.855-.031zm.645.937a3.283 3.283 0 0 1 1.44.514c.223.148.537.45"
            "8.671.662.166.251.26.508.303.82.02.143.01.251-.043.482-.08.345-.332.705-.672.957a3"
            ".115 3.115 0 0 1-.689.348c-.382.122-.632.144-1.525.138-.582-.006-.686-.01-.853-.04"
            "2-.57-.107-1.022-.334-1.35-.68-.264-.28-.385-.535-.45-.946-.03-.192.025-.509.137-."
            "776.136-.326.488-.73.836-.963.403-.269.934-.46 1.422-.512.187-.02.586-.02.773-.002"
            "zm-5.503-11a1.653 1.653 0 0 0-.683.298C5.617.74 5.173 1.666 4.985 2.819c-.07.436-."
            "119 1.04-.119 1.503 0 .544.064 1.24.155 1.721.02.107.031.202.023.208a8.12 8.12 0 0"
            " 1-.187.152 5.324 5.324 0 0 0-.949 1.02 5.49 5.49 0 0 0-.94 2.339 6.625 6.625 0 0 "
            "0-.023 1.357c.091.78.325 1.438.727 2.04l.13.195-.037.064c-.269.452-.498 1.105-.605"
            " 1.732-.084.496-.095.629-.095 1.294 0 .67.009.803.088 1.266.095.555.288 1.143.503 "
            "1.534.071.128.243.393.264.407.007.003-.014.067-.046.141a7.405 7.405 0 0 0-.548 1.8"
            "73c-.062.417-.071.552-.071.991 0 .56.031.832.148 1.279L3.42 24h1.478l-.05-.091c-.2"
            "97-.552-.325-1.575-.068-2.597.117-.472.25-.819.498-1.296l.148-.29v-.177c0-.165-.00"
            "3-.184-.057-.293a.915.915 0 0 0-.194-.25 1.74 1.74 0 0 1-.385-.543c-.424-.92-.506-"
            "2.286-.208-3.451.124-.486.329-.918.544-1.154a.787.787 0 0 0 .223-.531c0-.195-.07-."
            "355-.224-.522a3.136 3.136 0 0 1-.817-1.729c-.14-.96.114-2.005.69-2.834.563-.814 1."
            "353-1.336 2.237-1.475.199-.033.57-.028.776.01.226.04.367.028.512-.041.179-.085.268"
            "-.19.374-.431.093-.215.165-.333.36-.576.234-.29.46-.489.822-.729.413-.27.884-.467 "
            "1.352-.561.17-.035.25-.04.569-.04.319 0 .398.005.569.04a4.07 4.07 0 0 1 1.914.997c"
            ".117.109.398.457.488.602.034.057.095.177.132.267.105.241.195.346.374.43.14.068.286"
            ".082.503.045.343-.058.607-.053.943.016 1.144.23 2.14 1.173 2.581 2.437.385 1.108.2"
            "76 2.267-.296 3.153-.097.15-.193.27-.333.419-.301.322-.301.722-.001 1.053.493.539."
            "801 1.866.708 3.036-.062.772-.26 1.463-.533 1.854a2.096 2.096 0 0 1-.224.258.916.9"
            "16 0 0 0-.194.25c-.054.109-.057.128-.057.293v.178l.148.29c.248.476.38.823.498 1.29"
            "5.253 1.008.231 2.01-.059 2.581a.845.845 0 0 0-.044.098c0 .006.329.009.732.009h.73"
            "l.02-.074.036-.134c.019-.076.057-.3.088-.516.029-.217.029-1.016 0-1.258-.11-.875-."
            "295-1.57-.597-2.226-.032-.074-.053-.138-.046-.141.008-.005.057-.074.108-.152.376-."
            "569.607-1.284.724-2.228.031-.26.031-1.378 0-1.628-.083-.645-.182-1.082-.348-1.525a"
            "6.083 6.083 0 0 0-.329-.7l-.038-.064.131-.194c.402-.604.636-1.262.727-2.04a6.625 6"
            ".625 0 0 0-.024-1.358 5.512 5.512 0 0 0-.939-2.339 5.325 5.325 0 0 0-.95-1.02 8.09"
            "7 8.097 0 0 1-.186-.152.692.692 0 0 1 .023-.208c.208-1.087.201-2.443-.017-3.503-.1"
            "9-.924-.535-1.658-.98-2.082-.354-.338-.716-.482-1.15-.455-.996.059-1.8 1.205-2.116"
            " 3.01a6.805 6.805 0 0 0-.097.726c0 .036-.007.066-.015.066a.96.96 0 0 1-.149-.078A4"
            ".857 4.857 0 0 0 12 3.03c-.832 0-1.687.243-2.456.698a.958.958 0 0 1-.148.078c-.008"
            " 0-.015-.03-.015-.066a6.71 6.71 0 0 0-.097-.725C8.997 1.392 8.337.319 7.46.048a2.0"
            "96 2.096 0 0 0-.585-.041Zm.293 1.402c.248.197.523.759.682 1.388.03.113.06.244.069."
            "292.007.047.026.152.041.233.067.365.098.76.102 1.24l.002.475-.12.175-.118.178h-.27"
            "8c-.324 0-.646.041-.954.124l-.238.06c-.033.007-.038-.003-.057-.144a8.438 8.438 0 0"
            " 1 .016-2.323c.124-.788.413-1.501.696-1.711.067-.05.079-.049.157.013zm9.825-.012c."
            "17.126.358.46.498.888.28.854.36 2.028.212 3.145-.019.14-.024.151-.057.144l-.238-.0"
            "6a3.693 3.693 0 0 0-.954-.124h-.278l-.119-.178-.119-.175.002-.474c.004-.669.066-1."
            "19.214-1.772.157-.623.434-1.185.68-1.382.078-.062.09-.063.159-.012z"
        ),
        light_fg="#000000",
        light_tint="#EBEBEB",
        dark_fg="#7A7A7A",
        dark_tint="#2E2E2E",
    ),  # 'Ollama' (icons/ollama.svg), brand #000000
    "replit": BrandSpec(
        path=(
            "M2 1.5A1.5 1.5 0 0 1 3.5 0h7A1.5 1.5 0 0 1 12 1.5V8H3.5A1.5 1.5 0 0 1 2 6.5ZM12 8h"
            "8.5A1.5 1.5 0 0 1 22 9.5v5a1.5 1.5 0 0 1-1.5 1.5H12ZM2 17.5A1.5 1.5 0 0 1 3.5 16H1"
            "2v6.5a1.5 1.5 0 0 1-1.5 1.5h-7A1.5 1.5 0 0 1 2 22.5Z"
        ),
        light_fg="#DE5A06",
        light_tint="#F6E8DF",
        dark_fg="#F26207",
        dark_tint="#472815",
    ),  # 'Replit' (icons/replit.svg), brand #F26207
    "zhipu": BrandSpec(
        path=(
            "M12.606 1.806l-1.677 2.388c-0.258 0.374-0.697 0.606-1.161 0.606h-9.162V1.794C0.594"
            " 1.806 12.606 1.806 12.606 1.806zM24 1.806L9.6 22.206 0 22.206 14.4 1.806zM11.394 "
            "22.206l1.69-2.4c0.258-0.374 0.697-0.606 1.161-0.606h9.149v3.006H11.394z"
        ),
        light_fg="#2D2D2D",
        light_tint="#EBEBEB",
        dark_fg="#7A7A7A",
        dark_tint="#2E2E2E",
    ),  # 'Z.ai' (icons/zdotai.svg), brand #2D2D2D
}

assert set(BRAND) <= _CANONICAL_PROVIDERS_MIRROR, (
    "BRAND keys must be a subset of the canonical provider slugs"
)

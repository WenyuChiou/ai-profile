"""Vendored provider brand glyph data (round D1 brand identity spec,
``.ai/round_d1_brand_identity_spec.md``; ADR-017 records the decision).

Source: simple-icons (https://github.com/simple-icons/simple-icons),
package version 16.27.0, commit f7cc40071c00ca767e6f5532fb99bfbc25efb8fe on
``master`` (consulted 2026-07-22 via the public raw.githubusercontent.com
mirror and the GitHub REST API - no network access happens at render time;
this module is the vendored, static result of that one-time lookup).
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

Nominative-use rationale: each mark is used only to visually identify the
provider or tool whose AI activity a row/tile represents - never to imply
that Anthropic, Google, GitHub, Cursor, or Windsurf endorses aiprofile or
any particular generated card. Path geometry is vendored verbatim (no
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
roo-code, openhands, cognition. These six render via the neutral
letter-tile fallback in summary_svg.py (theme.chip_bg + theme.muted, first
letter of PROVIDER_DISPLAY), never an invented glyph - see ADR-017's
fallback policy.

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
}

assert set(BRAND) <= _CANONICAL_PROVIDERS_MIRROR, (
    "BRAND keys must be a subset of the canonical provider slugs"
)

"""Unit tests for the vendored provider brand glyph table (round D1 brand
identity spec, ``.ai/round_d1_brand_identity_spec.md``; ADR-017).

Unlike ``aiprofile.render.*``, this test module is NOT subject to the
render-layer isolation boundary (architecture.md section 2) — it may import
``aiprofile.schema.vocab`` freely, which lets it close the exact drift risk
``brand.py`` and ``summary_svg.py`` flag in their own docstrings: the
hand-mirrored ``_CANONICAL_PROVIDERS_MIRROR`` / ``_UNRECOGNIZED_PROVIDER``
constants those render-layer modules carry (because they cannot import the
real schema constants) could silently go stale if the schema ever changes.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.render import summary_svg
from aiprofile.render.brand import _CANONICAL_PROVIDERS_MIRROR, BRAND
from aiprofile.render.summary_svg import render_summary
from aiprofile.render.themes import THEMES
from aiprofile.schema.vocab import (
    CANONICAL_PROVIDERS,
    PROVIDER_DISPLAY,
    UNRECOGNIZED_DISPLAY,
    UNRECOGNIZED_PROVIDER,
)
from aiprofile.viz import (
    V01_PERIOD_LABEL,
    EvidenceTotals,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
)

GENERATED_ON = "2026-07-22"


def _single_provider_stats(slug: str, display_name: str) -> VizStats:
    """Minimal valid VizStats carrying exactly one provider row - enough to
    drive the full row lockup (tile + name + bar + count) through
    render_summary for a single slug without pulling in an unrelated fixture."""
    provider_count = 0 if slug == UNRECOGNIZED_PROVIDER else 1
    return VizStats(
        schema_version=ACE_SCHEMA_VERSION,
        period=Period(from_date=None, to_date=None, label=V01_PERIOD_LABEL),
        totals=Totals(
            commits_scanned=10,
            ai_attributed_commits=10,
            ai_actor_presences=10,
            human_declared_commits=0,
            unknown_commits=0,
            active_ai_days=1,
        ),
        providers=(ProviderRow(slug, display_name, 10, 10, 1),),
        provider_count=provider_count,
        evidence=EvidenceTotals(
            verified=0, declared=10, imported=0, inferred=0, unknown=0, total_records=10
        ),
        privacy=PrivacySplit(
            explicitly_publishable_commits=10,
            anonymous_aggregate_commits=0,
            includes_anonymous_aggregate=False,
        ),
        generated_on=GENERATED_ON,
    )


# ---------------------------------------------------------------------------
# BRAND keys subset assertion (round D1 spec: "assert set(BRAND) <=
# CANONICAL_PROVIDERS at import time"). brand.py already self-asserts this
# against its hand-mirrored local copy at import time (it cannot import the
# real schema constant - isolation boundary); this test is the independent
# check against the REAL schema.vocab.CANONICAL_PROVIDERS.
# ---------------------------------------------------------------------------


def test_brand_keys_are_subset_of_real_canonical_providers():
    assert set(BRAND) <= CANONICAL_PROVIDERS


def test_brand_keys_are_subset_of_its_own_local_mirror():
    # Regression guard for the mirror itself (belt + suspenders): even if
    # the real schema constant drifted out from under the mirror, BRAND's
    # keys must still satisfy the assertion brand.py runs at import time.
    assert set(BRAND) <= _CANONICAL_PROVIDERS_MIRROR


def test_canonical_providers_mirror_matches_real_schema_constant():
    """Closes the exact drift risk brand.py's own docstring flags: its
    hand-mirrored _CANONICAL_PROVIDERS_MIRROR must stay byte-for-byte in
    sync with aiprofile.schema.vocab.CANONICAL_PROVIDERS. This test can only
    live here (not in brand.py itself) because only a non-render-layer
    module may import aiprofile.schema."""
    assert _CANONICAL_PROVIDERS_MIRROR == CANONICAL_PROVIDERS


def test_unrecognized_provider_mirror_matches_real_schema_constant():
    """Same drift guard for summary_svg._UNRECOGNIZED_PROVIDER (used to pick
    the "?" fallback letter for the reserved Unrecognized bucket row)."""
    assert summary_svg._UNRECOGNIZED_PROVIDER == UNRECOGNIZED_PROVIDER


# ---------------------------------------------------------------------------
# Every CANONICAL_PROVIDERS slug renders a provider row without error -
# glyph path for a BRAND slug, letter-tile fallback for everything else,
# including the reserved Unrecognized bucket.
# ---------------------------------------------------------------------------


def test_every_canonical_provider_slug_renders_without_error():
    for slug in sorted(CANONICAL_PROVIDERS):
        display_name = PROVIDER_DISPLAY[slug]
        stats = _single_provider_stats(slug, display_name)
        for theme in THEMES.values():
            svg = render_summary(stats, theme)
            root = ET.fromstring(svg)  # raises ParseError if the row broke the XML
            assert root.tag == f"{{{'http://www.w3.org/2000/svg'}}}svg"
            assert display_name in svg


def test_unrecognized_bucket_row_renders_without_error():
    stats = _single_provider_stats(UNRECOGNIZED_PROVIDER, UNRECOGNIZED_DISPLAY)
    for theme in THEMES.values():
        svg = render_summary(stats, theme)
        ET.fromstring(svg)
        assert UNRECOGNIZED_DISPLAY in svg


def test_branded_slugs_render_a_path_element_unbranded_slugs_do_not():
    for slug in sorted(CANONICAL_PROVIDERS):
        stats = _single_provider_stats(slug, PROVIDER_DISPLAY[slug])
        svg = render_summary(stats, THEMES["github-light"])
        if slug in BRAND:
            assert "<path " in svg, f"{slug}: expected a glyph <path>, found none"
        else:
            assert "<path " not in svg, f"{slug}: unexpected glyph <path> (no BRAND entry)"
            # Fallback letter tile: first letter of the display name, uppercase.
            expected_letter = PROVIDER_DISPLAY[slug][0].upper()
            assert f">{expected_letter}<" in svg


# ---------------------------------------------------------------------------
# WCAG contrast (round D1 spec: "every (fg, tint) pair must clear 3:1
# against its tint AND the tint must be distinguishable from the theme card
# bg"; gate-7 L-01 precedent in test_render_summary.py).
# ---------------------------------------------------------------------------


def _relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    channels = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(a: str, b: str) -> float:
    la, lb = sorted((_relative_luminance(a), _relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_brand_fg_meets_3_to_1_contrast_against_its_own_tint():
    for slug, spec in sorted(BRAND.items()):
        light_ratio = _contrast_ratio(spec.light_fg, spec.light_tint)
        assert light_ratio >= 3.0, (slug, "light", round(light_ratio, 3))
        dark_ratio = _contrast_ratio(spec.dark_fg, spec.dark_tint)
        assert dark_ratio >= 3.0, (slug, "dark", round(dark_ratio, 3))


def test_brand_tint_distinguishable_from_theme_card_background():
    # The tile tint is a subtle pastel/deep-muted wash, not a graphical
    # object requiring the full 3:1 bar - but it must still visibly read as
    # a tinted chip rather than disappearing into the card background.
    # 1.1 (a 10% luminance-contrast margin) is comfortably below every
    # measured pair (min observed ~1.15 at spec-authoring time) while still
    # catching a tint that was accidentally left equal to (or barely off)
    # the card bg.
    min_distinguishable_ratio = 1.1
    for slug, spec in sorted(BRAND.items()):
        light_bg = THEMES["github-light"].bg
        dark_bg = THEMES["github-dark"].bg
        assert spec.light_tint.lower() != light_bg.lower(), slug
        assert spec.dark_tint.lower() != dark_bg.lower(), slug
        light_ratio = _contrast_ratio(spec.light_tint, light_bg)
        assert light_ratio >= min_distinguishable_ratio, (slug, "light", round(light_ratio, 3))
        dark_ratio = _contrast_ratio(spec.dark_tint, dark_bg)
        assert dark_ratio >= min_distinguishable_ratio, (slug, "dark", round(dark_ratio, 3))


# ---------------------------------------------------------------------------
# Glyph path data sanity: single path per BrandSpec, ASCII, no character
# that would be forbidden or need escaping inside an XML attribute value
# (the renderer interpolates spec.path directly into a `d="..."` attribute
# - see summary_svg._glyph_tile_svg).
# ---------------------------------------------------------------------------


def test_glyph_path_data_is_single_ascii_and_xml_attr_safe():
    forbidden_attr_chars = ('"', "&", "<", ">", "\n", "\t", "\r")
    for slug, spec in sorted(BRAND.items()):
        path = spec.path
        assert isinstance(path, str) and path, slug
        assert path.isascii(), slug
        for ch in forbidden_attr_chars:
            assert ch not in path, (slug, repr(ch))
        # BrandSpec carries exactly one path string per provider (the
        # dataclass shape itself enforces "one BrandSpec = one glyph"); this
        # guards against a vendoring mistake that concatenated multiple
        # <path> elements' `d` data (or a stray tag) into one string.
        assert "path" not in path.lower()
        assert path == path.strip(), slug  # no incidental leading/trailing whitespace


# ---------------------------------------------------------------------------
# Round D3 (.ai/round_d3_provider_ecosystem_spec.md): eight declaration-tier
# marks vendored via scripts/vendor_brand_icons.py. The tests above already
# cover every BRAND entry generically (they iterate BRAND.items() /
# CANONICAL_PROVIDERS, not a hard-coded slug list), so the new entries are
# exercised automatically - these two tests pin the round's two explicit
# provenance decisions so a future edit can't silently drop or add one.
# ---------------------------------------------------------------------------

_ROUND_D3_VENDORED_SLUGS = frozenset(
    {"moonshot", "deepseek", "alibaba", "mistral", "ollama", "replit", "zhipu", "meta"}
)
_ROUND_D3_LETTER_TILE_ONLY_SLUGS = frozenset({"amp", "xai"})


def test_round_d3_vendored_slugs_are_all_branded():
    for slug in sorted(_ROUND_D3_VENDORED_SLUGS):
        assert slug in BRAND, f"{slug}: expected a round D3 vendored BrandSpec, found none"


def test_round_d3_amp_and_xai_have_no_mark_by_owner_ruling():
    # ADR-017's D3 addendum + the round spec: amp and xai carry no
    # simple-icons mark and are letter-tile-only by explicit owner ruling,
    # not a vendoring gap - this pins that decision against accidental
    # future fabrication.
    for slug in sorted(_ROUND_D3_LETTER_TILE_ONLY_SLUGS):
        assert slug in CANONICAL_PROVIDERS, slug
        assert slug not in BRAND, f"{slug}: expected letter-tile fallback, found a BrandSpec"


def test_glyph_path_hex_colors_are_well_formed():
    hex_re_len = 7  # "#RRGGBB"
    for slug, spec in sorted(BRAND.items()):
        for field_name in ("light_fg", "light_tint", "dark_fg", "dark_tint"):
            value = getattr(spec, field_name)
            assert isinstance(value, str), (slug, field_name)
            assert len(value) == hex_re_len and value.startswith("#"), (slug, field_name, value)
            int(value[1:], 16)  # raises ValueError if not valid hex

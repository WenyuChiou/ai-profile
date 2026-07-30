#!/usr/bin/env python3
"""Release-time icon vendoring tool (round D3, `.ai/round_d3_provider_ecosystem_spec.md`;
extends the round D1 vendoring approach recorded in ADR-017).

WHEN TO RUN: manually, once per vendoring pass, when a new provider gains a
brand mark to add to `src/aiprofile/render/brand.py`. It is deliberately NOT
part of `python -m pytest` and is NOT collected by pytest (it lives outside
`tests/`, the sole pytest `testpaths` root per pyproject.toml, and its
filename does not match pytest's `test_*` pattern) — same discipline as
`scripts/release_smoke.py`.

WHAT IT DOES: given a pinned simple-icons commit ref and a
canonical-slug -> simple-icons-icon-slug mapping, this script:

1. Fetches `data/simple-icons.json` (title -> hex) and, per mapping entry,
   `icons/<icon-slug>.svg` from the public `raw.githubusercontent.com`
   mirror, at the PINNED commit only (never `master`/`HEAD` — pinning is
   what makes the output reproducible).
2. Extracts the icon's `<title>` and `<path d="...">` mechanically (regex /
   stdlib XML parsing over the fetched SVG text) — never hand-typed path
   data.
3. Verifies each icon carries exactly one `<path>` element. Multi-path or
   missing icons are SKIPPED and reported, never faked.
4. Looks the icon's hex up in `data/simple-icons.json` by exact `<title>`
   match (simple-icons' data file has no `slug` field in this schema
   version; title is the mechanical join key actually present in both
   documents).
5. Derives per-theme `(fg, tint)` pairs from the brand hex using the same
   rule ADR-017 records for the five round-D1 marks: the tint is a
   same-hue wash of the brand color (high lightness for the light theme,
   low lightness for the dark theme), and `fg` is the LITERAL brand hex
   wherever it already clears WCAG >=3:1 against its own derived tint —
   otherwise a same-hue, lightness-adjusted shade is substituted (darkened
   for the light-theme pairing, lightened for the dark-theme pairing) until
   it clears 3:1. Both derived tints are also checked for distinguishability
   against this project's two card backgrounds (`#fbfdff` light / `#091321`
   dark, `src/aiprofile/render/themes.py`'s `THEMES["github-light"/"github-
   dark"].bg`) using the same >=1.1 luminance-ratio bar
   `tests/unit/test_brand.py` already enforces.
6. Prints ready-to-paste `BrandSpec(...)` stubs (one per successfully
   vendored icon) and a WCAG contrast table (fg-vs-tint and tint-vs-card,
   both themes) for every icon attempted, success or skip.

Deterministic given the pinned ref: no random sampling, no "closest visually
pleasing" hand tuning — the lightness search below is a fixed step-wise
scan, so the same ref + mapping always produces the same stubs.

NON-GOALS (same as ADR-017): no network access at render time or anywhere
else in this repo's normal code paths — this script's output is meant to be
copy-pasted into `brand.py` and committed like any other source edit, not
re-run automatically. No redrawing or simplifying of vendored path
geometry — verbatim path data only. No glyph fabrication — an icon that is
missing or multi-path at the pinned ref is skipped, never approximated.

SECOND SOURCE (round D5): `--source lobe` switches to lobehub/lobe-icons
(MIT; Copyright (c) 2023 LobeHub — full text mirrored in this repo's
THIRD_PARTY_NOTICES.md), fetching `packages/static-svg/icons/<icon>.svg`
plus the icon's `COLOR_PRIMARY` from
`packages/react-native/src/icons/<Component>/style.ts` at the pinned
commit. Lobe SVGs are monochrome `currentColor` marks with no embedded
`<title>`, so the mapping gains a third segment naming the component dir
(`slug:icon-slug:Component`), the style.ts `TITLE` constant is the join
key, and the SVG's `viewBox` is asserted to be the same 24-grid
simple-icons uses (any other geometry is a SKIP, never rescaled). All
other discipline is unchanged: exactly one `<path>`, verbatim `d=` data,
skips reported and never faked.

Usage:

    python scripts/vendor_brand_icons.py --ref <commit-sha> \\
        --map moonshot:kimi --map deepseek:deepseek --map alibaba:qwen \\
        --map mistral:mistralai --map ollama:ollama --map replit:replit \\
        --map zhipu:zdotai --map meta:metaai

    python scripts/vendor_brand_icons.py --ref <commit-sha> --map slug:icon ...

    python scripts/vendor_brand_icons.py --source lobe --ref <commit-sha> \\
        --map openai:openai:OpenAI --map xai:grok:Grok

Exit code 0 if the ref/data fetch succeeded (regardless of per-icon skips —
skips are reported, not fatal); exit code 1 on a fetch/transport failure
that prevented evaluating the mapping at all.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

RAW_BASE = "https://raw.githubusercontent.com/simple-icons/simple-icons"
RAW_BASE_LOBE = "https://raw.githubusercontent.com/lobehub/lobe-icons"
USER_AGENT = "ai-profile-vendor-brand-icons/1.0 (+scripts/vendor_brand_icons.py)"
TIMEOUT_SECONDS = 20
EXPECTED_VIEWBOX = "0 0 24 24"

# This project's two card backgrounds (src/aiprofile/render/themes.py
# THEMES["github-light"/"github-dark"].bg) — mirrored here by hand for the
# same reason brand.py mirrors CANONICAL_PROVIDERS: this script lives
# outside the render package's import graph on purpose (a vendoring tool has
# no business importing the library it feeds). The AST parity regression in
# tests/unit/test_brand.py keeps these intentional mirrors synchronized.
LIGHT_CARD_BG = "#fbfdff"
DARK_CARD_BG = "#091321"

MIN_FG_TINT_CONTRAST = 3.0
MIN_TINT_CARD_CONTRAST = 1.1

LIGHT_TINT_LIGHTNESS = 0.92
DARK_TINT_LIGHTNESS = 0.18
TINT_SATURATION_CAP = 0.55  # keeps very high-chroma brand hues from producing a shouty tint

FORBIDDEN_ATTR_CHARS = ('"', "&", "<", ">", "\n", "\t", "\r")


@dataclass(frozen=True)
class VendorResult:
    canonical_slug: str
    icon_slug: str
    title: str
    brand_hex: str
    light_fg: str
    light_tint: str
    dark_fg: str
    dark_tint: str
    path: str


@dataclass(frozen=True)
class VendorSkip:
    canonical_slug: str
    icon_slug: str
    reason: str


# ---------------------------------------------------------------------------
# Network + parsing
# ---------------------------------------------------------------------------


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310
        return resp.read()


def fetch_icons_index(ref: str) -> dict[str, str]:
    """Returns {title: hex} for every icon in data/simple-icons.json at ref."""
    url = f"{RAW_BASE}/{ref}/data/simple-icons.json"
    raw = _fetch(url)
    entries = json.loads(raw)
    return {entry["title"]: entry["hex"] for entry in entries}


def fetch_icon_svg(ref: str, icon_slug: str) -> str | None:
    """Returns the raw SVG text for icons/<icon_slug>.svg at ref, or None on 404."""
    url = f"{RAW_BASE}/{ref}/icons/{icon_slug}.svg"
    try:
        return _fetch(url).decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


_TITLE_RE = re.compile(r"<title>(.*?)</title>")
_PATH_D_RE = re.compile(r'<path\b[^>]*\bd="([^"]*)"[^>]*/?>')
_PATH_TAG_RE = re.compile(r"<path\b")
_VIEWBOX_RE = re.compile(r'viewBox="([^"]*)"')
_LOBE_TITLE_RE = re.compile(r"export const TITLE = '([^']+)'")
_LOBE_COLOR_PRIMARY_RE = re.compile(r"export const COLOR_PRIMARY = '(#[0-9A-Fa-f]{3,6})'")


def fetch_lobe_icon_svg(ref: str, icon_slug: str) -> str | None:
    """Returns packages/static-svg/icons/<icon_slug>.svg at ref, or None on 404."""
    url = f"{RAW_BASE_LOBE}/{ref}/packages/static-svg/icons/{icon_slug}.svg"
    try:
        return _fetch(url).decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def fetch_lobe_style_meta(ref: str, component: str) -> tuple[str, str] | None:
    """Returns (TITLE, COLOR_PRIMARY as #RRGGBB) mechanically extracted from
    packages/react-native/src/icons/<component>/style.ts at ref, or None if
    the file 404s or either constant is missing. A 3-digit hex shorthand
    (lobe writes '#000') is expanded to 6 digits; nothing else is altered."""
    url = f"{RAW_BASE_LOBE}/{ref}/packages/react-native/src/icons/{component}/style.ts"
    try:
        text = _fetch(url).decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    title_match = _LOBE_TITLE_RE.search(text)
    color_match = _LOBE_COLOR_PRIMARY_RE.search(text)
    if title_match is None or color_match is None:
        return None
    raw_hex = color_match.group(1).lstrip("#")
    if len(raw_hex) == 3:
        raw_hex = "".join(ch * 2 for ch in raw_hex)
    return title_match.group(1), f"#{raw_hex.upper()}"


def parse_icon_svg(svg_text: str) -> tuple[str, list[str]]:
    """Mechanically extracts (title, [path-d-values]) from an icon SVG's raw text."""
    title_match = _TITLE_RE.search(svg_text)
    title = title_match.group(1) if title_match else ""
    paths = _PATH_D_RE.findall(svg_text)
    return title, paths


# ---------------------------------------------------------------------------
# Color math (WCAG relative luminance + contrast; HSL derivation)
# ---------------------------------------------------------------------------


def _hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def _rgb01_to_hex(rgb: tuple[float, float, float]) -> str:
    r, g, b = (max(0, min(255, round(c * 255))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def relative_luminance(hex_color: str) -> float:
    channels = _hex_to_rgb01(hex_color)
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_ratio(a: str, b: str) -> float:
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hex_to_hls(hex_color: str) -> tuple[float, float, float]:
    r, g, b = _hex_to_rgb01(hex_color)
    hue, lightness, sat = colorsys.rgb_to_hls(r, g, b)
    return hue, lightness, sat


def hls_to_hex(hue: float, lightness: float, sat: float) -> str:
    lightness = max(0.0, min(1.0, lightness))
    return _rgb01_to_hex(colorsys.hls_to_rgb(hue, lightness, sat))


def derive_tint(brand_hex: str, target_lightness: float) -> str:
    """Same-hue wash of the brand color at a fixed target lightness, with
    saturation capped so very saturated brand hues don't produce a shouty
    tint chip (mirrors the pastel/deep-muted tint style of the round D1
    hand-authored entries)."""
    hue, _lightness, sat = hex_to_hls(brand_hex)
    if sat == 0.0:
        # True achromatic brand hex (pure black/white/gray): fall back to a
        # neutral gray wash at the target lightness rather than an
        # arbitrary hue.
        return hls_to_hex(0.0, target_lightness, 0.0)
    return hls_to_hex(hue, target_lightness, min(sat, TINT_SATURATION_CAP))


def adjust_fg_for_contrast(brand_hex: str, tint_hex: str, darken: bool) -> str:
    """If brand_hex already clears MIN_FG_TINT_CONTRAST against tint_hex,
    return it verbatim. Otherwise walk the same hue/saturation toward black
    (darken=True, for a light tint) or white (darken=False, for a dark tint)
    in fixed lightness steps until the pair clears the bar. Deterministic:
    a fixed step size, no randomness, no "eyeball a nice shade" tuning."""
    if contrast_ratio(brand_hex, tint_hex) >= MIN_FG_TINT_CONTRAST:
        return brand_hex

    hue, lightness, sat = hex_to_hls(brand_hex)
    step = -0.02 if darken else 0.02
    candidate_lightness = lightness
    for _ in range(60):  # 60 * 0.02 = full lightness range, plenty of headroom
        candidate_lightness += step
        if candidate_lightness < 0.0 or candidate_lightness > 1.0:
            break
        candidate_hex = hls_to_hex(hue, candidate_lightness, sat)
        if contrast_ratio(candidate_hex, tint_hex) >= MIN_FG_TINT_CONTRAST:
            return candidate_hex
    # Exhausted the same-hue/sat range without clearing the bar (only
    # possible for a mid-gray tint against a mid-gray-ish brand hue) — fall
    # back to pure black/white, which always clears 3:1 against any tint
    # that itself clears the card-background distinguishability bar.
    return "#000000" if darken else "#FFFFFF"


# ---------------------------------------------------------------------------
# Vendoring pipeline
# ---------------------------------------------------------------------------


def vendor_one(
    ref: str, canonical_slug: str, icon_slug: str, hex_by_title: dict[str, str]
) -> VendorResult | VendorSkip:
    svg_text = fetch_icon_svg(ref, icon_slug)
    if svg_text is None:
        return VendorSkip(canonical_slug, icon_slug, f"icons/{icon_slug}.svg 404 at {ref}")

    title, paths = parse_icon_svg(svg_text)
    if not title:
        return VendorSkip(canonical_slug, icon_slug, "no <title> found in fetched SVG")

    path_tag_count = len(_PATH_TAG_RE.findall(svg_text))
    if path_tag_count != 1 or len(paths) != 1:
        return VendorSkip(
            canonical_slug,
            icon_slug,
            f"expected exactly 1 <path>, found {path_tag_count} tag(s)/{len(paths)} d= value(s)",
        )

    path_d = paths[0]
    if not path_d.isascii():
        return VendorSkip(canonical_slug, icon_slug, "path data is not ASCII")
    for ch in FORBIDDEN_ATTR_CHARS:
        if ch in path_d:
            return VendorSkip(canonical_slug, icon_slug, f"path data contains {ch!r}")

    brand_hex = hex_by_title.get(title)
    if brand_hex is None:
        return VendorSkip(
            canonical_slug, icon_slug, f"title {title!r} not found in data/simple-icons.json"
        )
    brand_hex = f"#{brand_hex.upper()}"

    light_tint = derive_tint(brand_hex, LIGHT_TINT_LIGHTNESS)
    dark_tint = derive_tint(brand_hex, DARK_TINT_LIGHTNESS)
    light_fg = adjust_fg_for_contrast(brand_hex, light_tint, darken=True)
    dark_fg = adjust_fg_for_contrast(brand_hex, dark_tint, darken=False)

    return VendorResult(
        canonical_slug=canonical_slug,
        icon_slug=icon_slug,
        title=title,
        brand_hex=brand_hex,
        light_fg=light_fg,
        light_tint=light_tint,
        dark_fg=dark_fg,
        dark_tint=dark_tint,
        path=path_d,
    )


def vendor_one_lobe(
    ref: str, canonical_slug: str, icon_slug: str, component: str
) -> VendorResult | VendorSkip:
    """Round D5 lobe-icons variant of vendor_one: same single-path/verbatim
    discipline, but the title + brand hex come from the icon component's
    style.ts (lobe's static SVGs are monochrome currentColor marks with no
    <title> and no central color index), and the 24-grid viewBox is asserted
    rather than assumed (simple-icons guarantees it; lobe does not)."""
    svg_text = fetch_lobe_icon_svg(ref, icon_slug)
    if svg_text is None:
        return VendorSkip(
            canonical_slug, icon_slug, f"static-svg/icons/{icon_slug}.svg 404 at {ref}"
        )

    viewbox_match = _VIEWBOX_RE.search(svg_text)
    if viewbox_match is None or viewbox_match.group(1) != EXPECTED_VIEWBOX:
        found = viewbox_match.group(1) if viewbox_match else "none"
        return VendorSkip(
            canonical_slug, icon_slug, f"viewBox {found!r} != {EXPECTED_VIEWBOX!r}; never rescaled"
        )

    _title_unused, paths = parse_icon_svg(svg_text)
    path_tag_count = len(_PATH_TAG_RE.findall(svg_text))
    if path_tag_count != 1 or len(paths) != 1:
        return VendorSkip(
            canonical_slug,
            icon_slug,
            f"expected exactly 1 <path>, found {path_tag_count} tag(s)/{len(paths)} d= value(s)",
        )

    path_d = paths[0]
    if not path_d.isascii():
        return VendorSkip(canonical_slug, icon_slug, "path data is not ASCII")
    for ch in FORBIDDEN_ATTR_CHARS:
        if ch in path_d:
            return VendorSkip(canonical_slug, icon_slug, f"path data contains {ch!r}")

    meta = fetch_lobe_style_meta(ref, component)
    if meta is None:
        return VendorSkip(
            canonical_slug,
            icon_slug,
            f"react-native/src/icons/{component}/style.ts missing TITLE/COLOR_PRIMARY at {ref}",
        )
    title, brand_hex = meta

    light_tint = derive_tint(brand_hex, LIGHT_TINT_LIGHTNESS)
    dark_tint = derive_tint(brand_hex, DARK_TINT_LIGHTNESS)
    light_fg = adjust_fg_for_contrast(brand_hex, light_tint, darken=True)
    dark_fg = adjust_fg_for_contrast(brand_hex, dark_tint, darken=False)

    return VendorResult(
        canonical_slug=canonical_slug,
        icon_slug=icon_slug,
        title=title,
        brand_hex=brand_hex,
        light_fg=light_fg,
        light_tint=light_tint,
        dark_fg=dark_fg,
        dark_tint=dark_tint,
        path=path_d,
    )


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _wrap_path(path_d: str, indent: str = " " * 12, width: int = 82) -> str:
    """Wraps a long path-d string into quoted concatenated line fragments,
    matching the style already used for the hand-vendored entries in
    brand.py (adjacent string literals, ~88-char lines)."""
    lines: list[str] = []
    remaining = path_d
    while remaining:
        chunk, remaining = remaining[:width], remaining[width:]
        lines.append(f'{indent}"{chunk}"')
    return "\n".join(lines)


def format_brandspec_stub(result: VendorResult) -> str:
    return (
        f'    "{result.canonical_slug}": BrandSpec(\n'
        f"        path=(\n"
        f"{_wrap_path(result.path)}\n"
        f"        ),\n"
        f'        light_fg="{result.light_fg}",\n'
        f'        light_tint="{result.light_tint}",\n'
        f'        dark_fg="{result.dark_fg}",\n'
        f'        dark_tint="{result.dark_tint}",\n'
        f"    ),  # {result.title!r} (icons/{result.icon_slug}.svg), brand {result.brand_hex}"
    )


def format_contrast_table(results: list[VendorResult]) -> str:
    header = (
        f"{'slug':<10} {'theme':<6} {'fg-vs-tint':>10} {'tint-vs-card':>13}  "
        f"{'fg':<8} {'tint':<8}"
    )
    rows = [header, "-" * len(header)]
    for r in results:
        fg_tint_light = contrast_ratio(r.light_fg, r.light_tint)
        tint_card_light = contrast_ratio(r.light_tint, LIGHT_CARD_BG)
        fg_tint_dark = contrast_ratio(r.dark_fg, r.dark_tint)
        tint_card_dark = contrast_ratio(r.dark_tint, DARK_CARD_BG)
        light_ok = (
            fg_tint_light >= MIN_FG_TINT_CONTRAST and tint_card_light >= MIN_TINT_CARD_CONTRAST
        )
        dark_ok = (
            fg_tint_dark >= MIN_FG_TINT_CONTRAST and tint_card_dark >= MIN_TINT_CARD_CONTRAST
        )
        rows.append(
            f"{r.canonical_slug:<10} {'light':<6} {fg_tint_light:>10.2f} "
            f"{tint_card_light:>13.2f}  {r.light_fg:<8} {r.light_tint:<8}"
            f"{'  OK' if light_ok else '  FAIL'}"
        )
        rows.append(
            f"{r.canonical_slug:<10} {'dark':<6} {fg_tint_dark:>10.2f} "
            f"{tint_card_dark:>13.2f}  {r.dark_fg:<8} {r.dark_tint:<8}"
            f"{'  OK' if dark_ok else '  FAIL'}"
        )
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_mapping(pairs: list[str], source: str) -> list[tuple[str, ...]]:
    expected_parts = 3 if source == "lobe" else 2
    shape = "slug:icon-slug:Component" if source == "lobe" else "slug:icon-slug"
    mapping: list[tuple[str, ...]] = []
    for pair in pairs:
        parts = tuple(pair.split(":"))
        if len(parts) != expected_parts or not all(parts):
            raise argparse.ArgumentTypeError(f"--map value {pair!r} must be {shape}")
        mapping.append(parts)
    return mapping


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ref", required=True, help="Pinned upstream commit SHA (never a branch name)"
    )
    parser.add_argument(
        "--source",
        choices=("simple-icons", "lobe"),
        default="simple-icons",
        help="Icon source repository (default: simple-icons; lobe = lobehub/lobe-icons)",
    )
    parser.add_argument(
        "--map",
        action="append",
        default=[],
        dest="map_pairs",
        metavar="CANONICAL_SLUG:ICON_SLUG[:COMPONENT]",
        help="Repeatable. e.g. --map moonshot:kimi (simple-icons) or"
        " --map openai:openai:OpenAI (lobe)",
    )
    args = parser.parse_args(argv)

    if not args.map_pairs:
        parser.error("at least one --map value is required")

    mapping = _parse_mapping(args.map_pairs, args.source)

    print(f"# Source: {args.source}; pinned ref: {args.ref}")
    hex_by_title: dict[str, str] = {}
    if args.source == "simple-icons":
        try:
            hex_by_title = fetch_icons_index(args.ref)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            print(
                f"FATAL: could not fetch data/simple-icons.json at {args.ref}: {exc}",
                file=sys.stderr,
            )
            return 1
        print(f"# Loaded {len(hex_by_title)} icon titles from data/simple-icons.json")
    print()

    results: list[VendorResult] = []
    skips: list[VendorSkip] = []
    for entry in mapping:
        canonical_slug, icon_slug = entry[0], entry[1]
        try:
            if args.source == "lobe":
                outcome = vendor_one_lobe(args.ref, canonical_slug, icon_slug, entry[2])
            else:
                outcome = vendor_one(args.ref, canonical_slug, icon_slug, hex_by_title)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            outcome = VendorSkip(canonical_slug, icon_slug, f"transport error: {exc}")
        if isinstance(outcome, VendorResult):
            results.append(outcome)
        else:
            skips.append(outcome)

    if skips:
        print("## Skipped (honest letter-tile fallback, no glyph fabricated)")
        for skip in skips:
            print(f"  - {skip.canonical_slug} ({skip.icon_slug}): {skip.reason}")
        print()

    if results:
        print("## BrandSpec stubs (paste into src/aiprofile/render/brand.py's BRAND dict)")
        print()
        for result in sorted(results, key=lambda r: r.canonical_slug):
            print(format_brandspec_stub(result))
            print()

        print("## WCAG contrast table")
        print(format_contrast_table(sorted(results, key=lambda r: r.canonical_slug)))
        print()

    print(f"# Summary: {len(results)} vendored, {len(skips)} skipped, {len(mapping)} attempted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

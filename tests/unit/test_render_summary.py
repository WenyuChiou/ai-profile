"""Unit tests for the summary-card SVG renderer (ADR-010; docs/mvp.md
section 5; docs/architecture.md sections 8-9; work package E).

All `VizStats` fixtures are built inline from the dataclasses in
`aiprofile.viz` (never round-tripped through storage/aggregate) — the
privacy split must sum to `commits_scanned` and `providers` must be
pre-ranked by `(-attributed_commits, provider)`, both enforced by
`VizStats.__post_init__`.

REGENERATING SNAPSHOTS: the golden files under `tests/snapshots/` are
byte-exact UTF-8 renders of the fixtures below (`render_summary(stats,
theme).encode("utf-8")`, no newline translation). If an intentional
layout/content change requires new golden files, delete the stale ones and
run this module directly:

    python tests/unit/test_render_summary.py

which re-renders every `(case, theme)` pair in `CASES` x `THEMES` and
overwrites `tests/snapshots/summary_<case>_<light|dark>.svg`. Inspect the
diff before committing regenerated snapshots.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from aiprofile.render.summary_svg import render_summary
from aiprofile.render.themes import THEMES
from aiprofile.schema.vocab import UNRECOGNIZED_DISPLAY, UNRECOGNIZED_PROVIDER
from aiprofile.viz import EvidenceTotals, Period, PrivacySplit, ProviderRow, Totals, VizStats

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "snapshots"
SVG_NS = "{http://www.w3.org/2000/svg}"
GENERATED_ON = "2026-07-14"


def _period(label: str = "All time") -> Period:
    return Period(from_date=None, to_date=None, label=label)


# ---------------------------------------------------------------------------
# Fixture 1: "populated" — 8 providers (6 visible + 2 in "+2 more"),
# including the reserved `unrecognized` bucket inside the visible 6.
# ---------------------------------------------------------------------------

_POPULATED_PROVIDERS = (
    ProviderRow(provider="anthropic", display_name="Claude", attributed_commits=120,
                actor_presences=150, active_days=40),
    ProviderRow(provider="openai", display_name="OpenAI", attributed_commits=95,
                actor_presences=118, active_days=35),
    ProviderRow(provider="google", display_name="Gemini", attributed_commits=60,
                actor_presences=75, active_days=22),
    ProviderRow(provider="github", display_name="Copilot", attributed_commits=40,
                actor_presences=50, active_days=18),
    ProviderRow(provider="cursor", display_name="Cursor", attributed_commits=25,
                actor_presences=30, active_days=12),
    ProviderRow(provider=UNRECOGNIZED_PROVIDER, display_name=UNRECOGNIZED_DISPLAY,
                attributed_commits=20, actor_presences=22, active_days=9),
    ProviderRow(provider="amazon", display_name="Amazon Q", attributed_commits=10,
                actor_presences=12, active_days=5),
    ProviderRow(provider="aider", display_name="Aider", attributed_commits=5,
                actor_presences=6, active_days=3),
)

FIXTURE_POPULATED = VizStats(
    schema_version="0.1.0",
    period=_period(),
    totals=Totals(
        commits_scanned=520,
        ai_attributed_commits=375,
        ai_actor_presences=463,
        human_declared_commits=5,
        unknown_commits=100,
        active_ai_days=58,
    ),
    providers=_POPULATED_PROVIDERS,
    provider_count=7,  # excludes the unrecognized bucket
    evidence=EvidenceTotals(
        verified=12,
        declared=400,
        imported=0,
        inferred=5,
        unknown=46,
        total_records=463,
    ),
    privacy=PrivacySplit(
        explicitly_publishable_commits=200,
        anonymous_aggregate_commits=320,
        includes_anonymous_aggregate=True,
    ),
    generated_on=GENERATED_ON,
)

# ---------------------------------------------------------------------------
# Fixture 2: zero-state — brand-new user, nothing scanned yet.
# ---------------------------------------------------------------------------

FIXTURE_ZERO = VizStats(
    schema_version="0.1.0",
    period=_period(),
    totals=Totals(
        commits_scanned=0,
        ai_attributed_commits=0,
        ai_actor_presences=0,
        human_declared_commits=0,
        unknown_commits=0,
        active_ai_days=0,
    ),
    providers=(),
    provider_count=0,
    evidence=EvidenceTotals(
        verified=0,
        declared=0,
        imported=0,
        inferred=0,
        unknown=0,
        total_records=0,
    ),
    privacy=PrivacySplit(
        explicitly_publishable_commits=0,
        anonymous_aggregate_commits=0,
        includes_anonymous_aggregate=False,
    ),
    generated_on=GENERATED_ON,
)

# ---------------------------------------------------------------------------
# Fixtures 3 & 4: identical providers/totals, differing only in the privacy
# split — isolates the "Includes aggregate-only activity" / "Public repositories
# only" line. Evidence here only carries declared/unknown (both always
# shown), exercising the branch where every optional evidence field is 0.
# ---------------------------------------------------------------------------

_PRIVACY_PROVIDERS = (
    ProviderRow(provider="anthropic", display_name="Claude", attributed_commits=30,
                actor_presences=34, active_days=10),
    ProviderRow(provider="openai", display_name="OpenAI", attributed_commits=18,
                actor_presences=20, active_days=7),
    ProviderRow(provider="google", display_name="Gemini", attributed_commits=6,
                actor_presences=7, active_days=3),
)

_PRIVACY_TOTALS = Totals(
    commits_scanned=60,
    ai_attributed_commits=54,
    ai_actor_presences=61,
    human_declared_commits=1,
    unknown_commits=5,
    active_ai_days=14,
)

_PRIVACY_EVIDENCE = EvidenceTotals(
    verified=0,
    declared=58,
    imported=0,
    inferred=0,
    unknown=3,
    total_records=61,
)

FIXTURE_PRIVACY_TRUE = VizStats(
    schema_version="0.1.0",
    period=_period(),
    totals=_PRIVACY_TOTALS,
    providers=_PRIVACY_PROVIDERS,
    provider_count=3,
    evidence=_PRIVACY_EVIDENCE,
    privacy=PrivacySplit(
        explicitly_publishable_commits=0,
        anonymous_aggregate_commits=60,
        includes_anonymous_aggregate=True,
    ),
    generated_on=GENERATED_ON,
)

FIXTURE_PRIVACY_FALSE = VizStats(
    schema_version="0.1.0",
    period=_period(),
    totals=_PRIVACY_TOTALS,
    providers=_PRIVACY_PROVIDERS,
    provider_count=3,
    evidence=_PRIVACY_EVIDENCE,
    privacy=PrivacySplit(
        explicitly_publishable_commits=60,
        anonymous_aggregate_commits=0,
        includes_anonymous_aggregate=False,
    ),
    generated_on=GENERATED_ON,
)

#: The 4 snapshot cases x both themes (mvp.md section 7 tests 11-13).
CASES: dict[str, VizStats] = {
    "populated": FIXTURE_POPULATED,
    "zero": FIXTURE_ZERO,
    "privacy_true": FIXTURE_PRIVACY_TRUE,
    "privacy_false": FIXTURE_PRIVACY_FALSE,
}

_THEME_SUFFIX = {"github-light": "light", "github-dark": "dark"}


def _snapshot_path(case_name: str, theme_name: str) -> Path:
    return SNAPSHOT_DIR / f"summary_{case_name}_{_THEME_SUFFIX[theme_name]}.svg"


# ---------------------------------------------------------------------------
# Additional fixtures for targeted (non-snapshot) assertions.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Determinism (mvp.md section 7 test 11).
# ---------------------------------------------------------------------------


def test_determinism_byte_identical_double_render():
    for stats in CASES.values():
        for theme in THEMES.values():
            first = render_summary(stats, theme)
            second = render_summary(stats, theme)
            assert first == second
            assert first.encode("utf-8") == second.encode("utf-8")


# ---------------------------------------------------------------------------
# Exact snapshot comparison (mvp.md section 7 test 11).
# ---------------------------------------------------------------------------


def test_snapshots_byte_exact():
    for case_name, stats in CASES.items():
        for theme_name, theme in THEMES.items():
            path = _snapshot_path(case_name, theme_name)
            assert path.exists(), f"missing golden file: {path}"
            rendered = render_summary(stats, theme).encode("utf-8")
            golden = path.read_bytes()
            assert rendered == golden, f"snapshot mismatch: {path}"


# ---------------------------------------------------------------------------
# Well-formed XML (mvp.md section 7 test 12).
# ---------------------------------------------------------------------------


def test_well_formed_xml_all_cases():
    for stats in list(CASES.values()) + [_share_stats(1, 201), _share_stats(200, 201)]:
        for theme in THEMES.values():
            svg = render_summary(stats, theme)
            root = ET.fromstring(svg)  # raises ParseError if malformed
            assert root.tag == f"{SVG_NS}svg"


# ---------------------------------------------------------------------------
# Accessibility: <title>, <desc>, role="img", font sizes >= 11px
# (proposal.md section 23, ADR-010; mvp.md section 7 test 12).
# ---------------------------------------------------------------------------


def test_title_and_desc_present():
    for stats in CASES.values():
        for theme in THEMES.values():
            svg = render_summary(stats, theme)
            root = ET.fromstring(svg)
            title_el = root.find(f"{SVG_NS}title")
            desc_el = root.find(f"{SVG_NS}desc")
            assert title_el is not None and (title_el.text or "").strip()
            assert desc_el is not None and (desc_el.text or "").strip()


def test_title_includes_card_title_and_period_label():
    theme = THEMES["github-light"]
    svg = render_summary(FIXTURE_POPULATED, theme)
    root = ET.fromstring(svg)
    title_text = root.find(f"{SVG_NS}title").text
    assert "AI Collaboration Summary" in title_text
    assert FIXTURE_POPULATED.period.label in title_text


def test_desc_summarizes_headline_numbers():
    theme = THEMES["github-dark"]
    svg = render_summary(FIXTURE_POPULATED, theme)
    root = ET.fromstring(svg)
    desc_text = root.find(f"{SVG_NS}desc").text
    assert "375" in desc_text  # ai_attributed_commits
    assert "463" in desc_text  # ai_actor_presences
    assert "58" in desc_text  # active_ai_days
    assert "7" in desc_text  # provider_count


def test_role_img_on_root_svg():
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_POPULATED, theme)
        root = ET.fromstring(svg)
        assert root.get("role") == "img"


def test_all_font_sizes_at_least_11px():
    for stats in CASES.values():
        for theme in THEMES.values():
            svg = render_summary(stats, theme)
            sizes = [int(n) for n in re.findall(r'font-size="(\d+)"', svg)]
            assert sizes, "expected at least one font-size attribute"
            assert all(size >= 11 for size in sizes), sizes


# ---------------------------------------------------------------------------
# Provider table content (mvp.md section 5; architecture.md section 9).
# ---------------------------------------------------------------------------


def test_plus_n_more_for_eight_provider_fixture():
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_POPULATED, theme)
        assert "+2 more" in svg


def test_no_more_line_when_six_or_fewer_providers():
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_PRIVACY_TRUE, theme)
        assert "more" not in svg.lower()


def test_provider_table_label_present():
    svg = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    assert "Attributed commits by provider" in svg


def test_every_visible_provider_count_is_printed_as_text():
    # No color-only distinctions (proposal.md section 23): each bar's count
    # is always rendered as its own text node, not implied by bar length.
    svg = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    for row in FIXTURE_POPULATED.providers[:6]:
        assert f'>{row.attributed_commits}</tspan>' in svg


def test_provider_percentages_and_denominator_label():
    # Percentages must state their denominator (proposal.md section 26
    # rule 6): the table header names it, each visible row carries its pct.
    svg = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    denominator = FIXTURE_POPULATED.totals.ai_attributed_commits
    assert f"% of {denominator} AI-attributed commits" in svg
    for row in FIXTURE_POPULATED.providers[:6]:
        pct = round(100 * row.attributed_commits / denominator)
        assert f"· {pct}%" in svg


def test_privacy_split_chip_only_when_both_sides_nonzero():
    # populated: public 200 / private 320 -> split chip present
    svg = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    assert "publishable 200 · aggregate-only 320" in svg
    # privacy_true: public 0 -> only the inclusion chip, no split chip
    svg_true = render_summary(FIXTURE_PRIVACY_TRUE, THEMES["github-light"])
    assert "publishable 0" not in svg_true
    # privacy_false: no private -> no split chip either
    svg_false = render_summary(FIXTURE_PRIVACY_FALSE, THEMES["github-light"])
    assert "· aggregate-only" not in svg_false


def test_evidence_chip_prefix_present():
    svg = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    assert "Evidence (all records:" in svg
    assert THEMES["github-light"].chip_bg in svg


def test_bar_proportional_to_top_row():
    # max = top row (stats.providers[0]); the top row's bar equals the full
    # bar-track width, every other visible row's bar is strictly smaller and
    # proportional to its own attributed_commits.
    from aiprofile.render.summary_svg import BAR_MAX_WIDTH

    svg = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    max_attributed = FIXTURE_POPULATED.providers[0].attributed_commits  # anthropic, 120
    assert f'width="{BAR_MAX_WIDTH}"' in svg  # top row's fill bar spans the full track

    smallest_visible = FIXTURE_POPULATED.providers[5]  # unrecognized bucket, 20 commits
    expected_w = round(BAR_MAX_WIDTH * smallest_visible.attributed_commits / max_attributed)
    assert 0 < expected_w < BAR_MAX_WIDTH
    assert f'width="{expected_w}"' in svg


def test_long_display_name_truncated_with_ellipsis():
    """Renderer defense-in-depth: since gate-7 H-01, a VizStats with an
    arbitrary long display name cannot be CONSTRUCTED (pinned in
    test_viz_contract), so truncation is exercised at the helper layer
    it still guards."""
    from aiprofile.render.summary_svg import NAME_FONT_SIZE, NAME_WIDTH, _text_width, _truncate

    long_name = (
        "This Is An Absurdly Long AI Tool Display Name That Should Overflow The"
        " Column Width Easily"
    )
    out = _truncate(long_name, NAME_WIDTH, NAME_FONT_SIZE)
    assert out.endswith("…")
    assert out != long_name
    assert _text_width(out, NAME_FONT_SIZE) <= NAME_WIDTH


def test_text_content_is_escaped():
    """Renderer defense-in-depth: every text node escapes XML specials
    regardless of source — exercised at the helper layer since the
    closed public vocabulary (gate-7 H-01) removed the arbitrary-string
    construction path."""
    from aiprofile.render.summary_svg import _text

    node = _text(0, 0, 'R&D <Beta> "Y"', size=12, fill="#000000")
    assert "&amp;" in node
    assert "&lt;Beta&gt;" in node
    assert "<Beta>" not in node
    root = ET.fromstring(node)  # would raise if unescaped specials broke the XML
    del root


# ---------------------------------------------------------------------------
# Secondary / evidence / privacy / footer lines (mvp.md section 5).
# ---------------------------------------------------------------------------


def test_secondary_line_metrics_present():
    svg = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    assert "520" in svg  # commits_scanned
    assert "100" in svg  # unknown_commits
    assert ">7<" in svg or "AI providers 7" in svg  # provider_count


def test_evidence_line_always_has_declared_and_unknown():
    for stats in (FIXTURE_POPULATED, FIXTURE_PRIVACY_TRUE, FIXTURE_ZERO):
        svg = render_summary(stats, THEMES["github-light"])
        if stats is FIXTURE_ZERO:
            continue  # zero-state replaces the evidence line entirely
        assert "declared" in svg
        assert "unknown" in svg


def test_evidence_line_appends_only_nonzero_optional_fields():
    populated_svg = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    assert "verified 12" in populated_svg
    assert "inferred 5" in populated_svg
    assert "imported" not in populated_svg  # imported == 0 for this fixture

    privacy_svg = render_summary(FIXTURE_PRIVACY_TRUE, THEMES["github-light"])
    assert "verified" not in privacy_svg
    assert "imported" not in privacy_svg
    assert "inferred" not in privacy_svg
    assert "declared 58" in privacy_svg
    assert "unknown 3" in privacy_svg


def test_privacy_line_true_and_false():
    true_svg = render_summary(FIXTURE_PRIVACY_TRUE, THEMES["github-light"])
    false_svg = render_summary(FIXTURE_PRIVACY_FALSE, THEMES["github-light"])
    assert "Includes aggregate-only activity (repository identity withheld)" in true_svg
    assert "All activity explicitly publishable" not in true_svg
    assert "All activity explicitly publishable" in false_svg
    assert "Includes aggregate-only activity" not in false_svg


def test_footer_generated_on_and_footnote():
    for stats in CASES.values():
        svg = render_summary(stats, THEMES["github-light"])
        assert f"Generated {GENERATED_ON} · aiprofile" in svg
        assert "One commit may include several AI actor presences (one per provider/tool)." in svg


# ---------------------------------------------------------------------------
# Zero-state rendering (mvp.md section 7 test 13).
# ---------------------------------------------------------------------------


def test_zero_state_shows_placeholder_message_and_hint():
    for theme in THEMES.values():
        svg = render_summary(FIXTURE_ZERO, theme)
        assert "No AI collaboration recorded yet" in svg
        assert (
            "Add AI-* trailers or scan a repository with AI co-authored commits."
            in svg
        )


def test_zero_state_omits_metrics_and_table():
    svg = render_summary(FIXTURE_ZERO, THEMES["github-light"])
    assert "Attributed commits by provider" not in svg
    assert ">AI-attributed commits</text>" not in svg
    # The metric *label* text node, not the footer footnote sentence that
    # also mentions "AI actor presences" in prose.
    assert ">AI actor presences</text>" not in svg


def test_zero_state_keeps_title_period_and_footer():
    svg = render_summary(FIXTURE_ZERO, THEMES["github-light"])
    assert "AI Collaboration Summary" in svg
    assert FIXTURE_ZERO.period.label in svg
    assert f"Generated {GENERATED_ON} · aiprofile" in svg


# ---------------------------------------------------------------------------
# Theming (ADR-010): same content, different tokens; card geometry pinned.
# ---------------------------------------------------------------------------


def test_light_and_dark_differ_only_in_color_tokens():
    light = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    dark = render_summary(FIXTURE_POPULATED, THEMES["github-dark"])
    assert light != dark
    assert THEMES["github-light"].bg in light
    assert THEMES["github-dark"].bg in dark
    assert THEMES["github-light"].bg not in dark
    assert THEMES["github-dark"].bg not in light


def test_card_width_830_and_dynamic_deterministic_height():
    from aiprofile.render.summary_svg import WIDTH, card_height

    assert WIDTH == 830
    for stats in CASES.values():
        svg = render_summary(stats, THEMES["github-light"])
        assert f'width="{WIDTH}" height="{card_height(stats)}"' in svg
    # Sparse profiles collapse (no dead band): zero < 3 providers < 8 providers.
    assert (
        card_height(FIXTURE_ZERO)
        < card_height(FIXTURE_PRIVACY_TRUE)
        < card_height(FIXTURE_POPULATED)
    )


def test_rounded_border_radius_8_and_1px_stroke():
    svg = render_summary(FIXTURE_POPULATED, THEMES["github-light"])
    assert 'rx="8"' in svg
    assert 'stroke-width="1"' in svg


# ---------------------------------------------------------------------------
# Regeneration entry point (see module docstring).
# ---------------------------------------------------------------------------


def _write_all_snapshots() -> int:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for case_name, stats in CASES.items():
        for theme_name, theme in THEMES.items():
            svg = render_summary(stats, theme)
            _snapshot_path(case_name, theme_name).write_bytes(svg.encode("utf-8"))
            count += 1
    return count


ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "assets"


def _write_sample_assets() -> int:
    """The committed README preview assets regenerate from the SAME
    authoritative fixture through this same sanctioned entry point
    (gate-7 L-02) — no manual copying, guarded byte-exact by
    test_docs_sample_assets_match_current_renderer."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for theme_name, suffix in _THEME_SUFFIX.items():
        svg = render_summary(FIXTURE_POPULATED, THEMES[theme_name])
        (ASSETS_DIR / f"summary-sample-{suffix}.svg").write_bytes(svg.encode("utf-8"))
        count += 1
    return count


if __name__ == "__main__":
    written = _write_all_snapshots()
    samples = _write_sample_assets()
    print(f"Wrote {written} snapshot files to {SNAPSHOT_DIR}")
    print(f"Wrote {samples} sample assets to {ASSETS_DIR}")


def test_coordinate_hygiene_no_float_noise():
    """Gate-review regression (P1, 2026-07-14): every numeric geometry
    attribute must be an integer or a short decimal (the 0.5 border) —
    never raw double-precision noise like x="120.67999999999999"."""
    attr_re = re.compile(r'\b(?:x|y|x1|y1|x2|y2|width|height)="([^"]+)"')
    for stats in list(CASES.values()) + [_share_stats(1, 201), _share_stats(200, 201)]:
        for theme in THEMES.values():
            svg = render_summary(stats, theme)
            for value in attr_re.findall(svg):
                assert re.fullmatch(r"-?\d+(\.\d{1,2})?", value), value


# ---------------------------------------------------------------------------
# SVG security contract (G2-19): allowlisted elements, no active content,
# no external references.
# ---------------------------------------------------------------------------

_ALLOWED_SVG_TAGS = {
    f"{SVG_NS}{t}"
    # "path" added for round D1 (ADR-017): vendored provider brand glyphs
    # (aiprofile.render.brand.BRAND) are 24x24 viewBox path data drawn as
    # a single static <path fill="..." transform="...">, never active
    # content — still covered by the checks below (no "on*" handlers, no
    # href, no external refs).
    for t in ("svg", "title", "desc", "rect", "line", "text", "tspan", "polygon", "path")
}


def test_svg_uses_only_allowlisted_elements_and_no_active_content():
    for stats in list(CASES.values()) + [_share_stats(1, 201), _share_stats(200, 201)]:
        for theme in THEMES.values():
            svg = render_summary(stats, theme)
            root = ET.fromstring(svg)
            for el in root.iter():
                assert el.tag in _ALLOWED_SVG_TAGS, el.tag
                for attr in el.attrib:
                    assert not attr.lower().startswith("on"), attr
                    assert "href" not in attr.lower(), attr
            lowered = svg.lower()
            assert "<script" not in lowered
            assert "foreignobject" not in lowered
            assert "http://" not in lowered.replace("http://www.w3.org/2000/svg", "")
            assert "https://" not in lowered


def test_evidence_segments_never_negative_and_sum_exactly():
    """Gate-6 visual round (reviewer finding): independent per-segment
    rounding let the remainder-sized LAST segment go negative with 3+
    lopsided nonzero categories (reproduced: width="-1"). Cumulative
    rounding must keep every width >= 0 and the widths + 2px gaps summing
    exactly to the inner bar width. Confirmed failing pre-fix.

    The segment selector anchors on the evidence bar's own y coordinate
    (reviewer hardening, aesthetic round): color+height alone coupled
    this test to BAR_HEIGHT never reaching 8 while bar_fill coincides
    with a ramp step (true in github-light)."""
    stats = VizStats(
        schema_version="0.1.0",
        period=_period(),
        totals=Totals(
            commits_scanned=4000000,
            ai_attributed_commits=3328728,
            ai_actor_presences=3328728,
            human_declared_commits=0,
            unknown_commits=100,
            active_ai_days=300,
        ),
        providers=(
            ProviderRow(provider="anthropic", display_name="Claude",
                        attributed_commits=3328728, actor_presences=3328728,
                        active_days=300),
        ),
        provider_count=1,
        evidence=EvidenceTotals(
            verified=91627,
            declared=1060607,
            imported=747695,
            inferred=1427466,
            unknown=1333,
            total_records=3328728,
        ),
        privacy=PrivacySplit(
            explicitly_publishable_commits=4000000,
            anonymous_aggregate_commits=0,
            includes_anonymous_aggregate=False,
        ),
        generated_on=GENERATED_ON,
    )
    from aiprofile.render.summary_svg import (
        EVIDENCE_BAR_Y_OFFSET,
        PADDING,
        PANEL_PAD_X,
        WIDTH,
        _panel_top,
    )

    bar_y = _panel_top(stats) + EVIDENCE_BAR_Y_OFFSET
    for theme in THEMES.values():
        svg = render_summary(stats, theme)
        assert 'width="-' not in svg
        ramp = {theme.evidence_verified, theme.evidence_declared,
                theme.evidence_imported, theme.evidence_inferred,
                theme.evidence_unknown}
        seg_re = re.compile(
            rf'<rect x="(\d+)" y="{bar_y}" width="(\d+)" height="8" rx="2" fill="([^"]+)"/>'
        )
        segs = [(int(x), int(w)) for x, w, fill in seg_re.findall(svg) if fill in ramp]
        assert len(segs) == 5
        total_w = sum(w for _, w in segs)
        gaps = 2 * (len(segs) - 1)
        inner_w = (WIDTH - 2 * PADDING) - 2 * PANEL_PAD_X
        assert total_w + gaps == inner_w, (total_w, gaps, inner_w)
        # contiguity: each segment starts 2px after the previous ends
        for (x1, w1), (x2, _) in zip(segs, segs[1:], strict=False):
            assert x2 == x1 + w1 + 2


def test_docs_sample_assets_match_current_renderer():
    """The committed README preview assets (docs/assets/) are exact
    renderer output from the synthetic showcase fixture — the same
    byte-exact guard test_snapshots_byte_exact gives the test snapshots,
    extended to the docs assets so a future card change that forgets to
    regenerate them fails loudly instead of drifting silently (reviewer
    recommendation, README-sample round)."""
    assets = Path(__file__).resolve().parent.parent.parent / "docs" / "assets"
    for theme_name, suffix in _THEME_SUFFIX.items():
        path = assets / f"summary-sample-{suffix}.svg"
        assert path.exists(), f"missing committed sample: {path}"
        rendered = render_summary(FIXTURE_POPULATED, THEMES[theme_name]).encode("utf-8")
        assert path.read_bytes() == rendered, f"stale sample asset: {path}"


def _share_stats(ai: int, total: int) -> VizStats:
    return VizStats(
        schema_version="0.1.0",
        period=_period(),
        totals=Totals(total, ai, max(ai, 1) if ai else 0, 0, total - ai, 1 if ai else 0),
        providers=(
            (ProviderRow("anthropic", "Claude", ai, ai, 1),) if ai else ()
        ),
        provider_count=1 if ai else 0,
        evidence=EvidenceTotals(0, ai, 0, 0, total - ai, total),
        privacy=PrivacySplit(total, 0, False),
        generated_on=GENERATED_ON,
    )


def test_share_percentage_never_lies_at_the_boundaries():
    """Gate-7 M-02: whole-number rounding published "0%" for a nonzero
    share (1/201) and "100%" for a non-total share (200/201) — both
    contradicting the hero count and share bar. Boundary shares must use
    the deterministic endpoint labels. Confirmed failing pre-fix."""
    svg_low = render_summary(_share_stats(1, 201), THEMES["github-light"])
    assert "<1% of 201 unique commits scanned" in svg_low.replace("&lt;", "<")
    assert ">0% of 201" not in svg_low

    svg_high = render_summary(_share_stats(200, 201), THEMES["github-light"])
    assert ">99% of 201 unique commits scanned" in svg_high.replace("&gt;", ">")
    assert "100% of 201" not in svg_high


def test_share_percentage_exact_endpoints_stay_exact():
    svg_zero = render_summary(_share_stats(0, 10), THEMES["github-light"])
    assert "0% of 10 unique commits scanned" in svg_zero
    svg_full = render_summary(_share_stats(10, 10), THEMES["github-light"])
    assert "100% of 10 unique commits scanned" in svg_full


def test_provider_percentage_never_lies_at_the_boundaries():
    stats = VizStats(
        schema_version="0.1.0",
        period=_period(),
        totals=Totals(300, 201, 202, 0, 99, 5),
        providers=(
            ProviderRow("anthropic", "Claude", 200, 201, 5),
            ProviderRow("openai", "OpenAI", 1, 1, 1),
        ),
        provider_count=2,
        evidence=EvidenceTotals(0, 202, 0, 0, 0, 202),
        privacy=PrivacySplit(300, 0, False),
        generated_on=GENERATED_ON,
    )
    svg = render_summary(stats, THEMES["github-light"])
    # 1/201 rounds to 0 but is nonzero; 200/201 rounds to 100 but is not total
    assert "&lt;1%" in svg
    assert "&gt;99%" in svg
    assert "· 0%" not in svg
    assert "· 100%" not in svg


def test_evidence_unknown_mark_meets_graphical_contrast():
    """Gate-7 L-01: the light-theme unknown evidence mark sat at 2.85:1
    against the provenance panel — below the 3:1 graphical threshold the
    rest of the evidence system clears. Confirmed failing pre-fix."""

    def lum(h):
        h = h.lstrip("#")
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    for theme in THEMES.values():
        la, lb = sorted((lum(theme.evidence_unknown), lum(theme.chip_bg)), reverse=True)
        ratio = (la + 0.05) / (lb + 0.05)
        assert ratio >= 3.0, (theme.name, round(ratio, 2))

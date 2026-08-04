"""Model-family contribution ledger renderer contract tests."""

from __future__ import annotations

import json
from dataclasses import replace

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.render.dashboard_html import render_dashboard
from aiprofile.render.summary_svg import render_summary
from aiprofile.render.themes import MODEL_CATEGORY_COLORS, THEMES, model_category_color
from aiprofile.viz import (
    DayCell,
    DayCount,
    EvidenceTotals,
    ModelRow,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
    dumps_stats,
)


def _stats(*, models: tuple[ModelRow, ...]) -> VizStats:
    model_presences = sum(row.actor_presences for row in models)
    provider_presences = model_presences or 4
    return VizStats(
        schema_version=ACE_SCHEMA_VERSION,
        period=Period(None, None, "All time"),
        totals=Totals(4, 3, provider_presences, 0, 1, 2),
        providers=(ProviderRow("anthropic", "Claude", 2, provider_presences, 2),),
        provider_count=1,
        evidence=EvidenceTotals(0, 3, 0, 0, 1, 4),
        privacy=PrivacySplit(4, 0, False),
        generated_on="2026-08-04",
        models=models,
        model_count=sum(m.category != "unknown" for m in models),
    )


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def test_summary_model_ledger_is_labeled_and_overflow_is_bounded():
    rows = tuple(
            ModelRow(category, display, 3 - index // 2, 3 - index // 2, 1)
        for index, (category, display) in enumerate(
            (
                ("claude", "Claude"),
                ("gpt", "GPT"),
                ("gemini", "Gemini"),
                ("llama", "Llama"),
                ("other", "Other"),
            )
        )
    )
    svg = render_summary(_stats(models=rows), THEMES["github-light"])
    assert "Model contribution" in svg
    assert "Non-exclusive" in svg
    assert "+1 model categories not shown" in svg
    assert "Claude" in svg and "GPT" in svg
    assert 'font-size="11"' in svg
    assert f'fill="{model_category_color(THEMES["github-light"], "claude")}"' in svg
    assert f'fill="{model_category_color(THEMES["github-light"], "gpt")}"' in svg
    for theme_name, theme in THEMES.items():
        for category, color in MODEL_CATEGORY_COLORS[theme_name].items():
            assert model_category_color(theme, category) == color
            foreground, background = sorted(
                (_relative_luminance(color), _relative_luminance(theme.bg)),
                reverse=True,
            )
            assert (foreground + 0.05) / (background + 0.05) >= 3


def test_summary_description_matches_unknown_and_overflow_visibility():
    known_only = tuple(
        ModelRow(category, display, 1, 1, 1)
        for category, display in (
            ("claude", "Claude"),
            ("gpt", "GPT"),
        )
    )
    known_svg = render_summary(_stats(models=known_only), THEMES["github-light"])
    assert "2 known model families are shown" in known_svg
    assert "plus an unknown bucket" not in known_svg

    overflow = known_only + (
        ModelRow("gemini", "Gemini", 1, 1, 1),
        ModelRow("llama", "Llama", 1, 1, 1),
        ModelRow("mistral", "Mistral", 1, 1, 1),
    )
    overflow = tuple(
        sorted(overflow, key=lambda row: (-row.attributed_commits, row.category))
    )
    overflow_svg = render_summary(_stats(models=overflow), THEMES["github-light"])
    assert "5 known model families recorded; top 4 rows shown, with 1 more hidden" in overflow_svg


def test_dashboard_embeds_same_validated_model_rows_without_raw_values():
    stats = _stats(
        models=(
            ModelRow("claude", "Claude", 2, 2, 1),
            ModelRow("unknown", "Unknown", 1, 2, 1),
        )
    )
    html = render_dashboard(stats)
    assert "Model contribution" in html
    assert "All AI view · family categories" in html
    payload = html.split('<script type="application/json" id="profileData">', 1)[1].split(
        "</script>", 1
    )[0]
    data = json.loads(payload)
    assert data["models"] == [
        {
            "category": "claude",
            "display_name": "Claude",
            "attributed_commits": 2,
            "actor_presences": 2,
            "active_days": 1,
        },
        {
            "category": "unknown",
            "display_name": "Unknown",
            "attributed_commits": 1,
            "actor_presences": 2,
            "active_days": 1,
        },
    ]
    assert "private-model-canary" not in html
    assert "model_raw" not in dumps_stats(stats)
    assert "honestPercentLabel" in html
    assert "const modelColors =" in html
    assert '"claude":"#8a3f2f"' in html
    assert '"gpt":"#146b5a"' in html
    assert "mark.style.color = categoryColor" in html
    assert "mark.style.borderColor = categoryColor" in html


def test_dashboard_zero_model_state_is_honest():
    stats = _stats(models=())
    html = render_dashboard(stats)
    assert "No explicit model-family evidence published." in html


def test_model_ledger_does_not_change_daily_terrain_geometry():
    daily = (DayCell("2026-08-01", (DayCount("anthropic", 1),), 1, 1),)
    rows = (
        ModelRow("claude", "Claude", 2, 2, 1),
        ModelRow("unknown", "Unknown", 1, 2, 1),
    )
    without_models = render_summary(
        replace(_stats(models=()), daily=daily), THEMES["github-light"]
    )
    with_models = render_summary(
        replace(_stats(models=rows), daily=daily), THEMES["github-light"]
    )
    start = "Daily collaboration (last 12 weeks)"
    end = "Attributed commits by provider"
    assert without_models[without_models.index(start) : without_models.index(end)] == (
        with_models[with_models.index(start) : with_models.index(end)]
    )

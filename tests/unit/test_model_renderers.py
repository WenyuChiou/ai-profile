"""Renderer contract tests for data-only model-family evidence."""

from __future__ import annotations

import json

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.render.dashboard_html import render_dashboard
from aiprofile.render.summary_svg import render_summary
from aiprofile.render.themes import THEMES
from aiprofile.viz import (
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


def test_summary_keeps_provider_ledger_and_hides_model_rows():
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
    assert "Attributed commits by provider" in svg
    assert "Claude" in svg
    assert "Model contribution" not in svg
    assert "model-family" not in svg.lower()
    assert "Gemini" not in svg
    assert "Llama" not in svg
    assert "Other" not in svg


def test_summary_description_omits_model_ledger_claims():
    known_only = tuple(
        ModelRow(category, display, 1, 1, 1)
        for category, display in (
            ("claude", "Claude"),
            ("gpt", "GPT"),
        )
    )
    known_svg = render_summary(_stats(models=known_only), THEMES["github-light"])
    assert "Attributed commits by provider" in known_svg
    assert "known model families" not in known_svg
    assert "model-family" not in known_svg.lower()

    overflow = known_only + (
        ModelRow("gemini", "Gemini", 1, 1, 1),
        ModelRow("llama", "Llama", 1, 1, 1),
        ModelRow("mistral", "Mistral", 1, 1, 1),
    )
    overflow = tuple(
        sorted(overflow, key=lambda row: (-row.attributed_commits, row.category))
    )
    overflow_svg = render_summary(_stats(models=overflow), THEMES["github-light"])
    assert "Attributed commits by provider" in overflow_svg
    assert "model categories not shown" not in overflow_svg


def test_dashboard_keeps_model_rows_in_data_but_hides_model_visuals():
    stats = _stats(
        models=(
            ModelRow("claude", "Claude", 2, 2, 1),
            ModelRow("unknown", "Unknown", 1, 2, 1),
        )
    )
    html = render_dashboard(stats)
    assert "Provider ledger" in html
    assert 'id="providersTitle">Providers</h2>' in html
    assert "Model contribution" not in html
    assert "models-panel" not in html
    assert "model-list" not in html
    assert "renderModels" not in html
    assert "modelMarks" not in html
    assert "modelColors" not in html
    assert "--model-accent" not in html
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


def test_dashboard_zero_model_state_has_no_model_visual_or_copy():
    stats = _stats(models=())
    html = render_dashboard(stats)
    assert "Provider ledger" in html
    assert "Model contribution" not in html
    assert "model-list" not in html
    assert "renderModels" not in html
    assert '"models":[]' in html


def test_model_rows_do_not_change_summary_layout_or_provider_ledger():
    rows = (
        ModelRow("claude", "Claude", 2, 2, 1),
        ModelRow("unknown", "Unknown", 1, 2, 1),
    )
    without_models = render_summary(_stats(models=()), THEMES["github-light"])
    with_models = render_summary(_stats(models=rows), THEMES["github-light"])
    assert without_models == with_models


def test_summary_card_height_ignores_data_only_model_rows():
    from aiprofile.render.summary_svg import card_height

    models = (ModelRow("claude", "Claude", 2, 2, 1),)
    assert card_height(_stats(models=models)) == card_height(_stats(models=()))


def test_dashboard_layout_has_provider_panel_but_no_model_panel():
    html = render_dashboard(
        _stats(models=(ModelRow("claude", "Claude", 2, 2, 1),))
    )
    assert html.count('class="panel providers-panel"') == 1
    assert 'class="panel models-panel"' not in html
    assert html.index('id="providersTitle"') < html.index('id="evidenceTitle"')

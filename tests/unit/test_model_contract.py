"""Backend/public-contract tests for the v0.5 model-family ledger.

These tests deliberately exercise the storage -> aggregate -> privacy path
instead of constructing only renderer fixtures.  Model categories are derived
from the canonical ACE ``model`` value; raw model text is a local diagnostic
only and never enters ``VizStats`` or its JSON representation.
"""

from __future__ import annotations

import json

import pytest

from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.aggregate import ModelAgg, ProviderAgg, RepoAggregates, compute_repo_aggregates
from aiprofile.config import Config, RepoEntry
from aiprofile.errors import RenderError
from aiprofile.privacy import build_viz_stats, local_only_details
from aiprofile.schema.event import ProvenanceSource, build_event
from aiprofile.schema.vocab import (
    MODEL_CATEGORIES,
    MODEL_DISPLAY,
    ActorType,
    EvidenceLevel,
    PublicationLevel,
    SourceType,
    normalize_model_category,
)
from aiprofile.storage import db, store
from aiprofile.storage.store import CommitEvents
from aiprofile.viz import (
    EvidenceTotals,
    ModelRow,
    Period,
    PrivacySplit,
    ProviderRow,
    Totals,
    VizStats,
    dumps_stats,
    to_json_dict,
)


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "models.db")
    db.migrate(connection)
    yield connection
    connection.close()


def _sha(n: int) -> str:
    return f"{n:040x}"


def _ai_event(
    *,
    repository_uid: str,
    commit_sha: str,
    model: str | None,
    model_raw: str | None = None,
    provider: str = "anthropic",
    tool: str = "claude-code",
    timestamp: str = "2026-07-01T10:00:00+00:00",
):
    return build_event(
        actor_type=ActorType.AI,
        repository_uid=repository_uid,
        commit_sha=commit_sha,
        timestamp=timestamp,
        provider=provider,
        provider_raw=provider.title(),
        model=model,
        model_raw=model_raw,
        tool=tool,
        tool_raw=tool,
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER,
                EvidenceLevel.DECLARED,
                "ai-provider",
            ),
        ),
    )


def _human_event(*, repository_uid: str, commit_sha: str):
    return build_event(
        actor_type=ActorType.HUMAN,
        repository_uid=repository_uid,
        commit_sha=commit_sha,
        timestamp="2026-07-01T11:00:00+00:00",
        sources=(
            ProvenanceSource(
                SourceType.GIT_TRAILER,
                EvidenceLevel.DECLARED,
                "ai-mode",
            ),
        ),
    )


def _unknown_event(*, repository_uid: str, commit_sha: str):
    return build_event(
        actor_type=ActorType.UNKNOWN,
        repository_uid=repository_uid,
        commit_sha=commit_sha,
        timestamp="2026-07-01T12:00:00+00:00",
        sources=(ProvenanceSource(SourceType.NONE, EvidenceLevel.UNKNOWN),),
    )


def _scan(conn, *, uid: str, commits: list[CommitEvents]) -> None:
    store.replace_repository_scan(
        conn,
        repository_uid=uid,
        display_name=uid,
        local_path=f"/tmp/{uid}",
        scanned=commits,
        scanned_at="2026-07-01T12:00:00+00:00",
    )


def _one(results, uid: str):
    matches = [result for result in results if result.repository_uid == uid]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize(
    ("canonical_model", "category"),
    (
        ("claude-sonnet-4", "claude"),
        ("anthropic/claude-3-7-sonnet", "claude"),
        ("gpt-4o-mini", "gpt"),
        ("o3-mini", "gpt"),
        ("chatgpt-4o", "gpt"),
        ("gemini-2.5-pro", "gemini"),
        ("llama3.1", "llama"),
        ("mistralai/Mixtral-8x7B", "mistral"),
        ("deepseek-r1", "deepseek"),
        ("qwen2.5-coder", "qwen"),
        ("grok-3", "grok"),
        ("kimi-k2", "kimi"),
        ("private-org-secret-model", "other"),
        ("anthropic", "other"),
        (None, "unknown"),
        ("", "unknown"),
        ("  ", "unknown"),
    ),
)
def test_model_normalizer_is_closed_and_canonical_only(canonical_model, category):
    assert normalize_model_category(canonical_model) == category


def test_model_aggregation_is_nonexclusive_and_preserves_unknown_human(conn):
    uid = "model-aggregate"
    sha_multi = _sha(1)
    sha_ai_unknown = _sha(2)
    sha_human = _sha(3)
    sha_unknown = _sha(4)
    _scan(
        conn,
        uid=uid,
        commits=[
            CommitEvents(
                sha_multi,
                "dev@example.com",
                "2026-07-01T10:00:00+00:00",
                [
                    _ai_event(
                        repository_uid=uid,
                        commit_sha=sha_multi,
                        model="claude-sonnet-4",
                        model_raw="Claude Sonnet 4 (PRIVATE-RAW)",
                        provider="anthropic",
                        tool="claude-code",
                    ),
                    _ai_event(
                        repository_uid=uid,
                        commit_sha=sha_multi,
                        model="gpt-4o",
                        model_raw="GPT-4o",
                        provider="openai",
                        tool="codex-cli",
                    ),
                ],
            ),
            CommitEvents(
                sha_ai_unknown,
                "dev@example.com",
                "2026-07-01T12:00:00+00:00",
                [
                    _ai_event(
                        repository_uid=uid,
                        commit_sha=sha_ai_unknown,
                        model=None,
                        model_raw="Claude-Sonnet (PRIVATE-RAW-UNKNOWN)",
                    ),
                ],
            ),
            CommitEvents(
                sha_human,
                "dev@example.com",
                "2026-07-01T13:00:00+00:00",
                [_human_event(repository_uid=uid, commit_sha=sha_human)],
            ),
            CommitEvents(
                sha_unknown,
                "dev@example.com",
                "2026-07-01T14:00:00+00:00",
                [_unknown_event(repository_uid=uid, commit_sha=sha_unknown)],
            ),
        ],
    )

    agg = _one(compute_repo_aggregates(conn), uid)

    assert isinstance(agg.models["claude"], ModelAgg)
    assert agg.ai_attributed_commits == 2
    assert agg.ai_actor_presences == 3
    assert agg.human_declared_commits == 1
    assert agg.unknown_commits == 1
    assert agg.models["claude"].attributed_commits == 1
    assert agg.models["claude"].actor_presences == 1
    assert agg.models["gpt"].attributed_commits == 1
    assert agg.models["gpt"].actor_presences == 1
    assert agg.models["unknown"].attributed_commits == 1
    assert agg.models["unknown"].actor_presences == 1
    assert agg.models["claude"].active_dates == {"2026-07-01"}
    assert "PRIVATE-RAW" in " ".join(agg.models["claude"].raw_values)


def test_model_active_days_use_commit_author_date_not_event_timestamp(conn):
    uid = "model-author-day"
    sha = _sha(41)
    author_date = "2026-08-01T23:30:00+08:00"
    event_timestamp = "2026-08-02T09:00:00+00:00"
    _scan(
        conn,
        uid=uid,
        commits=[
            CommitEvents(
                sha,
                "dev@example.com",
                author_date,
                [
                    _ai_event(
                        repository_uid=uid,
                        commit_sha=sha,
                        model="claude-sonnet-4",
                        timestamp=event_timestamp,
                    )
                ],
            )
        ],
    )

    agg = _one(compute_repo_aggregates(conn), uid)

    assert agg.active_ai_dates == {"2026-08-01"}
    assert agg.models["claude"].active_dates == {"2026-08-01"}


def test_model_aggregate_old_event_schema_remains_readable(conn):
    uid = "model-old-schema"
    sha = _sha(5)
    _scan(
        conn,
        uid=uid,
        commits=[
            CommitEvents(
                sha,
                "dev@example.com",
                "2026-07-01T10:00:00+00:00",
                [
                    _ai_event(
                        repository_uid=uid,
                        commit_sha=sha,
                        model="claude-sonnet",
                    ),
                ],
            ),
        ],
    )
    conn.execute("UPDATE events SET schema_version = '0.2.0'")

    agg = _one(compute_repo_aggregates(conn), uid)
    assert agg.models["claude"].attributed_commits == 1


def _cfg(*levels: tuple[str, PublicationLevel]) -> Config:
    return Config(
        identities=["dev@example.com"],
        salt="s" * 64,
        repositories=[RepoEntry(f"/tmp/{uid}", uid, level) for uid, level in levels],
    )


def _model_agg(
    *,
    attributed_commits: int,
    actor_presences: int,
    active_dates: set[str],
    raw_values: set[str] | None = None,
) -> ModelAgg:
    return ModelAgg(
        attributed_commits=attributed_commits,
        actor_presences=actor_presences,
        active_dates=active_dates,
        raw_values=raw_values or set(),
    )


def test_privacy_model_rows_include_aggregate_only_counts_but_no_raw_model():
    full = RepoAggregates(
        repository_uid="u-full",
        commits_scanned=2,
        ai_attributed_commits=2,
        ai_actor_presences=2,
        active_ai_dates={"2026-07-01"},
        evidence_records={"declared": 2},
        providers={
            "anthropic": ProviderAgg(
                attributed_commits=2,
                actor_presences=2,
                active_dates={"2026-07-01"},
            ),
        },
        models={
            "claude": _model_agg(
                attributed_commits=1,
                actor_presences=1,
                active_dates={"2026-07-01"},
                raw_values={"Claude Sonnet 4 (FULL-RAW)"},
            ),
            "unknown": _model_agg(
                attributed_commits=1,
                actor_presences=1,
                active_dates={"2026-07-01"},
            ),
        },
    )
    aggregate_only = RepoAggregates(
        repository_uid="u-private",
        commits_scanned=1,
        ai_attributed_commits=1,
        ai_actor_presences=1,
        active_ai_dates={"2026-07-01"},
        evidence_records={"declared": 1},
        providers={
            "openai": ProviderAgg(
                attributed_commits=1,
                actor_presences=1,
                active_dates={"2026-07-01"},
            ),
        },
        models={
            "gpt": _model_agg(
                attributed_commits=1,
                actor_presences=1,
                active_dates={"2026-07-01"},
                raw_values={"GPT-4o (PRIVATE-RAW)"},
            ),
        },
    )

    stats = build_viz_stats(
        [full, aggregate_only],
        _cfg(
            ("u-full", PublicationLevel.FULL),
            ("u-private", PublicationLevel.AGGREGATE_ONLY),
        ),
        generated_on="2026-07-14",
    )

    assert [
        (row.category, row.attributed_commits, row.actor_presences)
        for row in stats.models
    ] == [
        ("claude", 1, 1),
        ("gpt", 1, 1),
        ("unknown", 1, 1),
    ]
    assert stats.model_count == 2
    assert stats.totals.ai_actor_presences == sum(row.actor_presences for row in stats.models)
    payload = dumps_stats(stats)
    assert "FULL-RAW" not in payload
    assert "PRIVATE-RAW" not in payload
    assert "u-private" not in payload
    details = local_only_details(
        [full, aggregate_only],
        _cfg(
            ("u-full", PublicationLevel.FULL),
            ("u-private", PublicationLevel.AGGREGATE_ONLY),
        ),
    )
    assert details["unrecognized_model_values"] == [
        "Claude Sonnet 4 (FULL-RAW)",
        "GPT-4o (PRIVATE-RAW)",
    ]


def _stats_with_models(
    models: tuple[ModelRow, ...],
    *,
    model_count: int | None = None,
    totals_ai_commits: int | None = None,
    totals_ai_presences: int | None = None,
) -> VizStats:
    ai_presences = sum(row.actor_presences for row in models)
    ai_commits = max((row.attributed_commits for row in models), default=0)
    total_ai_commits = ai_commits if totals_ai_commits is None else totals_ai_commits
    total_ai_presences = (
        ai_presences if totals_ai_presences is None else totals_ai_presences
    )
    providers = (
        (ProviderRow("anthropic", "Claude", total_ai_commits, total_ai_presences, 1),)
        if total_ai_presences
        else ()
    )
    return VizStats(
        schema_version=ACE_SCHEMA_VERSION,
        period=Period(None, None, "All time"),
        totals=Totals(total_ai_commits + 1, total_ai_commits, total_ai_presences, 0, 1, 1),
        providers=providers,
        provider_count=len(providers),
        evidence=EvidenceTotals(0, ai_presences, 0, 0, 1, ai_presences + 1),
        privacy=PrivacySplit(1, total_ai_commits, total_ai_commits > 0),
        generated_on="2026-07-14",
        models=models,
        model_count=(
            sum(row.category != "unknown" for row in models)
            if model_count is None
            else model_count
        ),
    )


def test_model_row_validation_and_json_parity():
    row = ModelRow("claude", MODEL_DISPLAY["claude"], 2, 2, 1)
    stats = _stats_with_models((row,))
    data = to_json_dict(stats)
    assert data["models"] == [
        {
            "category": "claude",
            "display_name": "Claude",
            "attributed_commits": 2,
            "actor_presences": 2,
            "active_days": 1,
        }
    ]
    assert data["model_count"] == 1
    assert json.loads(dumps_stats(stats))["models"] == data["models"]
    assert json.loads(dumps_stats(stats))["model_count"] == data["model_count"]


@pytest.mark.parametrize(
    "models,model_count,kwargs,match",
    (
        (
            (ModelRow("claude", "Claude", 2, 1, 1),),
            1,
            {"totals_ai_presences": 2},
            "actor_presences",
        ),
        (
            (ModelRow("claude", "Claude", 3, 1, 1),),
            1,
            {"totals_ai_commits": 2},
            "attributed_commits",
        ),
        (
            (ModelRow("claude", "Claude", 2, 1, 1),),
            1,
            {"totals_ai_commits": 2},
            "cannot exceed its",
        ),
        (
            (ModelRow("claude", "Claude", 1, 2, 2),),
            1,
            {},
            "active_days value cannot exceed",
        ),
        (
            (
                ModelRow("claude", "Claude", 1, 1, 1),
                ModelRow("claude", "Claude", 1, 1, 1),
            ),
            2,
            {},
            "one row",
        ),
        (
            (ModelRow("private", "Claude", 1, 1, 1),),
            1,
            {},
            "closed public vocabulary",
        ),
    ),
)
def test_model_row_validation_rejects_invalid_rows(models, model_count, kwargs, match):
    with pytest.raises(RenderError, match=match):
        _stats_with_models(models, model_count=model_count, **kwargs)


def test_model_row_validation_rejects_non_exact_numeric_types():
    class EvilInt(int):
        pass

    with pytest.raises(RenderError, match="exact int"):
        _stats_with_models((ModelRow("claude", "Claude", EvilInt(1), 1, 1),))


def test_model_category_display_names_are_schema_owned():
    assert set(MODEL_CATEGORIES) == set(MODEL_DISPLAY)
    for category, display_name in MODEL_DISPLAY.items():
        assert type(category) is str
        assert type(display_name) is str

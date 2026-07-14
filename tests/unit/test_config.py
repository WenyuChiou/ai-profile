"""Config policy-home tests (gate round-2 P2: G2-12 rejection and
fail-closed resolution get their own regression pins)."""

from __future__ import annotations

import json

import pytest

from aiprofile.config import (
    Config,
    RepoEntry,
    effective_level,
    load_config,
    resolve_publication_levels,
    save_config,
)
from aiprofile.errors import ConfigError
from aiprofile.schema.vocab import PublicationLevel


def _write_config(home, repositories):
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.json").write_text(
        json.dumps(
            {"identities": ["a@example.com"], "salt": "s" * 64, "repositories": repositories}
        ),
        encoding="utf-8",
    )


def test_repository_anonymous_is_rejected_as_reserved(tmp_path):
    # G2-12: reserved vocabulary must fail loudly, not behave like
    # aggregate_only.
    _write_config(
        tmp_path,
        [{"path": "/x", "repository_uid": "u1", "publication_level": "repository_anonymous"}],
    )
    with pytest.raises(ConfigError, match="reserved for post-v0.1"):
        load_config(tmp_path)


@pytest.mark.parametrize("level", ["full", "aggregate_only", "excluded"])
def test_v01_levels_load(tmp_path, level):
    _write_config(
        tmp_path,
        [{"path": "/x", "repository_uid": "u1", "publication_level": level}],
    )
    cfg = load_config(tmp_path)
    assert cfg.repositories[0].publication_level is PublicationLevel(level)


def test_unconfigured_uid_is_excluded_fail_closed(tmp_path):
    cfg = Config(identities=["a@example.com"], salt="s" * 64, repositories=[])
    assert effective_level(cfg, "remote:v2:github.com/x/y") is PublicationLevel.EXCLUDED


def test_duplicate_uid_resolves_most_restrictive():
    cfg = Config(
        identities=["a@example.com"],
        salt="s" * 64,
        repositories=[
            RepoEntry("/a", "u1", PublicationLevel.FULL),
            RepoEntry("/b", "u1", PublicationLevel.AGGREGATE_ONLY),
        ],
    )
    assert resolve_publication_levels(cfg)["u1"] is PublicationLevel.AGGREGATE_ONLY


def test_save_load_roundtrip(tmp_path):
    cfg = Config(
        identities=["a@example.com"],
        salt="s" * 64,
        repositories=[RepoEntry("/a", "u1", PublicationLevel.FULL)],
    )
    save_config(tmp_path, cfg)
    loaded = load_config(tmp_path)
    assert loaded == cfg

"""Config policy-home tests (gate round-2 P2: G2-12 rejection and
fail-closed resolution get their own regression pins)."""

from __future__ import annotations

import json
import os
import stat
import sys

import pytest

from aiprofile.config import (
    Config,
    RepoEntry,
    effective_level,
    init_home,
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


# ---------------------------------------------------------------------------
# Owner-only file permissions (ROADMAP "owner-only file permissions where
# supported"; docs/PRIVACY.md "Implemented hardening").
#
# Two layers per artifact: an exact-mode-bits assertion, POSIX-only (skipped
# on Windows — `os.chmod` there cannot express owner/group/other bits at
# all, matching the suite's existing POSIX-skip convention, see
# test_gitio_uid.py::test_c02_case_distinct_local_repos_split_on_posix), and
# a platform-independent call-recording assertion that `os.chmod` was
# invoked with the right (path, mode) pair — this one runs everywhere,
# including this Windows dev environment, and is what actually proved these
# tests red against the pre-fix code (no chmod call existed at all).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only owner-only permission bits; Windows os.chmod cannot"
    " represent them (see config._restrict_to_owner)",
)
def test_init_home_dir_is_owner_only_on_posix(tmp_path):
    home = tmp_path / "aiprofile_home"
    init_home(home, [])
    assert stat.S_IMODE(home.stat().st_mode) == 0o700


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only owner-only permission bits; Windows os.chmod cannot"
    " represent them (see config._restrict_to_owner)",
)
def test_save_config_file_is_owner_only_on_posix(tmp_path):
    cfg = Config(identities=["a@example.com"], salt="s" * 64, repositories=[])
    save_config(tmp_path, cfg)
    assert stat.S_IMODE((tmp_path / "config.json").stat().st_mode) == 0o600


def test_init_home_chmods_dir_owner_only(tmp_path, monkeypatch):
    calls: list[tuple[str, int]] = []
    real_chmod = os.chmod

    def recording_chmod(path, mode):
        calls.append((str(path), mode))
        real_chmod(path, mode)

    monkeypatch.setattr(os, "chmod", recording_chmod)
    home = tmp_path / "aiprofile_home"
    init_home(home, [])
    assert (str(home), 0o700) in calls


def test_save_config_chmods_file_owner_only(tmp_path, monkeypatch):
    calls: list[tuple[str, int]] = []
    real_chmod = os.chmod

    def recording_chmod(path, mode):
        calls.append((str(path), mode))
        real_chmod(path, mode)

    monkeypatch.setattr(os, "chmod", recording_chmod)
    cfg = Config(identities=["a@example.com"], salt="s" * 64, repositories=[])
    save_config(tmp_path, cfg)
    tmp_file = str(tmp_path / "config.json.tmp")
    assert (tmp_file, 0o600) in calls

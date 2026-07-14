"""Gate-3 scan-orchestration regressions (gate-review.md C-03, C-04, H-04):
config persists only after a fully successful scan; uid-algorithm migration
moves whole alias groups fail-closed; unsupported object formats are
rejected before any mutation. Each test was confirmed failing pre-fix."""

from __future__ import annotations

import subprocess

import pytest

from aiprofile import gitio, scanner
from aiprofile.config import Config, RepoEntry, load_config, save_config
from aiprofile.errors import ConfigError, GitError
from aiprofile.schema.vocab import PublicationLevel
from aiprofile.storage import store
from aiprofile.storage.db import connect, migrate


def _mkrepo(path, origin: str | None = None, commit: bool = True):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "fx@example.com"],
        cwd=str(path), check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Fx"], cwd=str(path), check=True, capture_output=True
    )
    if origin:
        subprocess.run(
            ["git", "remote", "add", "origin", origin],
            cwd=str(path), check=True, capture_output=True,
        )
    if commit:
        (path / "f.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "f.txt"], cwd=str(path), check=True, capture_output=True)
        env_date = {"GIT_AUTHOR_DATE": "2026-03-01T10:00:00+00:00",
                    "GIT_COMMITTER_DATE": "2026-03-01T10:00:00+00:00"}
        import os
        subprocess.run(
            ["git", "commit", "-q", "-m", "c"],
            cwd=str(path), check=True, capture_output=True,
            env={**os.environ, **env_date},
        )
    return path


def _fresh(tmp_path, repo):
    home = tmp_path / "home"
    home.mkdir()
    cfg = Config(identities=["fx@example.com"], salt="s" * 64, repositories=[])
    save_config(home, cfg)
    conn = connect(home / "db.sqlite")
    migrate(conn)
    return home, cfg, conn


def test_c04_failed_storage_leaves_config_untouched(tmp_path, monkeypatch):
    repo = _mkrepo(tmp_path / "r1")
    home, cfg, conn = _fresh(tmp_path, repo)
    before = (home / "config.json").read_bytes()

    def boom(*a, **k):
        raise RuntimeError("storage exploded")

    monkeypatch.setattr(scanner, "replace_repository_scan", boom)
    with pytest.raises(RuntimeError, match="storage exploded"):
        scanner.scan_repository(home, cfg, conn, str(repo), make_full=True)
    assert (home / "config.json").read_bytes() == before, (
        "a failed scan must not persist config (incl. --full elevation)"
    )
    conn.close()


def test_c04_failed_enumeration_leaves_config_untouched(tmp_path, monkeypatch):
    repo = _mkrepo(tmp_path / "r2")
    home, cfg, conn = _fresh(tmp_path, repo)
    before = (home / "config.json").read_bytes()

    def boom(path):
        raise GitError("enumeration exploded")

    monkeypatch.setattr(scanner.gitio, "enumerate_commits", boom)
    with pytest.raises(GitError):
        scanner.scan_repository(home, cfg, conn, str(repo), make_full=True)
    assert (home / "config.json").read_bytes() == before
    conn.close()


def test_c03_alias_group_migrates_together_and_old_rows_purged(tmp_path):
    # Two clones of one remote, both holding a stale prior-algorithm uid in
    # config; stale rows exist in the DB under the old uid. Rescanning ONE
    # clone must re-derive BOTH entries (keeping the alias group intact for
    # most-restrictive resolution) and purge the old uid's cached rows in
    # the same scan.
    old_uid = "remote:v2:github.com/org/repo"
    a = _mkrepo(tmp_path / "a", origin="https://github.com/org/repo")
    b = _mkrepo(tmp_path / "b", origin="git@github.com:org/repo.git")
    home = tmp_path / "home"
    home.mkdir()
    cfg = Config(
        identities=["fx@example.com"],
        salt="s" * 64,
        repositories=[
            RepoEntry(str(a.resolve()), old_uid, PublicationLevel.FULL),
            RepoEntry(str(b.resolve()), old_uid, PublicationLevel.AGGREGATE_ONLY),
        ],
    )
    save_config(home, cfg)
    conn = connect(home / "db.sqlite")
    migrate(conn)
    # seed stale rows under the old uid
    store.replace_repository_scan(
        conn, repository_uid=old_uid, display_name="stale", local_path=str(a),
        scanned=[], scanned_at=None,
    )

    scanner.scan_repository(home, cfg, conn, str(a))

    reloaded = load_config(home)
    uids = {e.path: e.repository_uid for e in reloaded.repositories}
    new_uid = gitio.repository_uid(a, "s" * 64)
    assert uids[str(a.resolve())] == new_uid
    assert uids[str(b.resolve())] == new_uid, "alias sibling must migrate together"
    stale = conn.execute(
        "SELECT COUNT(*) AS n FROM repositories WHERE repository_uid = ?", (old_uid,)
    ).fetchone()["n"]
    assert stale == 0, "old-uid rows must be purged in the same scan"
    conn.close()


def test_c03_excluded_alias_stays_fail_closed_and_unpersisted(tmp_path):
    # When the migrated alias group resolves EXCLUDED (most restrictive),
    # the scan is skipped and NOTHING is persisted: policy can never weaken
    # through a partial migration, and stale uids on excluded groups are
    # harmless because excluded repositories are never scanned or published.
    old_uid = "remote:v2:github.com/org/repo"
    a = _mkrepo(tmp_path / "a3", origin="https://github.com/org/repo")
    b = _mkrepo(tmp_path / "b3", origin="git@github.com:org/repo.git")
    home = tmp_path / "home"
    home.mkdir()
    cfg = Config(
        identities=["fx@example.com"],
        salt="s" * 64,
        repositories=[
            RepoEntry(str(a.resolve()), old_uid, PublicationLevel.FULL),
            RepoEntry(str(b.resolve()), old_uid, PublicationLevel.EXCLUDED),
        ],
    )
    save_config(home, cfg)
    conn = connect(home / "db.sqlite")
    migrate(conn)
    before = (home / "config.json").read_bytes()

    summary = scanner.scan_repository(home, cfg, conn, str(a))

    assert summary.excluded is True
    assert (home / "config.json").read_bytes() == before
    rows = conn.execute("SELECT COUNT(*) AS n FROM repositories").fetchone()["n"]
    assert rows == 0
    conn.close()


def test_c03_unresolvable_alias_sibling_halts_fail_closed(tmp_path):
    old_uid = "remote:v2:github.com/org/repo"
    a = _mkrepo(tmp_path / "a2", origin="https://github.com/org/repo")
    ghost = tmp_path / "ghost-clone"  # does not exist
    home = tmp_path / "home"
    home.mkdir()
    cfg = Config(
        identities=["fx@example.com"],
        salt="s" * 64,
        repositories=[
            RepoEntry(str(a.resolve()), old_uid, PublicationLevel.FULL),
            RepoEntry(str(ghost), old_uid, PublicationLevel.EXCLUDED),
        ],
    )
    save_config(home, cfg)
    conn = connect(home / "db.sqlite")
    migrate(conn)
    before = (home / "config.json").read_bytes()
    with pytest.raises(ConfigError, match="fail-closed"):
        scanner.scan_repository(home, cfg, conn, str(a))
    assert (home / "config.json").read_bytes() == before
    conn.close()


def test_h04_empty_sha256_repo_rejected_without_mutation(tmp_path):
    repo = tmp_path / "s256"
    repo.mkdir()
    probe = subprocess.run(
        ["git", "init", "-q", "--object-format=sha256"],
        cwd=str(repo), capture_output=True, text=True,
    )
    if probe.returncode != 0:
        pytest.skip("this git build does not support --object-format=sha256")
    home, cfg, conn = _fresh(tmp_path, repo)
    before = (home / "config.json").read_bytes()
    with pytest.raises(GitError) as exc:
        scanner.scan_repository(home, cfg, conn, str(repo))
    assert "SHA-1" in str(exc.value) or "sha256" in str(exc.value)
    assert str(repo) not in str(exc.value), "default error must be path-free"
    assert (home / "config.json").read_bytes() == before
    rows = conn.execute("SELECT COUNT(*) AS n FROM repositories").fetchone()["n"]
    assert rows == 0
    conn.close()

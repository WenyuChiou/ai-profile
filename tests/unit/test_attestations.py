"""Private reconciliation survives a full replacement scan without history edits."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from aiprofile import attestations, scanner
from aiprofile.cli import main
from aiprofile.config import Config, save_config
from aiprofile.errors import ConfigError
from aiprofile.storage.db import connect, migrate


def _repo(path):
    path.mkdir()
    for args in (
        ["init", "-q"],
        ["config", "user.email", "fx@example.com"],
        ["config", "user.name", "Fx"],
        ["remote", "add", "origin", "https://github.com/example/fixture.git"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)
    (path / "f").write_text("fixture", encoding="utf-8")
    for args in (["add", "f"], ["commit", "-qm", "unmarked change"]):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    return sha


def test_private_declaration_survives_rescan_and_removal_restores_unknown(tmp_path):
    repo = tmp_path / "repo"
    sha = _repo(repo)
    home = tmp_path / "home"
    home.mkdir()
    cfg = Config(identities=["fx@example.com"], salt="s" * 64)
    save_config(home, cfg)
    conn = connect(home / "db.sqlite")
    migrate(conn)
    scanner.scan_repository(home, cfg, conn, str(repo), make_full=True)
    assert conn.execute("SELECT actor_type FROM events").fetchone()[0] == "unknown"

    entry = {
        "repo": attestations.repository_key(repo),
        "sha": sha,
        "provider": "OpenAI",
        "tool": "Codex CLI",
        "mode": "ai_assisted",
    }
    attestations.confirm_reachable(repo, sha, cfg.identities)
    attestations.save(home, [entry])
    first = (home / attestations.LEDGER_NAME).read_bytes()
    for _ in range(2):
        scanner.scan_repository(home, cfg, conn, str(repo))
        assert conn.execute("SELECT actor_type,provider FROM events").fetchone()[:] == (
            "ai",
            "openai",
        )
        assert (home / attestations.LEDGER_NAME).read_bytes() == first

    attestations.save(home, [])
    scanner.scan_repository(home, cfg, conn, str(repo))
    assert conn.execute("SELECT actor_type FROM events").fetchone()[0] == "unknown"
    conn.close()


def test_private_ledger_rejects_malformed_and_over_limit(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / attestations.LEDGER_NAME).write_text('{"version":1,"entries":{}}', encoding="utf-8")
    with pytest.raises(ConfigError, match="entries must be a list"):
        attestations.load(home)
    (home / attestations.LEDGER_NAME).write_bytes(b" " * (attestations.LOCAL_LEDGER_LIMIT + 1))
    with pytest.raises(ConfigError, match="8 MB"):
        attestations.load(home)


def test_private_ledger_rejects_noncanonical_github_repo_key(tmp_path):
    home = tmp_path / "home"
    with pytest.raises(ConfigError, match="not canonical"):
        attestations.save(
            home,
            [{
                "repo": "github.com/Example/Fixture",
                "sha": "a" * 40,
                "provider": "OpenAI",
                "tool": None,
                "mode": "ai_assisted",
            }],
        )


def test_confirmed_unregistered_provider_stays_unrecognized_not_discarded(tmp_path):
    home = tmp_path / "home"
    entry = {
        "repo": "github.com/example/fixture",
        "sha": "a" * 40,
        "provider": "New AI Vendor",
        "tool": "New Agent",
        "mode": "ai_assisted",
    }
    attestations.save(home, [entry])
    spec = attestations.spec_for(attestations.load(home)[0])
    assert spec.provider is None
    assert spec.provider_raw == "New AI Vendor"
    assert spec.tool is None
    assert spec.tool_raw == "New Agent"


def test_cloud_sync_uses_stdin_and_rejects_non_github_entries(tmp_path, monkeypatch):
    home = tmp_path / "home"
    attestations.save(home, [])
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(attestations.subprocess, "run", fake_run)
    assert attestations.sync_github(home, "owner/profile") == 0
    args, kwargs = calls[0]
    assert args == ["gh", "secret", "set", "AIPROFILE_ATTESTATIONS", "--repo", "owner/profile"]
    assert b'"entries":[]' in kwargs["input"]
    assert kwargs["capture_output"] is True
    assert all(b"entries" not in str(arg).encode() for arg in args)
    attestations.save(
        home,
        [
            {
                "repo": "local:/private/repo",
                "sha": "a" * 40,
                "provider": "OpenAI",
                "tool": None,
                "mode": "ai_assisted",
            }
        ],
    )
    with pytest.raises(ConfigError, match="non-GitHub"):
        attestations.sync_github(home, "owner/profile")


def test_cloud_sync_rejects_complete_ledger_above_48kb(tmp_path):
    home = tmp_path / "home"
    attestations.save(
        home,
        [
            {
                "repo": "github.com/example/fixture",
                "sha": f"{index:040x}",
                "provider": "OpenAI",
                "tool": None,
                "mode": "ai_assisted",
            }
            for index in range(600)
        ],
    )
    assert len(attestations.load(home)) == 600  # locally usable
    with pytest.raises(ConfigError, match="48 KB"):
        attestations.sync_github(home, "owner/profile")


def test_source_suggestion_is_read_only(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    _repo(repo)
    home = tmp_path / "home"
    home.mkdir()
    cfg = Config(identities=["fx@example.com"], salt="s" * 64)
    save_config(home, cfg)
    conn = connect(home / "db.sqlite")
    migrate(conn)
    scanner.scan_repository(home, cfg, conn, str(repo))
    conn.close()
    before = (home / "config.json").read_bytes()
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert main(["sources", "suggest", "example/fixture", "example/other"]) == 0
    output = capsys.readouterr().out
    assert "example/fixture: configured" in output
    assert "example/other: not configured" in output
    assert (home / "config.json").read_bytes() == before

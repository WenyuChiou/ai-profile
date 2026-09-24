"""CLI reconciliation uses a private ledger, not Git history rewriting."""

from __future__ import annotations

import subprocess

from aiprofile.cli import main
from aiprofile.config import Config, save_config


def test_confirmed_commit_is_attributed_then_restored_on_remove(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ["init", "-q"],
        ["config", "user.email", "fx@example.com"],
        ["config", "user.name", "Fx"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    (repo / "f").write_text("unmarked", encoding="utf-8")
    subprocess.run(["git", "add", "f"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-qm", "recent AI-assisted work without trailer"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    home = tmp_path / "home"
    home.mkdir()
    save_config(home, Config(identities=["fx@example.com"], salt="s" * 64))
    monkeypatch.setenv("AIPROFILE_HOME", str(home))

    assert main(["scan", str(repo)]) == 0
    capsys.readouterr()
    assert main(["aggregate"]) == 0
    assert "unknown commits:            1" in capsys.readouterr().out
    before = subprocess.check_output(["git", "log", "-1", "--format=%B"], cwd=repo)

    assert (
        main(
            [
                "reconcile", "add", "--repo", str(repo), "--sha", sha,
                "--provider", "OpenAI", "--confirm-ai",
            ]
        ) == 0
    )
    assert main(["scan", str(repo)]) == 0
    assert main(["aggregate"]) == 0
    output = capsys.readouterr().out
    assert "AI-attributed commits:      1" in output
    assert "unknown commits:            0" in output
    assert subprocess.check_output(["git", "log", "-1", "--format=%B"], cwd=repo) == before

    assert main(["reconcile", "remove", "--repo", str(repo), "--sha", sha, "--confirm-remove"]) == 0
    assert main(["scan", str(repo)]) == 0
    assert main(["aggregate"]) == 0
    assert "unknown commits:            1" in capsys.readouterr().out


def test_remove_private_declaration_after_history_rewrite(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ["init", "-q"],
        ["config", "user.email", "fx@example.com"],
        ["config", "user.name", "Fx"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    (repo / "f").write_text("change", encoding="utf-8")
    subprocess.run(["git", "add", "f"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "original"], cwd=repo, check=True, capture_output=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    home = tmp_path / "home"
    home.mkdir()
    save_config(home, Config(identities=["fx@example.com"], salt="s" * 64))
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert main([
        "reconcile", "add", "--repo", str(repo), "--sha", sha,
        "--provider", "OpenAI", "--confirm-ai",
    ]) == 0
    subprocess.run(
        ["git", "commit", "--amend", "-qm", "rewritten"],
        cwd=repo, check=True, capture_output=True,
    )
    assert main([
        "reconcile", "remove", "--repo", str(repo), "--sha", sha, "--confirm-remove",
    ]) == 0

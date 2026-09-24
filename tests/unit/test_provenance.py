"""One-commit opt-in marks fail closed when HEAD or staging changes."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aiprofile import provenance
from aiprofile.adapters.trailers import parse_commit_trailers
from aiprofile.errors import ConfigError

ROOT = Path(__file__).resolve().parents[2]


def _repo(path):
    path.mkdir()
    for args in (
        ["init", "-q"],
        ["config", "user.email", "fx@example.com"],
        ["config", "user.name", "Fx"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)
    (path / "f").write_text("one", encoding="utf-8")
    subprocess.run(["git", "add", "f"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=path, check=True, capture_output=True)
    (path / "f").write_text("two", encoding="utf-8")
    subprocess.run(["git", "add", "f"], cwd=path, check=True, capture_output=True)


def test_mark_prepare_retry_post_consumes_once(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    _repo(repo)
    provenance.mark(home, repo, "OpenAI", "Codex CLI", "AI-Assisted")
    message = tmp_path / "message"
    message.write_text("change\n", encoding="utf-8")
    provenance.hook_run(home, repo, "prepare", message)
    body = message.read_text(encoding="utf-8")
    assert "AI-Provider: openai" in body
    assert "AI-Tool: codex-cli" in body
    assert "AI-Mode: AI-Assisted" in body
    assert provenance._read(home)  # failed commit leaves mark for retry
    subprocess.run(
        ["git", "commit", "-qF", str(message)], cwd=repo, check=True, capture_output=True
    )
    provenance.hook_run(home, repo, "post")
    assert provenance._read(home) == {}


def test_mark_refuses_changed_staging_and_amend(tmp_path):
    repo = tmp_path / "repo"
    _repo(repo)
    home = tmp_path / "home"
    provenance.mark(home, repo, "Anthropic", "Claude Code", "AI-Assisted")
    message = tmp_path / "message"
    message.write_text("change\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="amend/merge/squash"):
        provenance.hook_run(home, repo, "prepare", message, "commit")
    (repo / "f").write_text("three", encoding="utf-8")
    subprocess.run(["git", "add", "f"], cwd=repo, check=True, capture_output=True)
    with pytest.raises(ConfigError, match="staged content changed"):
        provenance.hook_run(home, repo, "prepare", message)
    assert provenance._read(home)


def test_mark_can_declare_new_provider_without_inference(tmp_path):
    repo = tmp_path / "repo"
    _repo(repo)
    home = tmp_path / "home"
    provenance.mark(home, repo, "New AI Vendor", "New Agent", "AI-Assisted")
    entry = next(iter(provenance._read(home).values()))
    assert entry["provider"] == "New AI Vendor"
    assert entry["tool"] == "New Agent"


def test_tampered_pending_mark_cannot_inject_commit_trailers(tmp_path):
    repo = tmp_path / "repo"
    _repo(repo)
    home = tmp_path / "home"
    provenance.mark(home, repo, "OpenAI", None, "AI-Assisted")
    path = home / provenance.MARKS_NAME
    data = json.loads(path.read_text(encoding="utf-8"))
    next(iter(data["marks"].values()))["provider"] = "OpenAI\nAI-Provider: Evil"
    path.write_text(json.dumps(data), encoding="utf-8")
    message = tmp_path / "message"
    message.write_text("change\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="malformed"):
        provenance.hook_run(home, repo, "prepare", message)
    assert message.read_text(encoding="utf-8") == "change\n"


def test_install_does_not_overwrite_existing_hook(tmp_path):
    repo = tmp_path / "repo"
    _repo(repo)
    hook = repo / ".git" / "hooks" / "prepare-commit-msg"
    hook.write_text("existing", encoding="utf-8")
    with pytest.raises(ConfigError, match="existing/custom hooks"):
        provenance.install_hooks(tmp_path / "home", repo)
    assert hook.read_text(encoding="utf-8") == "existing"
    assert not (repo / ".git" / "hooks" / "post-commit").exists()


def test_installed_hooks_mark_exact_next_commit(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    _repo(repo)
    home = tmp_path / "home"
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    provenance.install_hooks(home, repo)
    provenance.mark(home, repo, "OpenAI", "Codex CLI", "AI-Assisted")
    result = subprocess.run(
        ["git", "commit", "-m", "change"], cwd=repo, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    body = subprocess.check_output(["git", "log", "-1", "--format=%B"], cwd=repo, text=True)
    assert "AI-Provider: openai" in body
    assert "AI-Tool: codex-cli" in body
    assert provenance._read(home) == {}


def test_later_message_hook_cannot_consume_lost_evidence(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    _repo(repo)
    home = tmp_path / "home"
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    provenance.install_hooks(home, repo)
    # An independent hook can edit the message after prepare-commit-msg.
    message_hook = repo / ".git" / "hooks" / "commit-msg"
    message_hook.write_text("#!/bin/sh\nprintf 'change\\n' > \"$1\"\n", encoding="utf-8")
    message_hook.chmod(0o755)
    provenance.mark(home, repo, "OpenAI", "Codex CLI", "AI-Assisted")
    result = subprocess.run(
        ["git", "commit", "-m", "change"], cwd=repo, capture_output=True, text=True, check=False
    )
    assert "AI-Provider" not in subprocess.check_output(
        ["git", "log", "-1", "--format=%B"], cwd=repo, text=True
    )
    assert provenance._read(home)
    assert "mark retained" in result.stderr


@pytest.mark.parametrize(
    ("existing", "expected"),
    [
        ("AI-Tool: Claude Code", [("ai", "anthropic", "claude-code"),
                                  ("ai", "openai", "codex-cli")]),
        ("AI-Mode: Human-Only", [("human", None, None),
                                 ("ai", "openai", "codex-cli")]),
    ],
)
def test_prepare_preserves_existing_actor_group(tmp_path, existing, expected):
    repo = tmp_path / "repo"
    _repo(repo)
    home = tmp_path / "home"
    provenance.mark(home, repo, "OpenAI", "Codex CLI", "AI-Assisted")
    message = tmp_path / "message"
    message.write_text(f"change\n\n{existing}\n", encoding="utf-8")
    provenance.hook_run(home, repo, "prepare", message)
    parsed = subprocess.run(
        ["git", "interpret-trailers", "--parse", "--no-divider", str(message)],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    specs, warnings = parse_commit_trailers(parsed.stdout.splitlines())
    assert warnings == []
    assert [(s.actor_type.value, s.provider, s.tool) for s in specs] == expected
    subprocess.run(
        ["git", "commit", "-qF", str(message)], cwd=repo, check=True, capture_output=True
    )
    provenance.hook_run(home, repo, "post")
    assert provenance._read(home) == {}


@pytest.mark.parametrize("existing", ["AI-Tool: Claude Code", "AI-Role: testing"])
def test_prepare_refuses_unseparable_group_without_changing_message(tmp_path, existing):
    repo = tmp_path / "repo"
    _repo(repo)
    home = tmp_path / "home"
    provenance.mark(home, repo, "OpenAI", None, "AI-Assisted")
    message = tmp_path / "message"
    original = f"change\n\n{existing}\n"
    message.write_text(original, encoding="utf-8")
    with pytest.raises(ConfigError, match="cannot safely separate"):
        provenance.hook_run(home, repo, "prepare", message)
    assert message.read_text(encoding="utf-8") == original
    assert provenance._read(home)


def test_pr_check_requires_source_evidence_in_proposed_squash(tmp_path):
    repo = tmp_path / "repo"
    _repo(repo)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    subprocess.run(
        ["git", "commit", "-qm", "AI change\n\nAI-Provider: OpenAI\nAI-Tool: Codex CLI"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    proposed = tmp_path / "squash"
    proposed.write_text("AI change\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="loses the evidence"):
        provenance.check_squash_message(repo, base, head, proposed)
    proposed.write_text("AI change\n\nAI-Provider: OpenAI\nAI-Tool: Codex CLI\n", encoding="utf-8")
    assert provenance.check_squash_message(repo, base, head, proposed) == (1, 1)

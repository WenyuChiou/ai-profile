"""Orchestrator regression tests for gitio path semantics (post-WP-F finding:
the user home being a git worktree means subdirectory scans silently hit the
CONTAINING repository unless scan requires the repository root)."""

import subprocess

import pytest

from aiprofile import gitio
from aiprofile.errors import GitError


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def test_scanning_a_subdirectory_of_a_repo_is_rejected(tmp_path):
    repo = tmp_path / "realrepo"
    sub = repo / "src"
    sub.mkdir(parents=True)
    _git(["init", "-q"], repo)
    with pytest.raises(GitError, match="inside the repository"):
        gitio.assert_repository(sub)


def test_repo_root_is_accepted(tmp_path):
    repo = tmp_path / "rootrepo"
    repo.mkdir()
    _git(["init", "-q"], repo)
    gitio.assert_repository(repo)  # must not raise


def test_sha256_repository_fails_with_targeted_error(tmp_path):
    """G2-13: SHA-1-only is declared, never silently truncated."""
    repo = tmp_path / "sha256repo"
    repo.mkdir()
    probe = subprocess.run(
        ["git", "init", "-q", "--object-format=sha256"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        pytest.skip("this git build does not support --object-format=sha256")
    _git(["config", "user.email", "s@example.com"], repo)
    _git(["config", "user.name", "S"], repo)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    _git(["add", "f.txt"], repo)
    _git(["commit", "-q", "-m", "sha256 commit"], repo)
    with pytest.raises(GitError, match="SHA-256"):
        gitio.enumerate_commits(repo)

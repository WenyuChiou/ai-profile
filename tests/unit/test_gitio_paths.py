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

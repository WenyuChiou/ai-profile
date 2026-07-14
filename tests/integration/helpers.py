"""Integration-test fixture helpers (work package F).

Two responsibilities only:

- ``build_repo``: construct a throwaway git repository with deterministic,
  pinned-date commits via subprocess git (no library shortcuts — the CLI
  under test talks to real git, so the fixtures must too).
- ``run_cli``: invoke the packaged CLI (``python -m aiprofile``) as a
  subprocess against an isolated ``AIPROFILE_HOME``, exactly like a real
  user would from a shell.

Nothing here imports ``aiprofile`` — these tests exercise the installed
command-line surface end to end, not the library API (that is what
tests/unit/ is for).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

#: repo root (tests/integration/helpers.py -> integration -> tests -> root)
REPO_ROOT = Path(__file__).resolve().parents[2]

#: identity used by every fixture commit (matches the seeded git config, so
#: `aiprofile init` picks it up automatically as the sole configured identity)
FIXTURE_AUTHOR_EMAIL = "fixture@example.com"
FIXTURE_AUTHOR_NAME = "Fixture"


def _run_git(args: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {cwd} (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


def build_repo(path: Path, commits: list[tuple[str, str]]) -> Path:
    """Build a throwaway git repository at ``path``.

    ``commits`` is an ordered list of ``(message, author_date_iso)`` pairs.
    Each entry produces one commit: a small file is changed (a commit with
    an unchanged tree cannot be created), and the author/committer dates are
    pinned via ``GIT_AUTHOR_DATE``/``GIT_COMMITTER_DATE`` so scans of the
    resulting history are fully deterministic across runs and machines.
    """
    path.mkdir(parents=True, exist_ok=True)
    _run_git(["init", "-q"], path)
    _run_git(["config", "user.email", FIXTURE_AUTHOR_EMAIL], path)
    _run_git(["config", "user.name", FIXTURE_AUTHOR_NAME], path)
    _run_git(["config", "core.autocrlf", "false"], path)

    target = path / "content.txt"
    for index, (message, author_date_iso) in enumerate(commits):
        target.write_text(f"commit {index}\n", encoding="utf-8")
        _run_git(["add", "content.txt"], path)

        env = dict(os.environ)
        env["GIT_AUTHOR_NAME"] = FIXTURE_AUTHOR_NAME
        env["GIT_AUTHOR_EMAIL"] = FIXTURE_AUTHOR_EMAIL
        env["GIT_AUTHOR_DATE"] = author_date_iso
        env["GIT_COMMITTER_NAME"] = FIXTURE_AUTHOR_NAME
        env["GIT_COMMITTER_EMAIL"] = FIXTURE_AUTHOR_EMAIL
        env["GIT_COMMITTER_DATE"] = author_date_iso
        _run_git(["commit", "-q", "-m", message], path, env=env)

    return path


def run_cli(args: list[str], *, home: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run ``python -m aiprofile <args>`` as a real subprocess.

    Uses an isolated ``AIPROFILE_HOME`` (never the developer's real one) and
    points ``PYTHONPATH`` at this checkout's ``src/`` so the in-tree package
    is used without requiring an editable install.
    """
    env = dict(os.environ)
    env["AIPROFILE_HOME"] = str(home)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "aiprofile", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )

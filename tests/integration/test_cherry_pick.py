"""Cherry-pick cross-repository counting (ROADMAP "cherry-pick cross-
repository counting documented+tested").

Per ADR-007, event identity hashes ``repository_uid`` + ``commit_sha``
(schema.md section 8.1) -- not the patch content -- so the SAME logical
change, cherry-picked into a second repository, produces a NEW sha and is
counted as a SECOND, independent AI actor presence, once per repository it
lands in. This is accepted-by-design and documented explicitly in
docs/schema.md section 8.4 ("Cherry-pick and cross-repository counting"):
aiprofile counts commits, not changes.

Like tests/integration/test_end_to_end.py, this shells out to real git and
to the in-tree CLI (python -m aiprofile) via helpers.run_cli -- no aiprofile
library imports, no monkeypatching, no network.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from helpers import FIXTURE_AUTHOR_EMAIL, FIXTURE_AUTHOR_NAME, run_cli

_AI_TRAILER_MESSAGE = (
    "Claude AI-* commit\n\n"
    "AI-Provider: Anthropic\nAI-Tool: Claude-Code\nAI-Role: implementation"
)


def _git(
    args: list[str], cwd: Path, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
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
    return result


def _commit_env(date: str) -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_AUTHOR_NAME"] = FIXTURE_AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = FIXTURE_AUTHOR_EMAIL
    env["GIT_AUTHOR_DATE"] = date
    env["GIT_COMMITTER_NAME"] = FIXTURE_AUTHOR_NAME
    env["GIT_COMMITTER_EMAIL"] = FIXTURE_AUTHOR_EMAIL
    env["GIT_COMMITTER_DATE"] = date
    return env


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], path)
    _git(["config", "user.email", FIXTURE_AUTHOR_EMAIL], path)
    _git(["config", "user.name", FIXTURE_AUTHOR_NAME], path)
    _git(["config", "core.autocrlf", "false"], path)


def _head_sha(path: Path) -> str:
    return _git(["rev-parse", "HEAD"], path).stdout.strip()


def test_cherry_pick_counts_again_in_each_repository(tmp_path):
    """Build repo A with a root commit + one AI-trailer commit, cherry-pick
    the AI commit into an unrelated repo B (new sha, no shared history),
    scan both under one AIPROFILE_HOME, and assert the actor presence is
    counted in EACH repository."""
    home = tmp_path / "home"
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"

    # --- repo A: root commit + the commit that will be cherry-picked ---
    _init_repo(repo_a)
    shared_a = repo_a / "shared.txt"
    shared_a.write_text("seed\n", encoding="utf-8")
    _git(["add", "shared.txt"], repo_a)
    _git(
        ["commit", "-q", "-m", "root commit"],
        repo_a,
        env=_commit_env("2026-01-01T12:00:00+00:00"),
    )

    shared_a.write_text("seed\nai change\n", encoding="utf-8")
    _git(["add", "shared.txt"], repo_a)
    _git(
        ["commit", "-q", "-m", _AI_TRAILER_MESSAGE],
        repo_a,
        env=_commit_env("2026-01-02T12:00:00+00:00"),
    )
    ai_sha_in_a = _head_sha(repo_a)

    # --- repo B: an independent root commit with the SAME base content, so
    # the cherry-picked patch applies cleanly with no shared history at all ---
    _init_repo(repo_b)
    (repo_b / "shared.txt").write_text("seed\n", encoding="utf-8")
    _git(["add", "shared.txt"], repo_b)
    _git(
        ["commit", "-q", "-m", "root commit"],
        repo_b,
        env=_commit_env("2026-01-03T12:00:00+00:00"),
    )

    # Fetch repo A's AI commit object into repo B, then cherry-pick it --
    # this is the real `git cherry-pick`, not a copy-pasted patch.
    _git(["fetch", str(repo_a), ai_sha_in_a], repo_b)
    _git(["cherry-pick", "FETCH_HEAD"], repo_b, env=_commit_env("2026-01-04T12:00:00+00:00"))
    ai_sha_in_b = _head_sha(repo_b)

    assert ai_sha_in_a != ai_sha_in_b  # different sha: this is the whole point

    # trailers survive a plain cherry-pick (no -x) byte-for-byte
    message_b = _git(["log", "-1", "--format=%B"], repo_b).stdout
    assert "AI-Provider: Anthropic" in message_b
    assert "AI-Tool: Claude-Code" in message_b

    # --- scan both repositories under one AIPROFILE_HOME ---
    assert run_cli(["init"], home=home, cwd=repo_a).returncode == 0
    scan_a = run_cli(["scan", str(repo_a)], home=home, cwd=repo_a)
    assert scan_a.returncode == 0, scan_a.stderr
    scan_b = run_cli(["scan", str(repo_b)], home=home, cwd=repo_b)
    assert scan_b.returncode == 0, scan_b.stderr

    config = json.loads((home / "config.json").read_text(encoding="utf-8"))
    assert len(config["repositories"]) == 2
    uids = {entry["repository_uid"] for entry in config["repositories"]}
    assert len(uids) == 2  # two distinct repository_uid values -> two identities

    out = tmp_path / "dist"
    render_res = run_cli(["render", "--out", str(out)], home=home, cwd=tmp_path)
    assert render_res.returncode == 0, render_res.stderr
    profile = json.loads((out / "profile.json").read_text(encoding="utf-8"))

    # Repo A: root commit (unknown) + AI commit -> commits_scanned=2,
    # ai_attributed_commits=1, ai_actor_presences=1.
    # Repo B: root commit (unknown) + the cherry-picked AI commit, counted
    # again because it has repository_uid_B + a NEW commit_sha (ADR-007
    # section 8.1 identity fields) -> another commits_scanned=2,
    # ai_attributed_commits=1, ai_actor_presences=1.
    # Combined across both repositories (privacy.py sums per-repo aggregates):
    assert profile["totals"]["commits_scanned"] == 4
    assert profile["totals"]["ai_attributed_commits"] == 2
    assert profile["totals"]["ai_actor_presences"] == 2
    assert profile["totals"]["unknown_commits"] == 2
    assert profile["totals"]["human_declared_commits"] == 0

    anthropic = next(p for p in profile["providers"] if p["provider"] == "anthropic")
    assert anthropic["attributed_commits"] == 2
    assert anthropic["actor_presences"] == 2

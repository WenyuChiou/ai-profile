"""Real-git scheduler launcher publication tests (v0.7.0 Task B2)."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiprofile.export import PUBLIC_ASSET_NAMES
from aiprofile.schedule import launcher, service

PATHS = tuple(f"dist/{name}" for name in sorted(PUBLIC_ASSET_NAMES))


def _git(repo: Path, *args: str, check: bool = True):
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"git command failed: {args}: {result.stderr}")
    return result


def _setup(tmp_path: Path, *, push: bool = True, shared: bool = False):
    profile = tmp_path / "profile"
    profile.mkdir()
    init_args = ["init", "-q", "-b", "main"]
    if shared:
        init_args.append("--shared=group")
    _git(profile, *init_args)
    _git(profile, "config", "user.name", "Fixture")
    _git(profile, "config", "user.email", "fixture@example.com")
    (profile / "README.md").write_text("profile\n", encoding="utf-8")
    _git(profile, "add", "README.md")
    _git(profile, "commit", "-q", "-m", "seed")

    bare = tmp_path / "remote.git"
    bare.mkdir()
    _git(bare, "init", "-q", "--bare")
    _git(profile, "remote", "add", "origin", bare.resolve().as_uri())
    _git(profile, "push", "-q", "-u", "origin", "main")

    home = tmp_path / "home"
    service.write_scheduler_files(
        home, profile, "07:30", push, branch="main", remote="origin"
    )
    return home, profile, bare


def _refresh_writer(content: str):
    def refresh(_home, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in PUBLIC_ASSET_NAMES:
            (out_dir / name).write_text(f"{name}:{content}\n", encoding="utf-8")
        return SimpleNamespace(ok=True, failures=(), written=tuple(out_dir.iterdir()))

    return refresh


def _advance_current_ref_atomically(profile: Path, subject: str) -> str:
    old = _git(profile, "rev-parse", "HEAD").stdout.strip()
    tree = _git(profile, "rev-parse", "HEAD^{tree}").stdout.strip()
    created = subprocess.run(
        ["git", "commit-tree", tree, "-p", old],
        cwd=str(profile),
        input=f"{subject}\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert created.returncode == 0, created.stderr
    new_oid = created.stdout.strip()
    _git(profile, "update-ref", "refs/heads/main", new_oid, old)
    return new_oid


def test_commit_uses_exact_pathspec_and_ignores_prestaged_files(tmp_path, monkeypatch):
    home, profile, _bare = _setup(tmp_path)
    secret = profile / "secret.txt"
    secret.write_text("private\n", encoding="utf-8")
    _git(profile, "add", "secret.txt")
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("first"))

    assert launcher.run_launcher(home) == 0
    changed = sorted(
        line
        for line in _git(profile, "show", "--format=", "--name-only", "HEAD").stdout.splitlines()
        if line
    )
    assert changed == sorted(PATHS)
    assert _git(profile, "diff", "--cached", "--name-only").stdout.strip() == "secret.txt"
    assert all((profile / path).exists() for path in PATHS)
    assert not list((home / "scheduler").glob(".publication-index-*"))


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits only")
@pytest.mark.parametrize("shared", [False, True])
def test_private_index_is_confined_and_removed(tmp_path, monkeypatch, shared):
    home, profile, _bare = _setup(tmp_path, push=False, shared=shared)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("private-index"))
    observed_parent_modes = []
    observed_final_index_modes = []

    def runner(argv, **kwargs):
        result = subprocess.run(argv, **kwargs)
        if any(operation in argv for operation in ("read-tree", "add", "write-tree")):
            index = Path(kwargs["env"]["GIT_INDEX_FILE"])
            observed_parent_modes.append(stat.S_IMODE(index.parent.stat().st_mode))
        if "rev-parse" in argv and argv[-1].endswith("^{tree}"):
            index = Path(next(iter(observed_index_paths)))
            observed_final_index_modes.append(stat.S_IMODE(index.stat().st_mode))
        return result

    observed_index_paths = set()

    def recording_runner(argv, **kwargs):
        if "env" in kwargs and "GIT_INDEX_FILE" in kwargs["env"]:
            observed_index_paths.add(kwargs["env"]["GIT_INDEX_FILE"])
        return runner(argv, **kwargs)

    previous_umask = os.umask(0o022)
    try:
        assert launcher.run_launcher(home, runner=recording_runner) == 0
        restored_umask = os.umask(0o022)
        assert restored_umask == 0o022
    finally:
        os.umask(previous_umask)

    assert observed_parent_modes == [0o700, 0o700, 0o700]
    assert observed_final_index_modes == [0o600]
    assert not list((home / "scheduler").glob(".publication-index-*"))


@pytest.mark.skipif(os.name == "nt", reason="POSIX umask only")
def test_private_index_cleanup_preserves_umask_when_runner_raises(tmp_path):
    home = tmp_path / "home"
    (home / "scheduler").mkdir(parents=True)
    profile = tmp_path / "profile"
    profile.mkdir()

    def runner(argv, **kwargs):
        if "read-tree" in argv:
            Path(kwargs["env"]["GIT_INDEX_FILE"]).touch()
            return subprocess.CompletedProcess(argv, 0, "", "")
        if "add" in argv:
            raise RuntimeError("runner failure")
        raise AssertionError(argv)

    previous_umask = os.umask(0o022)
    try:
        with pytest.raises(RuntimeError, match="runner failure"):
            launcher._prepare_commit(
                runner,
                "git",
                profile,
                home=home,
                head_oid="a" * 40,
            )
        restored_umask = os.umask(0o022)
        assert restored_umask == 0o022
    finally:
        os.umask(previous_umask)

    assert not list((home / "scheduler").glob(".publication-index-*"))


def _loose_object_modes(profile: Path) -> tuple[set[int], set[int]]:
    objects = profile / ".git" / "objects"
    directories: set[int] = set()
    files: set[int] = set()
    for directory in objects.iterdir():
        if len(directory.name) != 2 or not directory.is_dir():
            continue
        try:
            int(directory.name, 16)
        except ValueError:
            continue
        directories.add(stat.S_IMODE(directory.stat().st_mode))
        for item in directory.iterdir():
            if item.is_file():
                files.add(stat.S_IMODE(item.stat().st_mode))
    return directories, files


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits only")
@pytest.mark.parametrize("shared", [False, True])
def test_private_index_preserves_repository_object_modes(tmp_path, monkeypatch, shared):
    previous_umask = os.umask(0o022)
    try:
        home, profile, _bare = _setup(tmp_path, push=False, shared=shared)
        baseline = _loose_object_modes(profile)
        monkeypatch.setattr(
            launcher.refresh,
            "run_refresh",
            _refresh_writer(f"object-modes-{shared}"),
        )

        assert launcher.run_launcher(home) == 0
        assert _loose_object_modes(profile) == baseline
        restored_umask = os.umask(0o022)
        assert restored_umask == 0o022
    finally:
        os.umask(previous_umask)


def test_scheduler_commit_does_not_execute_repository_hooks(tmp_path, monkeypatch):
    home, profile, _bare = _setup(tmp_path, push=False)
    marker = profile / "hook-ran"
    hook = profile / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nprintf ran > hook-ran\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("no-hooks"))

    assert launcher.run_launcher(home) == 0
    assert not marker.exists()


def test_no_change_means_no_commit(tmp_path, monkeypatch):
    home, profile, _bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("stable"))
    assert launcher.run_launcher(home) == 0
    first = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert launcher.run_launcher(home) == 0
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == first
    assert "no change" in (home / "scheduler" / "last-run.log").read_text(
        encoding="utf-8"
    )


def test_staged_only_tool_path_difference_does_not_create_empty_commit(
    tmp_path, monkeypatch
):
    home, profile, _bare = _setup(tmp_path, push=False)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("stable"))
    assert launcher.run_launcher(home) == 0
    before = _git(profile, "rev-parse", "HEAD").stdout.strip()

    tool_path = profile / PATHS[0]
    committed_bytes = tool_path.read_bytes()
    tool_path.write_text("staged-only difference\n", encoding="utf-8")
    _git(profile, "add", PATHS[0])
    tool_path.write_bytes(committed_bytes)

    assert launcher.run_launcher(home) == 0
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == before
    assert _git(profile, "diff", "--cached", "--name-only").stdout.strip() == PATHS[0]
    assert "no change" in (home / "scheduler" / "last-run.log").read_text(
        encoding="utf-8"
    ).splitlines()[-1]


@pytest.mark.parametrize("detached", [False, True])
def test_launcher_refuses_on_branch_drift(tmp_path, monkeypatch, detached):
    home, profile, _bare = _setup(tmp_path)
    if detached:
        _git(profile, "checkout", "-q", "--detach")
    else:
        _git(profile, "checkout", "-q", "-b", "other")
    calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("refresh must not run")

    monkeypatch.setattr(launcher.refresh, "run_refresh", forbidden)
    assert launcher.run_launcher(home) == 1
    assert calls == 0
    assert "recorded branch is no longer checked out" in (
        home / "scheduler" / "last-run.log"
    ).read_text(encoding="utf-8")


def test_launcher_refuses_branch_switch_during_refresh_before_git_mutation(
    tmp_path, monkeypatch
):
    home, profile, _bare = _setup(tmp_path)
    before = _git(profile, "rev-parse", "HEAD").stdout.strip()

    def refresh_then_switch(call_home, out_dir):
        result = _refresh_writer("drifted")(call_home, out_dir)
        _git(profile, "checkout", "-q", "-b", "other")
        return result

    monkeypatch.setattr(launcher.refresh, "run_refresh", refresh_then_switch)
    assert launcher.run_launcher(home) == 1
    assert _git(profile, "branch", "--show-current").stdout.strip() == "other"
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == before
    assert _git(profile, "diff", "--cached", "--name-only").stdout.strip() == ""
    assert "repository state changed during scheduled refresh" in (
        home / "scheduler" / "last-run.log"
    ).read_text(encoding="utf-8")


def test_launcher_refuses_head_oid_change_during_refresh(tmp_path, monkeypatch):
    home, profile, _bare = _setup(tmp_path)
    before = _git(profile, "rev-parse", "HEAD").stdout.strip()

    def refresh_then_commit(call_home, out_dir):
        result = _refresh_writer("drifted-oid")(call_home, out_dir)
        _git(profile, "commit", "--allow-empty", "-q", "-m", "concurrent change")
        return result

    monkeypatch.setattr(launcher.refresh, "run_refresh", refresh_then_commit)
    assert launcher.run_launcher(home) == 1
    after = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert after != before
    assert _git(profile, "rev-list", "--count", f"{before}..{after}").stdout.strip() == "1"
    assert _git(profile, "diff", "--cached", "--name-only").stdout.strip() == ""


def test_branch_drift_after_real_add_restores_only_tool_index_paths(
    tmp_path, monkeypatch
):
    home, profile, _bare = _setup(tmp_path, push=False)
    secret = profile / "secret.txt"
    secret.write_text("private\n", encoding="utf-8")
    _git(profile, "add", "secret.txt")
    before = _git(profile, "rev-parse", "HEAD").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("race"))

    switched = False

    def runner(argv, **kwargs):
        nonlocal switched
        result = subprocess.run(argv, **kwargs)
        if "add" in argv and result.returncode == 0 and not switched:
            switched = True
            _git(profile, "checkout", "-q", "-b", "other")
        return result

    assert launcher.run_launcher(home, runner=runner) == 1
    assert switched is True
    assert _git(profile, "branch", "--show-current").stdout.strip() == "other"
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == before
    assert _git(profile, "diff", "--cached", "--name-only").stdout.strip() == "secret.txt"


@pytest.mark.parametrize("push", [False, True])
def test_atomic_ref_advance_before_scheduler_commit_refuses_publication(
    tmp_path, monkeypatch, push
):
    home, profile, bare = _setup(tmp_path, push=push)
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    base = _git(profile, "rev-parse", "HEAD").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("parent-race"))
    injected = None

    def runner(argv, **kwargs):
        nonlocal injected
        result = subprocess.run(argv, **kwargs)
        if "commit-tree" in argv and result.returncode == 0 and injected is None:
            injected = _advance_current_ref_atomically(profile, "concurrent ref advance")
        return result

    assert launcher.run_launcher(home, runner=runner) == 1
    assert injected is not None
    local = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert _git(profile, "rev-list", "--count", f"{base}..{local}").stdout.strip() == "1"
    assert _git(profile, "rev-parse", "HEAD^").stdout.strip() == base
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before
    assert "repository state changed before branch update; publication refused" in (
        home / "scheduler" / "last-run.log"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize("switch_before", ["update-ref", "reset"])
def test_branch_switch_at_cas_boundary_rolls_back_without_index_pollution(
    tmp_path, monkeypatch, switch_before
):
    home, profile, bare = _setup(tmp_path)
    base = _git(profile, "rev-parse", "HEAD").stdout.strip()
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    (profile / "secret.txt").write_text("private staged content\n", encoding="utf-8")
    _git(profile, "add", "secret.txt")
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("cas-race"))
    switched = False

    def runner(argv, **kwargs):
        nonlocal switched
        if switch_before in argv and not switched:
            switched = True
            _git(profile, "checkout", "-q", "-b", "other")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 1
    assert switched is True
    assert _git(profile, "branch", "--show-current").stdout.strip() == "other"
    assert _git(profile, "rev-parse", "refs/heads/main").stdout.strip() == base
    assert _git(profile, "diff", "--cached", "--name-only").stdout.strip() == "secret.txt"
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "publication rolled back" in log


def test_ref_advance_after_cas_cleans_index_and_refuses_push(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    (profile / "secret.txt").write_text("private staged content\n", encoding="utf-8")
    _git(profile, "add", "secret.txt")
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("post-cas"))
    injected = None

    def runner(argv, **kwargs):
        nonlocal injected
        if "reset" in argv and injected is None:
            injected = _advance_current_ref_atomically(profile, "post-CAS advance")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 1
    assert injected is not None
    assert _git(profile, "rev-parse", "refs/heads/main").stdout.strip() == injected
    assert _git(profile, "diff", "--cached", "--name-only").stdout.strip() == "secret.txt"
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "local scheduler commit or ref may remain" in log
    assert "push was refused" in log


def test_drift_cleanup_failure_reports_staged_residual(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    base = _git(profile, "rev-parse", "HEAD").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("cleanup-fail"))
    reset_calls = 0

    def runner(argv, **kwargs):
        nonlocal reset_calls
        if "reset" in argv:
            reset_calls += 1
            if reset_calls == 1:
                _git(profile, "checkout", "-q", "-b", "other")
            else:
                return subprocess.CompletedProcess(argv, 19, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 1
    assert reset_calls == 2
    assert _git(profile, "rev-parse", "refs/heads/main").stdout.strip() == base
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == base
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "publication rolled back" in log
    assert "tool paths may remain staged" in log
    assert "push was refused" in log
    assert "private-path-canary" not in log


def test_cleanup_and_rollback_failure_reports_both_residuals(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("dual-fail"))
    reset_calls = 0
    injected = None

    def runner(argv, **kwargs):
        nonlocal reset_calls, injected
        if "reset" in argv:
            reset_calls += 1
            if reset_calls == 1:
                _git(profile, "checkout", "-q", "-b", "other")
                scheduler_oid = _git(profile, "rev-parse", "refs/heads/main").stdout.strip()
                tree = _git(profile, "rev-parse", f"{scheduler_oid}^{{tree}}").stdout.strip()
                created = subprocess.run(
                    ["git", "commit-tree", tree, "-p", scheduler_oid],
                    cwd=str(profile),
                    input="concurrent main advance\n",
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=60,
                )
                assert created.returncode == 0, created.stderr
                injected = created.stdout.strip()
                _git(
                    profile,
                    "update-ref",
                    "refs/heads/main",
                    injected,
                    scheduler_oid,
                )
            else:
                return subprocess.CompletedProcess(argv, 21, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 1
    assert injected is not None
    assert _git(profile, "rev-parse", "refs/heads/main").stdout.strip() == injected
    remote = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    assert remote != injected
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "tool paths may remain staged" in log
    assert "local scheduler commit or ref may remain" in log
    assert "push was refused" in log
    assert "private-path-canary" not in log


def test_push_uses_captured_commit_when_head_advances_after_final_check(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("push-race"))
    scheduler_oid = None
    injected = None
    push_argv = None

    def runner(argv, **kwargs):
        nonlocal scheduler_oid, injected, push_argv
        if "push" in argv:
            push_argv = argv
            scheduler_oid = _git(profile, "rev-parse", "HEAD").stdout.strip()
            injected = _advance_current_ref_atomically(profile, "post-check ref advance")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 0
    assert scheduler_oid is not None and injected is not None and push_argv is not None
    assert scheduler_oid != injected
    assert push_argv[-1] == f"{scheduler_oid}:refs/heads/main"
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == scheduler_oid
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == injected


def test_push_default_and_no_push(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("pushed"))
    before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    assert launcher.run_launcher(home) == 0
    pushed = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    assert pushed != before
    assert pushed == _git(profile, "rev-parse", "HEAD").stdout.strip()

    service.write_scheduler_files(
        home, profile, "07:30", False, branch="main", remote="origin"
    )
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("local-only"))
    assert launcher.run_launcher(home) == 0
    local = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert local != pushed
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == pushed


def test_real_index_sync_failure_retains_local_commit_and_refuses_push(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("sync-failure"))

    def runner(argv, **kwargs):
        if "reset" in argv:
            return subprocess.CompletedProcess(argv, 17, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 1
    local = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert local != remote_before
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before
    staged = _git(profile, "diff", "--cached", "--name-only").stdout.splitlines()
    assert sorted(staged) == sorted(PATHS)
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "tool paths may remain staged and push was refused" in log
    assert "private-path-canary" not in log

"""Real-git scheduler launcher publication tests (v0.7.0 Task B2)."""

from __future__ import annotations

import hashlib
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


def _setup(
    tmp_path: Path,
    *,
    push: bool = True,
    shared: bool = False,
    profile_name: str = "profile",
):
    profile = tmp_path / profile_name
    profile.mkdir(parents=True)
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


def _setup_shallow(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-q", "-b", "main")
    _git(source, "config", "user.name", "Fixture")
    _git(source, "config", "user.email", "fixture@example.com")
    for index in range(3):
        (source / "README.md").write_text(f"profile {index}\n", encoding="utf-8")
        _git(source, "add", "README.md")
        _git(source, "commit", "-q", "-m", f"seed {index}")

    bare = tmp_path / "remote.git"
    bare.mkdir()
    _git(bare, "init", "-q", "--bare")
    _git(source, "remote", "add", "origin", bare.resolve().as_uri())
    _git(source, "push", "-q", "origin", "main")

    profile = tmp_path / "profile"
    result = subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--depth=1",
            "-b",
            "main",
            bare.resolve().as_uri(),
            str(profile),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    _git(profile, "config", "user.name", "Fixture")
    _git(profile, "config", "user.email", "fixture@example.com")
    assert _git(profile, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"

    home = tmp_path / "home"
    service.write_scheduler_files(
        home, profile, "07:30", True, branch="main", remote="origin"
    )
    return home, profile, bare


def _refresh_writer(content: str):
    def refresh(_home, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in PUBLIC_ASSET_NAMES:
            (out_dir / name).write_bytes(f"{name}:{content}\n".encode())
        manifest = tuple(
            launcher.refresh.AssetDigest(
                name=name,
                sha256=hashlib.sha256((out_dir / name).read_bytes()).hexdigest(),
            )
            for name in sorted(PUBLIC_ASSET_NAMES)
        )
        return SimpleNamespace(
            ok=True,
            failures=(),
            written=tuple(out_dir.iterdir()),
            asset_manifest=manifest,
        )

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


def _prepare_remote_parent(profile: Path) -> tuple[str, str]:
    prior = _git(profile, "rev-parse", "HEAD").stdout.strip()
    (profile / "README.md").write_text("published parent\n", encoding="utf-8")
    _git(profile, "add", "README.md")
    _git(profile, "commit", "-q", "-m", "published parent")
    expected = _git(profile, "rev-parse", "HEAD").stdout.strip()
    _git(profile, "push", "-q", "origin", "main")
    return expected, prior


def _remote_boundary_change(
    profile: Path,
    bare: Path,
    *,
    expected: str,
    prior: str,
    change: str,
) -> str | None:
    if change == "rewind":
        _git(bare, "update-ref", "refs/heads/main", prior, expected)
        return prior
    if change == "missing":
        _git(bare, "update-ref", "-d", "refs/heads/main", expected)
        return None
    if change == "advance":
        tree = _git(profile, "rev-parse", f"{expected}^{{tree}}").stdout.strip()
        created = subprocess.run(
            ["git", "commit-tree", tree, "-p", expected, "-m", "remote advance"],
            cwd=str(profile),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        assert created.returncode == 0, created.stderr
        advanced = created.stdout.strip()
        _git(profile, "push", "-q", "origin", f"{advanced}:refs/heads/main")
        return advanced
    if change == "no-op-success":
        return expected
    raise AssertionError(f"unexpected boundary change: {change}")


def _remote_boundary_change_with_content(
    profile: Path,
    *,
    expected: str,
) -> str:
    original = (profile / "README.md").read_text(encoding="utf-8")
    (profile / "README.md").write_text("remote advance\n", encoding="utf-8")
    _git(profile, "add", "README.md")
    tree = _git(profile, "write-tree").stdout.strip()
    (profile / "README.md").write_text(original, encoding="utf-8")
    _git(profile, "reset", "-q", "HEAD", "--", "README.md")
    assert (profile / "README.md").read_text(encoding="utf-8") == original
    created = subprocess.run(
        ["git", "commit-tree", tree, "-p", expected, "-m", "remote advance"],
        cwd=str(profile),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert created.returncode == 0, created.stderr
    advanced = created.stdout.strip()
    _git(profile, "push", "-q", "origin", f"{advanced}:refs/heads/main")
    return advanced


def _remote_main(bare: Path) -> str | None:
    result = _git(bare, "rev-parse", "--verify", "refs/heads/main", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


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
                expected_manifest=(),
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


def test_launcher_fast_forwards_clean_checkout_when_remote_is_ahead(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    local_parent = _git(profile, "rev-parse", "HEAD").stdout.strip()
    remote_tip = _remote_boundary_change_with_content(
        profile,
        expected=local_parent,
    )
    assert remote_tip is not None
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_parent
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("remote-ahead"))

    assert launcher.run_launcher(home) == 0
    scheduler_commit = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert _git(profile, "rev-parse", "HEAD^").stdout.strip() == remote_tip
    assert scheduler_commit == _remote_main(bare)
    assert (profile / "README.md").read_text(encoding="utf-8") == "remote advance\n"
    assert _git(profile, "status", "--porcelain").stdout == ""


def test_launcher_keeps_dirty_checkout_fail_closed_when_remote_is_ahead(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    local_parent = _git(profile, "rev-parse", "HEAD").stdout.strip()
    remote_tip = _remote_boundary_change(
        profile,
        bare,
        expected=local_parent,
        prior=local_parent,
        change="advance",
    )
    assert remote_tip is not None
    (profile / "local-notes.txt").write_text("keep me\n", encoding="utf-8")
    refreshed = False

    def forbidden_refresh(*_args, **_kwargs):
        nonlocal refreshed
        refreshed = True
        raise AssertionError("dirty remote-ahead checkout must not refresh")

    monkeypatch.setattr(launcher.refresh, "run_refresh", forbidden_refresh)
    assert launcher.run_launcher(home) == 1
    assert refreshed is False
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_parent
    assert _remote_main(bare) == remote_tip
    assert (profile / "local-notes.txt").read_text(encoding="utf-8") == "keep me\n"
    assert "remote branch does not match local HEAD" in (
        home / "scheduler" / "last-run.log"
    ).read_text(encoding="utf-8")


def test_launcher_refuses_diverged_local_and_remote_history(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    common_parent = _git(profile, "rev-parse", "HEAD").stdout.strip()
    local_tip = _advance_current_ref_atomically(profile, "local deliberate change")
    remote_tip = _remote_boundary_change(
        profile,
        bare,
        expected=common_parent,
        prior=common_parent,
        change="advance",
    )
    assert remote_tip is not None and remote_tip != local_tip
    refreshed = False

    def forbidden_refresh(*_args, **_kwargs):
        nonlocal refreshed
        refreshed = True
        raise AssertionError("diverged checkout must not refresh")

    monkeypatch.setattr(launcher.refresh, "run_refresh", forbidden_refresh)
    assert launcher.run_launcher(home) == 1
    assert refreshed is False
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_tip
    assert _remote_main(bare) == remote_tip


def test_launcher_rolls_back_fast_forward_when_checkout_update_fails(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    local_parent = _git(profile, "rev-parse", "HEAD").stdout.strip()
    remote_tip = _remote_boundary_change(
        profile,
        bare,
        expected=local_parent,
        prior=local_parent,
        change="advance",
    )
    assert remote_tip is not None
    failed = False

    def runner(argv, **kwargs):
        nonlocal failed
        if "read-tree" in argv and "-u" in argv and not failed:
            result = subprocess.run(argv, **kwargs)
            failed = True
            return subprocess.CompletedProcess(
                argv, 17, result.stdout, "checkout failed after mutation"
            )
        return subprocess.run(argv, **kwargs)

    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("rollback"))
    assert launcher.run_launcher(home, runner=runner) == 1
    assert failed is True
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_parent
    assert _git(profile, "status", "--porcelain").stdout == ""
    assert (profile / "README.md").read_text(encoding="utf-8") == "profile\n"
    assert _remote_main(bare) == remote_tip


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
    assert "pending retry state remains" in log
    assert "push was refused" in log
    assert (home / "scheduler" / "pending-push.json").is_file()


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
    assert "pending retry state remains" in log
    assert "push was refused" in log
    assert "private-path-canary" not in log
    assert (home / "scheduler" / "pending-push.json").is_file()


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


@pytest.mark.parametrize("change", ["rewind", "advance", "missing", "no-op-success"])
def test_direct_push_uses_exact_remote_parent_lease(
    tmp_path, monkeypatch, change
):
    home, profile, bare = _setup(tmp_path)
    expected, prior = _prepare_remote_parent(profile)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("leased"))
    changed = False
    boundary_tip = None

    def runner(argv, **kwargs):
        nonlocal changed, boundary_tip
        if "push" in argv and not changed:
            changed = True
            boundary_tip = _remote_boundary_change(
                profile,
                bare,
                expected=expected,
                prior=prior,
                change=change,
            )
            if change == "no-op-success":
                return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 1
    assert changed is True
    assert _remote_main(bare) == boundary_tip
    assert (home / "scheduler" / "pending-push.json").is_file()
    tail = (home / "scheduler" / "last-run.log").read_text(
        encoding="utf-8"
    ).splitlines()[-1]
    assert "pending commit retained" in tail
    assert "refresh committed and pushed" not in tail


@pytest.mark.parametrize("change", ["rewind", "advance", "missing", "no-op-success"])
def test_pending_retry_push_uses_exact_remote_parent_lease(
    tmp_path, monkeypatch, change
):
    home, profile, bare = _setup(tmp_path)
    expected, prior = _prepare_remote_parent(profile)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("retry-lease"))

    def fail_first_push(argv, **kwargs):
        if "push" in argv:
            return subprocess.CompletedProcess(argv, 17, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=fail_first_push) == 1
    pending = home / "scheduler" / "pending-push.json"
    assert pending.is_file()
    changed = False
    boundary_tip = None

    def retry_runner(argv, **kwargs):
        nonlocal changed, boundary_tip
        if "push" in argv and not changed:
            changed = True
            boundary_tip = _remote_boundary_change(
                profile,
                bare,
                expected=expected,
                prior=prior,
                change=change,
            )
            if change == "no-op-success":
                return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=retry_runner) == 1
    assert changed is True
    assert _remote_main(bare) == boundary_tip
    assert pending.is_file()
    tail = (home / "scheduler" / "last-run.log").read_text(
        encoding="utf-8"
    ).splitlines()[-1]
    assert "pending commit retained" in tail
    assert "refresh committed and pushed" not in tail


def test_verified_remote_commit_wins_over_uncertain_push_exit(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("verified"))

    def runner(argv, **kwargs):
        result = subprocess.run(argv, **kwargs)
        if "push" in argv and result.returncode == 0:
            return subprocess.CompletedProcess(argv, 17, "", "private-path-canary")
        return result

    assert launcher.run_launcher(home, runner=runner) == 0
    assert _remote_main(bare) == _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert not (home / "scheduler" / "pending-push.json").exists()


def test_post_push_remote_advance_is_not_reported_as_success(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("post-push"))
    advanced = None

    def runner(argv, **kwargs):
        nonlocal advanced
        result = subprocess.run(argv, **kwargs)
        if "push" in argv and result.returncode == 0:
            commit_oid = argv[-1].split(":", 1)[0]
            advanced = _remote_boundary_change(
                profile,
                bare,
                expected=commit_oid,
                prior=_git(profile, "rev-parse", f"{commit_oid}^").stdout.strip(),
                change="advance",
            )
        return result

    assert launcher.run_launcher(home, runner=runner) == 1
    assert advanced is not None and _remote_main(bare) == advanced
    assert (home / "scheduler" / "pending-push.json").is_file()
    tail = (home / "scheduler" / "last-run.log").read_text(
        encoding="utf-8"
    ).splitlines()[-1]
    assert "remote publication is not confirmed" in tail
    assert "refresh committed and pushed" not in tail


def _add_second_push_destination(profile: Path, destination: Path) -> None:
    destination.mkdir()
    _git(destination, "init", "-q", "--bare")
    fetch_url = _git(
        profile, "remote", "get-url", "origin"
    ).stdout.strip()
    _git(profile, "config", "--add", "remote.origin.pushurl", fetch_url)
    _git(
        profile,
        "config",
        "--add",
        "remote.origin.pushurl",
        destination.resolve().as_uri(),
    )


def test_direct_publication_rejects_multiple_push_destinations_before_mutation(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    second = tmp_path / "second-remote.git"
    _add_second_push_destination(profile, second)
    local_before = _git(profile, "rev-parse", "HEAD").stdout.strip()
    remote_before = _remote_main(bare)
    index_before = _git(profile, "diff", "--cached", "--name-only").stdout
    refresh_called = False

    def forbidden_refresh(*_args, **_kwargs):
        nonlocal refresh_called
        refresh_called = True
        raise AssertionError("refresh must not run for unsupported remote topology")

    monkeypatch.setattr(launcher.refresh, "run_refresh", forbidden_refresh)

    assert launcher.run_launcher(home) == 1
    assert refresh_called is False
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_before
    assert _remote_main(bare) == remote_before
    assert _git(profile, "diff", "--cached", "--name-only").stdout == index_before
    assert not (home / "scheduler" / "pending-push.json").exists()


def test_pending_retry_rejects_multiple_push_destinations_before_mutation(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("pending"))

    def fail_push(argv, **kwargs):
        if "push" in argv:
            return subprocess.CompletedProcess(argv, 17, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=fail_push) == 1
    pending = home / "scheduler" / "pending-push.json"
    assert pending.is_file()
    second = tmp_path / "second-remote.git"
    _add_second_push_destination(profile, second)
    local_before = _git(profile, "rev-parse", "HEAD").stdout.strip()
    remote_before = _remote_main(bare)
    index_before = _git(profile, "diff", "--cached", "--name-only").stdout

    monkeypatch.setattr(
        launcher.refresh,
        "run_refresh",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("refresh must not run while pending publication is blocked")
        ),
    )

    assert launcher.run_launcher(home) == 1
    assert pending.is_file()
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_before
    assert _remote_main(bare) == remote_before
    assert _git(profile, "diff", "--cached", "--name-only").stdout == index_before


def _seed_second_remote(profile: Path, destination: Path, oid: str) -> None:
    destination.mkdir()
    _git(destination, "init", "-q", "--bare")
    _git(profile, "push", "-q", destination.resolve().as_uri(), f"{oid}:refs/heads/main")


def test_direct_push_uses_captured_destination_when_remote_config_changes(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    parent = _remote_main(bare)
    second = tmp_path / "second-remote.git"
    _seed_second_remote(profile, second, parent)
    second_url = second.resolve().as_uri()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("captured"))
    changed = False

    def runner(argv, **kwargs):
        nonlocal changed
        if "push" in argv and not changed:
            changed = True
            _git(profile, "remote", "set-url", "origin", second_url)
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 0
    committed = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert changed is True
    assert _remote_main(bare) == committed
    assert _remote_main(second) == parent


@pytest.mark.parametrize("rewrite_key", ["insteadOf", "pushInsteadOf"])
def test_direct_push_isolated_from_late_url_rewrite(
    tmp_path, monkeypatch, rewrite_key
):
    home, profile, bare = _setup(tmp_path)
    parent = _remote_main(bare)
    second = tmp_path / "rewrite-target.git"
    _seed_second_remote(profile, second, parent)
    original_url = bare.resolve().as_uri()
    second_url = second.resolve().as_uri()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("rewrite"))
    changed = False

    def runner(argv, **kwargs):
        nonlocal changed
        if "push" in argv and not changed:
            changed = True
            _git(profile, "config", f"url.{second_url}.{rewrite_key}", original_url)
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 0
    committed = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert changed is True
    assert _remote_main(bare) == committed
    assert _remote_main(second) == parent


def test_isolated_transport_supports_profile_path_with_path_separator(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(
        tmp_path, profile_name=f"profile{os.pathsep}separator"
    )
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("separator"))
    objects = profile / ".git" / "objects"
    def object_manifest():
        return {
            path.relative_to(objects).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in objects.rglob("*")
            if path.is_file()
        }

    push_checked = False

    def runner(argv, **kwargs):
        nonlocal push_checked
        if "push" not in argv:
            return subprocess.run(argv, **kwargs)
        before = object_manifest()
        result = subprocess.run(argv, **kwargs)
        assert object_manifest() == before
        push_checked = True
        return result

    assert launcher.run_launcher(home, runner=runner) == 0
    assert push_checked is True
    assert _remote_main(bare) == _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert not list((home / "scheduler").glob(".publication-transport-*"))


@pytest.mark.parametrize("pending_retry", [False, True])
def test_relative_local_destination_is_bound_to_profile_repo(
    tmp_path, monkeypatch, pending_retry
):
    home, profile, intended = _setup(tmp_path, profile_name="nested/profile")
    parent = _remote_main(intended)
    wrong = home / "remote.git"
    _seed_second_remote(profile, wrong, parent)
    _git(profile, "config", "remote.origin.url", "../../remote.git")
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("relative"))

    if pending_retry:
        def fail_push(argv, **kwargs):
            if "push" in argv:
                return subprocess.CompletedProcess(argv, 17, "", "private-canary")
            return subprocess.run(argv, **kwargs)

        assert launcher.run_launcher(home, runner=fail_push) == 1
        assert (home / "scheduler" / "pending-push.json").is_file()

    assert launcher.run_launcher(home) == 0
    committed = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert _remote_main(intended) == committed
    assert _remote_main(wrong) == parent
    assert not (home / "scheduler" / "pending-push.json").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows drive-relative path semantics")
@pytest.mark.parametrize("pending_retry", [False, True])
def test_windows_drive_relative_destination_is_bound_to_profile_repo(
    tmp_path, monkeypatch, pending_retry
):
    home, profile, intended = _setup(tmp_path, profile_name="nested/profile")
    parent = _remote_main(intended)
    wrong = home / "remote.git"
    _seed_second_remote(profile, wrong, parent)
    _git(profile, "config", "remote.origin.url", f"{profile.drive}../../remote.git")
    monkeypatch.setattr(
        launcher.refresh, "run_refresh", _refresh_writer("drive-relative")
    )

    if pending_retry:
        def fail_push(argv, **kwargs):
            if "push" in argv:
                return subprocess.CompletedProcess(argv, 17, "", "private-canary")
            return subprocess.run(argv, **kwargs)

        assert launcher.run_launcher(home, runner=fail_push) == 1
        assert (home / "scheduler" / "pending-push.json").is_file()

    assert launcher.run_launcher(home) == 0
    committed = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert _remote_main(intended) == committed
    assert _remote_main(wrong) == parent
    assert not (home / "scheduler" / "pending-push.json").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX SCP syntax")
def test_posix_one_letter_host_scp_uses_fixed_alias_without_raw_destination(
    tmp_path, monkeypatch
):
    home, profile, _bare = _setup(tmp_path)
    destination = "x:owner/repo.git"
    _git(profile, "config", "remote.origin.url", destination)
    parent = _git(profile, "rev-parse", "HEAD").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("scp"))
    pushed_oid = None

    def runner(argv, **kwargs):
        nonlocal pushed_oid
        if "push" in argv:
            assert destination not in argv
            pushed_oid = argv[-1].split(":", 1)[0]
            return subprocess.CompletedProcess(argv, 0, "", "")
        if "ls-remote" in argv:
            assert destination not in argv
            oid = pushed_oid or parent
            return subprocess.CompletedProcess(
                argv, 0, f"{oid}\trefs/heads/main\n", ""
            )
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 0
    assert pushed_oid == _git(profile, "rev-parse", "HEAD").stdout.strip()


def test_shallow_repository_is_rejected_before_refresh_or_publication(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup_shallow(tmp_path)
    parent = _git(profile, "rev-parse", "HEAD").stdout.strip()
    refreshed = False

    def refresh_writer(*_args, **_kwargs):
        nonlocal refreshed
        refreshed = True
        return _refresh_writer("shallow")(*_args, **_kwargs)

    monkeypatch.setattr(launcher.refresh, "run_refresh", refresh_writer)

    assert launcher.run_launcher(home) == 1
    assert refreshed is False
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == parent
    assert _remote_main(bare) == parent
    assert not (home / "scheduler" / "pending-push.json").exists()
    assert not (profile / "dist").exists()


def test_pending_retry_refuses_repository_that_became_shallow(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    parent = _remote_main(bare)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("pending"))

    def fail_push(argv, **kwargs):
        if "push" in argv:
            return subprocess.CompletedProcess(argv, 17, "", "private-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=fail_push) == 1
    pending = home / "scheduler" / "pending-push.json"
    assert pending.is_file()
    local_commit = _git(profile, "rev-parse", "HEAD").stdout.strip()
    (profile / ".git" / "shallow").write_text(f"{parent}\n", encoding="ascii")
    assert _git(profile, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"

    assert launcher.run_launcher(home) == 1
    assert pending.is_file()
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_commit
    assert _remote_main(bare) == parent


@pytest.mark.parametrize("rewrite_key", ["insteadOf", "pushInsteadOf"])
def test_pending_retry_rejects_late_url_rewrite_without_publication(
    tmp_path, monkeypatch, rewrite_key
):
    home, profile, bare = _setup(tmp_path)
    parent = _remote_main(bare)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("pending"))

    def fail_push(argv, **kwargs):
        if "push" in argv:
            return subprocess.CompletedProcess(argv, 17, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=fail_push) == 1
    pending = home / "scheduler" / "pending-push.json"
    assert pending.is_file()
    second = tmp_path / "rewrite-target.git"
    _seed_second_remote(profile, second, parent)
    _git(
        profile,
        "config",
        f"url.{second.resolve().as_uri()}.{rewrite_key}",
        bare.resolve().as_uri(),
    )

    assert launcher.run_launcher(home) == 1
    assert pending.is_file()
    assert _remote_main(bare) == parent
    assert _remote_main(second) == parent


@pytest.mark.parametrize(
    "unsupported_url",
    [
        "--receive-pack=private-option-canary",
        "https://user:private-token-canary@example.test/repo.git",
        "https://example.test/repo.git?private-token-canary",
    ],
)
def test_unsupported_destination_refuses_before_refresh_or_git_mutation(
    tmp_path, monkeypatch, unsupported_url
):
    home, profile, bare = _setup(tmp_path)
    _git(profile, "config", "remote.origin.url", unsupported_url)
    local_before = _git(profile, "rev-parse", "HEAD").stdout.strip()
    remote_before = _remote_main(bare)
    index_before = _git(profile, "diff", "--cached", "--name-only").stdout
    refresh_called = False

    def forbidden_refresh(*_args, **_kwargs):
        nonlocal refresh_called
        refresh_called = True
        raise AssertionError("unsupported destination must fail before refresh")

    monkeypatch.setattr(launcher.refresh, "run_refresh", forbidden_refresh)
    assert launcher.run_launcher(home) == 1
    assert refresh_called is False
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_before
    assert _remote_main(bare) == remote_before
    assert _git(profile, "diff", "--cached", "--name-only").stdout == index_before
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "private-token-canary" not in log
    assert "private-option-canary" not in log


def test_pending_retry_rejects_changed_single_destination_with_same_parent(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    parent = _remote_main(bare)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("pending"))

    def fail_push(argv, **kwargs):
        if "push" in argv:
            return subprocess.CompletedProcess(argv, 17, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=fail_push) == 1
    pending = home / "scheduler" / "pending-push.json"
    assert pending.is_file()
    second = tmp_path / "second-remote.git"
    _seed_second_remote(profile, second, parent)
    _git(profile, "remote", "set-url", "origin", second.resolve().as_uri())
    local_before = _git(profile, "rev-parse", "HEAD").stdout.strip()
    index_before = _git(profile, "diff", "--cached", "--name-only").stdout

    assert launcher.run_launcher(home) == 1
    assert pending.is_file()
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_before
    assert _git(profile, "diff", "--cached", "--name-only").stdout == index_before
    assert _remote_main(bare) == parent
    assert _remote_main(second) == parent
    tail = (home / "scheduler" / "last-run.log").read_text(
        encoding="utf-8"
    ).splitlines()[-1]
    assert tail.endswith(
        "pending publication destination diverged; synchronize manually"
    )


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


def test_launcher_sanitizes_repository_selection_environment(
    tmp_path, monkeypatch
):
    home, _profile, _bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("sanitized"))
    hostile = {
        "GIT_DIR": str(tmp_path / "wrong.git"),
        "GIT_WORK_TREE": str(tmp_path / "wrong-tree"),
        "GIT_OBJECT_DIRECTORY": str(tmp_path / "wrong-objects"),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "alternate"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.bare",
        "GIT_CONFIG_VALUE_0": "true",
    }
    for key, value in hostile.items():
        monkeypatch.setenv(key, value)

        def runner(argv, **kwargs):
            env = kwargs.get("env")
            assert env is not None
            assert all(env.get(key) != value for key, value in hostile.items())
            return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 0


def test_launcher_refuses_unpushed_local_ancestor(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    (profile / "private-canary.txt").write_text("private\n", encoding="utf-8")
    _git(profile, "add", "private-canary.txt")
    _git(profile, "commit", "-q", "-m", "local unrelated secret")
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("blocked"))

    assert launcher.run_launcher(home) == 1
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before
    assert _git(bare, "cat-file", "-e", "main:private-canary.txt", check=False).returncode != 0


def test_private_index_rejects_bytes_substituted_after_refresh(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("expected"))
    changed = False

    def runner(argv, **kwargs):
        nonlocal changed
        if "add" in argv and not changed:
            changed = True
            (profile / "dist" / "profile.json").write_text(
                "PRIVATE-RACE-CANARY\n", encoding="utf-8"
            )
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 1
    assert changed is True
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before


@pytest.mark.parametrize("replacement", [b"expected:profile.json\r\n", b"\xff\x00"])
def test_private_index_hashes_raw_blob_bytes_without_text_normalization(
    tmp_path, monkeypatch, replacement
):
    home, profile, bare = _setup(tmp_path)
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("expected"))
    changed = False

    def runner(argv, **kwargs):
        nonlocal changed
        if "add" in argv and not changed:
            changed = True
            (profile / "dist" / "profile.json").write_bytes(replacement)
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=runner) == 1
    assert changed is True
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before


def test_failed_push_is_retried_from_pending_immutable_commit(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("retry"))

    def fail_push(argv, **kwargs):
        if "push" in argv:
            return subprocess.CompletedProcess(argv, 17, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=fail_push) == 1
    pending = home / "scheduler" / "pending-push.json"
    assert pending.is_file()
    if os.name != "nt":
        assert stat.S_IMODE(pending.stat().st_mode) == 0o600
    local = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert local != remote_before
    assert launcher.run_launcher(home) == 0
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == local
    assert not pending.exists()


def test_pending_state_write_failure_prevents_local_ref_advance(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    local_before = _git(profile, "rev-parse", "HEAD").stdout.strip()
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("blocked"))
    monkeypatch.setattr(launcher, "_write_pending", lambda *_args: False)

    assert launcher.run_launcher(home) == 1
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == local_before
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before
    assert not (home / "scheduler" / "pending-push.json").exists()
    assert "no branch update or push was attempted" in (
        home / "scheduler" / "last-run.log"
    ).read_text(encoding="utf-8").splitlines()[-1]


def test_pending_replace_is_the_final_fallible_publication_step(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("atomic"))
    real_chmod = launcher.os.chmod

    def reject_post_replace_chmod(path, mode):
        if Path(path).name == "pending-push.json":
            raise OSError("private-finalization-canary")
        return real_chmod(path, mode)

    monkeypatch.setattr(launcher.os, "chmod", reject_post_replace_chmod)
    assert launcher.run_launcher(home) == 0
    assert not (home / "scheduler" / "pending-push.json").exists()
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == _git(
        profile, "rev-parse", "HEAD"
    ).stdout.strip()


def test_pending_retry_repairs_exact_eight_index_after_post_cas_crash(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("crash"))
    cas_completed = False

    def crash_before_index_sync(argv, **kwargs):
        nonlocal cas_completed
        if cas_completed and "reset" in argv:
            raise SystemExit("simulated process death")
        result = subprocess.run(argv, **kwargs)
        if "update-ref" in argv and result.returncode == 0:
            cas_completed = True
        return result

    with pytest.raises(SystemExit, match="simulated process death"):
        launcher.run_launcher(home, runner=crash_before_index_sync)
    pending = home / "scheduler" / "pending-push.json"
    assert pending.is_file()
    assert _git(profile, "diff", "--cached", "--name-only", "HEAD").stdout.splitlines() == [
        f"dist/{name}" for name in sorted(launcher.PUBLIC_ASSET_NAMES)
    ]
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before

    assert launcher.run_launcher(home) == 0
    assert _git(profile, "diff", "--cached", "--name-only", "HEAD").stdout == ""
    assert not pending.exists()
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == _git(
        profile, "rev-parse", "HEAD"
    ).stdout.strip()


def test_pending_retry_completes_forward_cas_after_pre_cas_crash(
    tmp_path, monkeypatch
):
    home, profile, bare = _setup(tmp_path)
    parent = _git(profile, "rev-parse", "HEAD").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("pre-cas"))
    crashed = False

    def crash_before_forward_cas(argv, **kwargs):
        nonlocal crashed
        if "update-ref" in argv and not crashed:
            crashed = True
            raise SystemExit("simulated pre-CAS process death")
        return subprocess.run(argv, **kwargs)

    with pytest.raises(SystemExit, match="pre-CAS process death"):
        launcher.run_launcher(home, runner=crash_before_forward_cas)
    pending = home / "scheduler" / "pending-push.json"
    assert pending.is_file()
    assert _git(profile, "rev-parse", "HEAD").stdout.strip() == parent
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == parent

    assert launcher.run_launcher(home) == 0
    local = _git(profile, "rev-parse", "HEAD").stdout.strip()
    assert local != parent
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == local
    assert _git(profile, "diff", "--cached", "--name-only", "HEAD").stdout == ""
    assert not pending.exists()


def test_pending_retry_refuses_push_when_index_repair_fails(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    remote_before = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("crash"))
    cas_completed = False

    def crash_before_index_sync(argv, **kwargs):
        nonlocal cas_completed
        if cas_completed and "reset" in argv:
            raise SystemExit("simulated process death")
        result = subprocess.run(argv, **kwargs)
        if "update-ref" in argv and result.returncode == 0:
            cas_completed = True
        return result

    with pytest.raises(SystemExit):
        launcher.run_launcher(home, runner=crash_before_index_sync)

    def fail_repair(argv, **kwargs):
        if "reset" in argv:
            return subprocess.CompletedProcess(argv, 19, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=fail_repair) == 1
    assert (home / "scheduler" / "pending-push.json").is_file()
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_before
    tail = (home / "scheduler" / "last-run.log").read_text(
        encoding="utf-8"
    ).splitlines()[-1]
    assert "tool paths may remain staged" in tail
    assert "push was refused" in tail
    assert "private-path-canary" not in tail


def test_pending_push_refuses_remote_divergence_without_refresh(tmp_path, monkeypatch):
    home, profile, bare = _setup(tmp_path)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("retry"))

    def fail_push(argv, **kwargs):
        if "push" in argv:
            return subprocess.CompletedProcess(argv, 17, "", "private-path-canary")
        return subprocess.run(argv, **kwargs)

    assert launcher.run_launcher(home, runner=fail_push) == 1
    pending = home / "scheduler" / "pending-push.json"
    assert pending.is_file()

    other = tmp_path / "remote-writer"
    _git(tmp_path, "clone", "-q", str(bare), str(other))
    _git(other, "checkout", "-q", "-b", "main", "origin/main")
    _git(other, "config", "user.name", "Fixture")
    _git(other, "config", "user.email", "fixture@example.com")
    (other / "README.md").write_text("remote divergence\n", encoding="utf-8")
    _git(other, "add", "README.md")
    _git(other, "commit", "-q", "-m", "remote divergence")
    _git(other, "push", "-q", "origin", "main")
    remote_advanced = _git(bare, "rev-parse", "refs/heads/main").stdout.strip()

    def must_not_refresh(*_args, **_kwargs):
        raise AssertionError("divergent pending state must fail before refresh")

    monkeypatch.setattr(launcher.refresh, "run_refresh", must_not_refresh)
    assert launcher.run_launcher(home) == 1
    assert _git(bare, "rev-parse", "refs/heads/main").stdout.strip() == remote_advanced
    assert pending.is_file()
    assert "pending publication state diverged" in (
        home / "scheduler" / "last-run.log"
    ).read_text(encoding="utf-8").splitlines()[-1]


def test_invalid_pending_push_state_fails_before_refresh_without_leak(
    tmp_path, monkeypatch
):
    home, _profile, _bare = _setup(tmp_path)
    pending = home / "scheduler" / "pending-push.json"
    pending.write_text('{"private-path-canary": true}\n', encoding="utf-8")

    def must_not_refresh(*_args, **_kwargs):
        raise AssertionError("invalid pending state must fail before refresh")

    monkeypatch.setattr(launcher.refresh, "run_refresh", must_not_refresh)
    assert launcher.run_launcher(home) == 1
    line = (home / "scheduler" / "last-run.log").read_text(
        encoding="utf-8"
    ).splitlines()[-1]
    assert "pending publication state is invalid" in line
    assert "private-path-canary" not in line
    assert pending.is_file()


def test_two_homes_targeting_one_profile_are_serialized(tmp_path, monkeypatch):
    home_a, profile, _bare = _setup(tmp_path)
    home_b = tmp_path / "home-b"
    service.write_scheduler_files(
        home_b, profile, "07:30", True, branch="main", remote="origin"
    )
    nested_rc = None
    home_b_refreshes = 0

    def coordinated_refresh(call_home, out_dir):
        nonlocal nested_rc, home_b_refreshes
        if Path(call_home) == home_a:
            nested_rc = launcher.run_launcher(home_b)
            return _refresh_writer("home-a")(call_home, out_dir)
        home_b_refreshes += 1
        return _refresh_writer("home-b")(call_home, out_dir)

    monkeypatch.setattr(launcher.refresh, "run_refresh", coordinated_refresh)
    assert launcher.run_launcher(home_a) == 0
    assert nested_rc == 0
    assert home_b_refreshes == 0


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits only")
def test_last_run_log_is_owner_only(tmp_path, monkeypatch):
    home, _profile, _bare = _setup(tmp_path, push=False)
    monkeypatch.setattr(launcher.refresh, "run_refresh", _refresh_writer("log-mode"))
    previous = os.umask(0o022)
    try:
        assert launcher.run_launcher(home) == 0
    finally:
        os.umask(previous)
    assert stat.S_IMODE((home / "scheduler" / "last-run.log").stat().st_mode) == 0o600

"""Scheduler launcher unit contract (v0.7.0 Tasks B1/B2)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from aiprofile.errors import LockError, RefreshError, RefreshFailureState
from aiprofile.export import PUBLIC_ASSET_NAMES
from aiprofile.lockfile import acquire_home_lock
from aiprofile.schedule import launcher, service


def _write_config(home: Path, profile: Path, *, push: bool = True) -> None:
    service.write_scheduler_files(
        home,
        profile,
        "07:30",
        push,
        branch="main",
        remote="origin",
    )


def _runner(events: list[tuple[str, object]], *, push_rc: int = 0):
    def run(argv, **kwargs):
        events.append(("git", (argv, kwargs)))
        assert isinstance(argv, list)
        assert kwargs.get("shell") is False
        if "symbolic-ref" in argv:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if "rev-parse" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'a' * 40}\n", "")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if "push" in argv:
            return subprocess.CompletedProcess(argv, push_rc, "", "private stderr canary")
        return subprocess.CompletedProcess(argv, 0, "", "")

    return run


def test_write_scheduler_files_creates_launcher_and_config(tmp_path):
    home = tmp_path / "home"
    profile = tmp_path / "profile canary"
    profile.mkdir()
    service.write_scheduler_files(
        home, profile, "07:30", True, branch="main", remote="origin"
    )

    scheduler = home / "scheduler"
    stub = (scheduler / "launcher.py").read_text(encoding="utf-8")
    assert len(stub.splitlines()) == 5
    assert "from aiprofile.schedule.launcher import run_launcher" in stub
    assert "Path(__file__).resolve().parent.parent" in stub
    assert "aiprofile_home" not in stub
    assert "subprocess" not in stub
    payload = json.loads((scheduler / "config.json").read_text(encoding="utf-8"))
    assert payload == {
        "profile_repo": str(profile.resolve()),
        "time": "07:30",
        "push": True,
        "branch": "main",
        "remote": "origin",
        "installed_version": "0.7.0",
    }
    assert service.read_scheduler_config(home).profile_repo == profile.resolve()


def test_launcher_is_single_instance(tmp_path, monkeypatch):
    home = tmp_path / "home"
    profile = tmp_path / "profile"
    profile.mkdir()
    _write_config(home, profile)
    called = False

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("refresh must not run")

    monkeypatch.setattr(launcher.refresh, "run_refresh", forbidden)
    with acquire_home_lock(home, service.SCHEDULER_LOCK_NAME):
        assert launcher.run_launcher(home) == 0
    assert called is False


def test_launcher_calls_refresh_into_profile_repo_dist(tmp_path, monkeypatch):
    home = tmp_path / "home"
    profile = tmp_path / "profile"
    profile.mkdir()
    _write_config(home, profile)
    events: list[tuple[str, object]] = []

    def fake_refresh(call_home, out_dir):
        events.append(("refresh", (call_home, out_dir)))
        return SimpleNamespace(ok=True, failures=(), written=())

    monkeypatch.setattr(launcher.refresh, "run_refresh", fake_refresh)
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")
    assert launcher.run_launcher(home, runner=_runner(events)) == 0
    assert ("refresh", (home, profile.resolve() / "dist")) in events
    refresh_index = next(i for i, event in enumerate(events) if event[0] == "refresh")
    status_index = next(
        i for i, event in enumerate(events) if event[0] == "git" and "status" in event[1][0]
    )
    assert refresh_index < status_index


def test_launcher_aborts_before_git_on_refresh_failure(tmp_path, monkeypatch):
    home = tmp_path / "home"
    profile = tmp_path / "profile-private-canary"
    profile.mkdir()
    _write_config(home, profile)
    events: list[tuple[str, object]] = []

    def fail_refresh(*_args, **_kwargs):
        raise RefreshError(RefreshFailureState.NOT_PUBLISHED)

    monkeypatch.setattr(launcher.refresh, "run_refresh", fail_refresh)
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")
    assert launcher.run_launcher(home, runner=_runner(events)) == 1
    git_argvs = [event[1][0] for event in events if event[0] == "git"]
    assert all(
        "add" not in argv and "commit" not in argv and "push" not in argv
        for argv in git_argvs
    )
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "refresh failed" in log
    assert str(profile) not in log
    assert profile.name not in log


def test_last_run_log_is_path_and_name_free(tmp_path, monkeypatch):
    home = tmp_path / "private-home-canary"
    profile = tmp_path / "private-profile-canary"
    profile.mkdir()
    _write_config(home, profile)
    events: list[tuple[str, object]] = []
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(
        launcher.refresh,
        "run_refresh",
        lambda *_a, **_k: SimpleNamespace(ok=True, failures=(), written=()),
    )
    assert launcher.run_launcher(home, runner=_runner(events)) == 0
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    for canary in (
        str(home),
        str(profile),
        home.name,
        profile.name,
        "fixture@example.com",
        "AI-Provider",
        "deadbeef",
    ):
        assert canary not in log


def test_git_commands_are_argv_no_shell_and_push_never_forces(tmp_path, monkeypatch):
    home = tmp_path / "home"
    profile = tmp_path / "profile with spaces & symbols"
    profile.mkdir()
    _write_config(home, profile)
    events: list[tuple[str, object]] = []
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")

    def fake_refresh(*_args, **_kwargs):
        return SimpleNamespace(ok=True, failures=(), written=())

    monkeypatch.setattr(launcher.refresh, "run_refresh", fake_refresh)
    ref_updated = False

    def changed_runner(argv, **kwargs):
        nonlocal ref_updated
        events.append(("git", (argv, kwargs)))
        assert isinstance(argv, list)
        assert kwargs.get("shell") is False
        if "symbolic-ref" in argv:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if "rev-parse" in argv:
            if argv[-1].endswith("^{tree}"):
                return subprocess.CompletedProcess(argv, 0, f"{'d' * 40}\n", "")
            oid = "b" * 40 if ref_updated else "a" * 40
            return subprocess.CompletedProcess(argv, 0, f"{oid}\n", "")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, 0, " M dist/profile.json\n", "")
        if "read-tree" in argv:
            Path(kwargs["env"]["GIT_INDEX_FILE"]).touch()
        if "write-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'c' * 40}\n", "")
        if "commit-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'b' * 40}\n", "")
        if "update-ref" in argv:
            ref_updated = True
        return subprocess.CompletedProcess(argv, 0, "", "")

    assert launcher.run_launcher(home, runner=changed_runner) == 0
    argvs = [event[1][0] for event in events]
    assert all(
        flag not in argv
        for argv in argvs
        for flag in ("--force", "--force-with-lease", "-f")
    )
    add = next(argv for argv in argvs if "add" in argv)
    commit = next(argv for argv in argvs if "commit-tree" in argv)
    push = next(argv for argv in argvs if "push" in argv)
    expected = [f"dist/{name}" for name in sorted(PUBLIC_ASSET_NAMES)]
    assert add[-len(expected) :] == expected
    assert commit == [
        "git",
        "commit-tree",
        "c" * 40,
        "-p",
        "a" * 40,
        "-m",
        "chore: refresh ai-profile outputs",
    ]
    assert push == ["git", "push", "origin", f"{'b' * 40}:refs/heads/main"]


def test_push_failure_is_reported_not_fatal_to_commit(tmp_path, monkeypatch):
    home = tmp_path / "home"
    profile = tmp_path / "profile"
    profile.mkdir()
    _write_config(home, profile)
    events: list[tuple[str, object]] = []
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(
        launcher.refresh,
        "run_refresh",
        lambda *_a, **_k: SimpleNamespace(ok=True, failures=(), written=()),
    )
    ref_updated = False

    def runner(argv, **kwargs):
        nonlocal ref_updated
        events.append(("git", (argv, kwargs)))
        if "symbolic-ref" in argv:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if "rev-parse" in argv:
            if argv[-1].endswith("^{tree}"):
                return subprocess.CompletedProcess(argv, 0, f"{'d' * 40}\n", "")
            oid = "b" * 40 if ref_updated else "a" * 40
            return subprocess.CompletedProcess(argv, 0, f"{oid}\n", "")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, 0, " M dist/profile.json\n", "")
        if "read-tree" in argv:
            Path(kwargs["env"]["GIT_INDEX_FILE"]).touch()
        if "write-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'c' * 40}\n", "")
        if "commit-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'b' * 40}\n", "")
        if "update-ref" in argv:
            ref_updated = True
        if "push" in argv:
            return subprocess.CompletedProcess(argv, 23, "", "private-url-canary")
        return subprocess.CompletedProcess(argv, 0, "", "")

    assert launcher.run_launcher(home, runner=runner) == 1
    assert any("commit-tree" in event[1][0] for event in events)
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "push failed (exit 23)" in log
    assert "private-url-canary" not in log


def test_last_run_log_failure_does_not_emit_an_unhandled_traceback(tmp_path, monkeypatch):
    home = tmp_path / "home"
    profile = tmp_path / "profile"
    profile.mkdir()
    _write_config(home, profile)
    events: list[tuple[str, object]] = []
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(
        launcher.refresh,
        "run_refresh",
        lambda *_a, **_k: (_ for _ in ()).throw(
            RefreshError(RefreshFailureState.NOT_PUBLISHED)
        ),
    )
    monkeypatch.setattr(
        launcher,
        "open",
        lambda *_a, **_k: (_ for _ in ()).throw(
            OSError("private-log-path-canary")
        ),
        raising=False,
    )
    assert launcher.run_launcher(home, runner=_runner(events)) == 1


def test_last_run_writer_rejects_non_allowlisted_message(tmp_path):
    home = tmp_path / "home"
    private_canary = str(tmp_path / "private-path-canary")
    launcher._append_log(home, f"unexpected failure at {private_canary}")
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert private_canary not in log
    assert "scheduled refresh failed safely" in log


def test_unlock_failure_preserves_primary_publication_outcome(
    tmp_path, monkeypatch
):
    home = tmp_path / "private-home-canary"
    profile = tmp_path / "private-profile-canary"
    profile.mkdir()
    _write_config(home, profile)
    events: list[tuple[str, object]] = []
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(
        launcher.refresh,
        "run_refresh",
        lambda *_a, **_k: SimpleNamespace(ok=True, failures=(), written=()),
    )

    class FailingExitLock:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            raise LockError("refresh locking is unavailable; private-path-canary")

    monkeypatch.setattr(launcher, "acquire_home_lock", lambda *_a, **_k: FailingExitLock())
    assert launcher.run_launcher(home, runner=_runner(events)) == 1
    tail = (home / "scheduler" / "last-run.log").read_text(
        encoding="utf-8"
    ).splitlines()[-1]
    assert "refresh completed; no change" in tail
    assert "scheduler finalization failed" in tail
    assert "private-path-canary" not in tail


def test_launcher_invalid_utf8_config_fails_safely(tmp_path):
    home = tmp_path / "private-home-canary"
    scheduler = home / "scheduler"
    scheduler.mkdir(parents=True)
    (scheduler / "config.json").write_bytes(b"\xff")
    assert launcher.run_launcher(home) == 1
    log = (scheduler / "last-run.log").read_text(encoding="utf-8")
    assert "refresh failed safely; no publication attempted" in log
    assert str(home) not in log
    assert home.name not in log


def test_branch_drift_after_private_staging_leaves_real_index_untouched(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    profile = tmp_path / "profile"
    profile.mkdir()
    _write_config(home, profile)
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(
        launcher.refresh,
        "run_refresh",
        lambda *_a, **_k: SimpleNamespace(ok=True, failures=(), written=()),
    )
    events = []
    state_checks = 0

    def runner(argv, **kwargs):
        nonlocal state_checks
        events.append(argv)
        if "symbolic-ref" in argv:
            state_checks += 1
            branch = "other" if state_checks >= 4 else "main"
            return subprocess.CompletedProcess(argv, 0, f"{branch}\n", "")
        if "rev-parse" in argv:
            if argv[-1].endswith("^{tree}"):
                return subprocess.CompletedProcess(argv, 0, f"{'d' * 40}\n", "")
            return subprocess.CompletedProcess(argv, 0, f"{'a' * 40}\n", "")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, 0, " M dist/profile.json\n", "")
        if "read-tree" in argv:
            Path(kwargs["env"]["GIT_INDEX_FILE"]).touch()
        if "write-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'c' * 40}\n", "")
        if "commit-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'b' * 40}\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    assert launcher.run_launcher(home, runner=runner) == 1
    assert not any("update-ref" in argv or "reset" in argv or "push" in argv for argv in events)
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "repository state changed before branch update" in log


def test_head_drift_immediately_before_push_retains_local_commit(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    profile = tmp_path / "profile"
    profile.mkdir()
    _write_config(home, profile)
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(
        launcher.refresh,
        "run_refresh",
        lambda *_a, **_k: SimpleNamespace(ok=True, failures=(), written=()),
    )
    events = []
    oid_checks = 0

    def runner(argv, **kwargs):
        nonlocal oid_checks
        events.append(argv)
        if "symbolic-ref" in argv:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if "rev-parse" in argv:
            if argv[-1].endswith("^{tree}"):
                return subprocess.CompletedProcess(argv, 0, f"{'e' * 40}\n", "")
            oid_checks += 1
            if oid_checks <= 4:
                oid = "a" * 40
            else:
                oid = "c" * 40
            return subprocess.CompletedProcess(argv, 0, f"{oid}\n", "")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, 0, " M dist/profile.json\n", "")
        if "read-tree" in argv:
            Path(kwargs["env"]["GIT_INDEX_FILE"]).touch()
        if "write-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'d' * 40}\n", "")
        if "commit-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'b' * 40}\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    assert launcher.run_launcher(home, runner=runner) == 1
    assert any("commit-tree" in argv for argv in events)
    assert not any("push" in argv for argv in events)
    log = (home / "scheduler" / "last-run.log").read_text(encoding="utf-8")
    assert "repository state changed after branch update; publication rolled back" in log

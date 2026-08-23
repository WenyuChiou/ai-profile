"""Scheduler launcher unit contract (v0.7.0 Tasks B1/B2)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiprofile.errors import LockError, RefreshError, RefreshFailureState
from aiprofile.export import PUBLIC_ASSET_NAMES
from aiprofile.lockfile import acquire_home_lock
from aiprofile.schedule import launcher, service


def _write_config(home: Path, profile: Path, *, push: bool = True) -> None:
    (profile / ".git").mkdir(exist_ok=True)
    service.write_scheduler_files(
        home,
        profile,
        "07:30",
        push,
        branch="main",
        remote="origin",
    )


def _refresh_ok():
    digest = hashlib.sha256(b"").hexdigest()
    return SimpleNamespace(
        ok=True,
        failures=(),
        written=(),
        asset_manifest=tuple(
            launcher.AssetDigest(name=name, sha256=digest)
            for name in sorted(PUBLIC_ASSET_NAMES)
        ),
    )


def _security_prerequisite(argv):
    if "--git-common-dir" in argv:
        return subprocess.CompletedProcess(argv, 0, ".git\n", "")
    if "--is-shallow-repository" in argv:
        return subprocess.CompletedProcess(argv, 0, "false\n", "")
    if "config" in argv and argv[-2:] == ["--get", "extensions.partialClone"]:
        return subprocess.CompletedProcess(argv, 1, "", "")
    if "get-url" in argv:
        return subprocess.CompletedProcess(argv, 0, "file:///single-remote.git\n", "")
    if "config" in argv and "--null" in argv:
        return subprocess.CompletedProcess(argv, 0, b"", b"")
    if "ls-remote" in argv:
        return subprocess.CompletedProcess(
            argv, 0, f"{'a' * 40}\trefs/heads/main\n", ""
        )
    if "ls-files" in argv:
        entries = "".join(
            f"100644 {'e' * 40} 0\tdist/{name}\x00"
            for name in sorted(PUBLIC_ASSET_NAMES)
        )
        return subprocess.CompletedProcess(argv, 0, entries, "")
    if "cat-file" in argv:
        return subprocess.CompletedProcess(argv, 0, b"", b"")
    return None


def _runner(events: list[tuple[str, object]], *, push_rc: int = 0):
    def run(argv, **kwargs):
        events.append(("git", (argv, kwargs)))
        assert isinstance(argv, list)
        assert kwargs.get("shell") is False
        prerequisite = _security_prerequisite(argv)
        if prerequisite is not None:
            return prerequisite
        if "symbolic-ref" in argv:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if "rev-parse" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'a' * 40}\n", "")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if "read-tree" in argv:
            Path(kwargs["env"]["GIT_INDEX_FILE"]).touch()
        if "write-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{'a' * 40}\n", "")
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
        "installed_version": "0.8.0",
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
        return _refresh_ok()

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
        lambda *_a, **_k: _refresh_ok(),
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


def test_git_commands_are_argv_no_shell_and_push_uses_exact_old_lease(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    profile = tmp_path / "profile with spaces & symbols"
    profile.mkdir()
    _write_config(home, profile)
    events: list[tuple[str, object]] = []
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")

    def fake_refresh(*_args, **_kwargs):
        return _refresh_ok()

    monkeypatch.setattr(launcher.refresh, "run_refresh", fake_refresh)
    ref_updated = False
    pushed = False

    def changed_runner(argv, **kwargs):
        nonlocal ref_updated, pushed
        events.append(("git", (argv, kwargs)))
        assert isinstance(argv, list)
        assert kwargs.get("shell") is False
        if "ls-remote" in argv:
            oid = "b" * 40 if pushed else "a" * 40
            return subprocess.CompletedProcess(
                argv, 0, f"{oid}\trefs/heads/main\n", ""
            )
        prerequisite = _security_prerequisite(argv)
        if prerequisite is not None:
            return prerequisite
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
            pushed = True
        return subprocess.CompletedProcess(argv, 0, "", "")

    assert launcher.run_launcher(home, runner=changed_runner) == 0
    argvs = [event[1][0] for event in events]
    assert all(flag not in argv for argv in argvs for flag in ("--force", "-f"))
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
    assert push == [
        "git",
        "push",
        f"--force-with-lease=refs/heads/main:{'a' * 40}",
        "--",
        "aiprofile-publication",
        f"{'b' * 40}:refs/heads/main",
    ]
    assert "file:///single-remote.git" not in push
    push_event = next(event for event in events if event[1][0] == push)
    push_env = push_event[1][1]["env"]
    assert "file:///single-remote.git" in push_env.values()
    assert push_env["GIT_CONFIG_GLOBAL"] == launcher.os.devnull
    assert push_env["GIT_CONFIG_NOSYSTEM"] == "1"


@pytest.mark.parametrize(
    ("fetch_rc", "fetch_out", "push_rc", "push_out"),
    [
        (1, "private-fetch-canary\n", 0, "file:///one.git\n"),
        (0, "file:///one.git\nfile:///two.git\n", 0, "file:///one.git\n"),
        (0, "file:///one.git\n", 0, "file:///two.git\n"),
        (0, "file:///one.git\x00suffix\n", 0, "file:///one.git\x00suffix\n"),
        (0, "--receive-pack=private-option-canary\n", 0, "--receive-pack=private-option-canary\n"),
        (0, "https://user:private-token@example.test/repo.git\n", 0, "https://user:private-token@example.test/repo.git\n"),
        (0, "ssh://user:private-token@example.test/repo.git\n", 0, "ssh://user:private-token@example.test/repo.git\n"),
        (0, "https://example.test/repo.git?private-token\n", 0, "https://example.test/repo.git?private-token\n"),
        (0, "ext::private-helper-command\n", 0, "ext::private-helper-command\n"),
        (0, "file:///one.git\rprivate-option-canary\n", 0, "file:///one.git\rprivate-option-canary\n"),
    ],
)
def test_remote_destination_discovery_fails_closed(
    tmp_path, fetch_rc, fetch_out, push_rc, push_out
):
    def runner(argv, **_kwargs):
        is_push = "--push" in argv
        return subprocess.CompletedProcess(
            argv,
            push_rc if is_push else fetch_rc,
            push_out if is_push else fetch_out,
            "private-path-canary",
        )

    assert (
        launcher._single_symmetric_remote_destination(
            runner,
            "git",
            tmp_path,
            remote="origin",
        )
        is None
    )


@pytest.mark.parametrize(
    "destination",
    [
        "https://example.test/owner/repo.git",
        "ssh://git@example.test/owner/repo.git",
        "git@example.test:owner/repo.git",
        "file:///tmp/profile.git",
    ],
)
def test_supported_remote_destination_forms(destination, tmp_path):
    def runner(argv, **_kwargs):
        assert "get-url" in argv
        return subprocess.CompletedProcess(argv, 0, f"{destination}\n", "")

    assert (
        launcher._single_symmetric_remote_destination(
            runner,
            "git",
            tmp_path,
            remote="origin",
        )
        == destination
    )


def test_transport_config_snapshot_queries_only_allowlisted_keys(tmp_path):
    queried: list[str] = []
    def runner(argv, **kwargs):
        assert kwargs["text"] is False
        assert "--list" not in argv
        assert argv[-2] == "--get-all"
        key = argv[-1]
        queried.append(key)
        values = {
            "credential.helper": b"manager\x00second-helper\x00",
            "credential.usehttppath": b"true\x00",
            "http.sslverify": b"true\x00",
        }
        if key in values:
            return subprocess.CompletedProcess(argv, 0, values[key], b"")
        return subprocess.CompletedProcess(argv, 1, b"", b"")

    assert launcher._transport_config_snapshot(runner, "git", tmp_path) == (
        ("credential.helper", "manager"),
        ("credential.helper", "second-helper"),
        ("credential.usehttppath", "true"),
        ("http.sslverify", "true"),
    )
    assert queried == list(launcher._TRANSPORT_CONFIG_KEYS)
    assert "http.extraheader" not in queried
    assert "http.proxy" not in queried
    assert all(not key.startswith("url.") for key in queried)


@pytest.mark.skipif(os.name != "nt", reason="Windows path classification")
def test_windows_remote_destination_classification_is_unambiguous(tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    relative = f"{profile.drive}..\\remote.git"
    assert launcher._canonical_remote_destination(relative, profile) == (
        profile / ".." / "remote.git"
    ).resolve().as_uri()

    other_drive = "D:" if profile.drive.casefold() != "d:" else "C:"
    assert (
        launcher._canonical_remote_destination(
            f"{other_drive}..\\remote.git", profile
        )
        is None
    )
    assert launcher._canonical_remote_destination(
        str((tmp_path / "absolute.git").resolve()), profile
    ) == (tmp_path / "absolute.git").resolve().as_uri()
    assert launcher._supported_remote_destination(r"\\server\share\repo.git")
    assert launcher._canonical_remote_destination("git@example.test:repo.git", profile) == (
        "git@example.test:repo.git"
    )
    assert launcher._canonical_remote_destination(
        "ssh://git@[::1]/repo.git", profile
    ) == "ssh://git@[::1]/repo.git"
    assert not launcher._supported_remote_destination("[::1]:repo.git")
    assert not launcher._supported_remote_destination("git@[::1]:repo.git")


def test_posix_one_letter_host_scp_destination_remains_opaque(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher.os, "name", "posix")
    assert launcher._canonical_remote_destination(
        "x:owner/repo.git", tmp_path
    ) == "x:owner/repo.git"


def test_transport_environment_excludes_ambient_proxy_variables(tmp_path, monkeypatch):
    for key in ("HTTP_PROXY", "https_proxy", "All_Proxy", "NO_PROXY"):
        monkeypatch.setenv(key, f"https://private-proxy-canary.invalid/{key}")

    def runner(argv, **kwargs):
        if "config" in argv:
            return subprocess.CompletedProcess(argv, 1, b"", b"")
        return subprocess.CompletedProcess(argv, 0, "file:///remote.git\n", "")

    home = tmp_path / "home"
    (home / "scheduler").mkdir(parents=True)
    common = tmp_path / "common.git"
    (common / "objects").mkdir(parents=True)
    with launcher._publication_transport(
        runner,
        "git",
        tmp_path,
        home=home,
        common_dir=common,
        destination="file:///remote.git",
    ) as transport:
        assert transport is not None
        assert all(
            key.upper() not in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"}
            for key in transport.env
        )
        assert "private-proxy-canary" not in repr(transport.env)


def test_transport_argv_never_contains_destination_or_filtered_secret(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    profile = tmp_path / "profile"
    profile.mkdir()
    _write_config(home, profile)
    events: list[tuple[list[str], dict]] = []
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(launcher.refresh, "run_refresh", lambda *_a, **_k: _refresh_ok())
    ref_updated = False
    pushed = False
    destination = "https://example.test/owner/repo.git"
    secret = "private-header-canary"

    def runner(argv, **kwargs):
        nonlocal ref_updated, pushed
        events.append((argv, kwargs))
        if "get-url" in argv:
            return subprocess.CompletedProcess(argv, 0, f"{destination}\n", "")
        if "config" in argv and "--null" in argv:
            assert "--list" not in argv
            assert argv[-1] != "http.extraheader"
            if argv[-1] == "credential.helper":
                return subprocess.CompletedProcess(argv, 0, b"manager\x00", b"")
            return subprocess.CompletedProcess(argv, 1, b"", b"")
        if "ls-remote" in argv:
            oid = "b" * 40 if pushed else "a" * 40
            return subprocess.CompletedProcess(
                argv, 0, f"{oid}\trefs/heads/main\n", ""
            )
        prerequisite = _security_prerequisite(argv)
        if prerequisite is not None:
            return prerequisite
        if "symbolic-ref" in argv:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if "rev-parse" in argv:
            if argv[-1].endswith("^{tree}"):
                return subprocess.CompletedProcess(argv, 0, f"{'d' * 40}\n", "")
            return subprocess.CompletedProcess(
                argv, 0, f"{('b' if ref_updated else 'a') * 40}\n", ""
            )
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
            pushed = True
        return subprocess.CompletedProcess(argv, 0, "", "")

    assert launcher.run_launcher(home, runner=runner) == 0
    transport_events = [event for event in events if "push" in event[0] or "ls-remote" in event[0]]
    assert transport_events
    assert all(destination not in argv and secret not in argv for argv, _ in transport_events)
    assert all(secret not in kwargs["env"].values() for _, kwargs in transport_events)
    assert all("--" in argv and "aiprofile-publication" in argv for argv, _ in transport_events)


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
        lambda *_a, **_k: _refresh_ok(),
    )
    ref_updated = False

    def runner(argv, **kwargs):
        nonlocal ref_updated
        events.append(("git", (argv, kwargs)))
        prerequisite = _security_prerequisite(argv)
        if prerequisite is not None:
            return prerequisite
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
        lambda *_a, **_k: _refresh_ok(),
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
        lambda *_a, **_k: _refresh_ok(),
    )
    events = []
    state_checks = 0

    def runner(argv, **kwargs):
        nonlocal state_checks
        events.append(argv)
        prerequisite = _security_prerequisite(argv)
        if prerequisite is not None:
            return prerequisite
        if "symbolic-ref" in argv:
            state_checks += 1
            branch = "other" if state_checks >= 5 else "main"
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
        lambda *_a, **_k: _refresh_ok(),
    )
    events = []
    oid_checks = 0

    def runner(argv, **kwargs):
        nonlocal oid_checks
        events.append(argv)
        prerequisite = _security_prerequisite(argv)
        if prerequisite is not None:
            return prerequisite
        if "symbolic-ref" in argv:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if "rev-parse" in argv:
            if argv[-1].endswith("^{tree}"):
                return subprocess.CompletedProcess(argv, 0, f"{'e' * 40}\n", "")
            oid_checks += 1
            if oid_checks <= 5:
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

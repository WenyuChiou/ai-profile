"""Schedule install/status/remove CLI contract (v0.7.0 Task B6)."""

from __future__ import annotations

import copy
import json
import os
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiprofile import cli
from aiprofile import config as profile_config
from aiprofile.config import init_home
from aiprofile.errors import ConfigError, LockError
from aiprofile.lockfile import acquire_home_lock
from aiprofile.schedule import service
from aiprofile.schedule.adapters import (
    AdapterPlan,
    PlannedCommand,
    PlannedFile,
    ScheduleStatus,
    windows,
)


def test_schedule_install_help_defines_no_push_as_local_commit_only(capsys):
    with pytest.raises(SystemExit) as raised:
        cli.main(["schedule", "install", "--help"])

    assert raised.value.code == 0
    output = " ".join(capsys.readouterr().out.split())
    assert "create the local exact-eight commit but skip the remote push" in output


def _git(repo: Path, *args: str):
    result = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    return result


def _repo(tmp_path: Path, *, remote: bool = True) -> Path:
    repo = tmp_path / "private-profile-name-canary"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "config", "user.email", "fixture@example.com")
    (repo / "README.md").write_text("profile\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "seed")
    if remote:
        _git(repo, "remote", "add", "origin", "https://example.invalid/private.git")
        _git(repo, "config", "branch.main.remote", "origin")
    return repo


def _initialized_home(path: Path) -> Path:
    init_home(path, ["fixture@example.com"])
    return path


def _tree_state(path: Path) -> dict[str, tuple[bytes | None, int, int]]:
    return {
        str(item.relative_to(path)): (
            item.read_bytes() if item.is_file() else None,
            item.stat().st_mode,
            item.stat().st_mtime_ns,
        )
        for item in (path, *path.rglob("*"))
    }


class FakeAdapter:
    def __init__(self):
        self.calls = []
        self.installed = False
        self.installed_time = None
        self.fail_install = False
        self.fail_times: set[str] = set()
        self.fail_remove = False

    def plan(self, home, time):
        self.calls.append(("plan", time))
        return AdapterPlan(
            files=(PlannedFile(Path(home) / "scheduler" / "native.plan", b"x"),),
            commands=(PlannedCommand(("native-scheduler", "register")),),
        )

    def install(self, home, time):
        self.calls.append(("install", time))
        assert (Path(home) / "scheduler" / "config.json").exists()
        if self.fail_install or time in self.fail_times:
            raise ConfigError("private adapter detail canary")
        self.installed = True
        self.installed_time = time

    def status(self, home):
        self.calls.append(("status", None))
        return ScheduleStatus(
            installed=self.installed,
            time=self.installed_time if self.installed else None,
            active=self.installed,
        )

    def remove(self, home):
        self.calls.append(("remove", None))
        if self.fail_remove:
            raise ConfigError("private removal path canary")
        self.installed = False
        self.installed_time = None


@pytest.fixture
def fake_adapter(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(service, "_adapter_for", lambda _platform=None: adapter)
    return adapter


def test_os_dispatch():
    assert service._adapter_for("win32").__name__.endswith("windows")
    assert service._adapter_for("darwin").__name__.endswith("launchd")
    assert service._adapter_for("linux").__name__.endswith("systemd")
    with pytest.raises(ConfigError, match="unsupported platform"):
        service._adapter_for("plan9")


def test_unsupported_platform_cli_fails_clearly(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AIPROFILE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(service.sys, "platform", "plan9")
    assert cli.main(["schedule", "status"]) == 1
    captured = capsys.readouterr()
    assert "unsupported platform for aiprofile schedule" in captured.err


def test_install_requires_profile_repo_and_valid_time(tmp_path, monkeypatch, fake_adapter):
    home = _initialized_home(tmp_path / "home")
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    repo = _repo(tmp_path)
    with pytest.raises(SystemExit) as malformed:
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "7:5"]
        )
    assert malformed.value.code == 2
    with pytest.raises(SystemExit) as out_of_range:
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "24:00"]
        )
    assert out_of_range.value.code == 2
    assert (
        cli.main(
            [
                "schedule",
                "install",
                "--profile-repo",
                str(repo),
                "--time",
                "07:30",
            ]
        )
        == 0
    )

    missing_home = _initialized_home(tmp_path / "missing-home")
    monkeypatch.setenv("AIPROFILE_HOME", str(missing_home))
    assert (
        cli.main(
            [
                "schedule",
                "install",
                "--profile-repo",
                str(tmp_path / "missing-profile"),
                "--time",
                "07:30",
            ]
        )
        == 1
    )
    assert not (missing_home / "scheduler").exists()


def test_install_sanitizes_every_git_repository_probe(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    hostile = {
        "GIT_DIR": str(tmp_path / "private-git-dir-canary"),
        "GIT_WORK_TREE": str(tmp_path / "private-worktree-canary"),
        "GIT_COMMON_DIR": str(tmp_path / "private-common-canary"),
        "GIT_OBJECT_DIRECTORY": str(tmp_path / "private-objects-canary"),
        "GIT_CONFIG_GLOBAL": str(tmp_path / "private-config-canary"),
        "GIT_REPLACE_REF_BASE": "refs/private-canary/",
    }
    for name, value in hostile.items():
        monkeypatch.setenv(name, value)

    original_run = subprocess.run
    observed: list[dict[str, str]] = []

    def inspect_run(*args, **kwargs):
        command = args[0] if args else kwargs.get("args", [])
        if command and Path(command[0]).name.lower().startswith("git"):
            observed.append(dict(kwargs.get("env") or {}))
        return original_run(*args, **kwargs)

    monkeypatch.setattr(service.subprocess, "run", inspect_run)
    result = service.install(home, repo, "07:30", dry_run=True)

    assert result.dry_run is True
    assert observed
    assert all(not (set(env) & set(hostile)) for env in observed)
    assert fake_adapter.calls == [("status", None), ("plan", "07:30")]


def test_install_requires_initialized_parseable_home_before_scheduler_work(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    repo = _repo(tmp_path, remote=False)
    private_home = tmp_path / "private-home-canary"
    monkeypatch.setenv("AIPROFILE_HOME", str(private_home))

    for dry_run in (False, True):
        args = [
            "schedule",
            "install",
            "--profile-repo",
            str(repo),
            "--time",
            "07:30",
            "--no-push",
        ]
        if dry_run:
            args.append("--dry-run")
        assert cli.main(args) == 1
        captured = capsys.readouterr()
        assert "run 'aiprofile init' first" in captured.err
        assert str(private_home) not in captured.err
        assert private_home.name not in captured.err
        assert not private_home.exists()
        assert fake_adapter.calls == []

    private_home.mkdir()
    malformed = private_home / "config.json"
    malformed.write_text('{"salt":', encoding="utf-8")
    before = _tree_state(private_home)
    assert cli.main(args) == 1
    captured = capsys.readouterr()
    assert "run 'aiprofile init' first" in captured.err
    assert str(private_home) not in captured.err
    assert _tree_state(private_home) == before
    assert not (private_home / "scheduler").exists()
    assert fake_adapter.calls == []


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize(
    "payload",
    [
        b"\xff",
        json.dumps(
            {"identities": [], "salt": "s" * 64, "repositories": 7}
        ).encode("utf-8"),
    ],
)
def test_install_normalizes_invalid_config_without_any_downstream_work(
    tmp_path, monkeypatch, fake_adapter, capsys, payload, dry_run
):
    home = tmp_path / "private-home-canary"
    home.mkdir()
    (home / "config.json").write_bytes(payload)
    before = _tree_state(home)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    monkeypatch.setattr(
        service,
        "_validate_repository",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("git validation must not run")
        ),
    )
    args = [
        "schedule",
        "install",
        "--profile-repo",
        str(tmp_path / "private-profile-canary"),
        "--time",
        "07:30",
        "--no-push",
    ]
    if dry_run:
        args.append("--dry-run")

    assert cli.main(args) == 1
    captured = capsys.readouterr()
    assert "run 'aiprofile init' first" in captured.err
    assert "Traceback" not in captured.err
    assert str(home) not in captured.err
    assert home.name not in captured.err
    assert _tree_state(home) == before
    assert fake_adapter.calls == []


def test_install_rejects_detached_head(tmp_path, monkeypatch, fake_adapter, capsys):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    _git(repo, "checkout", "-q", "--detach")
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    rc = cli.main(
        ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "profile repository is on a detached HEAD" in captured.err
    assert str(repo) not in captured.err
    assert repo.name not in captured.err
    assert not (home / "scheduler").exists()


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("history_kind", ["shallow", "partial"])
def test_install_rejects_incomplete_repository_before_mutation(
    tmp_path, monkeypatch, fake_adapter, capsys, dry_run, history_kind
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    if history_kind == "shallow":
        head = _git(repo, "rev-parse", "HEAD").stdout.strip()
        (repo / ".git" / "shallow").write_text(f"{head}\n", encoding="ascii")
    else:
        _git(repo, "config", "extensions.partialClone", "origin")
    before = _tree_state(home)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    args = [
        "schedule",
        "install",
        "--profile-repo",
        str(repo),
        "--time",
        "07:30",
    ]
    if dry_run:
        args.append("--dry-run")

    assert cli.main(args) == 1
    captured = capsys.readouterr()
    assert "complete local history" in captured.err
    assert str(repo) not in captured.err
    assert repo.name not in captured.err
    assert "Traceback" not in captured.err
    assert _tree_state(home) == before
    assert fake_adapter.calls == []


def test_install_records_branch_and_remote(tmp_path, monkeypatch, fake_adapter):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert (
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
        )
        == 0
    )
    payload = json.loads(
        (home / "scheduler" / "config.json").read_text(encoding="utf-8")
    )
    assert payload["branch"] == "main"
    assert payload["remote"] == "origin"
    assert "example.invalid" not in json.dumps(payload)

    no_remote_home = _initialized_home(tmp_path / "no-remote-home")
    no_remote = _repo(tmp_path / "other", remote=False)
    monkeypatch.setenv("AIPROFILE_HOME", str(no_remote_home))
    assert (
        cli.main(
            [
                "schedule",
                "install",
                "--profile-repo",
                str(no_remote),
                "--time",
                "07:30",
            ]
        )
        == 1
    )
    assert not (no_remote_home / "scheduler").exists()


def test_stale_configured_remote_falls_back_to_sole_actual_remote(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    _git(repo, "config", "branch.main.remote", "stale-private-canary")
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert (
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
        )
        == 0
    )
    assert service.read_scheduler_config(home).remote == "origin"


def test_install_rejects_option_like_or_unknown_remote(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path, remote=False)
    _git(repo, "config", "branch.main.remote", "-force")
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    rc = cli.main(
        ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "no unambiguous configured remote" in captured.err
    assert "-force" not in captured.err
    assert not (home / "scheduler").exists()


def test_install_writes_files_then_registers_and_no_push(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    rc = cli.main(
        [
            "schedule",
            "install",
            "--profile-repo",
            str(repo),
            "--time",
            "12:45",
            "--no-push",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert fake_adapter.calls[-1] == ("install", "12:45")
    assert "12:45" in captured.out
    assert "push disabled" in captured.out
    assert str(repo) not in captured.out
    assert repo.name not in captured.out
    assert service.read_scheduler_config(home).push is False


def test_install_rollback_on_adapter_failure(tmp_path, monkeypatch, fake_adapter, capsys):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    fake_adapter.fail_install = True
    rc = cli.main(
        ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert not (home / "scheduler").exists()
    for canary in (str(repo), repo.name, "private adapter detail canary", "fixture@example.com"):
        assert canary not in captured.err


def test_install_dry_run_touches_nothing(tmp_path, monkeypatch, fake_adapter, capsys):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    before = _tree_state(home)
    permission_mutations = []
    monkeypatch.setattr(
        profile_config,
        "_restrict_to_owner",
        lambda *args: permission_mutations.append(args),
    )
    rc = cli.main(
        [
            "schedule",
            "install",
            "--profile-repo",
            str(repo),
            "--time",
            "07:30",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert fake_adapter.calls == [("status", None), ("plan", "07:30")]
    assert _tree_state(home) == before
    assert permission_mutations == []
    assert "would write 3 scheduler files" in captured.out
    assert "would run 1 registration command" in captured.out
    assert str(repo) not in captured.out


def test_install_twice_is_idempotent(tmp_path, monkeypatch, fake_adapter):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    base = ["schedule", "install", "--profile-repo", str(repo), "--time"]
    assert cli.main([*base, "07:30"]) == 0
    assert cli.main([*base, "08:31", "--no-push"]) == 0
    cfg = service.read_scheduler_config(home)
    assert cfg.time == "08:31"
    assert cfg.push is False
    assert [call[0] for call in fake_adapter.calls].count("install") == 2


def test_v081_status_and_reinstall_migrate_prior_scheduler_config(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert service.install(home, repo, "07:30").time == "07:30"
    config_path = home / "scheduler" / "config.json"

    for readable_version in ("0.7.0", "0.7.1", "0.7.2", "0.8.0"):
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        payload["installed_version"] = readable_version
        config_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        assert service.status(home).installed is True
        assert (
            service.read_scheduler_config(home).installed_version
            == readable_version
        )
        assert service.install(home, repo, "08:31").time == "08:31"
        assert service.read_scheduler_config(home).installed_version == "0.8.1"

    for unsupported_version in ("0.6.1", "0.7.3", "0.8.2"):
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        payload["installed_version"] = unsupported_version
        config_path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(
            ConfigError, match="scheduler configuration is unavailable"
        ):
            service.read_scheduler_config(home)


def test_scheduler_metadata_version_tracks_the_package_version():
    """v0.7.0 and v0.7.1 each wrote their own package version as
    ``installed_version``; a v0.8.1 wheel must not keep stamping v0.8.0
    metadata (written red-first against the un-bumped constant)."""
    import aiprofile

    assert service.SCHEDULER_VERSION == aiprofile.__version__
    assert service.SCHEDULER_VERSION == "0.8.1"


def test_scheduler_version_docs_state_the_current_contract():
    """The normative duplicates of the scheduler metadata contract —
    ADR-030's status/read-set paragraphs and architecture.md's scheduler
    section — must track the CODE's own constants: every readable prior
    version named, writers emitting exactly SCHEDULER_VERSION, and no
    stale 'writers emit' claim for a superseded version (v0.8.1 review
    finding: both docs still said writers emit v0.8.0 after the bump).
    Derived from `service` constants so a future bump fails here until
    both docs move with it. Historical release records are out of scope."""
    root = Path(__file__).resolve().parents[2]
    adr = " ".join(
        (root / "docs" / "decisions" / "ADR-030-automation-layer.md")
        .read_text(encoding="utf-8")
        .split()
    )
    arch = " ".join(
        (root / "docs" / "architecture.md").read_text(encoding="utf-8").split()
    )
    current = service.SCHEDULER_VERSION
    prior = sorted(service._READABLE_SCHEDULER_VERSIONS - {current})

    assert f"tracks the current package (v{current}" in adr
    assert f"writers always emit v{current}." in adr
    assert adr.count("writers always emit v") == 1
    for version in prior:
        assert f"v{version}" in adr
    readable_list = ", ".join(f"v{version}" for version in prior[:-1])
    assert f"readers accept the unchanged {readable_list}, and v{prior[-1]} schema" in arch
    assert f"the current v{current} form" in arch
    assert arch.count("the current v") == 1  # no second, stale "current" claim


def test_failed_reinstall_restores_previous_files_and_native_registration(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    base = ["schedule", "install", "--profile-repo", str(repo), "--time"]
    assert cli.main([*base, "07:30"]) == 0
    capsys.readouterr()
    before = {
        path.name: path.read_bytes()
        for path in (home / "scheduler").iterdir()
        if path.is_file()
    }

    fake_adapter.fail_times.add("08:00")
    assert cli.main([*base, "08:00"]) == 1
    captured = capsys.readouterr()
    assert "previous state restored" in captured.err
    after = {
        path.name: path.read_bytes()
        for path in (home / "scheduler").iterdir()
        if path.is_file()
    }
    assert after == before
    assert service.read_scheduler_config(home).time == "07:30"
    assert fake_adapter.installed is True
    assert fake_adapter.calls[-3:] == [
        ("install", "08:00"),
        ("remove", None),
        ("install", "07:30"),
    ]


def test_failed_reinstall_does_not_create_previously_absent_native_schedule(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    assert service.install(home, repo, "07:30").time == "07:30"
    fake_adapter.installed = False
    fake_adapter.calls.clear()
    fake_adapter.fail_times.add("08:00")

    with pytest.raises(ConfigError, match="previous state restored"):
        service.install(home, repo, "08:00")
    assert service.read_scheduler_config(home).time == "07:30"
    assert fake_adapter.installed is False
    assert fake_adapter.calls == [
        ("status", None),
        ("status", None),
        ("install", "08:00"),
        ("remove", None),
    ]


def test_reinstall_refuses_inactive_native_state_before_mutation(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    assert service.install(home, repo, "07:30").time == "07:30"
    before = _tree_state(home)
    fake_adapter.calls.clear()

    def inactive(_home):
        fake_adapter.calls.append(("status", None))
        return ScheduleStatus(installed=True, active=False)

    fake_adapter.status = inactive
    with pytest.raises(ConfigError, match="inactive"):
        service.install(home, repo, "08:00")
    assert _tree_state(home) == before
    assert fake_adapter.calls == [("status", None)]


def test_reinstall_refuses_native_time_mismatch_before_mutation(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    assert service.install(home, repo, "07:30").time == "07:30"
    before = _tree_state(home)
    fake_adapter.calls.clear()

    def mismatched(_home):
        fake_adapter.calls.append(("status", None))
        return ScheduleStatus(installed=True, time="08:30", active=True)

    fake_adapter.status = mismatched
    with pytest.raises(ConfigError, match="does not match local scheduler state"):
        service.install(home, repo, "08:00")
    assert _tree_state(home) == before
    assert fake_adapter.calls == [("status", None)]


def test_reinstall_refuses_unverifiable_native_active_state_before_mutation(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    assert service.install(home, repo, "07:30").time == "07:30"
    before = _tree_state(home)
    fake_adapter.calls.clear()

    def unverifiable(_home):
        fake_adapter.calls.append(("status", None))
        return ScheduleStatus(installed=True, time="07:30", active=None)

    fake_adapter.status = unverifiable
    with pytest.raises(ConfigError, match="inactive or unverifiable"):
        service.install(home, repo, "08:00")
    assert _tree_state(home) == before
    assert fake_adapter.calls == [("status", None)]


def test_install_native_without_local_state_refuses_without_home_mutation(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    before = _tree_state(home)
    fake_adapter.installed = True

    with pytest.raises(ConfigError, match="does not match local scheduler state"):
        service.install(home, repo, "08:00")

    assert _tree_state(home) == before
    assert not (home / "scheduler").exists()
    assert fake_adapter.calls == [("status", None)]


@pytest.mark.parametrize("query_failure", ["multiple-triggers", "nonzero"])
def test_install_windows_unverifiable_native_state_is_zero_mutation(
    tmp_path, monkeypatch, query_failure
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    service.write_scheduler_files(
        home,
        repo,
        "07:30",
        True,
        branch="main",
        remote="origin",
    )
    planned = windows.plan(home, "07:30").files[0]
    planned.path.write_bytes(planned.content)
    root = ET.fromstring(planned.content.decode("utf-16"))
    if query_failure == "multiple-triggers":
        triggers = next(
            node
            for node in root.iter()
            if node.tag.rsplit("}", 1)[-1] == "Triggers"
        )
        original = next(
            node
            for node in triggers
            if node.tag.rsplit("}", 1)[-1] == "CalendarTrigger"
        )
        extra = copy.deepcopy(original)
        boundary = next(
            node
            for node in extra
            if node.tag.rsplit("}", 1)[-1] == "StartBoundary"
        )
        boundary.text = "2000-01-01T19:45:00"
        triggers.append(extra)
    query_xml = ET.tostring(root, encoding="unicode")

    class WindowsProbeAdapter:
        @staticmethod
        def status(call_home):
            return windows.status(
                call_home,
                runner=lambda argv, **_: subprocess.CompletedProcess(
                    argv,
                    1 if query_failure == "nonzero" else 0,
                    "" if query_failure == "nonzero" else query_xml,
                    "ACCESS DENIED private-path-canary",
                ),
            )

    monkeypatch.setattr(service, "_adapter_for", lambda _platform=None: WindowsProbeAdapter)
    before = _tree_state(home)
    with pytest.raises(ConfigError, match="native scheduler state is unavailable") as exc:
        service.install(home, repo, "08:00")
    assert _tree_state(home) == before
    assert "private-path-canary" not in str(exc.value)


@pytest.mark.parametrize(
    ("remove_fails", "restore_fails", "expected"),
    [
        (False, False, "previous state restored"),
        (True, False, "native scheduler rollback may be incomplete"),
        (False, True, "local rollback is incomplete; native scheduler cleanup completed"),
        (
            True,
            True,
            "local rollback is incomplete and native scheduler state may remain inconsistent",
        ),
    ],
)
def test_install_rollback_reports_native_and_local_residual_matrix(
    tmp_path, monkeypatch, fake_adapter, remove_fails, restore_fails, expected
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    fake_adapter.fail_install = True
    fake_adapter.fail_remove = remove_fails
    original_restore = service._restore_directory

    def restore(*args, **kwargs):
        if restore_fails:
            raise ConfigError("private-restore-path-canary")
        return original_restore(*args, **kwargs)

    monkeypatch.setattr(service, "_restore_directory", restore)
    with pytest.raises(ConfigError, match=expected) as exc:
        service.install(home, repo, "07:30")
    assert "private-restore-path-canary" not in str(exc.value)
    assert str(home) not in str(exc.value)


def test_restore_directory_normalizes_permission_config_error(tmp_path, monkeypatch):
    directory = tmp_path / "private-scheduler-canary"
    snapshot = {Path("config.json"): b"{}"}
    monkeypatch.setattr(
        service,
        "_atomic_write",
        lambda *_args: (_ for _ in ()).throw(ConfigError("private-path-canary")),
    )
    with pytest.raises(ConfigError, match="local rollback was incomplete") as exc:
        service._restore_directory(directory, snapshot)
    assert "private-path-canary" not in str(exc.value)
    assert str(directory) not in str(exc.value)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits only")
def test_scheduler_state_is_owner_only_and_retrofits_insecure_modes(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    base = ["schedule", "install", "--profile-repo", str(repo), "--time"]
    assert cli.main([*base, "07:30"]) == 0
    scheduler = home / "scheduler"
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert stat.S_IMODE(scheduler.stat().st_mode) == 0o700
    for name in ("config.json", "launcher.py"):
        assert stat.S_IMODE((scheduler / name).stat().st_mode) == 0o600

    os.chmod(home, 0o755)
    os.chmod(scheduler, 0o755)
    os.chmod(scheduler / "config.json", 0o644)
    os.chmod(scheduler / "launcher.py", 0o644)
    service.read_scheduler_config(home)
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert stat.S_IMODE(scheduler.stat().st_mode) == 0o700
    assert stat.S_IMODE((scheduler / "config.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((scheduler / "launcher.py").stat().st_mode) == 0o600

    fake_adapter.fail_times.add("08:00")
    with pytest.raises(ConfigError):
        service.install(home, repo, "08:00")
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert stat.S_IMODE(scheduler.stat().st_mode) == 0o700
    assert stat.S_IMODE((scheduler / "config.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((scheduler / "launcher.py").stat().st_mode) == 0o600


def test_management_operations_share_launcher_lock_without_mutation(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert service.install(home, repo, "07:30").time == "07:30"
    config = home / "scheduler" / "config.json"
    before = config.read_bytes()
    calls_before = list(fake_adapter.calls)
    permission_mutations = []

    with acquire_home_lock(home, service.SCHEDULER_LOCK_NAME):
        monkeypatch.setattr(
            service,
            "_restrict_to_owner",
            lambda *args: permission_mutations.append(args),
        )
        monkeypatch.setattr(
            profile_config,
            "_restrict_to_owner",
            lambda *args: permission_mutations.append(args),
        )
        lock_path = home / service.SCHEDULER_LOCK_NAME
        inode = lock_path.stat().st_ino
        with pytest.raises(LockError, match="another aiprofile refresh"):
            service.install(home, repo, "08:00")
        with pytest.raises(LockError, match="another aiprofile refresh"):
            service.remove(home)
        with pytest.raises(LockError, match="another aiprofile refresh"):
            acquire_home_lock(home, service.SCHEDULER_LOCK_NAME).__enter__()
        assert lock_path.stat().st_ino == inode
        assert config.read_bytes() == before
        assert fake_adapter.calls == [*calls_before, ("status", None)]
        assert permission_mutations == []


def test_install_revalidates_home_after_acquiring_management_lock(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)

    class ConfigBreaksBeforeLock:
        def __enter__(self):
            (home / "config.json").write_text('{"salt":', encoding="utf-8")
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(
        service,
        "acquire_home_lock",
        lambda *_args, **_kwargs: ConfigBreaksBeforeLock(),
    )
    with pytest.raises(ConfigError, match="run 'aiprofile init' first"):
        service.install(home, repo, "07:30")
    assert not (home / "scheduler").exists()
    assert fake_adapter.calls == [("status", None)]


def test_install_refuses_branch_change_before_management_lock(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "private-home-canary")
    repo = _repo(tmp_path)

    class BranchChangesBeforeLock:
        def __enter__(self):
            _git(repo, "checkout", "-q", "-b", "other")
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(
        service,
        "acquire_home_lock",
        lambda *_args, **_kwargs: BranchChangesBeforeLock(),
    )
    with pytest.raises(ConfigError, match="repository state changed") as exc:
        service.install(home, repo, "07:30")
    assert str(repo) not in str(exc.value)
    assert repo.name not in str(exc.value)
    assert not (home / "scheduler").exists()
    assert fake_adapter.calls == [("status", None)]


def test_install_revalidates_repository_before_native_registration(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "private-home-canary")
    repo = _repo(tmp_path)
    original_write = service.write_scheduler_files

    def write_then_switch(*args, **kwargs):
        result = original_write(*args, **kwargs)
        _git(repo, "checkout", "-q", "-b", "other")
        return result

    monkeypatch.setattr(service, "write_scheduler_files", write_then_switch)
    with pytest.raises(ConfigError, match="repository state changed") as exc:
        service.install(home, repo, "07:30")
    assert str(repo) not in str(exc.value)
    assert repo.name not in str(exc.value)
    assert not (home / "scheduler").exists()
    assert fake_adapter.calls == [("status", None), ("status", None)]


def test_reinstall_pre_native_drift_does_not_touch_existing_native_schedule(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "private-home-canary")
    repo = _repo(tmp_path)
    assert service.install(home, repo, "07:30").time == "07:30"
    old_config = (home / "scheduler" / "config.json").read_bytes()
    fake_adapter.calls.clear()
    original_write = service.write_scheduler_files

    def write_then_switch(*args, **kwargs):
        result = original_write(*args, **kwargs)
        _git(repo, "checkout", "-q", "-b", "other")
        return result

    monkeypatch.setattr(service, "write_scheduler_files", write_then_switch)
    with pytest.raises(ConfigError, match="repository state changed"):
        service.install(home, repo, "08:00")
    assert (home / "scheduler" / "config.json").read_bytes() == old_config
    assert service.read_scheduler_config(home).time == "07:30"
    assert fake_adapter.installed is True
    assert fake_adapter.calls == [("status", None), ("status", None)]


def test_install_rolls_back_native_registration_on_post_install_branch_drift(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "private-home-canary")
    repo = _repo(tmp_path)
    original_install = fake_adapter.install

    def install_then_switch(call_home, time):
        original_install(call_home, time)
        _git(repo, "checkout", "-q", "-b", "other")

    fake_adapter.install = install_then_switch
    with pytest.raises(ConfigError, match="previous state restored") as exc:
        service.install(home, repo, "07:30")
    assert str(repo) not in str(exc.value)
    assert repo.name not in str(exc.value)
    assert fake_adapter.installed is False
    assert fake_adapter.calls == [
        ("status", None),
        ("status", None),
        ("install", "07:30"),
        ("remove", None),
    ]
    assert not (home / "scheduler").exists()


def test_install_permission_failure_keeps_default_diagnostics_path_free(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "private-home-canary")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    monkeypatch.setattr(profile_config, "_WARN_ON_CHMOD_FAILURE", True)

    def fail_chmod(_path, _mode):
        raise OSError("private-chmod-detail-canary")

    monkeypatch.setattr(os, "chmod", fail_chmod)
    monkeypatch.setattr(
        service,
        "_restrict_to_owner",
        lambda *_args: (_ for _ in ()).throw(
            ConfigError("scheduler privacy permissions could not be enforced")
        ),
    )
    before_head = _git(repo, "rev-parse", "HEAD").stdout
    before_status = _git(repo, "status", "--porcelain").stdout
    assert (
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
        )
        == 1
    )
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "could not restrict permissions on a private profile file" in combined
    for canary in (
        str(home),
        home.name,
        "config.json",
        "private-chmod-detail-canary",
        "Traceback",
    ):
        assert canary not in combined
    assert not (home / "scheduler").exists()
    assert fake_adapter.calls == [("status", None), ("status", None)]
    assert _git(repo, "rev-parse", "HEAD").stdout == before_head
    assert _git(repo, "status", "--porcelain").stdout == before_status


def test_status_reports_installed_and_not_installed(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert cli.main(["schedule", "status"]) == 0
    captured = capsys.readouterr()
    assert "not installed" in captured.out

    assert (
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
        )
        == 0
    )
    capsys.readouterr()
    (home / "scheduler" / "last-run.log").write_text(
        "2026-08-09T00:00:00+00:00 refresh completed; no change\n",
        encoding="utf-8",
    )
    assert cli.main(["schedule", "status"]) == 0
    captured = capsys.readouterr()
    assert "installed" in captured.out
    assert "07:30" in captured.out
    assert "main" in captured.out
    assert "origin" in captured.out
    assert "no change" in captured.out
    assert str(repo) not in captured.out
    assert repo.name not in captured.out


def test_status_dry_run_is_strictly_read_only(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    service.write_scheduler_files(
        home, repo, "07:30", True, branch="main", remote="origin"
    )
    before = _tree_state(home)
    permission_mutations = []
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    monkeypatch.setattr(
        service,
        "_restrict_to_owner",
        lambda *args: permission_mutations.append(args),
    )
    assert cli.main(["schedule", "status", "--dry-run"]) == 0
    captured = capsys.readouterr()
    assert "would inspect native scheduler status" in captured.out
    assert _tree_state(home) == before
    assert permission_mutations == []
    assert fake_adapter.calls == []


@pytest.mark.parametrize("dry_run", [False, True])
def test_status_invalid_utf8_config_is_path_free(
    tmp_path, monkeypatch, fake_adapter, capsys, dry_run
):
    home = _initialized_home(tmp_path / "private-home-canary")
    scheduler = home / "scheduler"
    scheduler.mkdir()
    (scheduler / "config.json").write_bytes(b"\xff")
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    args = ["schedule", "status"]
    if dry_run:
        args.append("--dry-run")
    assert cli.main(args) == 1
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "scheduler configuration is unavailable or invalid" in combined
    assert "Traceback" not in combined
    assert str(home) not in combined
    assert home.name not in combined
    assert fake_adapter.calls == []


def test_status_invalid_utf8_last_run_is_unavailable_not_traceback(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "private-home-canary")
    repo = _repo(tmp_path)
    service.write_scheduler_files(
        home, repo, "07:30", True, branch="main", remote="origin"
    )
    (home / "scheduler" / "last-run.log").write_bytes(b"\xff")
    fake_adapter.installed = True
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert cli.main(["schedule", "status"]) == 0
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "last-run log is unavailable or invalid" in combined
    assert "Traceback" not in combined
    assert str(home) not in combined
    assert home.name not in combined


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink and mode semantics")
@pytest.mark.parametrize("name", ["pending-push.json", "last-run.log"])
def test_status_rejects_tool_state_symlink_without_mutating_target(
    tmp_path, monkeypatch, fake_adapter, capsys, name
):
    home = _initialized_home(tmp_path / "private-home-canary")
    repo = _repo(tmp_path)
    service.write_scheduler_files(
        home, repo, "07:30", True, branch="main", remote="origin"
    )
    outside = tmp_path / "outside-private-canary"
    outside.write_text("outside-bytes", encoding="utf-8")
    outside.chmod(0o644)
    os.symlink(outside, home / "scheduler" / name)
    before = (outside.read_bytes(), stat.S_IMODE(outside.stat().st_mode))
    monkeypatch.setenv("AIPROFILE_HOME", str(home))

    assert cli.main(["schedule", "status"]) == 1
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "scheduler configuration is unavailable or invalid" in combined
    assert str(home) not in combined
    assert str(outside) not in combined
    assert (outside.read_bytes(), stat.S_IMODE(outside.stat().st_mode)) == before
    assert fake_adapter.calls == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink and mode semantics")
def test_status_dry_run_rejects_scheduler_directory_symlink_without_mutation(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "private-home-canary")
    outside_home = tmp_path / "outside-home"
    repo = _repo(tmp_path)
    service.write_scheduler_files(
        outside_home, repo, "07:30", True, branch="main", remote="origin"
    )
    outside = outside_home / "scheduler"
    outside.chmod(0o755)
    os.symlink(outside, home / "scheduler", target_is_directory=True)
    before = _tree_state(outside_home)
    before_mode = stat.S_IMODE(outside.stat().st_mode)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))

    assert cli.main(["schedule", "status", "--dry-run"]) == 1
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "scheduler configuration is unavailable or invalid" in combined
    assert str(home) not in combined
    assert str(outside) not in combined
    assert _tree_state(outside_home) == before
    assert stat.S_IMODE(outside.stat().st_mode) == before_mode
    assert fake_adapter.calls == []


def test_remove_idempotent_and_cleans_home(tmp_path, monkeypatch, fake_adapter, capsys):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert (
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["schedule", "remove"]) == 0
    assert not (home / "scheduler").exists()
    assert cli.main(["schedule", "remove"]) == 0
    captured = capsys.readouterr()
    assert "not installed" in captured.out
    before = list(home.iterdir()) if home.exists() else []
    assert cli.main(["schedule", "remove", "--dry-run"]) == 0
    assert (list(home.iterdir()) if home.exists() else []) == before


def test_remove_failure_reports_residual_state_honestly(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert (
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
        )
        == 0
    )
    capsys.readouterr()
    fake_adapter.fail_remove = True
    assert cli.main(["schedule", "remove"]) == 1
    captured = capsys.readouterr()
    assert "native registration may remain" in captured.err
    assert "local artifacts were retained" in captured.err
    assert "private removal path canary" not in captured.err
    assert (home / "scheduler" / "config.json").exists()


def test_remove_without_local_state_still_cleans_native_registration(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    fake_adapter.installed = True
    assert cli.main(["schedule", "remove"]) == 0
    assert ("remove", None) in fake_adapter.calls
    assert fake_adapter.installed is False


def test_remove_rechecks_local_state_after_acquiring_management_lock(
    tmp_path, monkeypatch, fake_adapter
):
    home = _initialized_home(tmp_path / "home")
    profile = tmp_path / "profile"
    profile.mkdir()

    class InstallCompletesBeforeLock:
        def __enter__(self):
            service.write_scheduler_files(
                home,
                profile,
                "07:30",
                True,
                branch="main",
                remote="origin",
            )
            fake_adapter.installed = True
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(
        service,
        "acquire_home_lock",
        lambda *_args, **_kwargs: InstallCompletesBeforeLock(),
    )
    result = service.remove(home)
    assert result.removed is True
    assert fake_adapter.installed is False
    assert not (home / "scheduler").exists()


def test_schedule_never_stores_tokens(tmp_path, monkeypatch, fake_adapter):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert (
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
        )
        == 0
    )
    scheduler = home / "scheduler"
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in scheduler.iterdir() if path.is_file()
    )
    lowered = combined.lower()
    assert "ghp_" not in lowered
    assert "authorization" not in lowered
    assert "token" not in lowered
    assert set(json.loads((scheduler / "config.json").read_text(encoding="utf-8"))) == {
        "profile_repo",
        "time",
        "push",
        "branch",
        "remote",
        "installed_version",
    }


def test_status_rejects_tampered_display_fields_without_leaking_them(
    tmp_path, monkeypatch, fake_adapter, capsys
):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert (
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
        )
        == 0
    )
    capsys.readouterr()
    config_path = home / "scheduler" / "config.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["branch"] = "main\nprivate-path-canary"
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    assert cli.main(["schedule", "status"]) == 1
    captured = capsys.readouterr()
    assert "scheduler configuration is unavailable or invalid" in captured.err
    assert "private-path-canary" not in captured.err


def test_status_never_echoes_tampered_last_run_log(tmp_path, monkeypatch, fake_adapter, capsys):
    home = _initialized_home(tmp_path / "home")
    repo = _repo(tmp_path)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    assert (
        cli.main(
            ["schedule", "install", "--profile-repo", str(repo), "--time", "07:30"]
        )
        == 0
    )
    capsys.readouterr()
    canary = str(tmp_path / "private-log-path-canary")
    (home / "scheduler" / "last-run.log").write_text(
        f"2026-08-09T00:00:00+00:00 failed at {canary}\n", encoding="utf-8"
    )
    assert cli.main(["schedule", "status"]) == 0
    captured = capsys.readouterr()
    assert canary not in captured.out + captured.err
    assert "last-run log is unavailable or invalid" in captured.out
def test_scheduler_state_rejects_windows_reparse_points():
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    info = SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=reparse)
    assert service._is_link_or_reparse(info) is True

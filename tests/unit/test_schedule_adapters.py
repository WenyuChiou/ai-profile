"""Native scheduler adapter contracts (v0.7.0 Tasks B3-B5)."""

from __future__ import annotations

import copy
import os
import plistlib
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from aiprofile.errors import ConfigError
from aiprofile.schedule import adapters
from aiprofile.schedule.adapters import (
    AdapterPlan,
    PlannedCommand,
    PlannedFile,
    launchd,
    systemd,
    windows,
)


def _completed(argv, rc=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, rc, stdout, stderr)


def _xml_payload(plan):
    planned = next(file for file in plan.files if file.path.name == "task.xml")
    return ET.fromstring(planned.content.decode("utf-16"))


def _find_text(root, local_name):
    node = next(node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == local_name)
    return node.text


def test_windows_install_registers_via_xml_not_tr(tmp_path):
    home = tmp_path / "home"
    plan = windows.plan(home, "07:30")
    assert [list(command.argv) for command in plan.commands] == [
        [
            "schtasks",
            "/Create",
            "/TN",
            windows.task_name(home),
            "/XML",
            str((tmp_path / "home" / "scheduler" / "task.xml").resolve()),
            "/F",
        ]
    ]
    flat = [part for command in plan.commands for part in command.argv]
    assert all(flag not in flat for flag in ("/TR", "/SC", "/ST"))


def test_windows_task_xml_contract(tmp_path):
    root = _xml_payload(windows.plan(tmp_path / "home", "07:30"))
    launcher_path = (tmp_path / "home" / "scheduler" / "launcher.py").resolve()
    assert _find_text(root, "Command") == sys.executable
    assert _find_text(root, "Arguments") == f'"{launcher_path}"'
    assert _find_text(root, "LogonType") == "InteractiveToken"
    assert _find_text(root, "RunLevel") == "LeastPrivilege"
    assert _find_text(root, "MultipleInstancesPolicy") == "IgnoreNew"
    assert _find_text(root, "StartWhenAvailable") == "true"
    assert _find_text(root, "StartBoundary").endswith("T07:30:00")


def test_windows_hostile_paths_stay_inert(tmp_path):
    home = tmp_path / "space & caret^ apostrophe' less< unicode-測試"
    root = _xml_payload(windows.plan(home, "08:05"))
    assert _find_text(root, "Command") == sys.executable
    assert _find_text(root, "Arguments") == f'"{(home / "scheduler" / "launcher.py").resolve()}"'
    with pytest.raises(ConfigError, match="unsupported character"):
        windows.plan(Path(str(home) + '"bad'), "08:05")


def test_windows_status_parses_query_and_remove_is_idempotent(tmp_path):
    calls = []
    home = tmp_path / "home"
    query_xml = windows.plan(home, "07:30").files[0].content.decode("utf-16")

    def installed(argv, **kwargs):
        calls.append((argv, kwargs))
        return _completed(argv, stdout=query_xml)

    status = windows.status(home, runner=installed)
    assert status.installed is True
    assert status.time == "07:30"
    assert status.active is True
    assert calls[0][0] == [
        "schtasks",
        "/Query",
        "/TN",
        windows.task_name(home),
        "/XML",
    ]
    assert calls[0][1]["shell"] is False

    assert windows.status(
        home, runner=lambda argv, **_: _completed(argv, rc=1)
    ).installed is False
    windows.remove(
        home,
        runner=lambda argv, **_: _completed(
            argv, rc=1, stderr="task does not exist"
        ),
    )


def test_windows_status_reports_disabled_task_from_locale_independent_xml(tmp_path):
    home = tmp_path / "home"
    root = _xml_payload(windows.plan(home, "07:30"))
    settings = next(
        node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "Settings"
    )
    enabled = next(
        node for node in settings if node.tag.rsplit("}", 1)[-1] == "Enabled"
    )
    enabled.text = "false"
    query_xml = ET.tostring(root, encoding="unicode")

    result = windows.status(
        home,
        runner=lambda argv, **_: _completed(argv, stdout=query_xml),
    )

    assert result == adapters.ScheduleStatus(
        installed=True,
        time="07:30",
        active=False,
    )

    enabled.text = "true"
    trigger = next(
        node
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "CalendarTrigger"
    )
    trigger_enabled = next(
        node for node in trigger if node.tag.rsplit("}", 1)[-1] == "Enabled"
    )
    trigger_enabled.text = "false"
    trigger_disabled_xml = ET.tostring(root, encoding="unicode")
    assert windows.status(
        home,
        runner=lambda argv, **_: _completed(argv, stdout=trigger_disabled_xml),
    ).active is False


@pytest.mark.parametrize(
    ("field", "value"),
    [("UserId", "different-user"), ("RunLevel", "HighestAvailable")],
)
def test_windows_status_rejects_principal_security_drift(tmp_path, field, value):
    home = tmp_path / "home"
    root = _xml_payload(windows.plan(home, "07:30"))
    node = next(
        item for item in root.iter() if item.tag.rsplit("}", 1)[-1] == field
    )
    node.text = value

    with pytest.raises(ConfigError, match="native scheduler status is unavailable"):
        windows.status(
            home,
            runner=lambda argv, **_: _completed(
                argv, stdout=ET.tostring(root, encoding="unicode")
            ),
        )


def test_windows_status_rejects_multiple_calendar_triggers(tmp_path):
    home = tmp_path / "home"
    root = _xml_payload(windows.plan(home, "07:30"))
    triggers = next(
        node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "Triggers"
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

    with pytest.raises(ConfigError, match="native scheduler status is unavailable"):
        windows.status(
            home,
            runner=lambda argv, **_: _completed(
                argv,
                stdout=ET.tostring(root, encoding="unicode"),
            ),
        )


@pytest.mark.parametrize(
    "boundary",
    [
        "2000-01-01T07:30:00Z",
        "2000-01-01T07:30:00+14:00",
        "2099-12-31T07:30:59",
        "2000-01-01T0\u0667:3\u0660:00",
    ],
)
def test_windows_status_rejects_noncanonical_start_boundary(tmp_path, boundary):
    home = tmp_path / "home"
    root = _xml_payload(windows.plan(home, "07:30"))
    start = next(
        node
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "StartBoundary"
    )
    start.text = boundary

    with pytest.raises(ConfigError, match="native scheduler status is unavailable"):
        windows.status(
            home,
            runner=lambda argv, **_: _completed(
                argv,
                stdout=ET.tostring(root, encoding="unicode"),
            ),
        )


@pytest.mark.parametrize(
    "extra_name",
    ["ExecutionTimeLimit", "RestartOnFailure"],
)
def test_windows_status_rejects_extra_execution_settings(tmp_path, extra_name):
    home = tmp_path / "home"
    root = _xml_payload(windows.plan(home, "07:30"))
    settings = next(
        node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "Settings"
    )
    extra = ET.SubElement(settings, f"{{{windows._NS}}}{extra_name}")
    if extra_name == "ExecutionTimeLimit":
        extra.text = "PT1S"
    else:
        interval = ET.SubElement(extra, f"{{{windows._NS}}}Interval")
        interval.text = "PT1M"
        count = ET.SubElement(extra, f"{{{windows._NS}}}Count")
        count.text = "999"

    with pytest.raises(ConfigError, match="native scheduler status is unavailable"):
        windows.status(
            home,
            runner=lambda argv, **_: _completed(
                argv,
                stdout=ET.tostring(root, encoding="unicode"),
            ),
        )


def test_windows_status_nonzero_with_owned_definition_fails_closed(tmp_path):
    home = tmp_path / "home"
    planned = windows.plan(home, "07:30").files[0]
    planned.path.parent.mkdir(parents=True)
    planned.path.write_bytes(planned.content)

    with pytest.raises(ConfigError, match="native scheduler status is unavailable"):
        windows.status(
            home,
            runner=lambda argv, **_: _completed(
                argv,
                rc=1,
                stderr="ACCESS DENIED private-path-canary",
            ),
        )


def test_two_homes_have_distinct_native_identities_on_every_adapter(
    tmp_path, monkeypatch
):
    first = tmp_path / "home-a"
    second = tmp_path / "home-b"
    monkeypatch.setattr(launchd, "_user_home", lambda: tmp_path / "user")
    monkeypatch.setattr(launchd, "_uid", lambda: 500)
    monkeypatch.setattr(systemd, "_user_home", lambda: tmp_path / "user")

    assert windows.task_name(first) != windows.task_name(second)
    assert launchd.label(first) != launchd.label(second)
    assert systemd.unit_names(first) != systemd.unit_names(second)
    assert windows.task_name(first) == windows.task_name(first.resolve())


def test_windows_install_status_remove_are_isolated_between_homes(tmp_path):
    first = tmp_path / "home-a"
    second = tmp_path / "home-b"
    tasks: dict[str, bytes] = {}

    def runner(argv, **_kwargs):
        name = argv[argv.index("/TN") + 1]
        if "/Create" in argv:
            xml_path = Path(argv[argv.index("/XML") + 1])
            tasks[name] = xml_path.read_bytes()
            return _completed(argv)
        if "/Delete" in argv:
            tasks.pop(name, None)
            return _completed(argv)
        return _completed(
            argv,
            rc=0 if name in tasks else 1,
            stdout=tasks.get(name, b""),
        )

    windows.install(first, "07:30", runner=runner)
    windows.install(second, "08:30", runner=runner)
    assert windows.status(first, runner=runner).installed is True
    assert windows.status(second, runner=runner).installed is True
    windows.remove(first, runner=runner)
    assert windows.status(first, runner=runner).installed is False
    assert windows.status(second, runner=runner).installed is True


def test_launchd_plan_writes_plist_and_bootstraps(tmp_path, monkeypatch):
    user_home = tmp_path / "user"
    monkeypatch.setattr(launchd, "_user_home", lambda: user_home)
    monkeypatch.setattr(launchd, "_uid", lambda: 501)
    home = tmp_path / "profile home"
    home_label = launchd.label(home)
    plan = launchd.plan(home, "09:41")
    planned = plan.files[0]
    payload = plistlib.loads(planned.content)
    assert planned.path == user_home / "Library/LaunchAgents" / f"{home_label}.plist"
    assert payload["ProgramArguments"] == [
        sys.executable,
        str((home / "scheduler" / "launcher.py").resolve()),
    ]
    assert payload["StartCalendarInterval"] == {"Hour": 9, "Minute": 41}
    assert payload["RunAtLoad"] is False
    assert payload["Label"] == home_label
    assert [list(command.argv) for command in plan.commands] == [
        ["launchctl", "bootout", f"gui/501/{home_label}"],
        ["launchctl", "bootstrap", "gui/501", str(planned.path)],
    ]
    assert plan.commands[0].ignore_failure is True


def test_launchd_plist_round_trips_hostile_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(launchd, "_user_home", lambda: tmp_path / "user")
    monkeypatch.setattr(launchd, "_uid", lambda: 502)
    home = tmp_path / 'space<&" unicode-測試'
    payload = plistlib.loads(launchd.plan(home, "10:12").files[0].content)
    assert payload["ProgramArguments"][1] == str(
        (home / "scheduler" / "launcher.py").resolve()
    )
    source = Path(launchd.__file__).read_text(encoding="utf-8")
    assert "xml.sax.saxutils" not in source


def test_launchd_status_and_remove_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(launchd, "_user_home", lambda: tmp_path / "user")
    monkeypatch.setattr(launchd, "_uid", lambda: 503)
    home = tmp_path / "home"
    planned = launchd.plan(home, "09:41").files[0]
    planned.path.parent.mkdir(parents=True)
    planned.path.write_bytes(planned.content)
    assert launchd.status(
        home, runner=lambda argv, **_: _completed(argv)
    ) == adapters.ScheduleStatus(installed=True, time="09:41", active=True)
    assert launchd.status(
        home, runner=lambda argv, **_: _completed(argv, rc=1)
    ) == adapters.ScheduleStatus(installed=True, time="09:41", active=False)
    absent_home = tmp_path / "absent-home"
    assert launchd.status(
        absent_home, runner=lambda argv, **_: _completed(argv, rc=1)
    ).installed is False
    launchd.remove(
        absent_home,
        runner=lambda argv, **_: _completed(
            argv, rc=1, stderr="Could not find specified service"
        ),
    )


def test_launchd_status_rejects_additional_execution_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(launchd, "_user_home", lambda: tmp_path / "user")
    monkeypatch.setattr(launchd, "_uid", lambda: 503)
    home = tmp_path / "home"
    planned = launchd.plan(home, "09:41").files[0]
    payload = plistlib.loads(planned.content)
    payload["KeepAlive"] = True
    planned.path.parent.mkdir(parents=True)
    planned.path.write_bytes(plistlib.dumps(payload))

    with pytest.raises(ConfigError, match="native scheduler status is unavailable"):
        launchd.status(home, runner=lambda argv, **_: _completed(argv))


def test_systemd_plan_writes_unit_and_timer(tmp_path, monkeypatch):
    user_home = tmp_path / "user"
    monkeypatch.setattr(systemd, "_user_home", lambda: user_home)
    home = tmp_path / "profile home"
    service_name, timer_name = systemd.unit_names(home)
    plan = systemd.plan(home, "06:37")
    files = {file.path.name: file.content.decode("utf-8") for file in plan.files}
    assert "ExecStart=" in files[service_name]
    assert systemd.quote_word(sys.executable) in files[service_name]
    assert systemd.quote_word(str((home / "scheduler" / "launcher.py").resolve())) in files[
        service_name
    ]
    assert "OnCalendar=*-*-* 06:37:00" in files[timer_name]
    assert "Persistent=true" in files[timer_name]
    assert [list(command.argv) for command in plan.commands] == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", timer_name],
    ]


def test_systemd_execstart_quotes_hostile_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(systemd, "_user_home", lambda: tmp_path / "user")
    home = tmp_path / 'space $ percent% quote" slash\\ unicode-測試'
    plan = systemd.plan(home, "11:22")
    service_text = next(
        file.content.decode("utf-8")
        for file in plan.files
        if file.path.name.endswith(".service")
    )
    assert "%%" in service_text
    assert r'\"' in service_text
    raw_launcher = str((home / "scheduler" / "launcher.py").resolve()).replace(
        "%", "%%"
    )
    assert raw_launcher not in service_text
    with pytest.raises(ConfigError, match="unsupported character"):
        systemd.quote_word("bad\npath")
    assert systemd.quote_word("$HOME") == '"$$HOME"'
    assert systemd.quote_word("${HOME}") == '"$${HOME}"'


def test_systemd_status_and_remove_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(systemd, "_user_home", lambda: tmp_path / "user")
    home = tmp_path / "home"
    for planned in systemd.plan(home, "06:37").files:
        planned.path.parent.mkdir(parents=True, exist_ok=True)
        planned.path.write_bytes(planned.content)

    def enabled(argv, **_kwargs):
        if "is-enabled" in argv or "is-active" in argv:
            return _completed(argv, stdout="enabled\n")
        return _completed(argv)

    status = systemd.status(home, runner=enabled)
    assert status.installed is True
    assert status.time == "06:37"
    assert status.active is True
    disabled = systemd.status(
        home,
        runner=lambda argv, **_: _completed(argv, rc=1),
    )
    assert disabled == adapters.ScheduleStatus(
        installed=True,
        time="06:37",
        active=False,
    )
    systemd.remove(
        tmp_path / "absent-home",
        runner=lambda argv, **_: (
            _completed(argv)
            if "daemon-reload" in argv
            else _completed(argv, rc=1, stderr="Unit does not exist")
        ),
    )


def test_adapter_processes_are_argv_and_never_shell(tmp_path, monkeypatch):
    monkeypatch.setattr(launchd, "_user_home", lambda: tmp_path / "user")
    monkeypatch.setattr(launchd, "_uid", lambda: 504)
    monkeypatch.setattr(systemd, "_user_home", lambda: tmp_path / "user")
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return _completed(argv)

    windows.install(tmp_path / "home", "07:30", runner=runner)
    launchd.install(tmp_path / "home", "07:30", runner=runner)
    systemd.install(tmp_path / "home", "07:30", runner=runner)
    assert calls
    assert all(isinstance(argv, list) and kwargs.get("shell") is False for argv, kwargs in calls)


def test_adapter_runner_failure_is_safe_and_rolls_back(tmp_path):
    home = tmp_path / "home-private-canary"

    def timeout(argv, **_kwargs):
        raise subprocess.TimeoutExpired(argv, 60)

    with pytest.raises(ConfigError, match="native scheduler registration failed"):
        windows.install(home, "07:30", runner=timeout)
    assert not (home / "scheduler" / "task.xml").exists()

    def missing(argv, **_kwargs):
        raise FileNotFoundError("private-command-path-canary")

    with pytest.raises(ConfigError, match="native scheduler command is unavailable") as exc:
        windows.status(home, runner=missing)
    assert "private-command-path-canary" not in str(exc.value)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits only")
def test_native_scheduler_payload_is_owner_only_on_posix(tmp_path):
    payload = tmp_path / "shared-parent" / "private-native-payload"
    adapters.apply_plan(
        AdapterPlan(files=(PlannedFile(payload, b"private"),), commands=()),
        lambda argv, **kwargs: _completed(argv),
    )
    assert stat.S_IMODE(payload.stat().st_mode) == 0o600


def test_native_payload_permission_failure_is_path_free_and_rolls_back(
    tmp_path, monkeypatch
):
    payload = tmp_path / "private-path-canary" / "native-payload"
    command_called = False

    def fail_chmod(_path, _mode):
        raise OSError("private-path-canary")

    def runner(argv, **_kwargs):
        nonlocal command_called
        command_called = True
        return _completed(argv)

    monkeypatch.setattr(adapters, "_ENFORCE_POSIX_PERMISSIONS", True, raising=False)
    monkeypatch.setattr(os, "chmod", fail_chmod)
    plan = AdapterPlan(
        files=(PlannedFile(payload, b"private"),),
        commands=(PlannedCommand(("native-scheduler", "register")),),
    )
    with pytest.raises(ConfigError, match="native scheduler registration failed") as exc:
        adapters.apply_plan(plan, runner)
    assert "private-path-canary" not in str(exc.value)
    assert not payload.exists()
    assert command_called is False


def test_remove_ignores_only_missing_registration_not_other_failures(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    windows.remove(
        home,
        runner=lambda argv, **_: _completed(
            argv, rc=1, stderr="ERROR: The system cannot find the file specified."
        ),
    )
    task_xml = home / "scheduler" / "task.xml"
    task_xml.parent.mkdir(parents=True)
    task_xml.write_text("owned", encoding="utf-8")
    with pytest.raises(ConfigError, match="native scheduler removal failed"):
        windows.remove(
            home,
            runner=lambda argv, **_: _completed(
                argv, rc=5, stderr="access denied private-path-canary"
            ),
        )

    monkeypatch.setattr(launchd, "_user_home", lambda: tmp_path / "user")
    monkeypatch.setattr(launchd, "_uid", lambda: 505)
    launchd.remove(
        home,
        runner=lambda argv, **_: _completed(
            argv, rc=3, stderr="Could not find specified service"
        ),
    )
    launchd._plist_path(home).parent.mkdir(parents=True, exist_ok=True)
    launchd._plist_path(home).write_text("owned", encoding="utf-8")
    with pytest.raises(ConfigError, match="native scheduler removal failed"):
        launchd.remove(
            home,
            runner=lambda argv, **_: _completed(argv, rc=5, stderr="permission denied"),
        )

    monkeypatch.setattr(systemd, "_user_home", lambda: tmp_path / "user")
    unit_dir = tmp_path / "user" / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True)
    _service_name, timer_name = systemd.unit_names(home)
    (unit_dir / timer_name).write_text("timer", encoding="utf-8")
    with pytest.raises(ConfigError, match="native scheduler removal failed"):
        systemd.remove(
            home,
            runner=lambda argv, **_: _completed(argv, rc=1, stderr="permission denied"),
        )

    (unit_dir / timer_name).unlink(missing_ok=True)
    with pytest.raises(ConfigError, match="native scheduler removal failed"):
        systemd.remove(
            home,
            runner=lambda argv, **_: (
                _completed(argv, rc=7, stderr="daemon denied")
                if "daemon-reload" in argv
                else _completed(argv)
            ),
        )


def test_remove_idempotence_does_not_depend_on_english_stderr(
    tmp_path, monkeypatch
):
    localized = "不存在的排程項目"

    windows_calls = []
    home = tmp_path / "home"
    windows.remove(
        home,
        runner=lambda argv, **_: (
            windows_calls.append(argv) or _completed(argv, rc=1, stderr=localized)
        ),
    )
    assert windows_calls == [
        ["schtasks", "/Query", "/TN", windows.task_name(home), "/FO", "LIST"]
    ]

    monkeypatch.setattr(launchd, "_user_home", lambda: tmp_path / "user")
    monkeypatch.setattr(launchd, "_uid", lambda: 506)
    launchd_calls = []
    launchd.remove(
        home,
        runner=lambda argv, **_: (
            launchd_calls.append(argv) or _completed(argv, rc=1, stderr=localized)
        ),
    )
    assert launchd_calls == [
        ["launchctl", "print", f"gui/506/{launchd.label(home)}"]
    ]

    monkeypatch.setattr(systemd, "_user_home", lambda: tmp_path / "user")
    systemd_calls = []

    def systemd_missing(argv, **_kwargs):
        systemd_calls.append(argv)
        if "show" in argv:
            return _completed(argv, stdout="not-found\n", stderr=localized)
        return _completed(argv)

    systemd.remove(home, runner=systemd_missing)
    assert not any("disable" in argv for argv in systemd_calls)

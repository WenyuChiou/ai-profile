"""Windows Task Scheduler adapter using a structured XML definition."""

from __future__ import annotations

import getpass
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from ...errors import ConfigError
from . import (
    AdapterPlan,
    PlannedCommand,
    PlannedFile,
    Runner,
    ScheduleStatus,
    apply_plan,
    home_identity,
    run_command,
)

_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"

_REGISTERED_SETTINGS = {
    "DisallowStartIfOnBatteries": "true",
    "StopIfGoingOnBatteries": "true",
    "MultipleInstancesPolicy": "IgnoreNew",
    "StartWhenAvailable": "true",
    "UseUnifiedSchedulingEngine": "true",
}
_REGISTERED_IDLE_SETTINGS = {
    "StopOnIdleEnd": "true",
    "RestartOnIdle": "false",
}
_COM_NORMALIZED_SETTINGS = {
    "MultipleInstancesPolicy": "IgnoreNew",
    "DisallowStartIfOnBatteries": "true",
    "StopIfGoingOnBatteries": "true",
    "AllowHardTerminate": "true",
    "StartWhenAvailable": "true",
    "RunOnlyIfNetworkAvailable": "false",
    "AllowStartOnDemand": "true",
    "Enabled": "true",
    "Hidden": "false",
    "RunOnlyIfIdle": "false",
    "DisallowStartOnRemoteAppSession": "false",
    "WakeToRun": "false",
    "ExecutionTimeLimit": "PT72H",
    "Priority": "7",
}
_COM_NORMALIZED_IDLE_SETTINGS = {
    "StopOnIdleEnd": "true",
    "RestartOnIdle": "false",
}
_COM_NORMALIZED_SETTING_VARIANTS = tuple(
    {
        **_COM_NORMALIZED_SETTINGS,
        "Enabled": enabled,
        "UseUnifiedSchedulingEngine": unified,
    }
    for unified in ("false", "true")
    for enabled in ("true", "false")
)


def task_name(home: Path) -> str:
    return f"aiprofile-refresh-{home_identity(home)}"


def _node(parent: ET.Element, name: str, text: str | None = None) -> ET.Element:
    child = ET.SubElement(parent, f"{{{_NS}}}{name}")
    child.text = text
    return child


def _local_name(node: ET.Element) -> str:
    prefix = f"{{{_NS}}}"
    if not isinstance(node.tag, str) or not node.tag.startswith(prefix):
        raise ValueError
    local_name = node.tag[len(prefix) :]
    if not local_name:
        raise ValueError
    return local_name


def _only_descendant(root: ET.Element, name: str) -> ET.Element:
    matches = [node for node in root.iter() if _local_name(node) == name]
    if len(matches) != 1:
        raise ValueError
    return matches[0]


def _only_child(parent: ET.Element, name: str) -> ET.Element:
    matches = [node for node in parent if _local_name(node) == name]
    if len(matches) != 1:
        raise ValueError
    return matches[0]


def _current_user_sid() -> str | None:
    if sys.platform != "win32":
        return None

    import ctypes
    from ctypes import wintypes

    class SidAndAttributes(ctypes.Structure):
        _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]

    class TokenUser(ctypes.Structure):
        _fields_ = [("user", SidAndAttributes)]

    token_query = 0x0008
    token_user_class = 1
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32.OpenProcessToken.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    )
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetTokenInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.c_uint,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    advapi32.GetTokenInformation.restype = wintypes.BOOL
    advapi32.ConvertSidToStringSidW.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    )
    advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
    kernel32.LocalFree.restype = ctypes.c_void_p

    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), token_query, ctypes.byref(token)
    ):
        raise OSError(ctypes.get_last_error())
    try:
        size = wintypes.DWORD()
        advapi32.GetTokenInformation(
            token, token_user_class, None, 0, ctypes.byref(size)
        )
        if size.value == 0:
            raise OSError(ctypes.get_last_error())
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi32.GetTokenInformation(
            token,
            token_user_class,
            buffer,
            size,
            ctypes.byref(size),
        ):
            raise OSError(ctypes.get_last_error())
        token_user = ctypes.cast(buffer, ctypes.POINTER(TokenUser)).contents
        sid_string = ctypes.c_void_p()
        if not advapi32.ConvertSidToStringSidW(
            token_user.user.sid, ctypes.byref(sid_string)
        ):
            raise OSError(ctypes.get_last_error())
        try:
            return ctypes.wstring_at(sid_string.value)
        finally:
            kernel32.LocalFree(sid_string)
    finally:
        kernel32.CloseHandle(token)


def _validate_owned_principal(principal: ET.Element) -> None:
    names = [_local_name(child) for child in principal]
    if len(names) != len(set(names)) or principal.get("id") != "Author":
        raise ValueError
    if set(names) == {"UserId", "LogonType", "RunLevel"}:
        if (
            _only_child(principal, "UserId").text != getpass.getuser()
            or _only_child(principal, "LogonType").text != "InteractiveToken"
            or _only_child(principal, "RunLevel").text != "LeastPrivilege"
        ):
            raise ValueError
        return
    if set(names) != {"UserId", "LogonType"}:
        raise ValueError
    try:
        expected_sid = _current_user_sid()
    except OSError as exc:
        raise ValueError from exc
    if (
        expected_sid is None
        or _only_child(principal, "UserId").text != expected_sid
        or _only_child(principal, "LogonType").text != "InteractiveToken"
    ):
        raise ValueError


def _validate_owned_settings(settings: ET.Element) -> str:
    names = [_local_name(child) for child in settings]
    name_set = set(names)
    if len(names) != len(name_set):
        raise ValueError
    registered_names = set(_REGISTERED_SETTINGS) | {"IdleSettings"}
    if frozenset(name_set) in {
        frozenset(registered_names),
        frozenset(registered_names | {"Enabled"}),
    }:
        for name, expected in _REGISTERED_SETTINGS.items():
            if _only_child(settings, name).text != expected:
                raise ValueError
        idle = _only_child(settings, "IdleSettings")
        idle_names = [_local_name(child) for child in idle]
        if len(idle_names) != len(set(idle_names)) or set(idle_names) != set(
            _REGISTERED_IDLE_SETTINGS
        ):
            raise ValueError
        for name, expected in _REGISTERED_IDLE_SETTINGS.items():
            if _only_child(idle, name).text != expected:
                raise ValueError
        if "Enabled" not in name_set:
            return "true"
        if _only_child(settings, "Enabled").text != "false":
            raise ValueError
        return "false"
    expected_names = set(_COM_NORMALIZED_SETTINGS) | {
        "IdleSettings",
        "UseUnifiedSchedulingEngine",
    }
    if name_set != expected_names:
        raise ValueError
    actual_settings = {
        name: _only_child(settings, name).text
        for name in expected_names
        if name != "IdleSettings"
    }
    if actual_settings not in _COM_NORMALIZED_SETTING_VARIANTS:
        raise ValueError
    idle = _only_child(settings, "IdleSettings")
    idle_names = [_local_name(child) for child in idle]
    if len(idle_names) != len(set(idle_names)) or set(idle_names) != set(
        _COM_NORMALIZED_IDLE_SETTINGS
    ):
        raise ValueError
    for name, expected in _COM_NORMALIZED_IDLE_SETTINGS.items():
        if _only_child(idle, name).text != expected:
            raise ValueError
    return actual_settings["Enabled"] or ""


def _task_xml(home: Path, time: str) -> bytes:
    launcher = (Path(home) / "scheduler" / "launcher.py").resolve()
    if '"' in str(launcher):
        raise ConfigError("unsupported character in AIPROFILE_HOME path")
    root = ET.Element(f"{{{_NS}}}Task", {"version": "1.4"})
    triggers = _node(root, "Triggers")
    calendar = _node(triggers, "CalendarTrigger")
    _node(calendar, "StartBoundary", f"2000-01-01T{time}:00")
    _node(calendar, "Enabled", "true")
    schedule = _node(calendar, "ScheduleByDay")
    _node(schedule, "DaysInterval", "1")
    principals = _node(root, "Principals")
    principal = _node(principals, "Principal")
    principal.set("id", "Author")
    _node(principal, "UserId", getpass.getuser())
    _node(principal, "LogonType", "InteractiveToken")
    _node(principal, "RunLevel", "LeastPrivilege")
    settings = _node(root, "Settings")
    _node(settings, "DisallowStartIfOnBatteries", "true")
    _node(settings, "StopIfGoingOnBatteries", "true")
    _node(settings, "MultipleInstancesPolicy", "IgnoreNew")
    _node(settings, "StartWhenAvailable", "true")
    idle = _node(settings, "IdleSettings")
    _node(idle, "StopOnIdleEnd", "true")
    _node(idle, "RestartOnIdle", "false")
    _node(settings, "UseUnifiedSchedulingEngine", "true")
    actions = _node(root, "Actions")
    actions.set("Context", "Author")
    execute = _node(actions, "Exec")
    _node(execute, "Command", sys.executable)
    _node(execute, "Arguments", f'"{launcher}"')
    ET.register_namespace("", _NS)
    return ET.tostring(root, encoding="utf-16", xml_declaration=True)


def plan(home: Path, time: str) -> AdapterPlan:
    xml_path = (Path(home) / "scheduler" / "task.xml").resolve()
    name = task_name(home)
    return AdapterPlan(
        files=(PlannedFile(xml_path, _task_xml(home, time)),),
        commands=(
            PlannedCommand(
                (
                    "schtasks",
                    "/Create",
                    "/TN",
                    name,
                    "/XML",
                    str(xml_path),
                    "/F",
                )
            ),
        ),
    )


def install(
    home: Path, time: str, *, runner: Runner = subprocess.run
) -> None:
    apply_plan(plan(home, time), runner)


def status(
    home: Path, *, runner: Runner = subprocess.run
) -> ScheduleStatus:
    name = task_name(home)
    argv = ["schtasks", "/Query", "/TN", name, "/XML"]
    try:
        result = runner(
            argv,
            shell=False,
            check=False,
            capture_output=True,
            text=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigError("native scheduler command is unavailable") from exc
    if result.returncode != 0:
        local_definition = Path(home) / "scheduler" / "task.xml"
        try:
            local_definition.stat()
        except FileNotFoundError:
            return ScheduleStatus(installed=False)
        except OSError as exc:
            raise ConfigError("native scheduler status is unavailable") from exc
        raise ConfigError("native scheduler status is unavailable")
    raw = result.stdout
    if isinstance(raw, bytes):
        try:
            if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in raw[:8]:
                xml_text = raw.decode("utf-16")
            else:
                xml_text = raw.decode("utf-8-sig")
        except UnicodeError as exc:
            raise ConfigError("native scheduler status is unavailable") from exc
    else:
        xml_text = raw
    try:
        root = ET.fromstring(xml_text)
        if root.tag != f"{{{_NS}}}Task" or root.attrib != {"version": "1.4"}:
            raise ValueError
        settings = _only_descendant(root, "Settings")
        settings_enabled = _validate_owned_settings(settings)
        principals = _only_descendant(root, "Principals")
        if len(principals) != 1:
            raise ValueError
        principal = _only_child(principals, "Principal")
        _validate_owned_principal(principal)
        triggers_container = _only_descendant(root, "Triggers")
        if len(triggers_container) != 1:
            raise ValueError
        trigger = _only_child(triggers_container, "CalendarTrigger")
        trigger_names = [_local_name(child) for child in trigger]
        if len(trigger_names) != len(set(trigger_names)) or set(trigger_names) not in (
            {"StartBoundary", "ScheduleByDay"},
            {"StartBoundary", "Enabled", "ScheduleByDay"},
        ):
            raise ValueError
        trigger_enabled = (
            _only_child(trigger, "Enabled").text
            if "Enabled" in trigger_names
            else "true"
        )
        start = _only_child(trigger, "StartBoundary").text
        daily = _only_child(trigger, "ScheduleByDay")
        if len(daily) != 1 or _only_child(daily, "DaysInterval").text != "1":
            raise ValueError
        actions = _only_descendant(root, "Actions")
        if len(actions) != 1 or actions.get("Context") != "Author":
            raise ValueError
        execute = _only_child(actions, "Exec")
        if {_local_name(child) for child in execute} != {"Command", "Arguments"}:
            raise ValueError
        launcher = (Path(home) / "scheduler" / "launcher.py").resolve()
        if (
            _only_child(execute, "Command").text != sys.executable
            or _only_child(execute, "Arguments").text != f'"{launcher}"'
        ):
            raise ValueError
        if (
            settings_enabled not in {"true", "false"}
            or trigger_enabled not in {"true", "false"}
            or not isinstance(start, str)
        ):
            raise ValueError
        boundary = re.fullmatch(
            r"2000-01-01T((?:[01][0-9]|2[0-3]):[0-5][0-9]):00",
            start,
        )
        if boundary is None:
            raise ValueError
        time = boundary.group(1)
        hour, minute = (int(part) for part in time.split(":"))
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError
    except (ET.ParseError, StopIteration, TypeError, ValueError) as exc:
        raise ConfigError("native scheduler status is unavailable") from exc
    active = settings_enabled == "true" and trigger_enabled == "true"
    return ScheduleStatus(installed=True, time=time, active=active)


def remove(
    home: Path, *, runner: Runner = subprocess.run
) -> None:
    local_definition = Path(home) / "scheduler" / "task.xml"
    name = task_name(home)
    try:
        native_status = status(home, runner=runner)
    except ConfigError as exc:
        raise ConfigError("native scheduler removal failed") from exc
    if native_status.installed:
        result = run_command(
            runner,
            PlannedCommand(("schtasks", "/Delete", "/TN", name, "/F")),
        )
        if result.returncode != 0:
            raise ConfigError("native scheduler removal failed")
    try:
        local_definition.unlink(missing_ok=True)
    except OSError as exc:
        raise ConfigError("native scheduler cleanup failed") from exc

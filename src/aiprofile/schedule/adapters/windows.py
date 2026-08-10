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


def task_name(home: Path) -> str:
    return f"aiprofile-refresh-{home_identity(home)}"


def _node(parent: ET.Element, name: str, text: str | None = None) -> ET.Element:
    child = ET.SubElement(parent, f"{{{_NS}}}{name}")
    child.text = text
    return child


def _local_name(node: ET.Element) -> str:
    return node.tag.rsplit("}", 1)[-1]


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
    _node(settings, "MultipleInstancesPolicy", "IgnoreNew")
    _node(settings, "StartWhenAvailable", "true")
    _node(settings, "Enabled", "true")
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
        settings = _only_descendant(root, "Settings")
        if {_local_name(child) for child in settings} != {
            "MultipleInstancesPolicy",
            "StartWhenAvailable",
            "Enabled",
        }:
            raise ValueError
        settings_enabled = _only_child(settings, "Enabled").text
        if (
            _only_child(settings, "MultipleInstancesPolicy").text != "IgnoreNew"
            or _only_child(settings, "StartWhenAvailable").text != "true"
        ):
            raise ValueError
        principals = _only_descendant(root, "Principals")
        if len(principals) != 1:
            raise ValueError
        principal = _only_child(principals, "Principal")
        if (
            principal.get("id") != "Author"
            or {_local_name(child) for child in principal}
            != {"UserId", "LogonType", "RunLevel"}
            or _only_child(principal, "UserId").text != getpass.getuser()
            or _only_child(principal, "LogonType").text != "InteractiveToken"
            or _only_child(principal, "RunLevel").text != "LeastPrivilege"
        ):
            raise ValueError
        triggers_container = _only_descendant(root, "Triggers")
        if len(triggers_container) != 1:
            raise ValueError
        trigger = _only_child(triggers_container, "CalendarTrigger")
        if {_local_name(child) for child in trigger} != {
            "StartBoundary",
            "Enabled",
            "ScheduleByDay",
        }:
            raise ValueError
        trigger_enabled = _only_child(trigger, "Enabled").text
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
    query = run_command(
        runner,
        PlannedCommand(("schtasks", "/Query", "/TN", name, "/FO", "LIST")),
    )
    if query.returncode != 0 and local_definition.exists():
        raise ConfigError("native scheduler removal failed")
    if query.returncode == 0:
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

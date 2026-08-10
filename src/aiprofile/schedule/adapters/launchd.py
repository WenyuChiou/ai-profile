"""macOS launchd adapter.

``StartCalendarInterval`` coalesces runs missed during sleep into one run at
wake, but launchd does not catch up runs missed while the machine was powered
off.  The application-level launcher lock remains mandatory.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
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


def _user_home() -> Path:
    return Path.home()


def _uid() -> int:
    if sys.platform != "darwin" or not hasattr(os, "getuid"):
        raise ConfigError("launchd scheduling is unavailable on this platform")
    return os.getuid()


def label(home: Path) -> str:
    return f"com.aiprofile.refresh.{home_identity(home)}"


def _plist_path(home: Path) -> Path:
    return _user_home() / "Library" / "LaunchAgents" / f"{label(home)}.plist"


def plan(home: Path, time: str) -> AdapterPlan:
    hour, minute = (int(part) for part in time.split(":"))
    launcher = (Path(home) / "scheduler" / "launcher.py").resolve()
    home_label = label(home)
    payload = {
        "Label": home_label,
        "ProgramArguments": [sys.executable, str(launcher)],
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "RunAtLoad": False,
    }
    plist_path = _plist_path(home)
    domain = f"gui/{_uid()}"
    return AdapterPlan(
        files=(PlannedFile(plist_path, plistlib.dumps(payload, sort_keys=True)),),
        commands=(
            PlannedCommand(
                ("launchctl", "bootout", f"{domain}/{home_label}"),
                ignore_failure=True,
            ),
            PlannedCommand(("launchctl", "bootstrap", domain, str(plist_path))),
        ),
    )


def install(
    home: Path, time: str, *, runner: Runner = subprocess.run
) -> None:
    apply_plan(plan(home, time), runner)


def status(
    home: Path, *, runner: Runner = subprocess.run
) -> ScheduleStatus:
    home_label = label(home)
    definition = _plist_path(home)
    result = run_command(
        runner,
        PlannedCommand(("launchctl", "print", f"gui/{_uid()}/{home_label}")),
    )
    if not definition.exists() and result.returncode != 0:
        return ScheduleStatus(installed=False, active=False)
    try:
        payload = plistlib.loads(definition.read_bytes())
        interval = payload["StartCalendarInterval"]
        hour = interval["Hour"]
        minute = interval["Minute"]
        if (
            payload.get("Label") != home_label
            or payload.get("ProgramArguments")
            != [
                sys.executable,
                str((Path(home) / "scheduler" / "launcher.py").resolve()),
            ]
            or payload.get("RunAtLoad") is not False
            or not isinstance(hour, int)
            or isinstance(hour, bool)
            or not isinstance(minute, int)
            or isinstance(minute, bool)
            or not 0 <= hour <= 23
            or not 0 <= minute <= 59
        ):
            raise ValueError
    except (
        AttributeError,
        OSError,
        plistlib.InvalidFileException,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ConfigError("native scheduler status is unavailable") from exc
    return ScheduleStatus(
        installed=True,
        time=f"{hour:02d}:{minute:02d}",
        active=result.returncode == 0,
    )


def remove(
    home: Path, *, runner: Runner = subprocess.run
) -> None:
    local_definition = _plist_path(home)
    domain_target = f"gui/{_uid()}/{label(home)}"
    query = run_command(
        runner,
        PlannedCommand(("launchctl", "print", domain_target)),
    )
    if query.returncode != 0 and local_definition.exists():
        raise ConfigError("native scheduler removal failed")
    if query.returncode == 0:
        result = run_command(
            runner,
            PlannedCommand(("launchctl", "bootout", domain_target)),
        )
        if result.returncode != 0:
            raise ConfigError("native scheduler removal failed")
    try:
        local_definition.unlink(missing_ok=True)
    except OSError as exc:
        raise ConfigError("native scheduler cleanup failed") from exc

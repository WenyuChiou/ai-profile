"""Linux systemd user-timer adapter with persistent missed-run handling."""

from __future__ import annotations

import re
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


def quote_word(value: str) -> str:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ConfigError("unsupported character in scheduler path")
    escaped = (
        value.replace("%", "%%")
        .replace("$", "$$")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
    )
    return f'"{escaped}"'


def _unit_dir() -> Path:
    return _user_home() / ".config" / "systemd" / "user"


def unit_names(home: Path) -> tuple[str, str]:
    suffix = home_identity(home)
    return (
        f"aiprofile-refresh-{suffix}.service",
        f"aiprofile-refresh-{suffix}.timer",
    )


def plan(home: Path, time: str) -> AdapterPlan:
    launcher = (Path(home) / "scheduler" / "launcher.py").resolve()
    service = (
        "[Unit]\nDescription=Refresh ai-profile outputs\n\n"
        "[Service]\nType=oneshot\n"
        f"ExecStart={quote_word(sys.executable)} {quote_word(str(launcher))}\n"
    ).encode()
    timer = (
        "[Unit]\nDescription=Daily ai-profile refresh\n\n"
        f"[Timer]\nOnCalendar=*-*-* {time}:00\nPersistent=true\n\n"
        f"[Install]\nWantedBy=timers.target\n"
    ).encode()
    directory = _unit_dir()
    service_name, timer_name = unit_names(home)
    return AdapterPlan(
        files=(
            PlannedFile(directory / service_name, service),
            PlannedFile(directory / timer_name, timer),
        ),
        commands=(
            PlannedCommand(("systemctl", "--user", "daemon-reload")),
            PlannedCommand(
                ("systemctl", "--user", "enable", "--now", timer_name)
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
    service_name, timer_name = unit_names(home)
    service_path = _unit_dir() / service_name
    timer_path = _unit_dir() / timer_name
    enabled = run_command(
        runner,
        PlannedCommand(("systemctl", "--user", "is-enabled", timer_name)),
    )
    if enabled.returncode != 0 and not service_path.exists() and not timer_path.exists():
        return ScheduleStatus(installed=False, active=False)
    try:
        if not service_path.is_file():
            raise ValueError
        service_content = service_path.read_bytes()
        timer_content = timer_path.read_bytes()
        timer_text = timer_path.read_text(encoding="utf-8")
        match = re.search(
            r"(?m)^OnCalendar=\*-\*-\* (\d{2}:\d{2}):00$",
            timer_text,
        )
        if match is None:
            raise ValueError
        time = match.group(1)
        hour, minute = (int(part) for part in time.split(":"))
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError
        expected_files = {
            planned.path.name: planned.content for planned in plan(home, time).files
        }
        if (
            service_content != expected_files[service_name]
            or timer_content != expected_files[timer_name]
        ):
            raise ValueError
    except (OSError, UnicodeError, ValueError) as exc:
        raise ConfigError("native scheduler status is unavailable") from exc
    if enabled.returncode != 0:
        return ScheduleStatus(installed=True, time=time, active=False)
    active = run_command(
        runner,
        PlannedCommand(("systemctl", "--user", "is-active", timer_name)),
    )
    return ScheduleStatus(
        installed=True,
        time=time,
        active=active.returncode == 0,
    )


def remove(
    home: Path, *, runner: Runner = subprocess.run
) -> None:
    service_name, timer_name = unit_names(home)
    local_definitions = tuple(
        _unit_dir() / name for name in (service_name, timer_name)
    )
    loaded = run_command(
        runner,
        PlannedCommand(
            (
                "systemctl",
                "--user",
                "show",
                "--property=LoadState",
                "--value",
                timer_name,
            )
        ),
    )
    if loaded.returncode != 0 and any(path.exists() for path in local_definitions):
        raise ConfigError("native scheduler removal failed")
    if loaded.returncode == 0 and loaded.stdout.strip() != "not-found":
        disabled = run_command(
            runner,
            PlannedCommand(
                ("systemctl", "--user", "disable", "--now", timer_name)
            ),
        )
        if disabled.returncode != 0:
            raise ConfigError("native scheduler removal failed")
    try:
        for path in local_definitions:
            path.unlink(missing_ok=True)
    except OSError as exc:
        raise ConfigError("native scheduler cleanup failed") from exc
    reloaded = run_command(
        runner,
        PlannedCommand(("systemctl", "--user", "daemon-reload")),
    )
    if reloaded.returncode != 0:
        raise ConfigError("native scheduler removal failed")

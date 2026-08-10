"""Narrow platform-adapter protocol for native user schedulers."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ...errors import ConfigError

Runner = Callable[..., subprocess.CompletedProcess[str]]
_ENFORCE_POSIX_PERMISSIONS = sys.platform != "win32"


def home_identity(home: Path) -> str:
    """Return a stable opaque suffix for one canonical scheduler home."""
    try:
        canonical = os.path.normcase(str(Path(home).resolve()))
    except OSError as exc:
        raise ConfigError("scheduler home identity is unavailable") from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class PlannedFile:
    path: Path
    content: bytes


@dataclass(frozen=True)
class PlannedCommand:
    argv: tuple[str, ...]
    ignore_failure: bool = False


@dataclass(frozen=True)
class AdapterPlan:
    files: tuple[PlannedFile, ...]
    commands: tuple[PlannedCommand, ...]


@dataclass(frozen=True)
class ScheduleStatus:
    installed: bool
    time: str | None = None
    active: bool | None = None


def run_command(runner: Runner, command: PlannedCommand) -> subprocess.CompletedProcess[str]:
    try:
        return runner(
            list(command.argv),
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigError("native scheduler command is unavailable") from exc


def _write_private_payload(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(tmp, flags, 0o600)
        try:
            os.chmod(tmp, 0o600)
        except OSError as exc:
            if _ENFORCE_POSIX_PERMISSIONS:
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise ConfigError("native scheduler registration failed") from exc
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def apply_plan(plan: AdapterPlan, runner: Runner) -> None:
    written: list[Path] = []
    try:
        for planned in plan.files:
            _write_private_payload(planned.path, planned.content)
            written.append(planned.path)
        for command in plan.commands:
            result = run_command(runner, command)
            if result.returncode != 0 and not command.ignore_failure:
                raise ConfigError("native scheduler registration failed")
    except OSError as exc:
        for path in reversed(written):
            path.unlink(missing_ok=True)
        raise ConfigError("native scheduler registration failed") from exc
    except ConfigError as exc:
        for path in reversed(written):
            path.unlink(missing_ok=True)
        raise ConfigError("native scheduler registration failed") from exc


__all__ = [
    "AdapterPlan",
    "PlannedCommand",
    "PlannedFile",
    "Runner",
    "ScheduleStatus",
]

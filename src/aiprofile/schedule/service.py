"""Scheduler configuration and installation orchestration.

The configuration is private local state under ``AIPROFILE_HOME``.  Paths
stored there are never copied to default console output or the last-run log.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from ..config import load_config, load_config_read_only
from ..errors import AiProfileError, ConfigError, path_free_diagnostics
from ..lockfile import acquire_home_lock
from .adapters import AdapterPlan, ScheduleStatus

SCHEDULER_VERSION = "0.7.0"
SCHEDULER_DIRNAME = "scheduler"
CONFIG_NAME = "config.json"
LAUNCHER_NAME = "launcher.py"
SCHEDULER_LOCK_NAME = ".schedule.lock"
PENDING_PUSH_NAME = "pending-push.json"
LAST_RUN_NAME = "last-run.log"
_CONFIG_KEYS = frozenset(
    {"profile_repo", "time", "push", "branch", "remote", "installed_version"}
)
_LAST_RUN_LINE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00 "
    r"(?:scheduled refresh skipped; another run is active|"
    r"scheduled refresh skipped; another publication is active|"
    r"recorded branch is no longer checked out; run refused|"
    r"refresh failed for configured repositories; no outputs published|"
    r"git status failed \(exit \d+\); no commit was made|"
    r"refresh completed; no change|"
    r"git staging failed \(exit \d+\); no commit was made|"
    r"git commit failed \(exit \d+\)|"
    r"git index setup failed \(exit \d+\)|"
    r"git tree creation failed \(exit \d+\)|"
    r"git tree comparison failed \(exit \d+\)|"
    r"git commit creation failed \(exit \d+\)|"
    r"refresh committed locally; push disabled|"
    r"push failed \(exit \d+\); local commit retained|"
    r"push failed \(exit \d+\); pending commit retained|"
    r"push outcome could not be verified; pending commit retained|"
    r"push reported success but remote publication is not confirmed; "
    r"pending commit retained|"
    r"refresh committed and pushed|"
    r"repository state changed during scheduled refresh; publication refused|"
    r"repository state changed after staging; publication refused|"
    r"repository state changed after staging; tool paths may remain staged|"
    r"repository state changed before branch update; publication refused|"
    r"repository state changed after branch update; publication rolled back|"
    r"repository state changed after branch update; local scheduler commit or "
    r"ref may remain(?: and pending retry state remains)?; push was refused|"
    r"repository state changed after index synchronization; publication rolled "
    r"back but tool paths may remain staged and push was refused|"
    r"repository state changed after index synchronization; tool paths may remain "
    r"staged and local scheduler commit or ref may remain(?: and pending retry "
    r"state remains)?; push was refused|"
    r"repository state changed after commit; local commit retained and push refused|"
    r"local commit retained; tool paths may remain staged and push was refused|"
    r"temporary publication state could not be prepared safely|"
    r"temporary publication state may remain; no branch update or push was attempted|"
    r"rendered generation manifest is unavailable; publication refused|"
    r"generated asset verification failed; publication refused|"
    r"generated asset bytes changed after refresh; publication refused|"
    r"profile repository locking is unavailable; publication refused|"
    r"remote branch does not match local HEAD; synchronize manually|"
    r"remote publication destination is unsupported; no publication attempted|"
    r"pending publication state is invalid; synchronize manually|"
    r"pending publication state diverged; synchronize manually|"
    r"pending publication destination diverged; synchronize manually|"
    r"pending publication state diverged during index repair; tool paths were "
    r"restored and push was refused|"
    r"pending publication state diverged during index repair; tool paths may "
    r"remain staged and push was refused|"
    r"pending publication index could not be synchronized; tool paths may remain "
    r"staged and push was refused|"
    r"pending publication branch could not be advanced; pending retry state "
    r"remains and push was refused|"
    r"publication reached remote but pending retry state remains|"
    r"pending publication state unavailable; no branch update or push was attempted|"
    r"pending publication state remains; no branch update or push was attempted|"
    r"publication rolled back but pending retry state remains|"
    r"publication rolled back but tool paths may remain staged and pending retry state remains|"
    r"local commit and pending retry state retained; "
    r"tool paths may remain staged and push was refused|"
    r"refresh failed safely; no publication attempted|"
    r"scheduled refresh failed safely|"
    r"scheduled refresh failed because locking is unavailable)"
    r"(?:; scheduler finalization failed)?$"
)
_LAUNCHER_STUB = """from pathlib import Path
from aiprofile.schedule.launcher import run_launcher

if __name__ == "__main__":
    raise SystemExit(run_launcher(Path(__file__).resolve().parent.parent))
"""


class _RepositoryDriftError(ConfigError):
    """Internal typed signal for path-free install-state drift handling."""


@dataclass(frozen=True)
class SchedulerConfig:
    profile_repo: Path
    time: str
    push: bool
    branch: str
    remote: str
    installed_version: str


@dataclass(frozen=True)
class InstallResult:
    time: str
    push: bool
    dry_run: bool = False
    files: int = 0
    commands: int = 0


@dataclass(frozen=True)
class StatusResult:
    installed: bool
    time: str | None = None
    push: bool | None = None
    branch: str | None = None
    remote: str | None = None
    active: bool | None = None
    last_run: str | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class RemoveResult:
    removed: bool
    dry_run: bool = False


def scheduler_dir(home: Path) -> Path:
    return Path(home) / SCHEDULER_DIRNAME


_GIT_CREDENTIAL_ENV = frozenset(
    {
        "GIT_ASKPASS",
        "GIT_HTTP_USER_AGENT",
        "GIT_SSH",
        "GIT_SSH_COMMAND",
        "GIT_TERMINAL_PROMPT",
    }
)


def sanitized_git_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Copy the process environment without Git repository-selection state.

    Authentication transports remain available, but repository, object,
    namespace, replacement-ref, index, tracing, and injected-config variables
    never cross the scheduler's Git boundary.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
        or key.upper() in _GIT_CREDENTIAL_ENV
    }
    if extra:
        env.update(extra)
    return env


def is_safe_last_run_message(message: str) -> bool:
    """Whether ``message`` belongs to the closed path-free log vocabulary."""
    return bool(
        _LAST_RUN_LINE.fullmatch(f"2000-01-01T00:00:00+00:00 {message}")
    )


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _restrict_to_owner(path.parent, 0o700)
    tmp = path.with_name(path.name + ".tmp")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "wb") as handle:
            _restrict_to_owner(tmp, 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        _restrict_to_owner(path, 0o600)
    finally:
        tmp.unlink(missing_ok=True)


def _restrict_to_owner(path: Path, mode: int) -> None:
    """Enforce owner-only POSIX state without exposing ``path`` on failure."""
    try:
        os.chmod(path, mode)
    except OSError as exc:
        if sys.platform != "win32":
            raise ConfigError(
                "scheduler privacy permissions could not be enforced"
            ) from exc


def _prepare_home(home: Path) -> None:
    try:
        home.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        raise ConfigError("scheduler storage is unavailable") from exc
    _restrict_to_owner(home, 0o700)


def _ensure_lock_parent(home: Path) -> None:
    """Create a missing lock parent without mutating an existing locked home."""
    try:
        home.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        raise ConfigError("scheduler storage is unavailable") from exc


def _is_link_or_reparse(info: os.stat_result) -> bool:
    """Recognize POSIX links and Windows reparse-backed links/junctions."""
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISLNK(info.st_mode) or bool(reparse_flag and attributes & reparse_flag)


def _validated_scheduler_state(home: Path) -> tuple[Path, bool]:
    """Validate local scheduler nodes without following or mutating links."""
    directory = scheduler_dir(home)
    try:
        directory_info = directory.lstat()
    except FileNotFoundError:
        return directory, False
    except OSError as exc:
        raise ConfigError("scheduler configuration is unavailable or invalid") from exc
    if not stat.S_ISDIR(directory_info.st_mode) or _is_link_or_reparse(
        directory_info
    ):
        raise ConfigError("scheduler configuration is unavailable or invalid")
    try:
        for path in directory.iterdir():
            info = path.lstat()
            if _is_link_or_reparse(info):
                raise ConfigError("scheduler configuration is unavailable or invalid")
            if stat.S_ISDIR(info.st_mode) and path.name.startswith(
                ".publication-index-"
            ):
                # A hard process termination can strand the already-private
                # 0700 temporary directory.  It is never traversed here.
                continue
            if not stat.S_ISREG(info.st_mode):
                raise ConfigError("scheduler configuration is unavailable or invalid")
    except ConfigError:
        raise
    except OSError as exc:
        raise ConfigError("scheduler configuration is unavailable or invalid") from exc
    return directory, True


def _secure_scheduler_state(home: Path, *, create: bool) -> Path:
    _prepare_home(home)
    directory, exists = _validated_scheduler_state(home)
    if create:
        if not exists:
            try:
                directory.mkdir(parents=True, exist_ok=False, mode=0o700)
            except OSError as exc:
                raise ConfigError("scheduler storage is unavailable") from exc
            directory, exists = _validated_scheduler_state(home)
    if exists:
        _restrict_to_owner(directory, 0o700)
        for name in (LAUNCHER_NAME, CONFIG_NAME, PENDING_PUSH_NAME, LAST_RUN_NAME):
            path = directory / name
            try:
                path.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise ConfigError(
                    "scheduler configuration is unavailable or invalid"
                ) from exc
            else:
                _restrict_to_owner(path, 0o600)
    return directory


def scheduler_payloads(
    profile_repo: Path,
    time: str,
    push: bool,
    *,
    branch: str,
    remote: str,
) -> dict[str, bytes]:
    payload = {
        "profile_repo": str(Path(profile_repo).resolve()),
        "time": time,
        "push": bool(push),
        "branch": branch,
        "remote": remote,
        "installed_version": SCHEDULER_VERSION,
    }
    return {
        LAUNCHER_NAME: _LAUNCHER_STUB.encode("utf-8"),
        CONFIG_NAME: (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    }


def write_scheduler_files(
    home: Path,
    profile_repo: Path,
    time: str,
    push: bool,
    *,
    branch: str,
    remote: str,
) -> tuple[Path, Path]:
    directory = _secure_scheduler_state(Path(home), create=True)
    payloads = scheduler_payloads(
        profile_repo, time, push, branch=branch, remote=remote
    )
    for name, content in payloads.items():
        _atomic_write(directory / name, content)
    return directory / LAUNCHER_NAME, directory / CONFIG_NAME


def read_scheduler_config(home: Path, *, read_only: bool = False) -> SchedulerConfig:
    _directory, directory_exists = _validated_scheduler_state(Path(home))
    path = scheduler_dir(home) / CONFIG_NAME
    if not directory_exists:
        raise ConfigError("scheduler configuration is unavailable or invalid")
    if not read_only:
        _secure_scheduler_state(Path(home), create=False)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError("scheduler configuration is unavailable or invalid") from exc
    if not isinstance(raw, dict) or set(raw) != _CONFIG_KEYS:
        raise ConfigError("scheduler configuration is unavailable or invalid")
    values = (
        raw["profile_repo"],
        raw["time"],
        raw["push"],
        raw["branch"],
        raw["remote"],
        raw["installed_version"],
    )
    if not (
        isinstance(values[0], str)
        and isinstance(values[1], str)
        and isinstance(values[2], bool)
        and all(isinstance(value, str) for value in values[3:])
    ):
        raise ConfigError("scheduler configuration is unavailable or invalid")
    profile_repo, time, push, branch, remote, installed_version = values
    if not profile_repo or "\x00" in profile_repo:
        raise ConfigError("scheduler configuration is unavailable or invalid")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time):
        raise ConfigError("scheduler configuration is unavailable or invalid")
    if not branch or any(char in branch for char in "\r\n\x00"):
        raise ConfigError("scheduler configuration is unavailable or invalid")
    if remote and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", remote):
        raise ConfigError("scheduler configuration is unavailable or invalid")
    if push and not remote:
        raise ConfigError("scheduler configuration is unavailable or invalid")
    if installed_version != SCHEDULER_VERSION:
        raise ConfigError("scheduler configuration is unavailable or invalid")
    return SchedulerConfig(
        profile_repo=Path(profile_repo),
        time=time,
        push=push,
        branch=branch,
        remote=remote,
        installed_version=installed_version,
    )


def _adapter_for(platform: str | None = None) -> ModuleType:
    platform = platform or sys.platform
    if platform == "win32":
        from .adapters import windows

        return windows
    if platform == "darwin":
        from .adapters import launchd

        return launchd
    if platform.startswith("linux"):
        from .adapters import systemd

        return systemd
    raise ConfigError("unsupported platform for aiprofile schedule")


def _run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo),
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            env=sanitized_git_env(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigError("profile repository git metadata is unavailable") from exc


def _validate_repository(profile_repo: Path, push: bool) -> tuple[Path, str, str]:
    repo = Path(profile_repo)
    try:
        repo = repo.resolve(strict=True)
    except OSError as exc:
        raise ConfigError("profile repository is unavailable or invalid") from exc
    inside = _run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise ConfigError("profile repository is unavailable or invalid")
    shallow = _run_git(repo, ["rev-parse", "--is-shallow-repository"])
    partial = _run_git(repo, ["config", "--get", "extensions.partialClone"])
    if (
        shallow.returncode != 0
        or shallow.stdout.strip() != "false"
        or partial.returncode != 1
    ):
        raise ConfigError(
            "profile repository must have complete local history; "
            "shallow and partial clones are unsupported"
        )
    branch_result = _run_git(
        repo, ["symbolic-ref", "--quiet", "--short", "HEAD"]
    )
    branch = branch_result.stdout.strip()
    if branch_result.returncode != 0 or not branch:
        raise ConfigError(
            "profile repository is on a detached HEAD; check out a branch first"
        )
    if any(char in branch for char in "\r\n\x00"):
        raise ConfigError("profile repository branch name is unsupported")

    configured = _run_git(
        repo, ["config", "--get", f"branch.{branch}.remote"]
    )
    configured_name = configured.stdout.strip() if configured.returncode == 0 else ""
    remotes = _run_git(repo, ["remote"])
    names = [line.strip() for line in remotes.stdout.splitlines() if line.strip()]
    remote = configured_name if configured_name in names else ""
    if not remote and len(names) == 1:
        remote = names[0]
    if remote and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", remote):
        raise ConfigError("profile repository remote name is unsupported")
    if push and not remote:
        raise ConfigError(
            "profile repository has no unambiguous configured remote;"
            " configure one or install with --no-push"
        )
    return repo, branch, remote


def _assert_repository_state(
    profile_repo: Path,
    push: bool,
    *,
    expected: tuple[Path, str, str],
) -> tuple[Path, str, str]:
    try:
        current = _validate_repository(profile_repo, push)
    except ConfigError as exc:
        raise _RepositoryDriftError(
            "profile repository state changed during scheduler installation; retry"
        ) from exc
    if current != expected:
        raise _RepositoryDriftError(
            "profile repository state changed during scheduler installation; retry"
        )
    return current


def _validate_initialized_home(home: Path, *, read_only: bool) -> None:
    loader = load_config_read_only if read_only else load_config
    try:
        with path_free_diagnostics():
            loader(Path(home))
    except (AiProfileError, OSError) as exc:
        raise ConfigError(
            "ai-profile home is not initialized or valid;"
            " run 'aiprofile init' first"
        ) from exc


def _inspect_existing_native_state(
    home: Path,
    adapter: ModuleType,
) -> tuple[SchedulerConfig | None, ScheduleStatus]:
    """Read and validate the local/native scheduler pair without mutation."""
    config_path = scheduler_dir(home) / CONFIG_NAME
    previous = (
        read_scheduler_config(home, read_only=True) if config_path.exists() else None
    )
    try:
        native: ScheduleStatus = adapter.status(home)
    except (AiProfileError, OSError, subprocess.SubprocessError) as exc:
        raise ConfigError(
            "existing native scheduler state is unavailable; install refused"
        ) from exc
    if previous is None and native.installed:
        raise ConfigError(
            "native scheduler state does not match local scheduler state;"
            " remove it before installing"
        )
    if previous is not None and native.installed:
        if native.active is not True:
            raise ConfigError(
                "existing native scheduler is inactive or unverifiable;"
                " remove it before reinstalling"
            )
        if native.time != previous.time:
            raise ConfigError(
                "native scheduler state does not match local scheduler state;"
                " remove it before reinstalling"
            )
    return previous, native


def _snapshot_directory(directory: Path) -> dict[Path, bytes] | None:
    if not directory.exists():
        return None
    try:
        return {
            path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*")
            if path.is_file()
        }
    except OSError as exc:
        raise ConfigError("existing scheduler state is unreadable") from exc


def _restore_directory(directory: Path, snapshot: dict[Path, bytes] | None) -> None:
    try:
        if directory.exists():
            shutil.rmtree(directory)
        if snapshot is not None:
            for relative, content in snapshot.items():
                target = directory / relative
                _atomic_write(target, content)
            _restrict_to_owner(directory, 0o700)
            for name in (LAUNCHER_NAME, CONFIG_NAME):
                path = directory / name
                if path.exists():
                    _restrict_to_owner(path, 0o600)
    except (AiProfileError, OSError) as exc:
        raise ConfigError(
            "scheduler installation failed and local rollback was incomplete"
        ) from exc


def install(
    home: Path,
    profile_repo: Path,
    time: str,
    *,
    push: bool = True,
    dry_run: bool = False,
) -> InstallResult:
    adapter = _adapter_for()
    home = Path(home)
    _validate_initialized_home(home, read_only=True)
    expected_repository = _validate_repository(profile_repo, push)
    _inspect_existing_native_state(home, adapter)
    if dry_run:
        repo, branch, remote = expected_repository
        native: AdapterPlan = adapter.plan(Path(home), time)
        return InstallResult(
            time=time,
            push=push,
            dry_run=True,
            files=len(scheduler_payloads(repo, time, push, branch=branch, remote=remote))
            + len(native.files),
            commands=len(native.commands),
        )

    _ensure_lock_parent(home)
    with acquire_home_lock(home, SCHEDULER_LOCK_NAME):
        _validate_initialized_home(home, read_only=True)
        repo, branch, remote = _assert_repository_state(
            profile_repo,
            push,
            expected=expected_repository,
        )
        directory = scheduler_dir(home)
        directory_existed = directory.exists()
        snapshot = _snapshot_directory(directory) if directory_existed else None
        previous, previous_native = _inspect_existing_native_state(home, adapter)
        _validate_initialized_home(home, read_only=False)
        _prepare_home(home)
        _secure_scheduler_state(home, create=True)
        native_install_attempted = False
        try:
            write_scheduler_files(
                home, repo, time, push, branch=branch, remote=remote
            )
            _assert_repository_state(
                repo,
                push,
                expected=(repo, branch, remote),
            )
            native_install_attempted = True
            adapter.install(home, time)
            _assert_repository_state(
                repo,
                push,
                expected=(repo, branch, remote),
            )
        except (AiProfileError, OSError, subprocess.SubprocessError) as exc:
            native_cleanup_failed = False
            if native_install_attempted:
                try:
                    adapter.remove(home)
                except (AiProfileError, OSError, subprocess.SubprocessError):
                    native_cleanup_failed = True
            local_restore_failed = False
            try:
                _restore_directory(directory, snapshot)
            except (AiProfileError, OSError):
                local_restore_failed = True
            native_recovery_failed = False
            if (
                native_install_attempted
                and previous is not None
                and previous_native.installed
                and not native_cleanup_failed
                and not local_restore_failed
            ):
                try:
                    adapter.install(home, previous.time)
                except (AiProfileError, OSError, subprocess.SubprocessError):
                    native_recovery_failed = True
            if native_cleanup_failed and local_restore_failed:
                raise ConfigError(
                    "scheduler installation failed; local rollback is incomplete and"
                    " native scheduler state may remain inconsistent"
                ) from exc
            if local_restore_failed:
                if previous_native.installed:
                    raise ConfigError(
                        "scheduler installation failed; local rollback is incomplete"
                        " and previous native scheduler state may not be restored"
                    ) from exc
                raise ConfigError(
                    "scheduler installation failed; local rollback is incomplete;"
                    " native scheduler cleanup completed"
                ) from exc
            if native_cleanup_failed:
                raise ConfigError(
                    "scheduler installation failed; previous local files were restored,"
                    " but native scheduler rollback may be incomplete"
                ) from exc
            if native_recovery_failed:
                raise ConfigError(
                    "scheduler installation failed; previous local files were restored,"
                    " but previous native scheduler state could not be restored"
                ) from exc
            if isinstance(exc, _RepositoryDriftError):
                raise ConfigError(
                    "profile repository state changed during scheduler installation;"
                    " previous state restored; retry"
                ) from exc
            raise ConfigError(
                "scheduler installation failed; previous state restored"
            ) from exc
    return InstallResult(time=time, push=push)


def status(home: Path, *, dry_run: bool = False) -> StatusResult:
    adapter = _adapter_for()
    directory, directory_exists = _validated_scheduler_state(Path(home))
    config_path = directory / CONFIG_NAME
    try:
        config_info = config_path.lstat() if directory_exists else None
    except FileNotFoundError:
        config_info = None
    except OSError as exc:
        raise ConfigError("scheduler configuration is unavailable or invalid") from exc
    if config_info is None or not stat.S_ISREG(config_info.st_mode):
        return StatusResult(installed=False, dry_run=dry_run)
    cfg = read_scheduler_config(home, read_only=dry_run)
    if dry_run:
        return StatusResult(
            installed=True,
            time=cfg.time,
            push=cfg.push,
            branch=cfg.branch,
            remote=cfg.remote,
            dry_run=True,
        )
    native: ScheduleStatus = adapter.status(Path(home))
    last_run = None
    log_path = directory / "last-run.log"
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
            last_run = lines[-1] if lines else None
            if last_run is not None and not _LAST_RUN_LINE.fullmatch(last_run):
                last_run = "last-run log is unavailable or invalid"
        except UnicodeError:
            last_run = "last-run log is unavailable or invalid"
        except OSError as exc:
            raise ConfigError("scheduler status is unavailable") from exc
    return StatusResult(
        installed=native.installed,
        time=cfg.time,
        push=cfg.push,
        branch=cfg.branch,
        remote=cfg.remote,
        active=native.active,
        last_run=last_run,
    )


def remove(home: Path, *, dry_run: bool = False) -> RemoveResult:
    adapter = _adapter_for()
    directory = scheduler_dir(home)
    if dry_run:
        _directory, exists = _validated_scheduler_state(Path(home))
        return RemoveResult(removed=exists, dry_run=True)
    home = Path(home)
    _ensure_lock_parent(home)
    with acquire_home_lock(home, SCHEDULER_LOCK_NAME):
        _prepare_home(home)
        _directory, exists = _validated_scheduler_state(home)
        try:
            adapter.remove(home)
        except (OSError, ConfigError, subprocess.SubprocessError) as exc:
            message = "scheduler removal failed; native registration may remain"
            if exists:
                message += "; local artifacts were retained"
            raise ConfigError(message) from exc
        if not exists:
            return RemoveResult(removed=False)
        try:
            shutil.rmtree(directory)
        except OSError as exc:
            raise ConfigError(
                "native schedule was removed, but tool-owned local artifacts remain"
            ) from exc
    return RemoveResult(removed=True)

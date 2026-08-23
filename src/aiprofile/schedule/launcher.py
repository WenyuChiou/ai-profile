"""Importable implementation used by the generated scheduler launcher.

All subprocesses receive argv lists with ``shell=False``.  Git publication
is limited to the exact eight public asset paths; existing unrelated staged
content remains staged and cannot enter the mechanical output commit.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Callable
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .. import refresh
from ..errors import AiProfileError, ConfigError, LockError
from ..export import PUBLIC_ASSET_NAMES
from ..lockfile import acquire_home_lock, acquire_publication_lock
from ..refresh import AssetDigest
from .service import (
    LAST_RUN_NAME,
    PENDING_PUSH_NAME,
    SCHEDULER_LOCK_NAME,
    SchedulerConfig,
    _is_link_or_reparse,
    is_safe_last_run_message,
    read_scheduler_config,
    sanitized_git_env,
    scheduler_dir,
)

Runner = Callable[..., subprocess.CompletedProcess]
_PATHS = tuple(f"dist/{name}" for name in sorted(PUBLIC_ASSET_NAMES))
_OID = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_TRANSPORT_ALIAS = "aiprofile-publication"
_REMOTE_SYNC_ATTEMPTS = 3
_TRANSPORT_CONFIG_KEYS = (
    "core.sshcommand",
    "credential.helper",
    "credential.usehttppath",
    "http.sslbackend",
    "http.sslcainfo",
    "http.sslverify",
    "http.version",
    "ssh.variant",
)
_PROXY_ENV_KEYS = frozenset({"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"})


@dataclass(frozen=True)
class _RemoteSyncResult:
    state: tuple[str, str] | None
    failure: str | None = None


def _append_log(home: Path, message: str) -> None:
    directory = scheduler_dir(home)
    try:
        if not is_safe_last_run_message(message):
            message = "scheduled refresh failed safely"
        try:
            directory_info = directory.lstat()
        except FileNotFoundError:
            directory.mkdir(parents=True, exist_ok=False, mode=0o700)
            directory_info = directory.lstat()
        if _is_link_or_reparse(directory_info) or not stat.S_ISDIR(
            directory_info.st_mode
        ):
            return
        os.chmod(directory, 0o700)
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        path = directory / LAST_RUN_NAME
        try:
            path_info = path.lstat()
        except FileNotFoundError:
            pass
        else:
            if _is_link_or_reparse(path_info) or not stat.S_ISREG(path_info.st_mode):
                return
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        try:
            os.chmod(path, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8", newline="\n") as log:
                fd = -1
                log.write(f"{stamp} {message}\n")
        finally:
            if fd >= 0:
                os.close(fd)
    except OSError:
        # The launcher has no privacy-safe secondary logging channel.  In
        # particular, surfacing the raw filesystem error would disclose the
        # private AIPROFILE_HOME path through an unattended scheduler trace.
        pass


def _run_git(
    runner: Runner,
    git: str,
    profile_repo: Path,
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    kwargs = {
        "cwd": str(profile_repo),
        "shell": False,
        "check": False,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 300,
    }
    kwargs["env"] = env if env is not None else sanitized_git_env()
    return runner([git, *args], **kwargs)


def _run_git_bytes(
    runner: Runner,
    git: str,
    cwd: Path,
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run one Git command without decoding or newline translation."""
    return runner(
        [git, *args],
        cwd=str(cwd),
        shell=False,
        check=False,
        capture_output=True,
        text=False,
        timeout=300,
        env=env if env is not None else sanitized_git_env(),
    )


def _checked_out_branch(
    runner: Runner, git: str, profile_repo: Path
) -> tuple[int, str]:
    proc = _run_git(
        runner, git, profile_repo, ["symbolic-ref", "--quiet", "--short", "HEAD"]
    )
    return proc.returncode, proc.stdout.strip()


def _repository_state(
    runner: Runner, git: str, profile_repo: Path
) -> tuple[str, str] | None:
    branch_rc, branch = _checked_out_branch(runner, git, profile_repo)
    if branch_rc != 0 or not branch:
        return None
    oid = _run_git(runner, git, profile_repo, ["rev-parse", "--verify", "HEAD"])
    head_oid = oid.stdout.strip()
    if oid.returncode != 0 or not head_oid:
        return None
    return branch, head_oid


def _repository_has_complete_history(
    runner: Runner, git: str, profile_repo: Path
) -> bool:
    """Require a complete object graph before private-Git publication."""
    shallow = _run_git(
        runner, git, profile_repo, ["rev-parse", "--is-shallow-repository"]
    )
    if shallow.returncode != 0 or shallow.stdout.strip() != "false":
        return False
    partial = _run_git(
        runner, git, profile_repo, ["config", "--get", "extensions.partialClone"]
    )
    return partial.returncode == 1


def _git_common_dir(runner: Runner, git: str, profile_repo: Path) -> Path | None:
    result = _run_git(runner, git, profile_repo, ["rev-parse", "--git-common-dir"])
    value = result.stdout.strip()
    if result.returncode != 0 or not value or "\x00" in value or "\n" in value:
        return None
    try:
        path = Path(value)
        if not path.is_absolute():
            path = profile_repo / path
        path = path.resolve()
        return path if path.is_dir() else None
    except OSError:
        return None


def _remote_tip(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    transport: _PublicationTransport,
    branch: str,
) -> str | None:
    reference = f"refs/heads/{branch}"
    result = _run_git(
        runner,
        git,
        transport.git_dir,
        ["ls-remote", "--exit-code", "--", _TRANSPORT_ALIAS, reference],
        env=transport.env,
    )
    lines = result.stdout.splitlines()
    if result.returncode != 0 or len(lines) != 1:
        return None
    fields = lines[0].split()
    if len(fields) != 2 or fields[1] != reference or not _OID.fullmatch(fields[0]):
        return None
    return fields[0]


def _worktree_is_clean(
    runner: Runner, git: str, profile_repo: Path
) -> bool:
    """Return whether a fast-forward can update the checkout safely.

    Remote synchronization is deliberately limited to a clean checkout.  The
    scheduler must never overwrite a user's staged, unstaged, or untracked
    work merely because another actor pushed the recorded branch.
    """
    status = _run_git(
        runner,
        git,
        profile_repo,
        ["status", "--porcelain", "--untracked-files=all"],
    )
    return status.returncode == 0 and not status.stdout


def _restore_fast_forward_checkout(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    branch: str,
    head_oid: str,
) -> bool:
    """Restore the index and worktree after the branch ref is rolled back."""
    for _attempt in range(_REMOTE_SYNC_ATTEMPTS):
        restored = _run_git(
            runner,
            git,
            profile_repo,
            ["read-tree", "-m", "-u", head_oid],
        )
        state = _repository_state(runner, git, profile_repo)
        if (
            restored.returncode == 0
            and state == (branch, head_oid)
            and _worktree_is_clean(runner, git, profile_repo)
        ):
            return True
    return False


def _fast_forward_remote_checkout(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    transport: _PublicationTransport,
    branch: str,
    local_state: tuple[str, str],
) -> _RemoteSyncResult:
    """Fast-forward a clean local checkout when the remote is ahead.

    The remote is fetched through the already-isolated publication transport,
    so no repository URL/config rewrite can redirect this synchronization.  A
    local branch that is ahead or diverged, a dirty checkout, a missing tip, or
    an unstable/unverifiable fetch remains fail-closed for manual resolution.
    """
    if not _worktree_is_clean(runner, git, profile_repo):
        return _RemoteSyncResult(None)

    local_branch, local_oid = local_state
    if local_branch != branch:
        return _RemoteSyncResult(None)
    remote_tip = _remote_tip(
        runner,
        git,
        profile_repo,
        transport=transport,
        branch=branch,
    )
    if remote_tip is None:
        return _RemoteSyncResult(None)
    if remote_tip == local_oid:
        return _RemoteSyncResult(local_state)

    # Fetch only the recorded branch into the private transport.  The object
    # directory is shared with the real repository, but no real ref/index is
    # touched until the ancestry and checkout checks below pass.
    fetched_tip: str | None = None
    for _attempt in range(_REMOTE_SYNC_ATTEMPTS):
        fetched = _run_git(
            runner,
            git,
            profile_repo,
            [
                "fetch",
                "--no-tags",
                "--quiet",
                "--",
                _TRANSPORT_ALIAS,
                f"refs/heads/{branch}",
            ],
            env=transport.env,
        )
        if fetched.returncode != 0:
            return _RemoteSyncResult(None)
        observed = _remote_tip(
            runner,
            git,
            profile_repo,
            transport=transport,
            branch=branch,
        )
        if observed is None:
            return _RemoteSyncResult(None)
        commit = _run_git(
            runner,
            git,
            profile_repo,
            ["cat-file", "-e", f"{observed}^{{commit}}"],
        )
        if commit.returncode == 0:
            fetched_tip = observed
            break
    if fetched_tip is None:
        return _RemoteSyncResult(None)

    if fetched_tip == local_oid:
        return _RemoteSyncResult(local_state)
    ancestor = _run_git(
        runner,
        git,
        profile_repo,
        ["merge-base", "--is-ancestor", local_oid, fetched_tip],
    )
    if ancestor.returncode != 0:
        return _RemoteSyncResult(None)

    # Compare-and-swap the recorded branch so a concurrent local change cannot
    # be silently replaced.  The checkout is still required to be clean after
    # the final preflight; read-tree then updates only the ordinary worktree
    # and index for the verified fast-forward commit, without running hooks.
    if not _state_matches(
        runner,
        git,
        profile_repo,
        branch=branch,
        head_oid=local_oid,
    ) or not _worktree_is_clean(runner, git, profile_repo):
        return _RemoteSyncResult(None)
    updated = _run_git(
        runner,
        git,
        profile_repo,
        ["update-ref", f"refs/heads/{branch}", fetched_tip, local_oid],
    )
    if updated.returncode != 0:
        return _RemoteSyncResult(None)
    checked_out = _run_git(
        runner,
        git,
        profile_repo,
        ["read-tree", "-m", "-u", fetched_tip],
    )
    if checked_out.returncode != 0:
        rolled_back = _rollback_branch(
            runner,
            git,
            profile_repo,
            branch=branch,
            from_oid=fetched_tip,
            to_oid=local_oid,
        )
        if not rolled_back or not _restore_fast_forward_checkout(
            runner,
            git,
            profile_repo,
            branch=branch,
            head_oid=local_oid,
        ):
            return _RemoteSyncResult(
                None,
                "remote branch synchronization rollback failed; "
                "manual synchronization required",
            )
        return _RemoteSyncResult(None)
    synchronized = _repository_state(runner, git, profile_repo)
    if synchronized != (branch, fetched_tip):
        return _RemoteSyncResult(None)
    if not _worktree_is_clean(runner, git, profile_repo):
        return _RemoteSyncResult(None)
    return _RemoteSyncResult(synchronized)


def _single_symmetric_remote_destination(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    remote: str,
) -> str | None:
    fetch = _run_git(
        runner,
        git,
        profile_repo,
        ["remote", "get-url", "--all", remote],
    )
    push = _run_git(
        runner,
        git,
        profile_repo,
        ["remote", "get-url", "--push", "--all", remote],
    )
    if fetch.returncode != 0 or push.returncode != 0:
        return None
    fetch_urls = fetch.stdout.splitlines()
    push_urls = push.stdout.splitlines()
    if (
        len(fetch_urls) != 1
        or len(push_urls) != 1
        or not fetch_urls[0]
        or fetch_urls[0] != push_urls[0]
        or not _supported_remote_destination(fetch_urls[0])
    ):
        return None
    return _canonical_remote_destination(fetch_urls[0], profile_repo)


def _supported_remote_destination(destination: str) -> bool:
    """Accept supported credential-free remote forms as opaque data."""
    if (
        not destination
        or destination.startswith("-")
        or any(char in destination for char in ("\x00", "\r", "\n"))
        or any(ord(char) < 0x20 for char in destination)
        or "?" in destination
        or "#" in destination
        or re.match(r"^(?:[^@]+@)?\[[^]]+\]:", destination) is not None
    ):
        return False
    if re.match(r"^[A-Za-z]:[\\/]", destination):
        return True
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*::", destination):
        return False
    scheme_match = re.match(r"^([A-Za-z][A-Za-z0-9+.-]*)://", destination)
    if scheme_match is None:
        return True
    scheme = scheme_match.group(1).lower()
    if scheme not in {"file", "git", "http", "https", "ssh"}:
        return False
    authority = destination[scheme_match.end() :].split("/", 1)[0]
    if scheme != "file" and not authority:
        return False
    if "@" in authority:
        userinfo = authority.rsplit("@", 1)[0]
        if scheme in {"http", "https", "git"} or ":" in userinfo:
            return False
    return True


def _canonical_remote_destination(destination: str, profile_repo: Path) -> str | None:
    """Resolve local paths before publication moves into its private Git dir."""
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", destination):
        return destination
    drive_relative = re.match(r"^([A-Za-z]):(?![\\/])(.*)$", destination)
    if drive_relative is not None and os.name == "nt":
        drive = f"{drive_relative.group(1)}:"
        if profile_repo.drive.casefold() != drive.casefold():
            return None
        try:
            return (profile_repo / drive_relative.group(2)).resolve().as_uri()
        except (OSError, ValueError):
            return None
    if re.match(r"^(?:[^@/\\:]+@)?[^/\\:]+:.+", destination) and not (
        os.name == "nt" and re.match(r"^[A-Za-z]:", destination)
    ):
        return destination
    try:
        path = Path(destination)
        if not path.is_absolute():
            path = profile_repo / path
        return path.resolve().as_uri()
    except (OSError, ValueError):
        return None


def _transport_config_snapshot(
    runner: Runner, git: str, profile_repo: Path
) -> tuple[tuple[str, str], ...] | None:
    """Freeze only authentication/transport settings; exclude URL rewrites."""
    captured: list[tuple[str, str]] = []
    for key in _TRANSPORT_CONFIG_KEYS:
        result = _run_git_bytes(
            runner,
            git,
            profile_repo,
            ["config", "--null", "--get-all", key],
        )
        if result.returncode == 1:
            continue
        if result.returncode != 0 or not isinstance(result.stdout, bytes):
            return None
        if result.stdout and not result.stdout.endswith(b"\x00"):
            return None
        values = result.stdout.split(b"\x00")
        if values and values[-1] == b"":
            values.pop()
        try:
            for raw_value in values:
                value = raw_value.decode("utf-8", errors="strict")
                captured.append((key, value))
        except UnicodeError:
            return None
    return tuple(captured)


@dataclass(frozen=True)
class _PublicationTransport:
    git_dir: Path
    env: dict[str, str]
    destination_sha256: str


def _write_private_transport_file(path: Path, content: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(path, 0o600)
    finally:
        if fd >= 0:
            os.close(fd)


@contextmanager
def _publication_transport(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    home: Path,
    common_dir: Path,
    destination: str,
):
    """Isolate a captured destination from later Git config rewrites."""
    config = _transport_config_snapshot(runner, git, profile_repo)
    if config is None:
        yield None
        return
    private_dir: Path | None = None
    try:
        private_dir = Path(
            tempfile.mkdtemp(prefix=".publication-transport-", dir=scheduler_dir(home))
        )
        os.chmod(private_dir, 0o700)
        for relative in ("objects", "objects/info", "objects/pack", "refs", "refs/heads"):
            directory = private_dir / relative
            directory.mkdir(mode=0o700)
            os.chmod(directory, 0o700)
        _write_private_transport_file(
            private_dir / "HEAD", b"ref: refs/heads/aiprofile-publication\n"
        )
        _write_private_transport_file(
            private_dir / "config",
            b"[core]\n\trepositoryformatversion = 0\n\tbare = true\n",
        )
        injected = [
            (f"remote.{_TRANSPORT_ALIAS}.url", destination),
            (f"remote.{_TRANSPORT_ALIAS}.pushurl", destination),
            *config,
        ]
        extra = {
            "GIT_DIR": str(private_dir),
            "GIT_OBJECT_DIRECTORY": str(common_dir / "objects"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_COUNT": str(len(injected)),
        }
        for index, (key, value) in enumerate(injected):
            extra[f"GIT_CONFIG_KEY_{index}"] = key
            extra[f"GIT_CONFIG_VALUE_{index}"] = value
        transport_env = sanitized_git_env(extra)
        for key in tuple(transport_env):
            if key.upper() in _PROXY_ENV_KEYS:
                del transport_env[key]
        transport = _PublicationTransport(
            git_dir=private_dir,
            env=transport_env,
            destination_sha256=_destination_sha256(destination),
        )
    except OSError:
        yield None
        if private_dir is not None:
            try:
                shutil.rmtree(private_dir)
            except OSError:
                pass
        return
    try:
        yield transport
    finally:
        if private_dir is not None:
            try:
                shutil.rmtree(private_dir)
            except OSError:
                pass


def _destination_sha256(destination: str) -> str:
    return hashlib.sha256(destination.encode("utf-8")).hexdigest()


def _push_exact_remote_parent(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    transport: _PublicationTransport,
    branch: str,
    commit_oid: str,
    parent_oid: str,
) -> tuple[bool, str | None]:
    reference = f"refs/heads/{branch}"
    pushed = _run_git(
        runner,
        git,
        transport.git_dir,
        [
            "push",
            f"--force-with-lease={reference}:{parent_oid}",
            "--",
            _TRANSPORT_ALIAS,
            f"{commit_oid}:{reference}",
        ],
        env=transport.env,
    )
    remote_tip = _remote_tip(
        runner,
        git,
        profile_repo,
        transport=transport,
        branch=branch,
    )
    if remote_tip == commit_oid:
        return True, None
    if remote_tip is None:
        return False, "push outcome could not be verified; pending commit retained"
    if pushed.returncode != 0:
        return (
            False,
            f"push failed (exit {pushed.returncode}); pending commit retained",
        )
    return (
        False,
        "push reported success but remote publication is not confirmed; "
        "pending commit retained",
    )


@dataclass(frozen=True)
class _PendingPush:
    commit_oid: str
    parent_oid: str
    tree_oid: str
    branch: str
    remote: str
    destination_sha256: str


_PENDING_KEYS = frozenset(
    {
        "commit_oid",
        "parent_oid",
        "tree_oid",
        "branch",
        "remote",
        "destination_sha256",
    }
)


def _pending_path(home: Path) -> Path:
    return scheduler_dir(home) / PENDING_PUSH_NAME


def _write_pending(home: Path, pending: _PendingPush) -> bool:
    path = _pending_path(home)
    tmp = path.with_name(path.name + ".tmp")
    content = (
        json.dumps(
            {
                "branch": pending.branch,
                "commit_oid": pending.commit_oid,
                "destination_sha256": pending.destination_sha256,
                "parent_oid": pending.parent_oid,
                "remote": pending.remote,
                "tree_oid": pending.tree_oid,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "wb") as handle:
            os.chmod(tmp, 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        # The prepared temp file is already 0600.  Keep replacement as the
        # final fallible operation so success/failure cannot disagree with
        # whether the durable pending record exists.
        os.replace(tmp, path)
        return True
    except OSError:
        return False
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _read_pending(home: Path) -> tuple[_PendingPush | None, bool]:
    path = _pending_path(home)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, False
    except (OSError, UnicodeError):
        return None, True
    try:
        raw = json.loads(content)
        if not isinstance(raw, dict) or set(raw) != _PENDING_KEYS:
            raise ValueError
        values = [raw[key] for key in sorted(_PENDING_KEYS)]
        if not all(isinstance(value, str) for value in values):
            raise ValueError
        pending = _PendingPush(**raw)
        if (
            not _OID.fullmatch(pending.commit_oid)
            or not _SHA256.fullmatch(pending.destination_sha256)
            or not _OID.fullmatch(pending.parent_oid)
            or not _OID.fullmatch(pending.tree_oid)
            or not pending.branch
            or not pending.remote
            or any(char in pending.branch + pending.remote for char in "\r\n\x00")
        ):
            raise ValueError
        return pending, False
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, True


def _clear_pending(home: Path) -> bool:
    try:
        _pending_path(home).unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _state_matches(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    branch: str,
    head_oid: str,
) -> bool:
    return _repository_state(runner, git, profile_repo) == (branch, head_oid)


def _rollback_branch(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    branch: str,
    from_oid: str,
    to_oid: str,
) -> bool:
    rolled_back = _run_git(
        runner,
        git,
        profile_repo,
        ["update-ref", f"refs/heads/{branch}", to_oid, from_oid],
    )
    return rolled_back.returncode == 0


def _restore_tool_index_to_current_head(
    runner: Runner, git: str, profile_repo: Path
) -> bool:
    """Best-effort exact-path cleanup after a concurrent checkout/ref move."""
    for _attempt in range(3):
        current = _run_git(runner, git, profile_repo, ["rev-parse", "--verify", "HEAD"])
        current_oid = current.stdout.strip()
        if current.returncode != 0 or not current_oid:
            return False
        reset = _run_git(
            runner,
            git,
            profile_repo,
            ["reset", "-q", current_oid, "--", *_PATHS],
        )
        if reset.returncode != 0:
            return False
        clean = _run_git(
            runner,
            git,
            profile_repo,
            ["diff", "--cached", "--quiet", current_oid, "--", *_PATHS],
        )
        verified = _run_git(
            runner, git, profile_repo, ["rev-parse", "--verify", "HEAD"]
        )
        if (
            clean.returncode == 0
            and verified.returncode == 0
            and verified.stdout.strip() == current_oid
        ):
            return True
    return False


def _write_private_tree(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    index_path: Path,
    env: dict[str, str],
    head_oid: str,
    expected_manifest: tuple[AssetDigest, ...],
) -> tuple[str | None, str | None]:
    """Build a tree with the index confined beneath a POSIX 0700 directory."""
    read_tree = _run_git(
        runner, git, profile_repo, ["read-tree", head_oid], env=env
    )
    if read_tree.returncode != 0:
        return None, f"git index setup failed (exit {read_tree.returncode})"
    os.chmod(index_path, 0o600)

    added = _run_git(runner, git, profile_repo, ["add", "--", *_PATHS], env=env)
    if added.returncode != 0:
        return (
            None,
            f"git staging failed (exit {added.returncode}); no commit was made",
        )
    os.chmod(index_path, 0o600)

    expected = {
        f"dist/{item.name}": item.sha256 for item in expected_manifest
    }
    if (
        set(expected) != set(_PATHS)
        or len(expected) != len(expected_manifest)
        or any(not re.fullmatch(r"[0-9a-f]{64}", digest) for digest in expected.values())
    ):
        return None, "rendered generation manifest is unavailable; publication refused"
    listed = _run_git(
        runner,
        git,
        profile_repo,
        ["ls-files", "--stage", "-z", "--", *_PATHS],
        env=env,
    )
    if listed.returncode != 0:
        return None, "generated asset verification failed; publication refused"
    staged: dict[str, str] = {}
    try:
        for entry in listed.stdout.split("\x00"):
            if not entry:
                continue
            metadata, path = entry.split("\t", 1)
            mode, oid, stage = metadata.split()
            if mode != "100644" or stage != "0" or path in staged:
                raise ValueError
            staged[path] = oid
    except ValueError:
        return None, "generated asset verification failed; publication refused"
    if set(staged) != set(_PATHS):
        return None, "generated asset verification failed; publication refused"
    for path, oid in staged.items():
        blob = _run_git_bytes(
            runner, git, profile_repo, ["cat-file", "blob", oid]
        )
        if blob.returncode != 0 or not isinstance(blob.stdout, bytes):
            return None, "generated asset verification failed; publication refused"
        digest = hashlib.sha256(blob.stdout).hexdigest()
        if digest != expected[path]:
            return None, "generated asset bytes changed after refresh; publication refused"

    written = _run_git(runner, git, profile_repo, ["write-tree"], env=env)
    tree_oid = written.stdout.strip()
    if written.returncode != 0 or not tree_oid:
        return None, f"git tree creation failed (exit {written.returncode})"
    os.chmod(index_path, 0o600)
    return tree_oid, None


def _prepare_commit(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    home: Path,
    head_oid: str,
    expected_manifest: tuple[AssetDigest, ...],
) -> tuple[str | None, str | None, str | None, bool]:
    """Create an exact-path commit without touching the user's real index.

    ``commit-tree`` returns the scheduler-created OID directly. It deliberately
    bypasses user commit hooks and signing: scheduled publication is unattended
    and must not execute repository-provided code.
    """
    private_dir: Path | None = None
    commit_oid: str | None = None
    tree_oid: str | None = None
    failure: str | None = None
    unchanged = False
    try:
        private_dir = Path(
            tempfile.mkdtemp(prefix=".publication-index-", dir=scheduler_dir(home))
        )
        os.chmod(private_dir, 0o700)
        index_path = private_dir / "index"
        env = sanitized_git_env({"GIT_INDEX_FILE": str(index_path)})

        tree_oid, failure = _write_private_tree(
            runner,
            git,
            profile_repo,
            index_path=index_path,
            env=env,
            head_oid=head_oid,
            expected_manifest=expected_manifest,
        )
        if failure is None and tree_oid is not None:
            base_tree = _run_git(
                runner,
                git,
                profile_repo,
                ["rev-parse", f"{head_oid}^{{tree}}"],
            )
            base_tree_oid = base_tree.stdout.strip()
            if base_tree.returncode != 0 or not base_tree_oid:
                failure = f"git tree comparison failed (exit {base_tree.returncode})"
            elif base_tree_oid == tree_oid:
                unchanged = True
            else:
                created = _run_git(
                    runner,
                    git,
                    profile_repo,
                    [
                        "commit-tree",
                        tree_oid,
                        "-p",
                        head_oid,
                        "-m",
                        "chore: refresh ai-profile outputs",
                    ],
                )
                commit_oid = created.stdout.strip()
                if created.returncode != 0 or not commit_oid:
                    failure = f"git commit creation failed (exit {created.returncode})"
                    commit_oid = None
    except OSError:
        failure = "temporary publication state could not be prepared safely"
        commit_oid = None
    finally:
        if private_dir is not None:
            try:
                shutil.rmtree(private_dir)
            except OSError:
                failure = (
                    "temporary publication state may remain; "
                    "no branch update or push was attempted"
                )
                commit_oid = None
                unchanged = False
    return commit_oid, tree_oid if failure is None else None, failure, unchanged


def _pending_commit_matches(
    runner: Runner,
    git: str,
    profile_repo: Path,
    pending: _PendingPush,
) -> bool:
    parents = _run_git(
        runner,
        git,
        profile_repo,
        ["rev-list", "--parents", "-n", "1", pending.commit_oid],
    )
    fields = parents.stdout.split()
    tree = _run_git(
        runner,
        git,
        profile_repo,
        ["rev-parse", f"{pending.commit_oid}^{{tree}}"],
    )
    return (
        parents.returncode == 0
        and fields == [pending.commit_oid, pending.parent_oid]
        and tree.returncode == 0
        and tree.stdout.strip() == pending.tree_oid
    )


def _retry_pending_push(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    home: Path,
    branch: str,
    remote: str,
    transport: _PublicationTransport,
) -> tuple[bool, tuple[int, str] | None]:
    pending, invalid = _read_pending(home)
    if invalid:
        return False, (
            1,
            "pending publication state is invalid; synchronize manually",
        )
    if pending is None:
        return False, None
    if pending.branch != branch or pending.remote != remote:
        return False, (
            1,
            "pending publication state diverged; synchronize manually",
        )
    if pending.destination_sha256 != transport.destination_sha256:
        return False, (
            1,
            "pending publication destination diverged; synchronize manually",
        )
    if not _pending_commit_matches(runner, git, profile_repo, pending):
        return False, (
            1,
            "pending publication state diverged; synchronize manually",
        )
    local_state = _repository_state(runner, git, profile_repo)
    if local_state == (branch, pending.parent_oid):
        remote_before_cas = _remote_tip(
            runner,
            git,
            profile_repo,
            transport=transport,
            branch=branch,
        )
        if remote_before_cas != pending.parent_oid:
            return False, (
                1,
                "pending publication state diverged; synchronize manually",
            )
        advanced = _run_git(
            runner,
            git,
            profile_repo,
            [
                "update-ref",
                f"refs/heads/{branch}",
                pending.commit_oid,
                pending.parent_oid,
            ],
        )
        if advanced.returncode != 0:
            return False, (
                1,
                "pending publication branch could not be advanced; "
                "pending retry state remains and push was refused",
            )
        if not _state_matches(
            runner,
            git,
            profile_repo,
            branch=branch,
            head_oid=pending.commit_oid,
        ):
            if _rollback_branch(
                runner,
                git,
                profile_repo,
                branch=branch,
                from_oid=pending.commit_oid,
                to_oid=pending.parent_oid,
            ):
                return False, (
                    1,
                    "publication rolled back but pending retry state remains",
                )
            return False, (
                1,
                "repository state changed after branch update; local scheduler "
                "commit or ref may remain and pending retry state remains; "
                "push was refused",
            )
    elif local_state != (branch, pending.commit_oid):
        return False, (
            1,
            "pending publication state diverged; synchronize manually",
        )
    synchronized = _run_git(
        runner,
        git,
        profile_repo,
        ["reset", "-q", pending.commit_oid, "--", *_PATHS],
    )
    if synchronized.returncode != 0:
        return False, (
            1,
            "pending publication index could not be synchronized; "
            "tool paths may remain staged and push was refused",
        )
    if not _state_matches(
        runner,
        git,
        profile_repo,
        branch=branch,
        head_oid=pending.commit_oid,
    ):
        cleaned = _restore_tool_index_to_current_head(runner, git, profile_repo)
        suffix = (
            "tool paths were restored and push was refused"
            if cleaned
            else "tool paths may remain staged and push was refused"
        )
        return False, (
            1,
            f"pending publication state diverged during index repair; {suffix}",
        )
    clean = _run_git(
        runner,
        git,
        profile_repo,
        ["diff", "--cached", "--quiet", pending.commit_oid, "--", *_PATHS],
    )
    if clean.returncode != 0:
        return False, (
            1,
            "pending publication index could not be synchronized; "
            "tool paths may remain staged and push was refused",
        )
    remote_tip = _remote_tip(
        runner,
        git,
        profile_repo,
        transport=transport,
        branch=branch,
    )
    if remote_tip == pending.commit_oid:
        if not _clear_pending(home):
            return False, (
                1,
                "publication reached remote but pending retry state remains",
            )
        return True, None
    if remote_tip != pending.parent_oid:
        return False, (
            1,
            "pending publication state diverged; synchronize manually",
        )
    published, push_failure = _push_exact_remote_parent(
        runner,
        git,
        profile_repo,
        transport=transport,
        branch=branch,
        commit_oid=pending.commit_oid,
        parent_oid=pending.parent_oid,
    )
    if not published:
        return False, (1, push_failure or "push outcome is uncertain")
    if not _clear_pending(home):
        return False, (
            1,
            "publication reached remote but pending retry state remains",
        )
    return True, None


def _publish(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    push: bool,
    remote: str,
    transport: _PublicationTransport | None,
    branch: str,
    head_oid: str,
    home: Path,
    expected_manifest: tuple[AssetDigest, ...],
) -> tuple[int, str]:
    if not _state_matches(
        runner, git, profile_repo, branch=branch, head_oid=head_oid
    ):
        return (
            1,
            "repository state changed during scheduled refresh; publication refused",
        )
    status = _run_git(
        runner, git, profile_repo, ["status", "--porcelain", "--", *_PATHS]
    )
    if status.returncode != 0:
        return 1, f"git status failed (exit {status.returncode}); no commit was made"
    if not _state_matches(
        runner, git, profile_repo, branch=branch, head_oid=head_oid
    ):
        return (
            1,
            "repository state changed during scheduled refresh; publication refused",
        )
    committed_oid, tree_oid, preparation_failure, unchanged = _prepare_commit(
        runner,
        git,
        profile_repo,
        home=home,
        head_oid=head_oid,
        expected_manifest=expected_manifest,
    )
    if unchanged:
        return 0, "refresh completed; no change"
    if preparation_failure is not None or committed_oid is None or tree_oid is None:
        return 1, preparation_failure or "git commit creation failed"
    pending_written = False
    if push:
        assert transport is not None
        pending = _PendingPush(
            commit_oid=committed_oid,
            parent_oid=head_oid,
            tree_oid=tree_oid,
            branch=branch,
            remote=remote,
            destination_sha256=transport.destination_sha256,
        )
        if not _write_pending(home, pending):
            return (
                1,
                "pending publication state unavailable; "
                "no branch update or push was attempted",
            )
        pending_written = True
    if not _state_matches(
        runner, git, profile_repo, branch=branch, head_oid=head_oid
    ):
        if pending_written and not _clear_pending(home):
            return (
                1,
                "pending publication state remains; "
                "no branch update or push was attempted",
            )
        return (
            1,
            "repository state changed before branch update; publication refused",
        )
    updated = _run_git(
        runner,
        git,
        profile_repo,
        ["update-ref", f"refs/heads/{branch}", committed_oid, head_oid],
    )
    if updated.returncode != 0:
        if pending_written and not _clear_pending(home):
            return (
                1,
                "pending publication state remains; "
                "no branch update or push was attempted",
            )
        return (
            1,
            "repository state changed before branch update; publication refused",
        )
    if not _state_matches(
        runner, git, profile_repo, branch=branch, head_oid=committed_oid
    ):
        if _rollback_branch(
            runner,
            git,
            profile_repo,
            branch=branch,
            from_oid=committed_oid,
            to_oid=head_oid,
        ):
            if pending_written and not _clear_pending(home):
                return (
                    1,
                    "publication rolled back but pending retry state remains",
                )
            return (
                1,
                "repository state changed after branch update; publication rolled back",
            )
        return (
            1,
            "repository state changed after branch update; "
            "local scheduler commit or ref may remain"
            + (" and pending retry state remains" if pending_written else "")
            + "; push was refused",
        )
    synchronized = _run_git(
        runner,
        git,
        profile_repo,
        ["reset", "-q", committed_oid, "--", *_PATHS],
    )
    if not _state_matches(
        runner,
        git,
        profile_repo,
        branch=branch,
        head_oid=committed_oid,
    ):
        cleaned = _restore_tool_index_to_current_head(runner, git, profile_repo)
        rolled_back = _rollback_branch(
            runner,
            git,
            profile_repo,
            branch=branch,
            from_oid=committed_oid,
            to_oid=head_oid,
        )
        if not cleaned and rolled_back:
            if pending_written and not _clear_pending(home):
                return (
                    1,
                    "publication rolled back but tool paths may remain staged "
                    "and pending retry state remains",
                )
            return (
                1,
                "repository state changed after index synchronization; "
                "publication rolled back but tool paths may remain staged "
                "and push was refused",
            )
        if not cleaned and not rolled_back:
            return (
                1,
                "repository state changed after index synchronization; "
                "tool paths may remain staged and local scheduler commit or ref "
                "may remain"
                + (" and pending retry state remains" if pending_written else "")
                + "; push was refused",
            )
        if rolled_back:
            if pending_written and not _clear_pending(home):
                return (
                    1,
                    "publication rolled back but pending retry state remains",
                )
            return (
                1,
                "repository state changed after branch update; publication rolled back",
            )
        return (
            1,
            "repository state changed after branch update; "
            "local scheduler commit or ref may remain"
            + (" and pending retry state remains" if pending_written else "")
            + "; push was refused",
        )
    if synchronized.returncode != 0:
        if pending_written:
            return (
                1,
                "local commit and pending retry state retained; "
                "tool paths may remain staged and push was refused",
            )
        return (
            1,
            "local commit retained; tool paths may remain staged and push was refused",
        )
    if not push:
        return 0, "refresh committed locally; push disabled"
    published, push_failure = _push_exact_remote_parent(
        runner,
        git,
        profile_repo,
        transport=transport,
        branch=branch,
        commit_oid=committed_oid,
        parent_oid=head_oid,
    )
    if not published:
        return 1, push_failure or "push outcome is uncertain"
    if not _clear_pending(home):
        return 1, "publication reached remote but pending retry state remains"
    return 0, "refresh committed and pushed"


def _run_target_locked(
    home: Path, cfg: SchedulerConfig, runner: Runner, git: str
) -> tuple[int, str]:
    common_dir = _git_common_dir(runner, git, cfg.profile_repo)
    if common_dir is None:
        return 1, "profile repository locking is unavailable; publication refused"
    with acquire_publication_lock(common_dir):
        initial_state = _repository_state(runner, git, cfg.profile_repo)
        if initial_state is None or initial_state[0] != cfg.branch:
            return 1, "recorded branch is no longer checked out; run refused"
        if not _repository_has_complete_history(runner, git, cfg.profile_repo):
            return (
                1,
                "profile repository history is incomplete; "
                "scheduled publication is unsupported",
            )

        destination = None
        if cfg.push:
            destination = _single_symmetric_remote_destination(
                runner,
                git,
                cfg.profile_repo,
                remote=cfg.remote,
            )
            if destination is None:
                return (
                    1,
                    "remote publication destination is unsupported; "
                    "no publication attempted",
                )

        transport_context = (
            _publication_transport(
                runner,
                git,
                cfg.profile_repo,
                home=home,
                common_dir=common_dir,
                destination=destination,
            )
            if destination is not None
            else nullcontext(None)
        )
        with transport_context as transport:
            if cfg.push and transport is None:
                return (
                    1,
                    "remote publication destination is unsupported; "
                    "no publication attempted",
                )
            pending, invalid_pending = _read_pending(home)
            if not cfg.push and (invalid_pending or pending is not None):
                return 1, "pending publication state diverged; synchronize manually"
            if cfg.push:
                assert transport is not None
                _retried, retry_failure = _retry_pending_push(
                    runner,
                    git,
                    cfg.profile_repo,
                    home=home,
                    branch=cfg.branch,
                    remote=cfg.remote,
                    transport=transport,
                )
                if retry_failure is not None:
                    return retry_failure
                initial_state = _repository_state(runner, git, cfg.profile_repo)
                if initial_state is None or initial_state[0] != cfg.branch:
                    return 1, "recorded branch is no longer checked out; run refused"
                remote_tip = _remote_tip(
                    runner,
                    git,
                    cfg.profile_repo,
                    transport=transport,
                    branch=cfg.branch,
                )
                if remote_tip != initial_state[1]:
                    sync_result = _fast_forward_remote_checkout(
                        runner,
                        git,
                        cfg.profile_repo,
                        transport=transport,
                        branch=cfg.branch,
                        local_state=initial_state,
                    )
                    if sync_result.state is None:
                        return (
                            1,
                            sync_result.failure
                            or "remote branch does not match local HEAD; "
                            "synchronize manually",
                        )
                    initial_state = sync_result.state

            result = refresh.run_refresh(home, cfg.profile_repo / "dist")
            if not result.ok:
                return (
                    1,
                    "refresh failed for configured repositories; no outputs published",
                )
            return _publish(
                runner,
                git,
                cfg.profile_repo,
                push=cfg.push,
                remote=cfg.remote,
                transport=transport,
                branch=cfg.branch,
                head_oid=initial_state[1],
                home=home,
                expected_manifest=result.asset_manifest,
            )


def run_launcher(
    home: Path,
    *,
    runner: Runner = subprocess.run,
) -> int:
    """Run one scheduled refresh and optional publication.

    The fixed last-run messages intentionally exclude paths, repository names,
    git output, commit ids, identities, and trailer values.
    """
    home = Path(home)
    try:
        outcome: tuple[int, str] | None = None
        with acquire_home_lock(home, SCHEDULER_LOCK_NAME):
            try:
                cfg = read_scheduler_config(home)
                git = shutil.which("git")
                if not git:
                    raise ConfigError("git executable is unavailable")
                outcome = _run_target_locked(home, cfg, runner, git)

            except LockError:
                raise
            except AiProfileError:
                outcome = (1, "refresh failed safely; no publication attempted")
            except (OSError, subprocess.SubprocessError):
                outcome = (1, "scheduled refresh failed safely")
            _append_log(home, outcome[1])
    except LockError as exc:
        if outcome is not None:
            _append_log(home, f"{outcome[1]}; scheduler finalization failed")
            return 1
        if "another aiprofile refresh" in str(exc):
            _append_log(home, "scheduled refresh skipped; another run is active")
            return 0
        if "another aiprofile publication" in str(exc):
            _append_log(home, "scheduled refresh skipped; another publication is active")
            return 0
        _append_log(home, "scheduled refresh failed because locking is unavailable")
        return 1
    assert outcome is not None
    return outcome[0]

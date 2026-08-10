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
    remote: str,
    branch: str,
) -> str | None:
    reference = f"refs/heads/{branch}"
    result = _run_git(
        runner,
        git,
        profile_repo,
        ["ls-remote", "--exit-code", remote, reference],
    )
    lines = result.stdout.splitlines()
    if result.returncode != 0 or len(lines) != 1:
        return None
    fields = lines[0].split()
    if len(fields) != 2 or fields[1] != reference or not _OID.fullmatch(fields[0]):
        return None
    return fields[0]


@dataclass(frozen=True)
class _PendingPush:
    commit_oid: str
    parent_oid: str
    tree_oid: str
    branch: str
    remote: str


_PENDING_KEYS = frozenset(
    {"commit_oid", "parent_oid", "tree_oid", "branch", "remote"}
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
            remote=remote,
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
        remote=remote,
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
    pushed = _run_git(
        runner,
        git,
        profile_repo,
        ["push", remote, f"{pending.commit_oid}:refs/heads/{branch}"],
    )
    if pushed.returncode != 0:
        return False, (
            1,
            f"push failed (exit {pushed.returncode}); pending commit retained",
        )
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
        pending = _PendingPush(
            commit_oid=committed_oid,
            parent_oid=head_oid,
            tree_oid=tree_oid,
            branch=branch,
            remote=remote,
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
    pushed = _run_git(
        runner,
        git,
        profile_repo,
        ["push", remote, f"{committed_oid}:refs/heads/{branch}"],
    )
    if pushed.returncode != 0:
        return 1, f"push failed (exit {pushed.returncode}); pending commit retained"
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

        pending, invalid_pending = _read_pending(home)
        if not cfg.push and (invalid_pending or pending is not None):
            return 1, "pending publication state diverged; synchronize manually"
        if cfg.push:
            _retried, retry_failure = _retry_pending_push(
                runner,
                git,
                cfg.profile_repo,
                home=home,
                branch=cfg.branch,
                remote=cfg.remote,
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
                remote=cfg.remote,
                branch=cfg.branch,
            )
            if remote_tip != initial_state[1]:
                return (
                    1,
                    "remote branch does not match local HEAD; synchronize manually",
                )

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

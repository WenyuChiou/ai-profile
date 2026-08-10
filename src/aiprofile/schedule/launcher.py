"""Importable implementation used by the generated scheduler launcher.

All subprocesses receive argv lists with ``shell=False``.  Git publication
is limited to the exact eight public asset paths; existing unrelated staged
content remains staged and cannot enter the mechanical output commit.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .. import refresh
from ..errors import AiProfileError, ConfigError, LockError
from ..export import PUBLIC_ASSET_NAMES
from ..lockfile import acquire_home_lock
from .service import (
    SCHEDULER_LOCK_NAME,
    is_safe_last_run_message,
    read_scheduler_config,
    scheduler_dir,
)

Runner = Callable[..., subprocess.CompletedProcess[str]]
_PATHS = tuple(f"dist/{name}" for name in sorted(PUBLIC_ASSET_NAMES))


def _append_log(home: Path, message: str) -> None:
    directory = scheduler_dir(home)
    try:
        if not is_safe_last_run_message(message):
            message = "scheduled refresh failed safely"
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        with open(
            directory / "last-run.log", "a", encoding="utf-8", newline="\n"
        ) as log:
            log.write(f"{stamp} {message}\n")
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
    if env is not None:
        kwargs["env"] = env
    return runner([git, *args], **kwargs)


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


def _prepare_commit(
    runner: Runner,
    git: str,
    profile_repo: Path,
    *,
    home: Path,
    head_oid: str,
) -> tuple[str | None, str | None, bool]:
    """Create an exact-path commit without touching the user's real index.

    ``commit-tree`` returns the scheduler-created OID directly. It deliberately
    bypasses user commit hooks and signing: scheduled publication is unattended
    and must not execute repository-provided code.
    """
    private_dir: Path | None = None
    commit_oid: str | None = None
    failure: str | None = None
    unchanged = False
    try:
        private_dir = Path(
            tempfile.mkdtemp(prefix=".publication-index-", dir=scheduler_dir(home))
        )
        os.chmod(private_dir, 0o700)
        index_path = private_dir / "index"
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(index_path)

        read_tree = _run_git(
            runner, git, profile_repo, ["read-tree", head_oid], env=env
        )
        if read_tree.returncode != 0:
            failure = f"git index setup failed (exit {read_tree.returncode})"
        else:
            os.chmod(index_path, 0o600)
            added = _run_git(
                runner, git, profile_repo, ["add", "--", *_PATHS], env=env
            )
            if added.returncode != 0:
                failure = (
                    f"git staging failed (exit {added.returncode}); "
                    "no commit was made"
                )
            else:
                os.chmod(index_path, 0o600)
                written = _run_git(
                    runner, git, profile_repo, ["write-tree"], env=env
                )
                tree_oid = written.stdout.strip()
                if written.returncode != 0 or not tree_oid:
                    failure = f"git tree creation failed (exit {written.returncode})"
                else:
                    base_tree = _run_git(
                        runner, git, profile_repo, ["rev-parse", f"{head_oid}^{{tree}}"]
                    )
                    base_tree_oid = base_tree.stdout.strip()
                    if base_tree.returncode != 0 or not base_tree_oid:
                        failure = (
                            f"git tree comparison failed (exit {base_tree.returncode})"
                        )
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
                            failure = (
                                f"git commit creation failed (exit {created.returncode})"
                            )
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
    return commit_oid, failure, unchanged


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
    if not status.stdout.strip():
        return 0, "refresh completed; no change"

    committed_oid, preparation_failure, unchanged = _prepare_commit(
        runner,
        git,
        profile_repo,
        home=home,
        head_oid=head_oid,
    )
    if unchanged:
        return 0, "refresh completed; no change"
    if preparation_failure is not None or committed_oid is None:
        return 1, preparation_failure or "git commit creation failed"
    if not _state_matches(
        runner, git, profile_repo, branch=branch, head_oid=head_oid
    ):
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
            return (
                1,
                "repository state changed after branch update; publication rolled back",
            )
        return (
            1,
            "repository state changed after branch update; "
            "local scheduler commit or ref may remain and push was refused",
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
                "may remain; push was refused",
            )
        if rolled_back:
            return (
                1,
                "repository state changed after branch update; publication rolled back",
            )
        return (
            1,
            "repository state changed after branch update; "
            "local scheduler commit or ref may remain and push was refused",
        )
    if synchronized.returncode != 0:
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
        return 1, f"push failed (exit {pushed.returncode}); local commit retained"
    return 0, "refresh committed and pushed"


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
                initial_state = _repository_state(runner, git, cfg.profile_repo)
                if initial_state is None or initial_state[0] != cfg.branch:
                    outcome = (
                        1,
                        "recorded branch is no longer checked out; run refused",
                    )
                else:
                    result = refresh.run_refresh(home, cfg.profile_repo / "dist")
                    if not result.ok:
                        outcome = (
                            1,
                            "refresh failed for configured repositories; no outputs published",
                        )
                    else:
                        outcome = _publish(
                            runner,
                            git,
                            cfg.profile_repo,
                            push=cfg.push,
                            remote=cfg.remote,
                            branch=cfg.branch,
                            head_oid=initial_state[1],
                            home=home,
                        )

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
        _append_log(home, "scheduled refresh failed because locking is unavailable")
        return 1
    assert outcome is not None
    return outcome[0]

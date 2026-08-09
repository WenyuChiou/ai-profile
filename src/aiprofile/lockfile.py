"""Per-AIPROFILE_HOME advisory lock for the refresh service (v0.7.0).

Semantics: ADVISORY (only cooperating aiprofile invocations observe it),
PER-HOME (one lock file inside the locked directory), NONBLOCKING (a held
lock raises :class:`LockError` immediately - never waits), and
AUTO-RELEASED BY THE OS ON PROCESS DEATH (msvcrt region locks on Windows,
``flock`` elsewhere - a leftover lock FILE from a dead process is inert,
so there are no pid-file staleness heuristics to get wrong).

Release never deletes the lock file: on POSIX, unlinking races with a
concurrent acquirer that already opened the same path - the acquirer would
hold a lock on an anonymous inode while a third process recreates the
path and "wins" a lock the second process believes it holds.
"""

from __future__ import annotations

import errno
import os
import sys
from pathlib import Path

from .errors import LockError

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

#: Default-output privacy rule (frozen scope guards): lock errors never
#: name a path, repository, or basename - the holder is generic.
_CONTENTION_MESSAGE = (
    "another aiprofile refresh is running against this profile home;"
    " wait for it to finish and retry"
)
_UNAVAILABLE_MESSAGE = (
    "refresh locking is unavailable; verify profile-home access and filesystem"
    " locking support"
)
_CONTENTION_ERRNOS = frozenset(
    value
    for value in (
        errno.EACCES,
        errno.EAGAIN,
        getattr(errno, "EWOULDBLOCK", None),
        getattr(errno, "EDEADLK", None),
    )
    if value is not None
)


class _HomeLock:
    """Context manager holding the OS lock between __enter__ and __exit__."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def __enter__(self) -> _HomeLock:
        try:
            fd = os.open(self._path, os.O_RDWR | os.O_CREAT)
        except OSError as exc:
            raise LockError(_UNAVAILABLE_MESSAGE) from exc
        try:
            if sys.platform == "win32":
                # Lock byte 0 (locking works past EOF on an empty file);
                # the fd's position is 0 on a fresh open and stays there.
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            message = (
                _CONTENTION_MESSAGE
                if exc.errno in _CONTENTION_ERRNOS
                else _UNAVAILABLE_MESSAGE
            )
            error = LockError(message)
            try:
                os.close(fd)
            except OSError:
                # Preserve the primitive acquisition failure as the cause;
                # close diagnostics may contain a private path, so record
                # only the safe operation-level fact.
                error.add_note(
                    f"Additional descriptor close failure: {_UNAVAILABLE_MESSAGE}."
                )
            raise error from exc
        self._fd = fd
        return self

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        fd = self._fd
        self._fd = None
        if fd is None:  # pragma: no cover - defensive: exit without enter
            return None
        cleanup_failures: list[tuple[str, OSError]] = []
        try:
            if sys.platform == "win32":
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError as release_error:
            cleanup_failures.append(("lock release", release_error))
        try:
            os.close(fd)  # never unlink - see the module docstring
        except OSError as close_error:
            cleanup_failures.append(("descriptor close", close_error))

        if not cleanup_failures:
            return None
        if exc is not None:
            # Cleanup must never replace the body exception: publication
            # state (especially incomplete rollback) is the primary truth.
            # Notes omit raw OSError text because it may contain a private
            # path; verbose output still identifies the safe operation.
            for operation, _failure in cleanup_failures:
                exc.add_note(
                    f"Additional {operation} failure: {_UNAVAILABLE_MESSAGE}."
                )
            return False

        operation, primary = cleanup_failures[0]
        error = LockError(_UNAVAILABLE_MESSAGE)
        for secondary_operation, _failure in cleanup_failures[1:]:
            error.add_note(
                f"Additional {secondary_operation} failure: {_UNAVAILABLE_MESSAGE}."
            )
        error.add_note(f"Failed operation: {operation}.")
        raise error from primary


def acquire_home_lock(home: Path, name: str = ".refresh.lock") -> _HomeLock:
    """Nonblocking advisory lock on ``home`` (acquired at ``with`` entry).

    Raises :class:`LockError` immediately if another invocation holds it.
    """
    return _HomeLock(home / name)

"""Cross-platform nonblocking per-home advisory lock (v0.7.0 Task A1).

The lock is advisory and OS-enforced (msvcrt on Windows, fcntl elsewhere):
a leftover lock FILE from a dead process must never block a new acquire
(no pid-file semantics), and contention must fail fast (nonblocking) with
a LockError whose message follows the default-output privacy rule - no
filesystem path, no repository name, no basename.
"""

from __future__ import annotations

import errno
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import aiprofile.lockfile as lock_mod
from aiprofile.errors import IncompleteRollbackError, LockError
from aiprofile.lockfile import acquire_home_lock

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Python source for a subprocess that holds the home lock until killed.
#: The home and ready-file paths arrive via argv (never interpolated into
#: the code string), and readiness is signalled through a file the parent
#: polls - no timing guesswork on the acquire itself.
_HOLDER_SOURCE = """
import sys
import time
from pathlib import Path

from aiprofile.lockfile import acquire_home_lock

home = Path(sys.argv[1])
ready = Path(sys.argv[2])
with acquire_home_lock(home):
    ready.write_text("ready", encoding="utf-8")
    time.sleep(60)
"""


def test_acquire_creates_lock_file_and_releases_on_exit(tmp_path):
    home = tmp_path / "lock-canary-home-quokka-31"
    home.mkdir()
    with acquire_home_lock(home):
        assert (home / ".refresh.lock").exists()
    # Released on exit: a second acquire succeeds immediately.
    with acquire_home_lock(home):
        pass


def test_second_acquire_same_process_raises_lock_error(tmp_path, monkeypatch):
    home = tmp_path / "lock-canary-home-quokka-31"
    home.mkdir()
    with acquire_home_lock(home):
        with pytest.raises(LockError) as excinfo:
            with acquire_home_lock(home):
                pass  # pragma: no cover - acquisition must fail
    message = str(excinfo.value)
    assert "another aiprofile refresh" in message
    # Default-output privacy rule (frozen scope guards): lock errors are
    # path-free and repository-name-free - the holder is described
    # generically, never by where its home lives.
    assert str(home) not in message
    assert str(tmp_path) not in message
    assert home.name not in message
    assert ".refresh.lock" not in message
    assert "Traceback" not in message

    # P1 reviewer regression: only lock-contention errno values may make
    # the stronger "another refresh" claim.  Exercise every portable
    # contention spelling through the platform's actual primitive hook.
    contention_errnos = {
        errno.EACCES,
        errno.EAGAIN,
        errno.EWOULDBLOCK,
        getattr(errno, "EDEADLK", errno.EAGAIN),
    }
    for err in sorted(contention_errnos):
        def contended(*_args, _err=err):
            raise OSError(_err, "contention-detail-canary")

        _replace_lock_primitive(monkeypatch, contended)
        with pytest.raises(LockError) as mapped:
            with acquire_home_lock(home):
                pass
        assert "another aiprofile refresh" in str(mapped.value)
        assert mapped.value.__cause__.errno == err

    def unavailable(*_args):
        raise OSError(errno.EIO, "locking-unavailable-detail-canary")

    _replace_lock_primitive(monkeypatch, unavailable)
    with pytest.raises(LockError) as unavailable_error:
        with acquire_home_lock(home):
            pass
    unavailable_message = str(unavailable_error.value)
    assert "refresh locking is unavailable" in unavailable_message
    assert "another aiprofile refresh" not in unavailable_message
    assert str(home) not in unavailable_message
    assert unavailable_error.value.__cause__.errno == errno.EIO


def test_cross_process_contention_is_nonblocking(tmp_path):
    home = tmp_path / "lock-canary-home-quokka-31"
    home.mkdir()
    ready = tmp_path / "holder-ready"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    holder = subprocess.Popen(
        [sys.executable, "-c", _HOLDER_SOURCE, str(home), str(ready)],
        env=env,
    )
    try:
        deadline = time.monotonic() + 30
        while not ready.exists():
            assert holder.poll() is None, "lock-holder subprocess died early"
            assert time.monotonic() < deadline, "lock holder never signalled ready"
            time.sleep(0.01)
        started = time.monotonic()
        with pytest.raises(LockError):
            with acquire_home_lock(home):
                pass  # pragma: no cover - acquisition must fail
        assert time.monotonic() - started < 5, "contended acquire must not block"
    finally:
        holder.terminate()
        holder.wait(timeout=30)
    # The OS releases the lock with the holder's death; a bounded poll
    # keeps this deterministic on platforms where the handle close is
    # observed a moment after process exit.
    deadline = time.monotonic() + 10
    while True:
        try:
            with acquire_home_lock(home):
                pass
            break
        except LockError:
            assert time.monotonic() < deadline, "lock not released after holder exit"
            time.sleep(0.05)


def test_stale_lock_file_from_dead_process_is_reacquirable(tmp_path):
    home = tmp_path / "lock-canary-home-quokka-31"
    home.mkdir()
    # A plain leftover file with no live locker: advisory OS lock, not
    # pid-file semantics, so this must not block anything.
    (home / ".refresh.lock").write_text("stale leftover", encoding="utf-8")
    with acquire_home_lock(home):
        pass


def test_release_failure_never_replaces_active_body_exception(tmp_path, monkeypatch):
    home = tmp_path / "lock-canary-home-quokka-31"
    home.mkdir()
    primitive_calls = 0
    close_calls = 0
    real_close = os.close

    def fail_release(*_args):
        nonlocal primitive_calls
        primitive_calls += 1
        if primitive_calls == 2:
            raise OSError(errno.EIO, "unlock-private-detail-canary")

    def fail_close(fd):
        nonlocal close_calls
        close_calls += 1
        real_close(fd)
        raise OSError(errno.EIO, "close-private-detail-canary")

    _replace_lock_primitive(monkeypatch, fail_release)
    monkeypatch.setattr(lock_mod.os, "close", fail_close)
    primary = IncompleteRollbackError(
        "partial-output-primary-canary",
        unrestored=("summary-light.svg",),
        unretracted=(),
    )

    with pytest.raises(IncompleteRollbackError) as excinfo:
        with acquire_home_lock(home):
            raise primary

    assert excinfo.value is primary
    assert close_calls == 1
    notes = getattr(excinfo.value, "__notes__", ())
    assert any("refresh locking is unavailable" in note for note in notes)
    assert all(str(home) not in note for note in notes)
    assert all("unlock-private-detail-canary" not in note for note in notes)
    assert all("close-private-detail-canary" not in note for note in notes)


def test_close_failure_after_success_is_path_free_lock_error(tmp_path, monkeypatch):
    home = tmp_path / "lock-canary-home-quokka-31"
    home.mkdir()
    close_calls = 0
    real_close = os.close

    def fail_close(fd):
        nonlocal close_calls
        close_calls += 1
        real_close(fd)
        raise OSError(errno.EIO, "close-private-detail-canary")

    monkeypatch.setattr(lock_mod.os, "close", fail_close)
    with pytest.raises(LockError) as excinfo:
        with acquire_home_lock(home):
            pass

    assert close_calls == 1
    assert "refresh locking is unavailable" in str(excinfo.value)
    assert str(home) not in str(excinfo.value)
    assert "close-private-detail-canary" not in str(excinfo.value)
    assert "close-private-detail-canary" in str(excinfo.value.__cause__)


def test_acquire_failure_is_not_masked_when_descriptor_close_fails(
    tmp_path, monkeypatch
):
    home = tmp_path / "lock-canary-home-quokka-31"
    home.mkdir()
    close_calls = 0
    real_close = os.close
    private_canary = f"{home}/close-private-path-canary"

    def contended(*_args):
        raise OSError(errno.EAGAIN, "primitive-contention-canary")

    def fail_close(fd):
        nonlocal close_calls
        close_calls += 1
        real_close(fd)
        raise OSError(errno.EIO, private_canary)

    _replace_lock_primitive(monkeypatch, contended)
    monkeypatch.setattr(lock_mod.os, "close", fail_close)

    with pytest.raises(LockError) as excinfo:
        with acquire_home_lock(home):
            pass

    assert close_calls == 1
    assert "another aiprofile refresh" in str(excinfo.value)
    assert excinfo.value.__cause__.errno == errno.EAGAIN
    notes = getattr(excinfo.value, "__notes__", ())
    assert any("descriptor close" in note for note in notes)
    assert all(private_canary not in note for note in notes)
    assert all(str(home) not in note for note in notes)


def _replace_lock_primitive(monkeypatch, replacement) -> None:
    if sys.platform == "win32":
        monkeypatch.setattr(lock_mod.msvcrt, "locking", replacement)
    else:
        monkeypatch.setattr(lock_mod.fcntl, "flock", replacement)

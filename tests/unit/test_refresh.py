"""Refresh service unit tests (v0.7.0 Tasks A2/A3/A5).

Planning is a pure function over Config (no I/O): excluded entries are
skipped fail-closed (duplicate-uid most-restrictive resolution included),
and duplicates - identical resolved paths or alias clones sharing a
repository_uid - are planned exactly once. Everything destined for
user-facing output identifies repositories by config ordinal and
aggregate counts only.
"""

from __future__ import annotations

import errno
import sys
from pathlib import Path

import pytest

import aiprofile.lockfile as lock_mod
from aiprofile import cli
from aiprofile.config import Config, RepoEntry, init_home, save_config
from aiprofile.errors import (
    ConfigError,
    IncompleteRollbackError,
    LockError,
    RefreshError,
    RefreshFailureState,
)
from aiprofile.lockfile import acquire_home_lock
from aiprofile.refresh import (
    RefreshFailure,
    RefreshItem,
    RefreshPlan,
    RefreshResult,
    plan_refresh,
    run_refresh,
)
from aiprofile.scanner import ScanSummary
from aiprofile.schema.vocab import PublicationLevel

EIGHT_NAMES = [
    "badge-dark.svg",
    "badge-light.svg",
    "dashboard.html",
    "heatmap-dark.svg",
    "heatmap-light.svg",
    "profile.json",
    "summary-dark.svg",
    "summary-light.svg",
]


def test_refresh_help_states_dry_run_coordination_exceptions(capsys):
    with pytest.raises(SystemExit) as raised:
        cli.main(["refresh", "--help"])

    assert raised.value.code == 0
    output = capsys.readouterr().out
    assert "configuration, recorded database content, or output assets" in output
    assert "lock and transient SQLite coordination state may change" in output
    assert "without writing to the profile home" not in output


def _entry(path: str, uid: str, level: PublicationLevel = PublicationLevel.FULL) -> RepoEntry:
    return RepoEntry(path=path, repository_uid=uid, publication_level=level)


def _config(entries: list[RepoEntry]) -> Config:
    return Config(identities=["fixture@example.com"], salt="s" * 64, repositories=entries)


def test_plan_includes_each_configured_repo_once(tmp_path):
    paths = [str(tmp_path / f"repo-{i}") for i in (1, 2, 3)]
    cfg = _config(
        [
            _entry(paths[0], "uid-1"),
            _entry(paths[1], "uid-2", PublicationLevel.AGGREGATE_ONLY),
            _entry(paths[2], "uid-3"),
        ]
    )
    plan = plan_refresh(cfg)
    assert [item.repository_uid for item in plan.items] == ["uid-1", "uid-2", "uid-3"]
    assert [item.path for item in plan.items] == paths
    assert [item.display_name for item in plan.items] == ["repo-1", "repo-2", "repo-3"]
    assert [item.ordinal for item in plan.items] == [1, 2, 3]
    assert plan.total_configured == 3
    assert plan.skipped_excluded == ()
    assert plan.skipped_duplicates == ()


def test_plan_skips_excluded_entries(tmp_path):
    # Entry 2 is directly excluded; entries 3 and 4 share a uid whose
    # most-restrictive resolution (config.resolve_publication_levels) is
    # excluded, so BOTH are skipped fail-closed even though entry 3 says
    # "full" on its own line.
    cfg = _config(
        [
            _entry(str(tmp_path / "kept"), "uid-kept"),
            _entry(str(tmp_path / "direct"), "uid-direct", PublicationLevel.EXCLUDED),
            _entry(str(tmp_path / "alias-a"), "uid-shared", PublicationLevel.FULL),
            _entry(str(tmp_path / "alias-b"), "uid-shared", PublicationLevel.EXCLUDED),
        ]
    )
    plan = plan_refresh(cfg)
    assert [item.repository_uid for item in plan.items] == ["uid-kept"]
    assert plan.skipped_excluded == (2, 3, 4)
    assert plan.skipped_duplicates == ()


def test_plan_dedupes_identical_resolved_paths(tmp_path):
    repo = tmp_path / "same-repo"
    cfg = _config(
        [
            _entry(str(repo), "uid-a"),
            # Trailing-separator variant of the same location: identical
            # once resolved, so scanning it twice would be pure churn.
            _entry(str(repo) + "\\" if "\\" in str(repo) else str(repo) + "/", "uid-a"),
        ]
    )
    plan = plan_refresh(cfg)
    assert len(plan.items) == 1
    assert plan.items[0].ordinal == 1
    assert plan.skipped_duplicates == (2,)
    assert plan.skipped_excluded == ()


def test_plan_rejects_same_path_with_different_repository_uids(tmp_path):
    repo = tmp_path / "same-repo"
    cfg = _config(
        [
            _entry(str(repo), "uid-current", PublicationLevel.AGGREGATE_ONLY),
            _entry(str(repo), "uid-stale", PublicationLevel.FULL),
        ]
    )

    with pytest.raises(ConfigError, match="one path to multiple identities"):
        plan_refresh(cfg)


def test_plan_dedupes_alias_paths_by_repository_uid(tmp_path):
    # Alias clones: distinct paths, same repository_uid. A second scan of
    # the same uid would atomically replace the first's rows - pointless
    # churn - so the first entry wins and the second is skipped.
    cfg = _config(
        [
            _entry(str(tmp_path / "clone-a"), "uid-alias"),
            _entry(str(tmp_path / "clone-b"), "uid-alias"),
        ]
    )
    plan = plan_refresh(cfg)
    assert [item.path for item in plan.items] == [str(tmp_path / "clone-a")]
    assert plan.skipped_duplicates == (2,)


def test_refresh_holds_home_lock(tmp_path, monkeypatch):
    """While run_refresh executes, the per-home lock is held: a concurrent
    acquire on the same home must raise LockError (observed from inside a
    monkeypatched scan hook, i.e. mid-run)."""
    home = tmp_path / "home"
    cfg, created = init_home(home, ["fixture@example.com"])
    assert created
    cfg.repositories.append(
        RepoEntry(
            path=str(tmp_path / "some-repo"),
            repository_uid="uid-1",
            publication_level=PublicationLevel.FULL,
        )
    )
    save_config(home, cfg)

    observed: dict[str, bool] = {}

    def fake_scan(home_arg, cfg_arg, conn, repo_path, *, make_full=False, recorded_at=None):
        try:
            with acquire_home_lock(home):
                observed["locked_during_run"] = False
        except LockError:
            observed["locked_during_run"] = True
        return ScanSummary(repository_uid="uid-1", display_name="some-repo")

    monkeypatch.setattr("aiprofile.scanner.scan_repository", fake_scan)
    result = run_refresh(home, tmp_path / "dist", generated_on="2026-06-01")
    assert result.ok
    assert observed["locked_during_run"] is True


# ---------------------------------------------------------------------------
# CLI wiring (Task A5): `aiprofile refresh` maps RefreshResult to exit
# codes and a default-output summary that follows the privacy rule -
# config ordinals, aggregate counts, and allowlisted asset filenames only.
# run_refresh is monkeypatched; these tests pin the mapping, not the run.
# ---------------------------------------------------------------------------


def _summary(uid: str, name: str, seen: int, kept: int, skipped: int, stored: int) -> ScanSummary:
    return ScanSummary(
        repository_uid=uid,
        display_name=name,
        commits_seen=seen,
        commits_kept=kept,
        commits_skipped_identity=skipped,
        events_stored=stored,
    )


def _success_result() -> RefreshResult:
    plan = RefreshPlan(
        items=(
            RefreshItem(1, "/x/cli-canary-alpha", "uid-a", "cli-canary-alpha"),
            RefreshItem(4, "/x/cli-canary-beta", "uid-b", "cli-canary-beta"),
        ),
        skipped_excluded=(2,),
        skipped_duplicates=(3,),
        total_configured=4,
    )
    return RefreshResult(
        plan=plan,
        summaries=(
            (1, _summary("uid-a", "cli-canary-alpha", 4, 3, 1, 5)),
            (4, _summary("uid-b", "cli-canary-beta", 2, 2, 0, 2)),
        ),
        failures=(),
        written=tuple(Path("dist") / name for name in EIGHT_NAMES),
    )


def test_cli_refresh_success_exit_zero_and_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AIPROFILE_HOME", str(tmp_path / "cli-home"))
    recorded = {}

    def fake_run_refresh(home, out_dir, *, dry_run=False, **kwargs):
        recorded["home"] = home
        recorded["out_dir"] = Path(out_dir)
        recorded["dry_run"] = dry_run
        return _success_result()

    monkeypatch.setattr("aiprofile.refresh.run_refresh", fake_run_refresh)
    rc = cli.main(["refresh", "--out", str(tmp_path / "dist")])
    captured = capsys.readouterr()
    assert rc == 0
    assert recorded["dry_run"] is False
    assert recorded["out_dir"] == tmp_path / "dist"
    assert "repository 1/4: 4 commits seen, 3 by configured identities" in captured.out
    assert "(1 skipped), 5 records stored" in captured.out
    assert "repository 4/4: 2 commits seen" in captured.out
    assert "skipped: 1 excluded, 1 duplicate" in captured.out
    for name in EIGHT_NAMES:
        assert name in captured.out
    # Default-output privacy rule: no path, basename, or display name.
    combined = captured.out + captured.err
    assert "cli-canary-alpha" not in combined
    assert "cli-canary-beta" not in combined
    assert "/x/" not in combined
    assert str(tmp_path / "dist") not in combined


def test_cli_refresh_partial_failure_exit_one(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AIPROFILE_HOME", str(tmp_path / "cli-home"))
    plan = RefreshPlan(
        items=(
            RefreshItem(1, "/x/cli-canary-alpha", "uid-a", "cli-canary-alpha"),
            RefreshItem(2, "/x/cli-canary-beta", "uid-b", "cli-canary-beta"),
        ),
        skipped_excluded=(),
        skipped_duplicates=(),
        total_configured=2,
    )
    result = RefreshResult(
        plan=plan,
        summaries=((1, _summary("uid-a", "cli-canary-alpha", 4, 3, 1, 5)),),
        failures=(RefreshFailure(ordinal=2),),
        written=(),
    )
    monkeypatch.setattr("aiprofile.refresh.run_refresh", lambda *a, **k: result)
    rc = cli.main(["refresh", "--out", str(tmp_path / "dist")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "repository 2 of 2 failed" in captured.err
    assert "no assets were published" in captured.err
    combined = captured.out + captured.err
    assert "cli-canary-alpha" not in combined
    assert "cli-canary-beta" not in combined
    assert "/x/" not in combined


def test_cli_refresh_dry_run_exit_zero_reports_changes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AIPROFILE_HOME", str(tmp_path / "cli-home"))
    plan = RefreshPlan(
        items=(RefreshItem(1, "/x/cli-canary-alpha", "uid-a", "cli-canary-alpha"),),
        skipped_excluded=(),
        skipped_duplicates=(),
        total_configured=1,
    )
    success = RefreshResult(
        plan=plan,
        summaries=((1, _summary("uid-a", "cli-canary-alpha", 4, 4, 0, 4)),),
        failures=(),
        written=(),
        dry_run=True,
        changed=("dashboard.html", "profile.json"),
    )
    recorded = {}

    def fake_run_refresh(home, out_dir, *, dry_run=False, **kwargs):
        recorded["dry_run"] = dry_run
        return success

    monkeypatch.setattr("aiprofile.refresh.run_refresh", fake_run_refresh)
    rc = cli.main(["refresh", "--out", str(tmp_path / "dist"), "--dry-run"])
    captured = capsys.readouterr()
    assert rc == 0
    assert recorded["dry_run"] is True
    assert "would update: dashboard.html" in captured.out
    assert "would update: profile.json" in captured.out
    assert "cli-canary-alpha" not in captured.out + captured.err

    # Dry-run with scan failures exits 1.
    failing = RefreshResult(
        plan=plan,
        summaries=(),
        failures=(RefreshFailure(ordinal=1),),
        written=(),
        dry_run=True,
    )
    monkeypatch.setattr("aiprofile.refresh.run_refresh", lambda *a, **k: failing)
    rc = cli.main(["refresh", "--out", str(tmp_path / "dist"), "--dry-run"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "repository 1 of 1 failed" in captured.err


def test_cli_refresh_locked_home_exit_one(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AIPROFILE_HOME", str(tmp_path / "cli-home"))

    def raise_locked(*args, **kwargs):
        raise LockError(
            "another aiprofile refresh is running against this profile home;"
            " wait for it to finish and retry"
        )

    monkeypatch.setattr("aiprofile.refresh.run_refresh", raise_locked)
    rc = cli.main(["refresh", "--out", str(tmp_path / "dist")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "another aiprofile refresh is running" in captured.err

    # P1 reviewer regression: structured partial-publication state maps to
    # an honest, path-free default message; -v retains the chained local
    # exporter detail.
    private_path = str(tmp_path / "private-output-canary")
    cause = IncompleteRollbackError(
        f"cannot write assets to {private_path}: injected failure",
        unrestored=("summary-light.svg",),
        unretracted=(),
    )

    def raise_partial(*_args, **_kwargs):
        raise RefreshError(RefreshFailureState.PARTIAL_OUTPUT) from cause

    monkeypatch.setattr("aiprofile.refresh.run_refresh", raise_partial)
    rc = cli.main(["refresh", "--out", private_path])
    captured = capsys.readouterr()
    assert rc == 1
    assert "partial generated assets or recovery backups may remain" in captured.err
    assert private_path not in captured.err
    assert "Traceback" not in captured.err

    rc_verbose = cli.main(["-v", "refresh", "--out", private_path])
    captured_verbose = capsys.readouterr()
    assert rc_verbose == 1
    assert "Traceback" in captured_verbose.err
    assert private_path in captured_verbose.err

    # A generation that completed before lock __exit__ failed must never be
    # described as unpublished.
    home = tmp_path / "home"
    cfg, created = init_home(home, ["fixture@example.com"])
    assert created
    plan = plan_refresh(cfg)

    class FailingExitLock:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            raise OSError("lock-release-detail-canary")

    published = RefreshResult(
        plan=plan,
        summaries=(),
        failures=(),
        written=(tmp_path / "dist" / "profile.json",),
    )
    monkeypatch.setattr("aiprofile.refresh.acquire_home_lock", lambda _home: FailingExitLock())
    monkeypatch.setattr("aiprofile.refresh._run_real", lambda *_a, **_k: published)

    with pytest.raises(RefreshError) as excinfo:
        run_refresh(home, tmp_path / "dist")
    assert excinfo.value.state is RefreshFailureState.PUBLISHED_FINALIZATION_FAILED
    assert "generation was published" in str(excinfo.value)
    assert "no new asset generation" not in str(excinfo.value)
    assert "lock-release-detail-canary" in str(excinfo.value.__cause__)

    # A release failure must not replace an active incomplete rollback:
    # the CLI must keep the honest partial-output state as the primary error.
    primitive_calls = 0

    def fail_real_unlock(*_args):
        nonlocal primitive_calls
        primitive_calls += 1
        if primitive_calls == 2:
            raise OSError(errno.EIO, "unlock-private-detail-canary")

    if sys.platform == "win32":
        monkeypatch.setattr(lock_mod.msvcrt, "locking", fail_real_unlock)
    else:
        monkeypatch.setattr(lock_mod.fcntl, "flock", fail_real_unlock)

    def raise_incomplete(*_args, **_kwargs):
        raise cause

    monkeypatch.setattr("aiprofile.refresh._run_real", raise_incomplete)
    monkeypatch.setattr("aiprofile.refresh.acquire_home_lock", acquire_home_lock)
    monkeypatch.setattr("aiprofile.refresh.run_refresh", run_refresh)
    monkeypatch.setenv("AIPROFILE_HOME", str(home))

    rc = cli.main(["refresh", "--out", private_path])
    captured = capsys.readouterr()
    assert rc == 1
    assert "partial generated assets or recovery backups may remain" in captured.err
    assert private_path not in captured.err
    assert "unlock-private-detail-canary" not in captured.err

    primitive_calls = 0
    rc_verbose = cli.main(["-v", "refresh", "--out", private_path])
    captured_verbose = capsys.readouterr()
    assert rc_verbose == 1
    assert "partial generated assets or recovery backups may remain" in captured_verbose.err
    assert "Additional lock release failure" in captured_verbose.err
    assert "unlock-private-detail-canary" not in captured_verbose.err

    # A descriptor-close failure after a successful publication is also
    # normalized: default output stays path-free and -v retains the cause.
    if sys.platform == "win32":
        monkeypatch.setattr(lock_mod.msvcrt, "locking", lambda *_args: None)
    else:
        monkeypatch.setattr(lock_mod.fcntl, "flock", lambda *_args: None)
    real_close = lock_mod.os.close
    close_calls = 0

    def fail_real_close(fd):
        nonlocal close_calls
        close_calls += 1
        real_close(fd)
        raise OSError(errno.EIO, "close-private-detail-canary")

    monkeypatch.setattr(lock_mod.os, "close", fail_real_close)
    monkeypatch.setattr("aiprofile.refresh._run_real", lambda *_a, **_k: published)

    rc = cli.main(["refresh", "--out", private_path])
    captured = capsys.readouterr()
    assert rc == 1
    assert "generation was published" in captured.err
    assert private_path not in captured.err
    assert "close-private-detail-canary" not in captured.err

    rc_verbose = cli.main(["-v", "refresh", "--out", private_path])
    captured_verbose = capsys.readouterr()
    assert rc_verbose == 1
    assert "generation was published" in captured_verbose.err
    assert "close-private-detail-canary" in captured_verbose.err
    assert close_calls == 2

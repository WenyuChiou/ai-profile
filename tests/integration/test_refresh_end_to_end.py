"""Refresh service end-to-end (v0.7.0 Tasks A3/A4).

Exercises the library-level ``run_refresh`` against real fixture git
repositories (built with helpers.build_repo): success publishes exactly
the eight-file bundle, any scan failure publishes NOTHING (pre-existing
output bytes untouched, no debris), reruns with an injected generation
date are byte-identical, and dry-run mutates nothing while reporting
allowlisted changed filenames only.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import FIXTURE_AUTHOR_EMAIL, FIXTURE_AUTHOR_NAME, build_repo

import aiprofile.export as export_mod
import aiprofile.scanner as scanner_mod
from aiprofile import cli, gitio
from aiprofile.config import RepoEntry, init_home, load_config, save_config
from aiprofile.errors import (
    IncompleteRollbackError,
    RefreshError,
    RefreshFailureState,
)
from aiprofile.refresh import run_refresh
from aiprofile.schema.vocab import PublicationLevel

#: The exact public bundle (export allowlist + profile.json), sorted.
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

#: Distinctive fixture basenames double as privacy canaries: failure
#: messages must never contain them (default-output privacy rule).
AI_REPO_NAME = "refresh-canary-ai-vault-77"
PLAIN_REPO_NAME = "refresh-canary-plain-vault-88"

GENERATED_ON = "2026-06-01"
RECORDED_AT = "2026-06-01T00:00:00+00:00"


def _ai_commits() -> list[tuple[str, str]]:
    return [
        (
            "Claude AI-* commit\n\n"
            "AI-Provider: Anthropic\n"
            "AI-Tool: Claude-Code\n"
            "AI-Role: implementation",
            "2026-05-02T10:00:00+00:00",
        ),
    ]


def _plain_commits() -> list[tuple[str, str]]:
    return [
        ("plain commit one", "2026-05-01T10:00:00+00:00"),
        ("plain commit two", "2026-05-03T10:00:00+00:00"),
    ]


def _setup_home(home: Path, repos: list[Path]) -> None:
    """Init an isolated home and register ``repos`` as full-publication
    entries, the way prior `aiprofile scan --full` runs would have."""
    cfg, created = init_home(home, [FIXTURE_AUTHOR_EMAIL])
    assert created
    for repo in repos:
        cfg.repositories.append(
            RepoEntry(
                path=str(repo.resolve()),
                repository_uid=gitio.repository_uid(repo, cfg.salt),
                publication_level=PublicationLevel.FULL,
            )
        )
    save_config(home, cfg)


def _build_two_repo_home(tmp_path: Path) -> tuple[Path, Path, Path]:
    home = tmp_path / "home"
    ai_repo = build_repo(tmp_path / AI_REPO_NAME, _ai_commits())
    plain_repo = build_repo(tmp_path / PLAIN_REPO_NAME, _plain_commits())
    _setup_home(home, [ai_repo, plain_repo])
    return home, ai_repo, plain_repo


def _read_all(directory: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}


def _rmtree_force(path: Path) -> None:
    """Windows-safe rmtree: git leaves read-only loose objects behind.

    ``onexc=`` is 3.12+; the supported floor is 3.11, so mirror the
    version-compatible onexc/onerror dispatch scripts/release_smoke.py's
    ``_cleanup_tmp`` uses (onerror passes an exc_info tuple instead).
    """

    def _clear_readonly(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_clear_readonly)
    else:
        shutil.rmtree(path, onerror=lambda f, p, ei: _clear_readonly(f, p, ei[1]))


def test_refresh_success_writes_exactly_eight_files(tmp_path):
    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    result = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert result.ok
    assert not result.failures
    assert sorted(p.name for p in out_dir.iterdir()) == EIGHT_NAMES
    assert sorted(p.name for p in result.written) == EIGHT_NAMES


def test_refresh_unknown_never_becomes_human(tmp_path):
    import json

    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    result = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert result.ok
    profile = json.loads((out_dir / "profile.json").read_text(encoding="utf-8"))
    # The trailer-free repo's two commits are UNKNOWN - never human.
    assert profile["totals"]["unknown_commits"] == 2
    assert profile["totals"]["human_declared_commits"] == 0
    assert profile["totals"]["ai_attributed_commits"] == 1


def test_refresh_partial_failure_never_publishes(tmp_path):
    home, _, plain_repo = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    out_dir.mkdir()
    sentinels = {}
    for name in EIGHT_NAMES:
        content = f"sentinel for {name}".encode()
        (out_dir / name).write_bytes(content)
        sentinels[name] = content

    _rmtree_force(plain_repo)  # repository 2 of 2 is now gone

    result = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert not result.ok
    messages = result.failure_messages()
    assert messages, "a failed refresh must describe its failures"
    assert any("repository 2 of 2 failed" in m for m in messages)
    combined = " ".join(messages)
    # Default-output privacy rule: config ordinal + aggregate count only.
    assert str(plain_repo) not in combined
    assert PLAIN_REPO_NAME not in combined
    assert str(tmp_path) not in combined

    # Nothing published, nothing staged: every sentinel byte-identical,
    # no temp/backup debris added alongside them.
    assert _read_all(out_dir) == sentinels
    assert sorted(p.name for p in out_dir.iterdir()) == EIGHT_NAMES


def test_refresh_is_deterministic_across_reruns(tmp_path, monkeypatch, capsys):
    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    first = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert first.ok
    first_bytes = _read_all(out_dir)
    second = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert second.ok
    assert _read_all(out_dir) == first_bytes
    assert sorted(first_bytes) == EIGHT_NAMES
    assert first.asset_manifest == second.asset_manifest
    assert [item.name for item in first.asset_manifest] == EIGHT_NAMES
    assert {
        item.name: item.sha256 for item in first.asset_manifest
    } == {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in first_bytes.items()
    }

    # P1 reviewer regression: real write_outputs fault injection through
    # run_refresh.  A failed install plus failed restore leaves a partial
    # generated asset and recovery backup, so the structured error must say
    # so without disclosing paths; the chained exporter cause keeps detail.
    old_summary = first_bytes["summary-light.svg"]
    real_replace = os.replace

    def incomplete_replace(src, dst):
        source, target = str(src), str(dst)
        if target.endswith("profile.json") and source.endswith(".tmp"):
            raise OSError("install-failure-detail-canary")
        if target.endswith("summary-light.svg") and source.endswith(".bak"):
            raise OSError("restore-failure-detail-canary")
        return real_replace(src, dst)

    monkeypatch.setattr(export_mod.os, "replace", incomplete_replace)
    with pytest.raises(RefreshError) as excinfo:
        run_refresh(
            home,
            out_dir,
            generated_on="2026-06-02",
            recorded_at=RECORDED_AT,
        )

    error = excinfo.value
    assert error.state is RefreshFailureState.PARTIAL_OUTPUT
    assert "partial generated assets or recovery backups may remain" in str(error)
    assert str(out_dir) not in str(error)
    assert (out_dir / "summary-light.svg").read_bytes() != old_summary
    recovery = list(out_dir.glob("summary-light.svg.*.bak"))
    assert len(recovery) == 1
    assert recovery[0].read_bytes() == old_summary
    assert isinstance(error.__cause__, IncompleteRollbackError)
    assert error.__cause__.unrestored == ("summary-light.svg",)
    assert error.__cause__.unretracted == ()
    assert str(out_dir) in str(error.__cause__)
    assert "restore-failure-detail-canary" in str(error.__cause__)

    # Exercise the CLI boundary with the same real exporter injection.
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    rc = cli.main(["refresh", "--out", str(out_dir)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "partial generated assets or recovery backups may remain" in captured.err
    assert str(out_dir) not in captured.out + captured.err
    assert "Traceback" not in captured.out + captured.err

    rc_verbose = cli.main(["-v", "refresh", "--out", str(out_dir)])
    captured_verbose = capsys.readouterr()
    assert rc_verbose == 1
    assert "Traceback" in captured_verbose.err
    assert str(out_dir) in captured_verbose.err
    assert "restore-failure-detail-canary" in captured_verbose.err


# ---------------------------------------------------------------------------
# Dry-run (Task A4): shadow home under the held lock, sqlite online-backup
# DB snapshot (WAL-safe), in-memory render, byte-diff against the real
# out_dir - and ZERO mutation of the real home and output directory.
# ---------------------------------------------------------------------------


def _home_files(home: Path) -> dict[str, tuple[int, bytes]]:
    """Mode-aware ``(mode, bytes)`` snapshot + listing of every file
    directly under ``home``.

    The lock file is exempted BY NAME (the plan's one sanctioned
    exemption): acquiring the advisory lock touches it by design.
    ``st_mode`` is platform-aware by construction: on POSIX it carries the
    real owner/group/other bits; on Windows ``os.chmod`` can only express
    the read-only attribute, so only that bit can ever differ - comparing
    before/after snapshots on the same platform is valid either way.
    """
    snapshot: dict[str, tuple[int, bytes]] = {}
    for p in sorted(home.iterdir()):
        if p.is_file() and p.name != ".refresh.lock":
            snapshot[p.name] = (stat.S_IMODE(p.stat().st_mode), p.read_bytes())
    return snapshot


def _append_ai_commit(repo: Path, author_date_iso: str) -> None:
    """One more AI-trailer commit on an existing fixture repo."""
    (repo / "extra.txt").write_text("dry-run extra content\n", encoding="utf-8")
    env = dict(os.environ)
    env["GIT_AUTHOR_NAME"] = FIXTURE_AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = FIXTURE_AUTHOR_EMAIL
    env["GIT_AUTHOR_DATE"] = author_date_iso
    env["GIT_COMMITTER_NAME"] = FIXTURE_AUTHOR_NAME
    env["GIT_COMMITTER_EMAIL"] = FIXTURE_AUTHOR_EMAIL
    env["GIT_COMMITTER_DATE"] = author_date_iso
    for args in (
        ["git", "add", "extra.txt"],
        [
            "git",
            "commit",
            "-q",
            "-m",
            "Another AI commit\n\nAI-Provider: Anthropic\nAI-Role: implementation",
        ],
    ):
        proc = subprocess.run(
            args, cwd=str(repo), env=env, capture_output=True, text=True, timeout=60
        )
        assert proc.returncode == 0, proc.stderr


def test_dry_run_mutates_nothing(tmp_path):
    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    first = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert first.ok

    home_before = _home_files(home)
    out_before = _read_all(out_dir)
    assert "config.json" in home_before and "aiprofile.db" in home_before

    result = run_refresh(
        home,
        out_dir,
        dry_run=True,
        generated_on=GENERATED_ON,
        recorded_at=RECORDED_AT,
    )
    assert result.ok
    assert result.dry_run
    assert result.written == ()

    # Every byte and both listings unchanged: no temp files, no shadow
    # debris, no DB sidecar creation in the real home.
    assert _home_files(home) == home_before
    assert _read_all(out_dir) == out_before


def _keep_existing_rows_during_dry_run(monkeypatch) -> None:
    """Replace the scan mutation only; snapshot/aggregate/render stay real."""

    def no_op_scan(_home, cfg, _conn, repo_path, **_kwargs):
        entry = next(repo for repo in cfg.repositories if repo.path == repo_path)
        return scanner_mod.ScanSummary(
            repository_uid=entry.repository_uid,
            display_name="dry-run fixture",
        )

    monkeypatch.setattr(scanner_mod, "scan_repository", no_op_scan)


def test_dry_run_wal_committed_data_is_seen_and_source_untouched(
    tmp_path, monkeypatch
):
    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    first = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert first.ok

    # Preserve the existing repository rows while exercising the real
    # snapshot/aggregate/render path.  The marker commit below is committed
    # into the -wal only; the dry-run can see it if and only if its shadow
    # snapshot is WAL-aware.  This fixture intentionally avoids ambiguous
    # same-path/different-uid configuration, which refresh rejects fail-closed.
    cfg = load_config(home)
    marker_uid = cfg.repositories[0].repository_uid
    _keep_existing_rows_during_dry_run(monkeypatch)

    db = home / "aiprofile.db"
    writer = sqlite3.connect(str(db))
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        writer.execute("PRAGMA wal_autocheckpoint=0")
        repo_id = writer.execute(
            "SELECT id FROM repositories WHERE repository_uid = ?", (marker_uid,)
        ).fetchone()[0]
        cur = writer.execute(
            "INSERT INTO commits (repository_id, sha, author_email, author_date)"
            " VALUES (?, ?, ?, ?)",
            (repo_id, "f" * 40, FIXTURE_AUTHOR_EMAIL, "2026-05-04T10:00:00+00:00"),
        )
        commit_id = cur.lastrowid
        writer.execute(
            "INSERT INTO events"
            " (event_id, repository_id, commit_id, actor_type, roles_json,"
            " evidence_level, activity_type, activity_timestamp, recorded_at,"
            " schema_version)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "wal-canary-event-1",
                repo_id,
                commit_id,
                "unknown",
                "[]",
                "unknown",
                "commit",
                "2026-05-04T10:00:00+00:00",
                RECORDED_AT,
                "0.3.0",
            ),
        )
        writer.commit()

        wal = Path(str(db) + "-wal")
        shm = Path(str(db) + "-shm")
        assert wal.exists() and wal.stat().st_size > 0
        assert shm.exists()
        db_before = db.read_bytes()
        wal_before = wal.read_bytes()
        shm_size_before = shm.stat().st_size
        home_listing_before = sorted(
            p.name for p in home.iterdir() if p.name != ".refresh.lock"
        )

        result = run_refresh(
            home,
            out_dir,
            dry_run=True,
            generated_on=GENERATED_ON,
            recorded_at=RECORDED_AT,
        )
        assert result.ok
        # The WAL-resident unknown commit changes the published totals:
        # visible if and only if the shadow snapshot included committed
        # -wal content (a raw main-file copy would report no change).
        assert "profile.json" in result.changed
        assert set(result.changed) <= set(EIGHT_NAMES)

        # Source untouched: main DB and -wal byte-identical (no write, no
        # checkpoint), listing unchanged. The -shm file is SQLite's
        # shared-memory wal-index: ANY WAL-aware reader - including the
        # mandated read-only backup connection - publishes its read mark
        # there, so byte-equality is unsatisfiable by construction; the
        # pinned properties are same file, same size, and the db/-wal
        # byte-equality above proving zero data mutation.
        assert db.read_bytes() == db_before
        assert wal.read_bytes() == wal_before
        assert shm.stat().st_size == shm_size_before
        assert (
            sorted(p.name for p in home.iterdir() if p.name != ".refresh.lock")
            == home_listing_before
        )
    finally:
        writer.close()


def test_dry_run_reports_only_allowlisted_changed_filenames(tmp_path):
    home, ai_repo, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    first = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert first.ok

    # out_dir is now stale: a new AI commit landed after the render.
    _append_ai_commit(ai_repo, "2026-05-05T10:00:00+00:00")

    result = run_refresh(
        home,
        out_dir,
        dry_run=True,
        generated_on=GENERATED_ON,
        recorded_at=RECORDED_AT,
    )
    assert result.ok
    changed = list(result.changed)
    assert changed, "a stale out_dir must report pending changes"
    assert changed == sorted(changed)
    assert set(changed) <= set(EIGHT_NAMES)
    assert "profile.json" in changed
    # Nothing else ever appears in `changed`: no paths, no repo names.
    for name in changed:
        assert "/" not in name and "\\" not in name
        assert AI_REPO_NAME not in name and PLAIN_REPO_NAME not in name


def test_dry_run_detects_no_change_as_empty(tmp_path):
    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    first = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert first.ok
    result = run_refresh(
        home,
        out_dir,
        dry_run=True,
        generated_on=GENERATED_ON,
        recorded_at=RECORDED_AT,
    )
    assert result.ok
    assert list(result.changed) == []


def test_dry_run_scan_failure_reports_and_mutates_nothing(tmp_path):
    home, _, plain_repo = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    first = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert first.ok

    home_before = _home_files(home)
    out_before = _read_all(out_dir)
    _rmtree_force(plain_repo)

    result = run_refresh(
        home,
        out_dir,
        dry_run=True,
        generated_on=GENERATED_ON,
        recorded_at=RECORDED_AT,
    )
    assert not result.ok
    messages = result.failure_messages()
    assert any("repository 2 of 2 failed" in m for m in messages)
    assert str(plain_repo) not in " ".join(messages)
    assert PLAIN_REPO_NAME not in " ".join(messages)
    assert result.changed == ()

    assert _home_files(home) == home_before
    assert _read_all(out_dir) == out_before


# ---------------------------------------------------------------------------
# P1-3 regression: scan_repository mutates its Config in-memory (upsert +
# uid migration) BEFORE persisting on success - so each refresh scan
# attempt must start from the last successfully persisted config, and a
# FAILED attempt's mutations must never ride along with a later
# successful scan's save_config.
# ---------------------------------------------------------------------------


def test_failed_scan_config_mutation_never_persisted_by_later_success(tmp_path):
    """Repo 1 carries a stale uid plus a dead alias sibling sharing it:
    its scan mutates the config (upsert re-derives the uid) and THEN
    fails in the fail-closed uid-migration step. Repo 2 then succeeds
    and persists config - which must NOT include repo 1's failed
    mutation: the old cached rows stay governed by the old (stale) uid
    entry exactly as scan's own commit-ordering contract promises."""
    home, ai_repo, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    stale_uid = "stale-uid-migration-canary"
    cfg = load_config(home)
    assert Path(cfg.repositories[0].path) == ai_repo.resolve()
    cfg.repositories[0].repository_uid = stale_uid
    cfg.repositories.append(
        RepoEntry(
            path=str(tmp_path / "gone-alias-clone"),
            repository_uid=stale_uid,
            publication_level=PublicationLevel.FULL,
        )
    )
    save_config(home, cfg)
    config_before = (home / "config.json").read_bytes()

    result = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert not result.ok
    assert [f.ordinal for f in result.failures] == [1]
    # repo 2's ordinal-2 scan succeeded (and saved config)...
    assert [ordinal for ordinal, _ in result.summaries] == [2]
    # ...but the failed repo-1 attempt's uid migration was not saved with
    # it: the persisted config is byte-identical to the pre-refresh state.
    cfg_after = load_config(home)
    assert cfg_after.repositories[0].repository_uid == stale_uid
    assert (home / "config.json").read_bytes() == config_before


def test_successful_uid_migration_governs_publication(tmp_path):
    """Companion pin for the P1-3 fix: when a stale-uid repo's scan
    SUCCEEDS (uid migrated and persisted), aggregation/privacy must be
    built from the FINAL persisted config - a fix that kept using the
    pre-scan config object would fail-closed-exclude the migrated uid
    and silently drop the repo from the published bundle."""
    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    cfg = load_config(home)
    cfg.repositories[0].repository_uid = "stale-uid-now-migrated"
    save_config(home, cfg)

    result = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert result.ok
    profile = json.loads((out_dir / "profile.json").read_text(encoding="utf-8"))
    assert profile["totals"]["commits_scanned"] == 3
    assert profile["totals"]["ai_attributed_commits"] == 1


# ---------------------------------------------------------------------------
# P1-4 regression: dry-run must never load - and therefore never
# retrofit-chmod - the REAL home. The only sanctioned real-home touches
# are the advisory lock file and the read-only backup connection's
# transient -shm read marks.
# ---------------------------------------------------------------------------


def test_dry_run_never_chmods_the_real_home(tmp_path, monkeypatch):
    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    first = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert first.ok

    real_chmod = os.chmod
    touched: list[Path] = []

    def recording_chmod(path, mode, *args, **kwargs):
        touched.append(Path(path))
        return real_chmod(path, mode, *args, **kwargs)

    monkeypatch.setattr(os, "chmod", recording_chmod)
    result = run_refresh(
        home,
        out_dir,
        dry_run=True,
        generated_on=GENERATED_ON,
        recorded_at=RECORDED_AT,
    )
    assert result.ok
    home_resolved = home.resolve()
    inside_home = [
        str(p) for p in touched if p.resolve().is_relative_to(home_resolved)
    ]
    assert inside_home == []  # shadow-home chmods are fine; real-home never


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only mode bits; Windows os.chmod only toggles the"
    " read-only attribute (see config._restrict_to_owner)",
)
def test_dry_run_preserves_relaxed_posix_modes(tmp_path):
    """A user who deliberately relaxed their home permissions must not
    have dry-run silently tighten them back (the retrofit chmod belongs
    to REAL loads only)."""
    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    first = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert first.ok
    os.chmod(home, 0o755)
    os.chmod(home / "config.json", 0o644)

    result = run_refresh(
        home,
        out_dir,
        dry_run=True,
        generated_on=GENERATED_ON,
        recorded_at=RECORDED_AT,
    )
    assert result.ok
    assert stat.S_IMODE(home.stat().st_mode) == 0o755
    assert stat.S_IMODE((home / "config.json").stat().st_mode) == 0o644


# ---------------------------------------------------------------------------
# P1-5 regression: the read-only snapshot URI must percent-encode the
# database path (Path.as_uri()), or a home containing URI metacharacters
# ('#' fragment, '?' query) silently reads - or even creates - a
# DIFFERENT file with mode=ro dropped.
# ---------------------------------------------------------------------------


def _insert_marker_rows(db: Path, uid: str) -> None:
    """Add a marker commit to an existing or deliberately stale uid."""
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute(
            "SELECT id FROM repositories WHERE repository_uid = ?", (uid,)
        ).fetchone()
        if row is None:
            repo_id = conn.execute(
                "INSERT INTO repositories"
                " (repository_uid, display_name, local_path, last_scanned_at)"
                " VALUES (?, ?, ?, ?)",
                (uid, "private-stale-name-canary", "private-stale-path-canary", RECORDED_AT),
            ).lastrowid
        else:
            repo_id = row[0]
        cur = conn.execute(
            "INSERT INTO commits (repository_id, sha, author_email, author_date)"
            " VALUES (?, ?, ?, ?)",
            (repo_id, "e" * 40, FIXTURE_AUTHOR_EMAIL, "2026-05-06T10:00:00+00:00"),
        )
        commit_id = cur.lastrowid
        conn.execute(
            "INSERT INTO events"
            " (event_id, repository_id, commit_id, actor_type, roles_json,"
            " evidence_level, activity_type, activity_timestamp, recorded_at,"
            " schema_version)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"marker-event-{uid}",
                repo_id,
                commit_id,
                "unknown",
                "[]",
                "unknown",
                "commit",
                "2026-05-06T10:00:00+00:00",
                RECORDED_AT,
                "0.3.0",
            ),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.mark.parametrize("dry_run", [False, True])
def test_refresh_rejects_same_path_different_uid_before_cache_or_output_mutation(
    tmp_path, dry_run, monkeypatch
):
    home, _, _ = _build_two_repo_home(tmp_path)
    out_dir = tmp_path / "dist"
    assert run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    ).ok

    cfg = load_config(home)
    cfg.repositories.append(
        RepoEntry(
            path=cfg.repositories[0].path,
            repository_uid="private-stale-uid-canary",
            publication_level=PublicationLevel.FULL,
        )
    )
    save_config(home, cfg)
    _insert_marker_rows(home / "aiprofile.db", "private-stale-uid-canary")
    home_before = _home_files(home)
    out_before = _read_all(out_dir)
    if dry_run:
        monkeypatch.setattr(
            "aiprofile.refresh._snapshot_database",
            lambda *_args: (_ for _ in ()).throw(
                AssertionError("database snapshot must follow plan validation")
            ),
        )

    with pytest.raises(RefreshError) as raised:
        run_refresh(
            home,
            out_dir,
            dry_run=dry_run,
            generated_on=GENERATED_ON,
            recorded_at=RECORDED_AT,
        )

    assert _home_files(home) == home_before
    assert _read_all(out_dir) == out_before
    message = str(raised.value)
    assert "private-stale" not in message
    assert AI_REPO_NAME not in message


def _assert_dry_run_reads_correct_db(
    tmp_path: Path, home_name: str, monkeypatch
) -> None:
    home = tmp_path / home_name
    ai_repo = build_repo(tmp_path / AI_REPO_NAME, _ai_commits())
    plain_repo = build_repo(tmp_path / PLAIN_REPO_NAME, _plain_commits())
    _setup_home(home, [ai_repo, plain_repo])
    out_dir = tmp_path / "dist"
    first = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert first.ok

    cfg = load_config(home)
    marker_uid = cfg.repositories[0].repository_uid
    _insert_marker_rows(home / "aiprofile.db", marker_uid)
    _keep_existing_rows_during_dry_run(monkeypatch)

    siblings_before = sorted(p.name for p in tmp_path.iterdir())
    home_before = sorted(p.name for p in home.iterdir() if p.name != ".refresh.lock")

    result = run_refresh(
        home,
        out_dir,
        dry_run=True,
        generated_on=GENERATED_ON,
        recorded_at=RECORDED_AT,
    )
    assert result.ok
    # Marker rows change the would-be totals: visible if and only if the
    # snapshot opened the correct database file.
    assert "profile.json" in result.changed
    assert set(result.changed) <= set(EIGHT_NAMES)
    # No prefix/sibling debris from a mis-parsed URI path.
    assert sorted(p.name for p in tmp_path.iterdir()) == siblings_before
    assert (
        sorted(p.name for p in home.iterdir() if p.name != ".refresh.lock")
        == home_before
    )


def test_dry_run_home_with_hash_character_reads_correct_db(tmp_path, monkeypatch):
    _assert_dry_run_reads_correct_db(tmp_path, "ai#profile home-42", monkeypatch)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="'?' is not a legal Windows filename character",
)
def test_dry_run_home_with_question_mark_reads_correct_db(tmp_path, monkeypatch):
    _assert_dry_run_reads_correct_db(tmp_path, "ai?profile-home-43", monkeypatch)


def test_refresh_wal_home_database_is_supported(tmp_path):
    """A home database left in WAL journal mode by an external tool must
    not break refresh (regression companion to the dry-run WAL test)."""
    home, _, _ = _build_two_repo_home(tmp_path)
    db = home / "aiprofile.db"
    conn = sqlite3.connect(str(db))
    try:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    finally:
        conn.close()
    out_dir = tmp_path / "dist"
    result = run_refresh(
        home, out_dir, generated_on=GENERATED_ON, recorded_at=RECORDED_AT
    )
    assert result.ok
    assert sorted(p.name for p in out_dir.iterdir()) == EIGHT_NAMES

"""Batch refresh service (v0.7.0, ADR-030): re-scan every configured
repository and republish the eight-file dist bundle atomically.

Application-layer orchestration in cli.py's layer - it sequences EXISTING
behavior (scan all -> aggregate once -> render once -> export once) and
adds no render or privacy behavior of its own. Allowed imports: scanner,
aggregate, privacy, render.*, export, config, storage, lockfile, errors
(architecture.md section 2); never any network module.

Default-output privacy rule (frozen scope guards): everything destined
for user-facing output identifies repositories by config ordinal and
aggregate counts only - no paths, no repository names, no basenames.
The dataclasses below may carry paths INTERNALLY for execution; callers
printing summaries must use ordinals and counts.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from . import scanner
from .aggregate import (
    compute_daily_commit_totals,
    compute_daily_provider_counts,
    compute_repo_aggregates,
)
from .config import Config, config_path, db_path, load_config, resolve_publication_levels
from .errors import (
    AiProfileError,
    IncompleteRollbackError,
    LockError,
    RefreshError,
    RefreshFailureState,
    StorageError,
    path_free_diagnostics,
)
from .export import write_outputs
from .lockfile import acquire_home_lock
from .privacy import build_viz_stats
from .render.badge_svg import render_badge
from .render.dashboard_html import render_dashboard
from .render.heatmap_svg import render_heatmap
from .render.summary_svg import render_summary
from .render.themes import THEMES
from .schema.vocab import PublicationLevel
from .storage.db import connect, migrate
from .viz import VizStats, dumps_stats


@dataclass(frozen=True)
class RefreshItem:
    """One repository to scan. ``path``/``display_name`` are execution-only
    detail - user-facing output uses ``ordinal`` (1-based config position)."""

    ordinal: int
    path: str
    repository_uid: str
    display_name: str


@dataclass(frozen=True)
class RefreshPlan:
    """Scan plan over a Config: each repository exactly once, excluded
    entries skipped fail-closed, duplicates/aliases deduped in config
    order. Skip lists carry config ordinals only (printable as-is)."""

    items: tuple[RefreshItem, ...]
    skipped_excluded: tuple[int, ...]
    skipped_duplicates: tuple[int, ...]
    total_configured: int


def plan_refresh(cfg: Config) -> RefreshPlan:
    """Pure planning over ``cfg`` (no I/O).

    Skip order per entry: excluded first (fail-closed via
    ``resolve_publication_levels`` - a uid absent from the resolution is
    excluded, and duplicate uids resolve most-restrictive), then
    resolved-path dedupe, then uid (alias-clone) dedupe. A second scan of
    an already-planned uid would atomically replace the first's rows -
    pointless churn - so the first config entry always wins.
    """
    levels = resolve_publication_levels(cfg)
    items: list[RefreshItem] = []
    skipped_excluded: list[int] = []
    skipped_duplicates: list[int] = []
    seen_paths: set[str] = set()
    seen_uids: set[str] = set()
    for ordinal, entry in enumerate(cfg.repositories, start=1):
        level = levels.get(entry.repository_uid, PublicationLevel.EXCLUDED)
        if level is PublicationLevel.EXCLUDED:
            skipped_excluded.append(ordinal)
            continue
        resolved = Path(entry.path).resolve()
        key = str(resolved)
        if key in seen_paths or entry.repository_uid in seen_uids:
            skipped_duplicates.append(ordinal)
            continue
        seen_paths.add(key)
        seen_uids.add(entry.repository_uid)
        items.append(
            RefreshItem(
                ordinal=ordinal,
                path=entry.path,
                repository_uid=entry.repository_uid,
                display_name=resolved.name,
            )
        )
    return RefreshPlan(
        items=tuple(items),
        skipped_excluded=tuple(skipped_excluded),
        skipped_duplicates=tuple(skipped_duplicates),
        total_configured=len(cfg.repositories),
    )


@dataclass(frozen=True)
class RefreshFailure:
    """A failed per-repository scan, identified by config ordinal ONLY -
    the underlying error text may contain paths (GitError does by
    contract), so it is deliberately not carried here."""

    ordinal: int


@dataclass(frozen=True)
class RefreshResult:
    """Outcome of one refresh run. ``summaries`` pairs each scanned
    repository's config ordinal with its ScanSummary (whose count fields
    are printable; its display_name is not, in default output)."""

    plan: RefreshPlan
    summaries: tuple[tuple[int, scanner.ScanSummary], ...]
    failures: tuple[RefreshFailure, ...]
    written: tuple[Path, ...]
    dry_run: bool = False
    #: dry-run only: allowlisted output names whose bytes would change.
    changed: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        return not self.failures

    def failure_messages(self) -> list[str]:
        """Path-free, repository-name-free failure lines (default-output
        privacy rule): config ordinal + aggregate count only."""
        total = self.plan.total_configured
        return [f"repository {f.ordinal} of {total} failed" for f in self.failures]


def build_assets(stats: VizStats) -> dict[str, str]:
    """The seven rendered public assets (export adds profile.json as the
    eighth). Shared verbatim by `aiprofile render` and refresh so the two
    paths cannot drift."""
    light, dark = THEMES["github-light"], THEMES["github-dark"]
    return {
        "summary-light.svg": render_summary(stats, light),
        "summary-dark.svg": render_summary(stats, dark),
        "heatmap-light.svg": render_heatmap(stats, light),
        "heatmap-dark.svg": render_heatmap(stats, dark),
        "badge-light.svg": render_badge(stats, light),
        "badge-dark.svg": render_badge(stats, dark),
        "dashboard.html": render_dashboard(stats),
    }


def run_refresh(
    home: Path,
    out_dir: Path,
    *,
    dry_run: bool = False,
    verbose: bool = False,
    generated_on: str | None = None,
    recorded_at: str | None = None,
) -> RefreshResult:
    """Re-scan every planned repository, then publish the eight-file
    bundle exactly once - and only if EVERY scan succeeded (all-or-
    nothing: a partial failure publishes nothing and leaves any existing
    output bytes untouched).

    The per-home lock is held for the entire run (dry-run included).
    """
    out_dir = Path(out_dir)
    publication_completed = False
    try:
        # Lower layers retain their existing path-rich local diagnostics for
        # scan/render commands.  Refresh alone tightens the default boundary;
        # -v restores detail and the CLI prints the chained traceback.
        with path_free_diagnostics(not verbose):
            with acquire_home_lock(home):
                generated = generated_on or datetime.now(UTC).strftime("%Y-%m-%d")
                recorded = recorded_at or datetime.now(UTC).isoformat(
                    timespec="seconds"
                )
                # Dry-run must branch BEFORE load_config(real_home): that
                # function intentionally retrofits permissions, which would
                # violate the zero-mutation contract even if file bytes stay
                # unchanged.
                if dry_run:
                    return _run_dry(home, out_dir, generated, recorded)
                cfg = load_config(home)
                plan = plan_refresh(cfg)
                result = _run_real(home, out_dir, plan, generated, recorded)
                publication_completed = bool(result.written)
                return result
    except IncompleteRollbackError as exc:
        raise RefreshError(RefreshFailureState.PARTIAL_OUTPUT) from exc
    except LockError as exc:
        # LockError messages are already path-free; preserve their actionable
        # distinction before publication.  After completed publication, an
        # unlock/finalization failure needs the honest published outcome.
        if publication_completed:
            raise RefreshError(
                RefreshFailureState.PUBLISHED_FINALIZATION_FAILED
            ) from exc
        raise
    except Exception as exc:
        state = (
            RefreshFailureState.PUBLISHED_FINALIZATION_FAILED
            if publication_completed
            else RefreshFailureState.NOT_PUBLISHED
        )
        raise RefreshError(state) from exc


def _scan_all(
    home: Path,
    conn,
    plan: RefreshPlan,
    recorded: str,
) -> tuple[list[tuple[int, scanner.ScanSummary]], list[RefreshFailure]]:
    """Scan phase: every planned item is attempted (a failure never hides
    later failures); never ``--full`` - refresh never changes publication
    policy."""
    summaries: list[tuple[int, scanner.ScanSummary]] = []
    failures: list[RefreshFailure] = []
    for item in plan.items:
        try:
            # scan_repository mutates Config in memory before its config-last
            # save.  A fresh persisted load per attempt guarantees a failed
            # attempt's mutation cannot ride along with a later success.
            cfg = load_config(home)
            summary = scanner.scan_repository(
                home, cfg, conn, item.path, make_full=False, recorded_at=recorded
            )
        except AiProfileError:
            failures.append(RefreshFailure(ordinal=item.ordinal))
            continue
        summaries.append((item.ordinal, summary))
    return summaries, failures


def _run_real(
    home: Path,
    out_dir: Path,
    plan: RefreshPlan,
    generated: str,
    recorded: str,
) -> RefreshResult:
    conn = connect(db_path(home))
    try:
        migrate(conn)
        summaries, failures = _scan_all(home, conn, plan, recorded)
        if failures:
            return RefreshResult(
                plan=plan,
                summaries=tuple(summaries),
                failures=tuple(failures),
                written=(),
            )
        repo_aggs = compute_repo_aggregates(conn)
        daily_rows = compute_daily_provider_counts(conn)
        totals_rows = compute_daily_commit_totals(conn)
    finally:
        conn.close()
    # Successful scans may migrate repository uids.  Publication policy must
    # therefore come from the final persisted config, never the pre-scan plan.
    final_cfg = load_config(home)
    stats = build_viz_stats(
        repo_aggs,
        final_cfg,
        generated_on=generated,
        daily_rows=daily_rows,
        totals_rows=totals_rows,
    )
    written = write_outputs(stats, build_assets(stats), out_dir)
    return RefreshResult(
        plan=plan,
        summaries=tuple(summaries),
        failures=(),
        written=tuple(written),
    )


def _snapshot_database(real_db: Path, shadow_db: Path) -> None:
    """WAL-safe consistent snapshot via sqlite3's online backup API.

    The source is opened READ-ONLY and copied with ``Connection.backup``,
    which yields a transactionally consistent snapshot INCLUDING committed
    WAL content - never a raw copy of the main file (a WAL database's
    committed state can live entirely in the ``-wal`` sidecar, so a bare
    file copy silently drops data). Reading a WAL database updates
    SQLite's shared-memory read marks in the ``-shm`` wal-index; the main
    database and ``-wal`` bytes are never written.
    """
    try:
        source_uri = real_db.resolve().as_uri() + "?mode=ro"
        source = sqlite3.connect(source_uri, uri=True)
        try:
            shadow_conn = sqlite3.connect(str(shadow_db))
            try:
                source.backup(shadow_conn)
            finally:
                shadow_conn.close()
        finally:
            source.close()
    except sqlite3.Error as exc:
        raise StorageError(f"dry-run database snapshot failed: {exc}") from exc


def _run_dry(home: Path, out_dir: Path, generated: str, recorded: str) -> RefreshResult:
    """Faithful dry-run under the already-held home lock: build a shadow
    home (config copy + backup-API DB snapshot), scan into the SHADOW,
    render in memory, and byte-diff against the real ``out_dir``. The
    real home and output directory are never written."""
    with tempfile.TemporaryDirectory(prefix="aiprofile-dry-run-") as tmp:
        shadow = Path(tmp) / "home"
        shadow.mkdir()
        shutil.copyfile(config_path(home), config_path(shadow))
        real_db = db_path(home)
        if real_db.exists():
            _snapshot_database(real_db, db_path(shadow))
        cfg = load_config(shadow)
        plan = plan_refresh(cfg)
        conn = connect(db_path(shadow))
        try:
            migrate(conn)
            summaries, failures = _scan_all(shadow, conn, plan, recorded)
            if failures:
                return RefreshResult(
                    plan=plan,
                    summaries=tuple(summaries),
                    failures=tuple(failures),
                    written=(),
                    dry_run=True,
                )
            repo_aggs = compute_repo_aggregates(conn)
            daily_rows = compute_daily_provider_counts(conn)
            totals_rows = compute_daily_commit_totals(conn)
        finally:
            conn.close()
        final_cfg = load_config(shadow)
        stats = build_viz_stats(
            repo_aggs,
            final_cfg,
            generated_on=generated,
            daily_rows=daily_rows,
            totals_rows=totals_rows,
        )
        # In-memory render + byte-diff against the real out_dir, encoded
        # exactly as export writes (UTF-8, "\n" newlines - write_outputs
        # opens with newline="\n", so the rendered strings' bytes ARE the
        # published bytes). Missing file = changed. The report draws from
        # the closed eight-name set only.
        targets = build_assets(stats)
        targets["profile.json"] = dumps_stats(stats)
        changed = []
        for name in sorted(targets):
            current = out_dir / name
            if not current.is_file() or current.read_bytes() != targets[name].encode("utf-8"):
                changed.append(name)
        return RefreshResult(
            plan=plan,
            summaries=tuple(summaries),
            failures=(),
            written=(),
            dry_run=True,
            changed=tuple(changed),
        )

"""CLI wiring (ADR-002): init / scan / aggregate / render.

Exit codes: 0 success, 1 operational error, 2 usage. `aggregate` prints
exactly the published contract - it IS the v0.1 privacy preview
(mvp.md section 2); `-v` adds clearly-marked local-only detail.
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

from . import __version__, attestations, provenance, refresh
from .aggregate import (
    compute_daily_commit_totals,
    compute_daily_provider_counts,
    compute_repo_aggregates,
)
from .config import aiprofile_home, db_path, init_home, load_config
from .errors import AiProfileError
from .export import write_outputs
from .lockfile import acquire_home_lock
from .privacy import build_viz_stats, local_only_details
from .scanner import scan_repository
from .schedule import service as schedule_service
from .storage.db import connect, migrate
from .viz import VizStats


def _is_inside_git_worktree(path: Path) -> bool:
    """True if ``path`` (or any ancestor) contains a ``.git`` entry.

    Pure path walk, deliberately not a ``git`` subprocess call (unlike
    gitio.py's identity/uid helpers): this check runs unconditionally on
    every ``aiprofile init``, including against paths that are not git
    repositories at all (the common case - AIPROFILE_HOME normally lives
    outside any repo), so shelling out would mean a hard, always-paid git
    dependency at init time for what is fundamentally a filesystem
    question. It also keeps this concern out of config.py, which
    documents itself as deliberately git-free.

    A ``.git`` entry may be a directory (an ordinary repository) or a
    file (a worktree's or submodule's gitdir pointer) - either shape
    means "inside a work tree" for our purposes, so we only need to
    check existence, never open or parse it.
    """
    resolved = path.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        return args.func(args)
    except AiProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aiprofile",
        description=(
            "Local-first, profile-level AI collaboration analytics:"
            " explicit git provenance in, privacy-safe SVG/HTML/JSON out."
        ),
    )
    parser.add_argument("--version", action="version", version=f"aiprofile {__version__}")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="verbose output (local-only detail)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create AIPROFILE_HOME (config + salt + db)")
    p_init.set_defaults(func=_cmd_init)

    p_scan = sub.add_parser("scan", help="register and scan one local git repository")
    p_scan.add_argument("path", help="path to a local git repository")
    p_scan.add_argument(
        "--full",
        action="store_true",
        help=(
            "set this repository's publication level to 'full' (explicitly"
            " publishable - a policy decision, not a visibility claim);"
            " default is aggregate_only and a repeat scan never downgrades"
        ),
    )
    p_scan.set_defaults(func=_cmd_scan)

    p_agg = sub.add_parser(
        "aggregate",
        help="compute and print the published profile stats (the privacy preview)",
    )
    p_agg.set_defaults(func=_cmd_aggregate)

    p_render = sub.add_parser(
        "render",
        help="write dist/ assets (SVG light/dark + interactive HTML + JSON)",
        description=(
            "Write the summary/heatmap/badge SVG pairs, self-contained interactive"
            " dashboard, and profile.json as one bundle. Run ONE render at a time"
            " per output directory:"
            " concurrent renders into the same directory are unsupported and"
            " can publish a mixed generation."
        ),
    )
    p_render.add_argument("--out", default="dist", help="output directory (default: ./dist)")
    p_render.set_defaults(func=_cmd_render)

    p_refresh = sub.add_parser(
        "refresh",
        help="re-scan every configured repository and republish the dist bundle",
        description=(
            "Batch re-scan of every configured repository, then republish the"
            " eight-file dist bundle. A pre-publication failure publishes"
            " nothing; an incomplete filesystem rollback is reported honestly."
            " Runs one refresh at a time per profile home (a second invocation"
            " fails fast). Never commits, never pushes, never touches the"
            " network."
        ),
    )
    p_refresh.add_argument("--out", default="dist", help="output directory (default: ./dist)")
    p_refresh.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "report which outputs would change without changing configuration,"
            " recorded database content, or output assets; the advisory lock"
            " and transient SQLite coordination state may change"
        ),
    )
    p_refresh.set_defaults(func=_cmd_refresh)

    p_schedule = sub.add_parser("schedule", help="manage automatic daily local profile refresh")
    schedule_sub = p_schedule.add_subparsers(dest="schedule_command", required=True)
    p_schedule_install = schedule_sub.add_parser(
        "install", help="install or update the native user schedule"
    )
    p_schedule_install.add_argument("--profile-repo", required=True)
    p_schedule_install.add_argument(
        "--time",
        required=True,
        type=_schedule_time,
        help="daily local time in HH:MM form",
    )
    p_schedule_install.add_argument(
        "--no-push",
        action="store_true",
        help="create the local exact-eight commit but skip the remote push",
    )
    p_schedule_install.add_argument("--dry-run", action="store_true")
    p_schedule_install.set_defaults(func=_cmd_schedule_install)

    p_schedule_status = schedule_sub.add_parser(
        "status", help="show native scheduler and last-run status"
    )
    p_schedule_status.add_argument("--dry-run", action="store_true")
    p_schedule_status.set_defaults(func=_cmd_schedule_status)

    p_schedule_remove = schedule_sub.add_parser(
        "remove", help="remove only aiprofile-owned scheduler artifacts"
    )
    p_schedule_remove.add_argument("--dry-run", action="store_true")
    p_schedule_remove.set_defaults(func=_cmd_schedule_remove)

    p_reconcile = sub.add_parser("reconcile", help="manage private, per-commit AI declarations")
    reconcile_sub = p_reconcile.add_subparsers(dest="reconcile_command", required=True)
    p_add = reconcile_sub.add_parser("add", help="confirm AI participation in one reachable commit")
    p_add.add_argument("--repo", required=True)
    p_add.add_argument("--sha", required=True)
    p_add.add_argument("--provider")
    p_add.add_argument("--tool")
    p_add.add_argument(
        "--mode", choices=("ai_assisted", "ai_generated", "ai_reviewed"), default="ai_assisted"
    )
    p_add.add_argument("--confirm-ai", action="store_true", required=True)
    p_add.set_defaults(func=_cmd_reconcile_add)
    p_remove = reconcile_sub.add_parser("remove", help="remove one private declaration")
    p_remove.add_argument("--repo", required=True)
    p_remove.add_argument("--sha", required=True)
    p_remove.add_argument("--confirm-remove", action="store_true", required=True)
    p_remove.set_defaults(func=_cmd_reconcile_remove)
    p_list = reconcile_sub.add_parser("list", help="count private declarations")
    p_list.set_defaults(func=_cmd_reconcile_list)
    p_sync = reconcile_sub.add_parser(
        "sync-github", help="sync complete private ledger to a Profile Actions secret"
    )
    p_sync.add_argument("--profile-repo", required=True)
    p_sync.add_argument("--confirm-sync", action="store_true", required=True)
    p_sync.set_defaults(func=_cmd_reconcile_sync)

    p_prov = sub.add_parser("provenance", help="opt-in commit-time AI provenance")
    prov_sub = p_prov.add_subparsers(dest="provenance_command", required=True)
    p_mark = prov_sub.add_parser("mark", help="bind one AI declaration to HEAD and staged tree")
    p_mark.add_argument("--repo", default=".")
    p_mark.add_argument("--provider")
    p_mark.add_argument("--tool")
    p_mark.add_argument(
        "--mode", choices=("AI-Assisted", "AI-Generated", "AI-Reviewed"), default="AI-Assisted"
    )
    p_mark.add_argument("--confirm-ai", action="store_true", required=True)
    p_mark.set_defaults(func=_cmd_provenance_mark)
    p_clear = prov_sub.add_parser("clear", help="discard a pending one-commit mark")
    p_clear.add_argument("--repo", default=".")
    p_clear.set_defaults(func=_cmd_provenance_clear)
    p_doctor = prov_sub.add_parser("doctor", help="inspect hook and recent evidence status")
    p_doctor.add_argument("--repo", default=".")
    p_doctor.add_argument("--recent", type=int, default=30)
    p_doctor.set_defaults(func=_cmd_provenance_doctor)
    p_hooks = prov_sub.add_parser("hook", help="install optional non-overwriting Git hooks")
    hooks_sub = p_hooks.add_subparsers(dest="hook_command", required=True)
    p_hook_install = hooks_sub.add_parser("install")
    p_hook_install.add_argument("--repo", default=".")
    p_hook_install.set_defaults(func=_cmd_provenance_hook_install)
    p_hook_run = prov_sub.add_parser("hook-run", help=argparse.SUPPRESS)
    p_hook_run.add_argument("phase", choices=("prepare", "post"))
    p_hook_run.add_argument("message", nargs="?")
    p_hook_run.add_argument("source", nargs="?")
    p_hook_run.set_defaults(func=_cmd_provenance_hook_run)
    p_pr_check = prov_sub.add_parser(
        "pr-check", help="check proposed squash message against source trailers"
    )
    p_pr_check.add_argument("--repo", default=".")
    p_pr_check.add_argument("--base", required=True)
    p_pr_check.add_argument("--head", required=True)
    p_pr_check.add_argument("--message-file", required=True)
    p_pr_check.set_defaults(func=_cmd_provenance_pr_check)
    p_sources = sub.add_parser("sources", help="read-only source scope diagnostics")
    sources_sub = p_sources.add_subparsers(dest="sources_command", required=True)
    p_suggest = sources_sub.add_parser(
        "suggest", help="compare candidate public repos to configured sources"
    )
    p_suggest.add_argument("candidates", nargs="+")
    p_suggest.set_defaults(func=_cmd_sources_suggest)
    return parser


def _schedule_time(value: str) -> str:
    import re

    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise argparse.ArgumentTypeError("time must use 24-hour HH:MM form")
    return value


def _cmd_schedule_install(args: argparse.Namespace) -> int:
    result = schedule_service.install(
        aiprofile_home(),
        Path(args.profile_repo),
        args.time,
        push=not args.no_push,
        dry_run=args.dry_run,
    )
    if result.dry_run:
        file_word = "file" if result.files == 1 else "files"
        command_word = "command" if result.commands == 1 else "commands"
        print(
            f"dry run: would write {result.files} scheduler {file_word};"
            f" would run {result.commands} registration {command_word}"
        )
        return 0
    mode = "push enabled" if result.push else "push disabled"
    print(f"daily schedule installed for {result.time} local time; {mode}")
    return 0


def _cmd_schedule_status(args: argparse.Namespace) -> int:
    result = schedule_service.status(aiprofile_home(), dry_run=args.dry_run)
    if result.dry_run:
        print("dry run: would inspect native scheduler status")
        return 0
    if not result.installed:
        print("schedule not installed")
        return 0
    mode = "enabled" if result.push else "disabled"
    print(f"schedule installed; time {result.time} local; push {mode}")
    print(f"branch {result.branch}; remote {result.remote or '(none)'}")
    if result.active is not None:
        print(f"native schedule active: {'yes' if result.active else 'no'}")
    if result.last_run:
        print(f"last run: {result.last_run}")
    return 0


def _cmd_schedule_remove(args: argparse.Namespace) -> int:
    result = schedule_service.remove(aiprofile_home(), dry_run=args.dry_run)
    if result.dry_run:
        print(
            "dry run: would remove scheduler registration and tool-owned artifacts"
            if result.removed
            else "dry run: schedule not installed"
        )
        return 0
    print("schedule removed" if result.removed else "schedule not installed")
    return 0


def _cmd_reconcile_add(args: argparse.Namespace) -> int:
    from . import gitio
    from .adapters.trailers import parse_commit_trailers
    from .schema.vocab import ActorType

    home = aiprofile_home()
    cfg = load_config(home)
    repo = Path(args.repo)
    sha = args.sha.lower()
    with acquire_home_lock(home):
        attestations.confirm_reachable(repo, sha, cfg.identities)
        record = next((r for r in gitio.enumerate_commits(repo) if r.sha == sha), None)
        if record is None:
            raise AiProfileError("confirmed commit is no longer reachable")
        existing_specs, _ = parse_commit_trailers(record.trailer_lines)
        if any(spec.actor_type is ActorType.HUMAN for spec in existing_specs):
            raise AiProfileError(
                "commit already declares Human-Only; resolve that contradiction first"
            )
        entry = {
            "repo": attestations.repository_key(repo),
            "sha": sha,
            "provider": args.provider,
            "tool": args.tool,
            "mode": args.mode,
        }
        entries = attestations.load(home)
        entries = [e for e in entries if (e["repo"], e["sha"]) != (entry["repo"], sha)]
        entries.append(entry)
        attestations.save(home, entries)
    print("private AI declaration saved for one confirmed commit; run refresh to apply")
    return 0


def _cmd_reconcile_remove(args: argparse.Namespace) -> int:
    home = aiprofile_home()
    repo = Path(args.repo)
    with acquire_home_lock(home):
        # Rewritten history can orphan a declaration. Removal must still be
        # possible even when the old commit is no longer reachable.
        attestations.validate_commit_id(args.sha.lower())
        repo_key = attestations.repository_key(repo)
        original = attestations.load(home)
        remaining = [e for e in original if (e["repo"], e["sha"]) != (repo_key, args.sha.lower())]
        if len(remaining) == len(original):
            raise AiProfileError("private declaration not found")
        attestations.save(home, remaining)
    print("private declaration removed; run refresh to update the snapshot")
    return 0


def _cmd_reconcile_list(args: argparse.Namespace) -> int:
    entries = attestations.load(aiprofile_home())
    print(f"private declarations: {len(entries)}")
    if args.verbose:
        print("-- local-only commit IDs --")
        for entry in entries:
            print(f"{entry['repo']} {entry['sha']} {entry['provider'] or entry['tool']}")
    return 0


def _cmd_reconcile_sync(args: argparse.Namespace) -> int:
    home = aiprofile_home()
    with acquire_home_lock(home):
        count = attestations.sync_github(home, args.profile_repo)
    print(f"private cloud ledger synced: {count} individually confirmed commits")
    return 0


def _cmd_provenance_mark(args: argparse.Namespace) -> int:
    provenance.mark(aiprofile_home(), Path(args.repo), args.provider, args.tool, args.mode)
    print("one-commit AI mark saved for current HEAD and staged tree")
    return 0


def _cmd_provenance_clear(args: argparse.Namespace) -> int:
    removed = provenance.clear(aiprofile_home(), Path(args.repo))
    print("pending mark cleared" if removed else "no pending mark")
    return 0


def _cmd_provenance_doctor(args: argparse.Namespace) -> int:
    from . import gitio
    from .adapters.trailers import parse_commit_trailers
    from .schema.vocab import ActorType

    if not 1 <= args.recent <= 10000:
        raise AiProfileError("--recent must be between 1 and 10000")
    repo = Path(args.repo)
    status = provenance.hook_status(repo)
    marks = provenance._read(aiprofile_home())
    root = repo.resolve()
    pending = marks.get(provenance._repo_id(root))
    print(f"commit hooks: {status}")
    if pending:
        print(
            "pending mark: matches staged state"
            if provenance._head_and_tree(root) == (pending["head"], pending["tree"])
            else "pending mark: stale; clear and mark again"
        )
    else:
        print("pending mark: none")
    records = gitio.enumerate_commits(repo)[: args.recent]
    unattributed = 0
    attributed = 0
    for record in records:
        specs, _ = parse_commit_trailers(record.trailer_lines)
        if any(spec.actor_type is ActorType.AI for spec in specs):
            attributed += 1
        elif not specs:
            unattributed += 1
    print(
        f"recent {len(records)} commits: {attributed} with explicit AI evidence,"
        f" {unattributed} without attribution"
    )
    ledger = [
        entry
        for entry in attestations.load(aiprofile_home())
        if entry["repo"] == attestations.repository_key(repo)
    ]
    reachable = {record.sha for record in gitio.enumerate_commits(repo)}
    orphaned = sum(entry["sha"] not in reachable for entry in ledger)
    print(f"private reconciliations: {len(ledger)}; unreachable after history changes: {orphaned}")
    print("squash merge may replace source commits; inspect the final reachable commit message")
    return 0


def _cmd_provenance_hook_install(args: argparse.Namespace) -> int:
    provenance.install_hooks(aiprofile_home(), Path(args.repo))
    print("optional hooks installed; existing hooks were not changed")
    return 0


def _cmd_provenance_hook_run(args: argparse.Namespace) -> int:
    provenance.hook_run(
        aiprofile_home(),
        Path.cwd(),
        args.phase,
        Path(args.message) if args.message else None,
        args.source,
    )
    return 0


def _cmd_provenance_pr_check(args: argparse.Namespace) -> int:
    source, final = provenance.check_squash_message(
        Path(args.repo), args.base, args.head, Path(args.message_file)
    )
    print(f"proposed squash message checked: {source} source AI identities, {final} final")
    return 0


def _cmd_sources_suggest(args: argparse.Namespace) -> int:
    import re

    from . import gitio

    cfg = load_config(aiprofile_home())
    configured = {
        attestations.repository_key(Path(entry.path))
        for entry in cfg.repositories
        if Path(entry.path).exists()
    }
    pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}/[A-Za-z0-9._-]{1,100}$")
    for candidate in args.candidates:
        if pattern.fullmatch(candidate) is None:
            raise AiProfileError("candidate must be a GitHub OWNER/REPO identifier")
        key = gitio.canonicalize_remote(f"https://github.com/{candidate}.git")
        state = "configured" if key in configured else "not configured"
        print(f"{candidate}: {state}; no repository was added")
    print("Verify public visibility and identity scope before changing the explicit allowlist")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    from . import gitio  # git lookup stays out of config.py (architecture section 2)

    home = aiprofile_home()
    if _is_inside_git_worktree(home):
        print(
            f"warning: {home} is inside a git work tree; consider setting"
            " AIPROFILE_HOME to a directory outside any git repository so"
            " its private contents (salt, repository paths, identities)"
            " cannot be accidentally committed",
            file=sys.stderr,
        )
    email = gitio.config_user_email(Path.cwd())
    cfg, created = init_home(home, [email] if email else [])
    conn = connect(db_path(home))
    try:
        migrate(conn)
    finally:
        conn.close()
    if created:
        print(f"initialized {home}")
        if cfg.identities:
            print(f"identities: {', '.join(cfg.identities)} (from git config user.email)")
        else:
            print(
                "identities: none found - add your git author email(s) to"
                f" {home / 'config.json'} before scanning"
            )
        print("note: do not sync this directory to published dotfiles (it holds a salt)")
    else:
        print(f"already initialized: {home}")
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    home = aiprofile_home()
    cfg = load_config(home)
    conn = connect(db_path(home))
    try:
        migrate(conn)
        summary = scan_repository(
            home,
            cfg,
            conn,
            args.path,
            make_full=args.full,
            recorded_at=_now_iso(),
        )
    finally:
        conn.close()

    if summary.excluded:
        print(f"{summary.display_name}: excluded by publication policy - not scanned")
        return 0
    print(
        f"{summary.display_name}: {summary.commits_seen} commits seen,"
        f" {summary.commits_kept} by configured identities"
        f" ({summary.commits_skipped_identity} skipped),"
        f" {summary.events_stored} records stored"
    )
    _print_warnings(summary.warnings, verbose=args.verbose)
    return 0


def _cmd_aggregate(args: argparse.Namespace) -> int:
    stats, repo_aggs, cfg = _compute(args)
    _print_stats(stats)
    if args.verbose:
        detail = local_only_details(repo_aggs, cfg)
        print("\n-- local-only detail (never published) --")
        print(f"excluded repositories: {detail['excluded_repositories']}")
        raws = detail["unrecognized_provider_values"]
        print(f"unrecognized provider values: {', '.join(raws) if raws else '(none)'}")
        model_raws = detail["unrecognized_model_values"]
        print(f"raw model values: {', '.join(model_raws) if model_raws else '(none)'}")
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    stats, _, _ = _compute(args)
    paths = write_outputs(stats, refresh.build_assets(stats), Path(args.out))
    for p in paths:
        print(f"wrote {p}")
    return 0


def _cmd_refresh(args: argparse.Namespace) -> int:
    """Default-output privacy rule (v0.7.0 frozen scope guards): this
    summary identifies repositories by config ordinal and aggregate
    counts only - no paths, basenames, or display names; the allowlisted
    output filenames are the only printable names."""
    home = aiprofile_home()
    result = refresh.run_refresh(
        home,
        Path(args.out),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    total = result.plan.total_configured
    for ordinal, summary in result.summaries:
        print(
            f"repository {ordinal}/{total}: {summary.commits_seen} commits seen,"
            f" {summary.commits_kept} by configured identities"
            f" ({summary.commits_skipped_identity} skipped),"
            f" {summary.events_stored} records stored"
        )
        _print_warnings(summary.warnings, verbose=args.verbose)
    skipped_excluded = len(result.plan.skipped_excluded)
    skipped_duplicates = len(result.plan.skipped_duplicates)
    if skipped_excluded or skipped_duplicates:
        print(f"skipped: {skipped_excluded} excluded, {skipped_duplicates} duplicate")
    if not result.ok:
        for line in result.failure_messages():
            print(f"error: {line}", file=sys.stderr)
        print("error: no assets were published", file=sys.stderr)
        return 1
    if result.dry_run:
        for name in result.changed:
            print(f"would update: {name}")
        if not result.changed:
            print("no changes: published assets are up to date")
        return 0
    for p in result.written:
        print(f"wrote {p.name}")
    return 0


def _compute(args: argparse.Namespace):
    home = aiprofile_home()
    cfg = load_config(home)
    conn = connect(db_path(home))
    try:
        migrate(conn)
        repo_aggs = compute_repo_aggregates(conn)
        daily_rows = compute_daily_provider_counts(conn)
        totals_rows = compute_daily_commit_totals(conn)
    finally:
        conn.close()
    stats = build_viz_stats(
        repo_aggs,
        cfg,
        generated_on=_today_utc(),
        daily_rows=daily_rows,
        totals_rows=totals_rows,
    )
    return stats, repo_aggs, cfg


def _print_stats(s: VizStats) -> None:
    t = s.totals
    print(f"AI Collaboration Summary ({s.period.label})")
    print(f"generated: {s.generated_on} (UTC) | schema {s.schema_version}")
    print()
    print(f"commits scanned:            {t.commits_scanned}")
    print(f"AI-attributed commits:      {t.ai_attributed_commits}")
    print(f"AI actor presences:         {t.ai_actor_presences}")
    print(f"human-declared commits:     {t.human_declared_commits}")
    print(f"unknown commits:            {t.unknown_commits}")
    print(f"active AI days (author dates): {t.active_ai_days}")
    print(f"AI providers:               {s.provider_count}")
    if s.providers:
        print()
        print("providers (attributed commits | actor presences | active days):")
        for p in s.providers:
            print(
                f"  {p.display_name:<14} {p.attributed_commits}"
                f" | {p.actor_presences} | {p.active_days}"
            )
    print(f"AI model families:          {s.model_count}")
    if s.models:
        print()
        print("models (attributed commits | actor presences | active days):")
        for m in s.models:
            print(
                f"  {m.display_name:<14} {m.attributed_commits}"
                f" | {m.actor_presences} | {m.active_days}"
            )
    e = s.evidence
    parts = [f"declared {e.declared}", f"unknown {e.unknown}"]
    for label, n in (("verified", e.verified), ("imported", e.imported), ("inferred", e.inferred)):
        if n:
            parts.append(f"{label} {n}")
    print()
    print(f"evidence (all records: {e.total_records}): {' | '.join(parts)}")
    print(
        "publication: explicitly publishable commits"
        f" {s.privacy.explicitly_publishable_commits}"
        f" | aggregate-only commits {s.privacy.anonymous_aggregate_commits}"
        f" | includes aggregate-only:"
        f" {'yes' if s.privacy.includes_anonymous_aggregate else 'no'}"
    )


def _print_warnings(warnings, *, verbose: bool, limit: int = 20) -> None:
    """Diagnostics hygiene (architecture.md section 10, G2-08): default output
    names only the warning code, trailer key, and a scan-local commit
    ordinal - never SHAs or trailer values (those require --verbose)."""
    for ordinal, sha, warning in warnings[:limit]:
        line = f"warning: {warning.code} ({warning.trailer_key}) in commit #{ordinal}"
        if verbose:
            line += f" [{sha[:12]}]"
            if warning.local_detail:
                line += f" - {warning.local_detail}"
        print(line)
    if len(warnings) > limit:
        print(f"...and {len(warnings) - limit} more warnings")


def _today_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")

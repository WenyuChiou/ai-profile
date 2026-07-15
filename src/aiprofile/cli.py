"""CLI wiring (ADR-002): init / scan / aggregate / render.

Exit codes: 0 success, 1 operational error, 2 usage. `aggregate` prints
exactly the published contract — it IS the v0.1 privacy preview
(mvp.md section 2); `-v` adds clearly-marked local-only detail.
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .aggregate import compute_repo_aggregates
from .config import aiprofile_home, db_path, init_home, load_config
from .errors import AiProfileError
from .export import write_outputs
from .privacy import build_viz_stats, local_only_details
from .render.summary_svg import render_summary
from .render.themes import THEMES
from .scanner import scan_repository
from .storage.db import connect, migrate
from .viz import VizStats


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
            " explicit git provenance in, privacy-safe SVG/JSON out."
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
            " publishable — a policy decision, not a visibility claim);"
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
        help="write dist/ assets (SVG light/dark + JSON)",
        description=(
            "Write summary-light.svg, summary-dark.svg and profile.json as one"
            " bundle. Run ONE render at a time per output directory:"
            " concurrent renders into the same directory are unsupported and"
            " can publish a mixed generation."
        ),
    )
    p_render.add_argument(
        "--out", default="dist", help="output directory (default: ./dist)"
    )
    p_render.set_defaults(func=_cmd_render)
    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    from . import gitio  # git lookup stays out of config.py (architecture section 2)

    home = aiprofile_home()
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
                "identities: none found — add your git author email(s) to"
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
        print(f"{summary.display_name}: excluded by publication policy — not scanned")
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
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    stats, _, _ = _compute(args)
    svg_light = render_summary(stats, THEMES["github-light"])
    svg_dark = render_summary(stats, THEMES["github-dark"])
    paths = write_outputs(stats, svg_light, svg_dark, Path(args.out))
    for p in paths:
        print(f"wrote {p}")
    return 0


def _compute(args: argparse.Namespace):
    home = aiprofile_home()
    cfg = load_config(home)
    conn = connect(db_path(home))
    try:
        migrate(conn)
        repo_aggs = compute_repo_aggregates(conn)
    finally:
        conn.close()
    stats = build_viz_stats(repo_aggs, cfg, generated_on=_today_utc())
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
    ordinal — never SHAs or trailer values (those require --verbose)."""
    for ordinal, sha, warning in warnings[:limit]:
        line = f"warning: {warning.code} ({warning.trailer_key}) in commit #{ordinal}"
        if verbose:
            line += f" [{sha[:12]}]"
            if warning.local_detail:
                line += f" — {warning.local_detail}"
        print(line)
    if len(warnings) > limit:
        print(f"...and {len(warnings) - limit} more warnings")


def _today_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")

"""Console-output privacy canary sweeps (ROADMAP item: "canary sweeps over
stdout/stderr/logs (not only dist/)" - gate-2 section 14 gap).

tests/integration/test_end_to_end.py's test_privacy_leak and
test_privacy_leak_remote_org_and_uid_canaries sweep only the BYTES OF
dist/. helpers.run_cli captures stdout/stderr for every invocation and
that capture is never swept anywhere in the suite - this file closes that
gap. Fixture approach mirrors test_end_to_end.py (build_repo + run_cli
against an isolated AIPROFILE_HOME), with its own distinct canary strings
so a failure here is never confused with a failure in that file's tests.

Repo display-name policy (see the comment block above _default_forbidden()
below for the full citation): scan's default output
intentionally echoes back the directory-name fragment of the path the
user themselves typed on the command line. docs/PRIVACY.md's
"stdout/stderr/logs" threat-surface entry and architecture.md section 10's
pinned diagnostics rule both scope the "never print repository
names/paths" guarantee to WARNING lines specifically (cli.py's
_print_warnings), not to the scan command's primary result line - so the
repo directory name is deliberately excluded from the forbidden-canary
list, and is asserted present instead (positive control), so this test
still notices if that contract ever changes.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from helpers import FIXTURE_AUTHOR_EMAIL, build_repo, run_cli

# ---------------------------------------------------------------------------
# Canary constants - deliberately distinct from test_end_to_end.py's own
# canary strings (e.g. "secret-zebra-vault-77", "Zzz-Custom-LLM-9000") so a
# leak reported by this file can never be mistaken for one from that file.
# ---------------------------------------------------------------------------

REPO_DIR_NAME = "console-sweep-quokka-vault-19"
REMOTE_ORG = "console-sweep-quokka-org"
REMOTE_REPO = "console-sweep-quokka-repo"
REMOTE_URL = f"https://github.com/{REMOTE_ORG}/{REMOTE_REPO}.git"
RAW_UNRECOGNIZED_PROVIDER = "Qorvax-Mystery-Vendor-9"
# local_detail payload for a malformed-mode ParseWarning (trailers.py
# _build_ai_spec): NOT itself a forbidden canary - G2-08 explicitly allows
# verbose warning lines to carry local_detail. Present here only so the
# verbose test can assert that permissive branch is actually exercised.
BOGUS_MODE_VALUE = "totally-bogus-console-mode"


def _fixture_commits() -> list[tuple[str, str]]:
    return [
        ("plain commit, no trailers", "2026-05-01T10:00:00+00:00"),
        (
            "Recognized AI commit\n\n"
            "AI-Provider: Anthropic\n"
            "AI-Tool: Claude-Code\n"
            "AI-Role: implementation",
            "2026-05-02T10:00:00+00:00",
        ),
        (
            "Unrecognized-provider commit\n\n" f"AI-Provider: {RAW_UNRECOGNIZED_PROVIDER}",
            "2026-05-03T10:00:00+00:00",
        ),
        (
            "Malformed-mode commit\n\n"
            "AI-Provider: Anthropic\n"
            f"AI-Mode: {BOGUS_MODE_VALUE}",
            "2026-05-04T10:00:00+00:00",
        ),
    ]


def _build_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    """Build the repo (with a distinctive remote) plus an isolated
    AIPROFILE_HOME, mirroring test_end_to_end.py's fixture approach.
    Returns (home, repo_path, salt)."""
    home = tmp_path / "home"
    repo_path = tmp_path / REPO_DIR_NAME
    build_repo(repo_path, _fixture_commits())
    subprocess.run(
        ["git", "remote", "add", "origin", REMOTE_URL],
        cwd=str(repo_path),
        check=True,
        capture_output=True,
    )
    init_res = run_cli(["init"], home=home, cwd=repo_path)
    assert init_res.returncode == 0, init_res.stderr

    config = json.loads((home / "config.json").read_text(encoding="utf-8"))
    salt = config["salt"]
    assert salt  # sanity: init always writes a non-empty salt
    return home, repo_path, salt


def _sweep(output: str, forbidden: list[str], *, context: str) -> None:
    for needle in forbidden:
        assert needle not in output, f"{needle!r} leaked into {context} output"


# ---------------------------------------------------------------------------
# NEVER-PRINT canaries: salt, author email, remote org+repo (host+path
# fragments of a remote URL), and the raw unrecognized AI-Provider value.
# docs/PRIVACY.md "Threat surfaces and mitigations" > stdout/stderr/logs:
# "default diagnostics carry scan-local ordinals and trailer keys only
# (never SHAs, values, paths - G2-08); SHAs/values require --verbose."
# architecture.md section 10's pinned diagnostics rule pins that same
# guarantee to default-verbosity WARNING lines. Neither the salt nor the
# author email nor the remote org/URL nor a raw AI-Provider value is ever
# something the user just typed on this command line (unlike the scanned
# repo's directory name), so none of them get the display-name exception
# above - they must never appear in DEFAULT-mode console output at all.
# ---------------------------------------------------------------------------


def _default_forbidden(salt: str) -> list[str]:
    return [salt, FIXTURE_AUTHOR_EMAIL, REMOTE_ORG, REMOTE_REPO, RAW_UNRECOGNIZED_PROVIDER]


def test_console_default_mode_never_prints_never_print_canaries(tmp_path):
    """Sweep captured stdout+stderr of every run_cli invocation (init,
    scan, scan --full, aggregate, render), all in default (non-verbose)
    mode, against the never-print canary set."""
    home, repo_path, salt = _build_fixture(tmp_path)
    out_dir = tmp_path / "dist"
    forbidden = _default_forbidden(salt)

    # init already ran once inside _build_fixture (created branch); a
    # second invocation exercises cli.py's "already initialized" branch,
    # a genuinely different code path worth sweeping in its own right.
    init_res = run_cli(["init"], home=home, cwd=repo_path)
    assert init_res.returncode == 0, init_res.stderr
    _sweep(init_res.stdout + init_res.stderr, forbidden, context="init (default)")

    scan_res = run_cli(["scan", str(repo_path)], home=home, cwd=repo_path)
    assert scan_res.returncode == 0, scan_res.stderr
    _sweep(scan_res.stdout + scan_res.stderr, forbidden, context="scan (default)")
    # Positive control for the display-name policy documented at module
    # level: the summary line DOES echo back the repo directory name -
    # this is the deliberate exception, not an oversight.
    assert REPO_DIR_NAME in scan_res.stdout

    scan_full_res = run_cli(["scan", "--full", str(repo_path)], home=home, cwd=repo_path)
    assert scan_full_res.returncode == 0, scan_full_res.stderr
    _sweep(
        scan_full_res.stdout + scan_full_res.stderr,
        forbidden,
        context="scan --full (default)",
    )

    agg_res = run_cli(["aggregate"], home=home, cwd=repo_path)
    assert agg_res.returncode == 0, agg_res.stderr
    _sweep(agg_res.stdout + agg_res.stderr, forbidden, context="aggregate (default)")

    render_res = run_cli(["render", "--out", str(out_dir)], home=home, cwd=repo_path)
    assert render_res.returncode == 0, render_res.stderr
    _sweep(render_res.stdout + render_res.stderr, forbidden, context="render (default)")


# ---------------------------------------------------------------------------
# VERBOSE mode contract (G2-08): -v MAY print SHAs and raw provider values
# (aggregate -v prints unrecognized raws; scan -v warning lines may carry a
# SHA prefix and local_detail). It must still NEVER print salt, author
# email, or remote-URL/org canaries - a strictly narrower forbidden set
# than the default-mode test above, on purpose.
# ---------------------------------------------------------------------------


def test_console_verbose_mode_never_prints_salt_email_or_remote_canaries(tmp_path):
    home, repo_path, salt = _build_fixture(tmp_path)
    out_dir = tmp_path / "dist"
    forbidden = [salt, FIXTURE_AUTHOR_EMAIL, REMOTE_ORG, REMOTE_REPO]

    init_res = run_cli(["-v", "init"], home=home, cwd=repo_path)
    assert init_res.returncode == 0, init_res.stderr
    _sweep(init_res.stdout + init_res.stderr, forbidden, context="init (-v)")

    scan_res = run_cli(["-v", "scan", str(repo_path)], home=home, cwd=repo_path)
    assert scan_res.returncode == 0, scan_res.stderr
    _sweep(scan_res.stdout + scan_res.stderr, forbidden, context="scan (-v)")
    # Confirm the permissive G2-08 branch is actually exercised (not merely
    # absent): verbose scan warning lines carry a 12-hex-char sha prefix
    # and the malformed-mode local_detail token.
    assert re.search(r"\[[0-9a-f]{12}\]", scan_res.stdout), scan_res.stdout
    assert "malformed-mode" in scan_res.stdout
    assert BOGUS_MODE_VALUE in scan_res.stdout

    scan_full_res = run_cli(["-v", "scan", "--full", str(repo_path)], home=home, cwd=repo_path)
    assert scan_full_res.returncode == 0, scan_full_res.stderr
    _sweep(
        scan_full_res.stdout + scan_full_res.stderr,
        forbidden,
        context="scan --full (-v)",
    )

    agg_res = run_cli(["-v", "aggregate"], home=home, cwd=repo_path)
    assert agg_res.returncode == 0, agg_res.stderr
    _sweep(agg_res.stdout + agg_res.stderr, forbidden, context="aggregate (-v)")
    # mvp.md section 3 / G2-08: aggregate -v explicitly publishes
    # unrecognized raw provider values as local-only detail - confirm the
    # permissive branch fires rather than passing this test vacuously.
    assert RAW_UNRECOGNIZED_PROVIDER in agg_res.stdout

    render_res = run_cli(["-v", "render", "--out", str(out_dir)], home=home, cwd=repo_path)
    assert render_res.returncode == 0, render_res.stderr
    _sweep(render_res.stdout + render_res.stderr, forbidden, context="render (-v)")


# ---------------------------------------------------------------------------
# Exception path: an operational error (scan of a nonexistent path) must
# still respect the never-print canary set, in both default and verbose
# mode. architecture.md section 10: "GitError messages may include the
# failing command and paths - they go to the terminal only" - a path is
# not one of our four never-print canaries, so this is a genuine (not
# vacuous) regression test.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Refresh (v0.7.0 Task A5): deliberately STRICTER than scan's contract
# above. Default refresh output identifies repositories by config ordinal
# and aggregate counts ONLY - the repo directory name (basename/display
# name) that scan's summary line may echo is FORBIDDEN here, along with
# full paths, author emails, commit SHAs, and raw trailer values. Only
# the eight allowlisted output filenames are printable. (A future
# verbose/local-only mode may relax this; the v0.7.0 default must not.)
# ---------------------------------------------------------------------------


def test_console_refresh_default_mode_is_ordinal_and_counts_only(tmp_path):
    home, repo_path, salt = _build_fixture(tmp_path)
    out_dir = tmp_path / "dist"

    scan_res = run_cli(["scan", str(repo_path)], home=home, cwd=repo_path)
    assert scan_res.returncode == 0, scan_res.stderr

    shas = (
        subprocess.run(
            ["git", "log", "--format=%H"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.split()
    )
    assert shas
    forbidden = _default_forbidden(salt) + [
        str(repo_path),  # full repository path
        REPO_DIR_NAME,  # basename / display name - forbidden for refresh
        BOGUS_MODE_VALUE,  # raw trailer value
        *shas,  # full commit SHAs
        *[sha[:12] for sha in shas],  # the verbose-mode SHA prefix form
    ]

    refresh_res = run_cli(["refresh", "--out", str(out_dir)], home=home, cwd=repo_path)
    assert refresh_res.returncode == 0, refresh_res.stderr
    _sweep(
        refresh_res.stdout + refresh_res.stderr,
        forbidden,
        context="refresh (default)",
    )
    # Positive control: the ordinal-keyed summary line is the sanctioned
    # repository identifier.
    assert "repository 1/1:" in refresh_res.stdout

    dry_res = run_cli(
        ["refresh", "--out", str(out_dir), "--dry-run"], home=home, cwd=repo_path
    )
    assert dry_res.returncode == 0, dry_res.stderr
    _sweep(
        dry_res.stdout + dry_res.stderr,
        forbidden,
        context="refresh --dry-run (default)",
    )


def test_console_error_path_never_prints_never_print_canaries(tmp_path, monkeypatch):
    # Ceiling-dir guard, matching test_end_to_end.py::test_malformed_repository:
    # pins git's upward repository search inside tmp_path so an ambient
    # parent git repository on the host cannot change this outcome.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    home, repo_path, salt = _build_fixture(tmp_path)
    default_forbidden = _default_forbidden(salt)
    verbose_forbidden = [salt, FIXTURE_AUTHOR_EMAIL, REMOTE_ORG, REMOTE_REPO]

    missing = tmp_path / "does-not-exist-console-sweep"

    res = run_cli(["scan", str(missing)], home=home, cwd=tmp_path)
    assert res.returncode == 1
    combined = res.stdout + res.stderr
    assert combined.strip() != ""  # sanity: the error path actually printed something
    _sweep(combined, default_forbidden, context="scan missing path (default)")

    res_v = run_cli(["-v", "scan", str(missing)], home=home, cwd=tmp_path)
    assert res_v.returncode == 1
    combined_v = res_v.stdout + res_v.stderr
    assert combined_v.strip() != ""
    _sweep(combined_v, verbose_forbidden, context="scan missing path (-v)")


# ---------------------------------------------------------------------------
# Refresh error paths (v0.7.0 P1-2): infrastructure failures - missing
# home, absent/malformed config, unreadable database, failed publication
# - must be PATH-FREE at default verbosity with NO raw traceback, while
# still exiting nonzero (failure is never hidden). Unlike scan (whose
# GitError messages may carry paths per architecture.md section 10),
# refresh's default output follows the v0.7.0 default-output privacy
# rule end to end. -v deliberately retains local detail (traceback with
# the chained original error).
# ---------------------------------------------------------------------------


def _assert_pathfree_failure(res, canaries: list[str], *, context: str) -> None:
    combined = res.stdout + res.stderr
    assert res.returncode == 1, f"{context}: rc={res.returncode}\n{combined}"
    assert combined.strip(), f"{context}: the error path printed nothing"
    assert "error:" in res.stderr, f"{context}: no error line\n{combined}"
    assert "Traceback" not in combined, f"{context}: raw traceback leaked\n{combined}"
    _sweep(combined, canaries, context=context)


def test_console_refresh_missing_home_is_path_free(tmp_path):
    missing_home = tmp_path / "missing-home-canary-71"
    out_dir = tmp_path / "dist"
    canaries = [str(missing_home), "missing-home-canary-71", str(tmp_path)]

    res = run_cli(["refresh", "--out", str(out_dir)], home=missing_home, cwd=tmp_path)
    _assert_pathfree_failure(res, canaries, context="refresh missing home")

    res_dry = run_cli(
        ["refresh", "--out", str(out_dir), "--dry-run"], home=missing_home, cwd=tmp_path
    )
    _assert_pathfree_failure(res_dry, canaries, context="refresh --dry-run missing home")


def test_console_refresh_config_errors_are_path_free_and_verbose_keeps_detail(tmp_path):
    out_dir = tmp_path / "dist"

    # Home exists but has no config.json at all.
    empty_home = tmp_path / "empty-home-canary-72"
    empty_home.mkdir()
    res = run_cli(["refresh", "--out", str(out_dir)], home=empty_home, cwd=tmp_path)
    _assert_pathfree_failure(
        res,
        [str(empty_home), "empty-home-canary-72"],
        context="refresh without config",
    )

    # Malformed config.json.
    bad_home = tmp_path / "bad-home-canary-73"
    bad_home.mkdir()
    (bad_home / "config.json").write_text("{ not json", encoding="utf-8")
    bad_canaries = [str(bad_home), "bad-home-canary-73"]
    res_bad = run_cli(["refresh", "--out", str(out_dir)], home=bad_home, cwd=tmp_path)
    _assert_pathfree_failure(res_bad, bad_canaries, context="refresh malformed config")
    res_bad_dry = run_cli(
        ["refresh", "--out", str(out_dir), "--dry-run"], home=bad_home, cwd=tmp_path
    )
    _assert_pathfree_failure(
        res_bad_dry, bad_canaries, context="refresh --dry-run malformed config"
    )

    # -v retains local detail: the traceback (with the chained original
    # ConfigError, which names the config path) is the sanctioned
    # local-only diagnostic channel.
    res_v = run_cli(["-v", "refresh", "--out", str(out_dir)], home=bad_home, cwd=tmp_path)
    assert res_v.returncode == 1
    combined_v = res_v.stdout + res_v.stderr
    assert "Traceback" in combined_v
    assert str(bad_home) in combined_v


def test_console_refresh_unreadable_database_is_path_free(tmp_path):
    home, repo_path, _ = _build_fixture(tmp_path)
    scan_res = run_cli(["scan", str(repo_path)], home=home, cwd=repo_path)
    assert scan_res.returncode == 0, scan_res.stderr

    # Replace the database file with a directory: sqlite cannot open it.
    db = home / "aiprofile.db"
    db.unlink()
    db.mkdir()
    out_dir = tmp_path / "dist"
    canaries = [str(home), str(db), str(repo_path), REPO_DIR_NAME]

    res = run_cli(["refresh", "--out", str(out_dir)], home=home, cwd=repo_path)
    _assert_pathfree_failure(res, canaries, context="refresh unreadable database")

    res_dry = run_cli(
        ["refresh", "--out", str(out_dir), "--dry-run"], home=home, cwd=repo_path
    )
    _assert_pathfree_failure(
        res_dry, canaries, context="refresh --dry-run unreadable database"
    )


def test_console_refresh_publication_failure_is_path_free(tmp_path):
    home, repo_path, _ = _build_fixture(tmp_path)
    scan_res = run_cli(["scan", str(repo_path)], home=home, cwd=repo_path)
    assert scan_res.returncode == 0, scan_res.stderr

    # --out points at an existing FILE: the bundle directory cannot be
    # created, so publication fails after a fully successful scan phase.
    out_file = tmp_path / "not-a-directory-canary-74"
    out_file.write_text("occupied", encoding="utf-8")
    res = run_cli(["refresh", "--out", str(out_file)], home=home, cwd=repo_path)
    _assert_pathfree_failure(
        res,
        [str(out_file), "not-a-directory-canary-74", str(repo_path), REPO_DIR_NAME],
        context="refresh publication failure",
    )
    assert out_file.read_text(encoding="utf-8") == "occupied"  # never clobbered

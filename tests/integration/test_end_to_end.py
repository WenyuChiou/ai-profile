"""End-to-end integration tests for the aiprofile CLI (work package F).

These tests shell out to real git and to `python -m aiprofile` as a
subprocess (see helpers.py) — no aiprofile library imports, no monkeypatching.
Every expected number in test_happy_path_full_pipeline and
test_publication_policy_resolution is derived by hand in comments from
docs/schema.md section 15 (aggregation semantics) and the trailer adapter
contract documented in src/aiprofile/adapters/trailers.py; nothing here is
tuned to observed output.

Required-test cross-reference (docs/mvp.md section 7):
  test 6  (duplicate-scan idempotence)   -> test_duplicate_scan_idempotence
  test 9  (privacy leak)                 -> test_privacy_leak
  test 10 (publication-policy resolution)-> test_publication_policy_resolution
  test 14 (malformed repository)         -> test_malformed_repository
  test 15 (rewritten history)            -> test_rewritten_history_amend_rescan
  test 17 (export stability)             -> test_export_stability
  (zero-state + usage-error are covered too, matching mvp.md section 2/3
  CLI semantics, though they are not separately numbered in section 7)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from helpers import FIXTURE_AUTHOR_EMAIL, build_repo, run_cli

from aiprofile import ACE_SCHEMA_VERSION

# ---------------------------------------------------------------------------
# Shared fixture: the eight-commit repository used by the happy-path,
# idempotence, rewritten-history, privacy-leak, and export-stability tests.
# Each test builds its OWN copy under its own tmp_path — no shared state.
# ---------------------------------------------------------------------------

_STANDARD_DATES = [f"2026-01-0{n}T12:00:00+00:00" for n in range(1, 9)]


def _standard_commits() -> list[tuple[str, str]]:
    """The eight required fixture commits (docs/mvp.md section 7 integration
    fixtures list), in HEAD order, all authored by FIXTURE_AUTHOR_EMAIL on
    distinct January-2026 days."""
    return [
        # a. plain commit, no trailers -> unknown
        ("plain commit, no trailers", _STANDARD_DATES[0]),
        # b. Claude AI-* commit: one complete AI-* group
        (
            "Claude AI-* commit\n\n"
            "AI-Provider: Anthropic\n"
            "AI-Model: Claude-Sonnet\n"
            "AI-Tool: Claude-Code\n"
            "AI-Role: implementation\n"
            "AI-Mode: AI-Assisted\n"
            "AI-Reviewed-By: Human",
            _STANDARD_DATES[1],
        ),
        # c. Codex AI-* commit
        (
            "Codex AI-* commit\n\n"
            "AI-Provider: OpenAI\n"
            "AI-Tool: Codex-CLI\n"
            "AI-Role: review",
            _STANDARD_DATES[2],
        ),
        # d. Claude co-author commit (registry.py COAUTHOR_IDENTITIES exact-email match)
        (
            "Claude co-author commit\n\n"
            "Co-Authored-By: Claude <noreply@anthropic.com>",
            _STANDARD_DATES[3],
        ),
        # e. multi-AI commit: AI-Provider repeats -> ADR-005 closes group 1 and
        # opens group 2 (Anthropic/Claude-Code, then OpenAI/Codex-CLI)
        (
            "Multi-AI commit\n\n"
            "AI-Provider: Anthropic\n"
            "AI-Tool: Claude-Code\n"
            "AI-Role: implementation\n"
            "AI-Provider: OpenAI\n"
            "AI-Tool: Codex-CLI\n"
            "AI-Role: review",
            _STANDARD_DATES[4],
        ),
        # f. malformed-trailer commit: AI-Model alone has no anchor -> incomplete-group
        ("Malformed trailer commit\n\nAI-Model: Mystery-9", _STANDARD_DATES[5]),
        # g. human-declared commit: AI-Mode: Human-Only alone -> one human event
        ("Human-declared commit\n\nAI-Mode: Human-Only", _STANDARD_DATES[6]),
        # h. unrecognized-provider commit: registry has no alias for this raw value
        (
            "Unrecognized-provider commit\n\nAI-Provider: Zzz-Custom-LLM-9000",
            _STANDARD_DATES[7],
        ),
    ]


_ZERO_TOTALS = {
    "commits_scanned": 0,
    "ai_attributed_commits": 0,
    "ai_actor_presences": 0,
    "human_declared_commits": 0,
    "unknown_commits": 0,
    "active_ai_days": 0,
}


def _git_head_sha(repo_path: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


def test_happy_path_full_pipeline(tmp_path):
    """mvp.md section 7's core integration scenario: init -> scan -> aggregate
    -> render over the eight required commit shapes, with every published
    number derived by hand below (docs/schema.md section 15 definitions;
    src/aiprofile/adapters/trailers.py docstring for grouping/warning rules).

    Per-commit event tally (scanner.py: zero specs -> one synthetic `unknown`
    event; schema.md section 11):
      a unknown(1)   b ai(1, anthropic)   c ai(1, openai)   d ai(1, anthropic)
      e ai(2: anthropic + openai)         f unknown(1)      g human(1)
      h ai(1, provider=None -> unrecognized bucket)
      => 9 records stored across 8 commits.

    Aggregated (schema.md section 15):
      commits_scanned         = 8                    (a..h, all by the configured identity)
      ai_attributed_commits   = 5                    (b,c,d,e,h: >=1 ai/mixed event)
      ai_actor_presences = 6                    (b1+c1+d1+e2+h1)
      human_declared_commits  = 1                    (g: human event, no ai event)
      unknown_commits         = 2                    (a,f: only unknown events)
      active_ai_days          = 5                    (Jan 2,3,4,5,8 each have >=1 ai event)

      provider anthropic: attributed_commits=3 (b,d,e) actor_presences=3 active_days=3
      provider openai:    attributed_commits=2 (c,e)   actor_presences=2 active_days=2
      provider unrecognized: attributed_commits=1 (h)  actor_presences=1 active_days=1
      provider_count = 2 (anthropic, openai — unrecognized excluded per schema.md section 15)

      evidence declared = 7  (all 6 ai events + the 1 human event: every one of
                               them is sourced from an explicit git trailer,
                               so evidence_level=declared per build_event's
                               source-level derivation)
      evidence unknown  = 2  (a, f — the synthetic no-evidence events)
      evidence verified/imported/inferred = 0 (no v0.1 producer emits these)

      privacy: repository scanned without --full -> publication_level defaults
        to aggregate_only (mvp.md section 3) -> explicitly_publishable_commits=0,
        anonymous_aggregate_commits=8, includes_anonymous_aggregate=True.
    """
    home = tmp_path / "home"
    repo_path = tmp_path / "repo"
    out_dir = tmp_path / "dist"

    build_repo(repo_path, _standard_commits())

    init_res = run_cli(["init"], home=home, cwd=repo_path)
    assert init_res.returncode == 0, init_res.stderr

    scan_res = run_cli(["scan", str(repo_path)], home=home, cwd=repo_path)
    assert scan_res.returncode == 0, scan_res.stderr
    # cross-check against the derivation above via the scanner's own summary line
    assert "8 commits seen" in scan_res.stdout
    assert "9 records stored" in scan_res.stdout
    # commit f's dropped AI-Model-only group is diagnosed (diagnostics hygiene:
    # code + trailer key only, never the value — architecture.md section 10)
    assert "incomplete-group" in scan_res.stdout

    agg_res = run_cli(["aggregate"], home=home, cwd=repo_path)
    assert agg_res.returncode == 0, agg_res.stderr

    render_res = run_cli(["render", "--out", str(out_dir)], home=home, cwd=repo_path)
    assert render_res.returncode == 0, render_res.stderr

    profile = json.loads((out_dir / "profile.json").read_text(encoding="utf-8"))

    assert profile["schema_version"] == ACE_SCHEMA_VERSION
    assert profile["totals"] == {
        "commits_scanned": 8,
        "ai_attributed_commits": 5,
        "ai_actor_presences": 6,
        "human_declared_commits": 1,
        "unknown_commits": 2,
        "active_ai_days": 5,
    }
    assert profile["providers"] == [
        {
            "provider": "anthropic",
            "display_name": "Claude",
            "attributed_commits": 3,
            "actor_presences": 3,
            "active_days": 3,
        },
        {
            "provider": "openai",
            "display_name": "OpenAI",
            "attributed_commits": 2,
            "actor_presences": 2,
            "active_days": 2,
        },
        {
            "provider": "unrecognized",
            "display_name": "Unrecognized",
            "attributed_commits": 1,
            "actor_presences": 1,
            "active_days": 1,
        },
    ]
    assert profile["provider_count"] == 2
    assert profile["evidence_records"] == {
        "verified": 0,
        "declared": 7,
        "imported": 0,
        "inferred": 0,
        "unknown": 2,
        "total_records": 9,
    }
    assert profile["privacy"] == {
        "explicitly_publishable_commits": 0,
        "anonymous_aggregate_commits": 8,
        "includes_anonymous_aggregate": True,
    }


# ---------------------------------------------------------------------------
# 2. Duplicate-scan idempotence (mvp.md section 7 test 6)
# ---------------------------------------------------------------------------


def test_duplicate_scan_idempotence(tmp_path):
    """Re-scanning an unchanged repository must produce byte-identical
    published output (ADR-014: each scan atomically replaces the
    repository's scan-derived rows)."""
    home = tmp_path / "home"
    repo_path = tmp_path / "repo"
    build_repo(repo_path, _standard_commits())

    assert run_cli(["init"], home=home, cwd=repo_path).returncode == 0
    assert run_cli(["scan", str(repo_path)], home=home, cwd=repo_path).returncode == 0

    out1 = tmp_path / "dist1"
    r1 = run_cli(["render", "--out", str(out1)], home=home, cwd=repo_path)
    assert r1.returncode == 0, r1.stderr

    # re-scan the same, unchanged repository
    rescan = run_cli(["scan", str(repo_path)], home=home, cwd=repo_path)
    assert rescan.returncode == 0, rescan.stderr

    out2 = tmp_path / "dist2"
    r2 = run_cli(["render", "--out", str(out2)], home=home, cwd=repo_path)
    assert r2.returncode == 0, r2.stderr

    assert (out1 / "profile.json").read_bytes() == (out2 / "profile.json").read_bytes()


# ---------------------------------------------------------------------------
# 3. Rewritten history (mvp.md section 7 test 15)
# ---------------------------------------------------------------------------


def test_rewritten_history_amend_rescan(tmp_path):
    """Amending HEAD's message (new sha, trailers unchanged) and rescanning
    must leave totals unchanged: the scan replaces all scan-derived rows from
    the current HEAD every time (ADR-014), and event identity does not
    depend on the commit sha's specific value beyond being the join key."""
    home = tmp_path / "home"
    repo_path = tmp_path / "repo"
    build_repo(repo_path, _standard_commits())

    assert run_cli(["init"], home=home, cwd=repo_path).returncode == 0
    assert run_cli(["scan", str(repo_path)], home=home, cwd=repo_path).returncode == 0

    out_before = tmp_path / "dist_before"
    assert (
        run_cli(["render", "--out", str(out_before)], home=home, cwd=repo_path).returncode == 0
    )
    profile_before = json.loads((out_before / "profile.json").read_text(encoding="utf-8"))

    old_head = _git_head_sha(repo_path)

    # Amend HEAD (commit h, the unrecognized-provider commit): change only
    # the subject line, keep the AI-Provider trailer byte-for-byte.
    new_message = "Unrecognized-provider commit (amended)\n\nAI-Provider: Zzz-Custom-LLM-9000"
    env = dict(os.environ)
    original_date = _standard_commits()[-1][1]
    env["GIT_AUTHOR_DATE"] = original_date
    env["GIT_COMMITTER_DATE"] = original_date
    amend = subprocess.run(
        ["git", "commit", "--amend", "-q", "-m", new_message],
        cwd=str(repo_path),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert amend.returncode == 0, amend.stderr
    assert _git_head_sha(repo_path) != old_head

    rescan = run_cli(["scan", str(repo_path)], home=home, cwd=repo_path)
    assert rescan.returncode == 0, rescan.stderr
    assert "8 commits seen" in rescan.stdout

    out_after = tmp_path / "dist_after"
    assert run_cli(["render", "--out", str(out_after)], home=home, cwd=repo_path).returncode == 0
    profile_after = json.loads((out_after / "profile.json").read_text(encoding="utf-8"))

    assert profile_after["totals"] == profile_before["totals"]
    assert profile_after["totals"]["commits_scanned"] == 8
    assert profile_after["providers"] == profile_before["providers"]
    assert profile_after["evidence_records"] == profile_before["evidence_records"]


# ---------------------------------------------------------------------------
# 4. Privacy leak test (mvp.md section 7 test 9)
# ---------------------------------------------------------------------------


def test_privacy_leak(tmp_path):
    """No byte of any dist/ file may reveal the repository directory name (or
    a fragment of it), the fixture author email, the raw unrecognized
    AI-Provider trailer value, or the local config salt — while profile.json
    DOES surface an `unrecognized` provider bucket counting commit h
    (schema.md section 10's public-output rule for canonical-null values)."""
    home = tmp_path / "home"
    repo_path = tmp_path / "secret-zebra-vault-77"
    out_dir = tmp_path / "dist"

    build_repo(repo_path, _standard_commits())

    assert run_cli(["init"], home=home, cwd=repo_path).returncode == 0
    assert run_cli(["scan", str(repo_path)], home=home, cwd=repo_path).returncode == 0
    render_res = run_cli(["render", "--out", str(out_dir)], home=home, cwd=repo_path)
    assert render_res.returncode == 0, render_res.stderr

    config = json.loads((home / "config.json").read_text(encoding="utf-8"))
    salt = config["salt"]
    assert salt  # sanity: init always writes a non-empty salt

    forbidden = [
        "secret-zebra-vault-77",
        "secret-zebra",
        FIXTURE_AUTHOR_EMAIL,
        "Zzz-Custom-LLM-9000",
        salt,
    ]

    dist_files = sorted(p for p in out_dir.rglob("*") if p.is_file())
    assert [p.name for p in dist_files] == [
        "profile.json",
        "summary-dark.svg",
        "summary-light.svg",
    ]
    for path in dist_files:
        text = path.read_bytes().decode("utf-8")
        for needle in forbidden:
            assert needle not in text, f"{needle!r} leaked into {path.name}"

    profile = json.loads((out_dir / "profile.json").read_text(encoding="utf-8"))
    unrecognized = next(p for p in profile["providers"] if p["provider"] == "unrecognized")
    assert unrecognized["display_name"] == "Unrecognized"
    assert unrecognized["attributed_commits"] == 1
    assert unrecognized["actor_presences"] == 1


# ---------------------------------------------------------------------------
# 5. Publication-policy resolution (mvp.md section 7 test 10)
# ---------------------------------------------------------------------------


def test_publication_policy_resolution(tmp_path):
    """publication_level lives only in config.json (schema.md section 9) and
    is resolved fresh on every aggregate/render call with no rescan needed.
    A minimal two-commit repo is enough here: one unknown commit, one AI
    commit -> commits_scanned=2, so public/private math stays easy to read."""
    home = tmp_path / "home"
    repo_path = tmp_path / "repo"
    commits = [
        ("plain commit, no trailers", "2026-01-01T12:00:00+00:00"),
        (
            "Claude AI-* commit\n\n"
            "AI-Provider: Anthropic\n"
            "AI-Tool: Claude-Code\n"
            "AI-Role: implementation",
            "2026-01-02T12:00:00+00:00",
        ),
    ]
    build_repo(repo_path, commits)

    assert run_cli(["init"], home=home, cwd=repo_path).returncode == 0
    assert run_cli(["scan", str(repo_path)], home=home, cwd=repo_path).returncode == 0

    config_path = home / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert len(config["repositories"]) == 1
    entry = config["repositories"][0]
    assert entry["publication_level"] == "aggregate_only"  # default, no --full
    uid = entry["repository_uid"]
    original_path = entry["path"]

    def render_and_load(label: str) -> dict:
        out = tmp_path / f"dist_{label}"
        agg_res = run_cli(["aggregate"], home=home, cwd=repo_path)
        assert agg_res.returncode == 0, agg_res.stderr
        render_res = run_cli(["render", "--out", str(out)], home=home, cwd=repo_path)
        assert render_res.returncode == 0, render_res.stderr
        return json.loads((out / "profile.json").read_text(encoding="utf-8"))

    # (i) excluded -> fail-closed, everything zero
    config["repositories"] = [
        {"path": original_path, "repository_uid": uid, "publication_level": "excluded"}
    ]
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    profile_i = render_and_load("i")
    assert profile_i["totals"] == _ZERO_TOTALS
    assert profile_i["providers"] == []
    assert profile_i["privacy"] == {
        "explicitly_publishable_commits": 0,
        "anonymous_aggregate_commits": 0,
        "includes_anonymous_aggregate": False,
    }

    # (ii) full -> all activity counts as public
    config["repositories"] = [
        {"path": original_path, "repository_uid": uid, "publication_level": "full"}
    ]
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    profile_ii = render_and_load("ii")
    assert profile_ii["totals"]["commits_scanned"] == 2
    assert profile_ii["privacy"] == {
        "explicitly_publishable_commits": 2,
        "anonymous_aggregate_commits": 0,
        "includes_anonymous_aggregate": False,
    }

    # (iii) repository entry removed entirely -> fail-closed, everything zero
    config["repositories"] = []
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    profile_iii = render_and_load("iii")
    assert profile_iii["totals"] == _ZERO_TOTALS
    assert profile_iii["privacy"] == {
        "explicitly_publishable_commits": 0,
        "anonymous_aggregate_commits": 0,
        "includes_anonymous_aggregate": False,
    }

    # (iv) duplicate uid: one "full" + one "aggregate_only" entry -> the most
    # restrictive level wins (schema.md section 9 restrictiveness order:
    # excluded > aggregate_only > repository_anonymous > full), regardless
    # of which entry is listed first.
    config["repositories"] = [
        {"path": original_path, "repository_uid": uid, "publication_level": "full"},
        {
            "path": original_path + "-dup",
            "repository_uid": uid,
            "publication_level": "aggregate_only",
        },
    ]
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    profile_iv = render_and_load("iv")
    assert profile_iv["totals"]["commits_scanned"] == 2
    assert profile_iv["privacy"] == {
        "explicitly_publishable_commits": 0,
        "anonymous_aggregate_commits": 2,
        "includes_anonymous_aggregate": True,
    }


# ---------------------------------------------------------------------------
# 6. Malformed repository (mvp.md section 7 test 14)
# ---------------------------------------------------------------------------


def test_malformed_repository(tmp_path, monkeypatch):
    """scan_repository calls gitio.assert_repository before anything else
    (scanner.py), so a bad path fails fast with GitError -> exit 1, even
    before identities are checked.

    GIT_CEILING_DIRECTORIES is pinned to tmp_path so git's upward repository
    search cannot escape the fixture and discover an ambient parent
    repository (this machine's home directory is itself a git work tree —
    without the ceiling, `not-a-repo` would be reported as "inside" that
    unrelated repository instead of correctly failing)."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    home = tmp_path / "home"
    assert run_cli(["init"], home=home, cwd=tmp_path).returncode == 0

    empty_dir = tmp_path / "not-a-repo"
    empty_dir.mkdir()
    res = run_cli(["scan", str(empty_dir)], home=home, cwd=tmp_path)
    assert res.returncode == 1
    assert "not a git repository" in res.stderr.lower()

    missing = tmp_path / "does-not-exist"
    res2 = run_cli(["scan", str(missing)], home=home, cwd=tmp_path)
    assert res2.returncode == 1
    assert res2.stderr.strip() != ""


# ---------------------------------------------------------------------------
# 7. Zero state
# ---------------------------------------------------------------------------


def test_zero_state_render(tmp_path):
    """A fresh home with no scanned repositories still renders valid,
    readable, zero-filled output (mvp.md section 7 test 13)."""
    home = tmp_path / "home"
    out = tmp_path / "dist"

    assert run_cli(["init"], home=home, cwd=tmp_path).returncode == 0
    render_res = run_cli(["render", "--out", str(out)], home=home, cwd=tmp_path)
    assert render_res.returncode == 0, render_res.stderr

    profile = json.loads((out / "profile.json").read_text(encoding="utf-8"))
    assert profile["totals"] == _ZERO_TOTALS
    assert profile["providers"] == []
    assert profile["provider_count"] == 0
    assert profile["evidence_records"] == {
        "verified": 0,
        "declared": 0,
        "imported": 0,
        "inferred": 0,
        "unknown": 0,
        "total_records": 0,
    }
    assert profile["privacy"] == {
        "explicitly_publishable_commits": 0,
        "anonymous_aggregate_commits": 0,
        "includes_anonymous_aggregate": False,
    }

    svg_text = (out / "summary-light.svg").read_text(encoding="utf-8")
    ET.fromstring(svg_text)  # raises ParseError if this is not well-formed XML
    assert "No AI collaboration recorded yet" in svg_text


# ---------------------------------------------------------------------------
# 8. Export stability (mvp.md section 7 test 17)
# ---------------------------------------------------------------------------


def test_export_stability(tmp_path):
    """Rendering the same (unchanged) state twice on the same day must
    produce byte-identical assets: all three files, both runs."""
    home = tmp_path / "home"
    repo_path = tmp_path / "repo"
    build_repo(repo_path, _standard_commits())

    assert run_cli(["init"], home=home, cwd=repo_path).returncode == 0
    assert run_cli(["scan", str(repo_path)], home=home, cwd=repo_path).returncode == 0

    out1 = tmp_path / "dist1"
    out2 = tmp_path / "dist2"
    r1 = run_cli(["render", "--out", str(out1)], home=home, cwd=repo_path)
    r2 = run_cli(["render", "--out", str(out2)], home=home, cwd=repo_path)
    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr

    for name in ("summary-light.svg", "summary-dark.svg", "profile.json"):
        b1 = (out1 / name).read_bytes()
        b2 = (out2 / name).read_bytes()
        assert b1 == b2, f"{name} differs between two same-day renders"


# ---------------------------------------------------------------------------
# 9. Usage error
# ---------------------------------------------------------------------------


def test_usage_error_no_args(tmp_path):
    """No subcommand -> argparse usage error -> exit code 2 (mvp.md section 3:
    'all commands support -v and exit 0 / 1 (operational error) / 2 (usage)')."""
    home = tmp_path / "home"
    result = run_cli([], home=home, cwd=tmp_path)
    assert result.returncode == 2


# ---------------------------------------------------------------------------
# Diagnostics hygiene (gate round-2 P2; G2-08): default scan output carries
# scan-local ordinals, never commit SHAs; --verbose opts into the sha prefix.
# ---------------------------------------------------------------------------


def test_default_scan_warnings_use_ordinals_never_shas(tmp_path):
    home = tmp_path / "home"
    repo = tmp_path / "warnrepo"
    build_repo(
        repo,
        [
            ("plain first commit", "2026-02-01T10:00:00+08:00"),
            ("has a broken group\n\nAI-Model: Mystery-9", "2026-02-02T10:00:00+08:00"),
        ],
    )
    assert run_cli(["init"], home=home, cwd=repo).returncode == 0

    default_res = run_cli(["scan", str(repo)], home=home, cwd=repo)
    assert default_res.returncode == 0, default_res.stderr
    assert "incomplete-group" in default_res.stdout
    assert "commit #" in default_res.stdout
    combined = default_res.stdout + default_res.stderr
    assert not re.search(r"\b[0-9a-f]{40}\b", combined), combined
    assert not re.search(r"\[[0-9a-f]{12}\]", combined), combined

    verbose_res = run_cli(["-v", "scan", str(repo)], home=home, cwd=repo)
    assert verbose_res.returncode == 0, verbose_res.stderr
    assert re.search(r"\[[0-9a-f]{12}\]", verbose_res.stdout), verbose_res.stdout


# ---------------------------------------------------------------------------
# Gate-3 M-05: privacy canaries for the repository uid and a distinctive
# remote-organization string, and scanner-to-published-output permutation
# invariance.
# ---------------------------------------------------------------------------


def test_privacy_leak_remote_org_and_uid_canaries(tmp_path):
    home = tmp_path / "home"
    repo = tmp_path / "org-canary-repo"
    build_repo(
        repo,
        [
            (
                "AI commit\n\nAI-Provider: Anthropic\nAI-Tool: Claude-Code",
                "2026-04-01T10:00:00+00:00",
            ),
            ("plain", "2026-04-02T10:00:00+00:00"),
        ],
    )
    subprocess.run(
        ["git", "remote", "add", "origin",
         "https://github.com/secret-zebra-org/secret-repo-x9.git"],
        cwd=str(repo), check=True, capture_output=True,
    )
    out = tmp_path / "dist"
    assert run_cli(["init"], home=home, cwd=repo).returncode == 0
    assert run_cli(["scan", str(repo)], home=home, cwd=repo).returncode == 0
    assert run_cli(["render", "--out", str(out)], home=home, cwd=repo).returncode == 0

    cfg = json.loads((home / "config.json").read_text(encoding="utf-8"))
    uid = cfg["repositories"][0]["repository_uid"]
    assert "secret-zebra-org" in uid  # the uid itself embeds the org...
    salt = cfg["salt"]

    for asset in out.iterdir():
        blob = asset.read_text(encoding="utf-8")
        for canary in ("secret-zebra-org", "secret-repo-x9", uid, salt):
            assert canary not in blob, f"{asset.name} leaked {canary[:24]}..."


def test_published_outputs_invariant_under_trailer_reordering(tmp_path):
    """Scanner -> storage -> aggregate -> publication permutation invariance
    (M-05): the same evidence with reordered trailer lines must publish a
    byte-identical profile.json."""
    profiles = []
    orders = [
        "Multi-AI\n\nAI-Provider: Anthropic\nAI-Tool: Claude-Code\n"
        "AI-Provider: OpenAI\nAI-Tool: Codex-CLI\n"
        "Co-Authored-By: Claude <noreply@anthropic.com>",
        "Multi-AI\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"
        "AI-Provider: OpenAI\nAI-Tool: Codex-CLI\n"
        "AI-Provider: Anthropic\nAI-Tool: Claude-Code",
    ]
    for i, message in enumerate(orders):
        home = tmp_path / f"home{i}"
        repo = tmp_path / f"repo{i}"
        out = tmp_path / f"dist{i}"
        build_repo(repo, [(message, "2026-04-03T10:00:00+00:00")])
        assert run_cli(["init"], home=home, cwd=repo).returncode == 0
        assert run_cli(["scan", str(repo)], home=home, cwd=repo).returncode == 0
        assert run_cli(["render", "--out", str(out)], home=home, cwd=repo).returncode == 0
        profiles.append((out / "profile.json").read_bytes())
    assert profiles[0] == profiles[1]

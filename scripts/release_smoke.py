#!/usr/bin/env python3
"""Packaged clean-install smoke test.

Implements the ROADMAP "v0.1 OSS release" exit criterion "clean-install/
packaged smoke test" (docs/ROADMAP.md).

WHEN TO RUN: manually, once, right before tagging a release. It is
deliberately NOT part of `python -m pytest` and is NOT collected by pytest
(it lives outside `tests/`, which is the sole pytest `testpaths` root per
pyproject.toml, and its filename does not match pytest's `test_*` pattern).
The default suite is network-free by contract (CONTRIBUTING.md) — but
installing this project through its declared PEP 517 build backend
(hatchling, pyproject.toml `[build-system]`) requires either fetching that
backend from PyPI (a normal `pip install`) or having it already resolvable
locally and skipping pip's own isolated build environment
(`--no-build-isolation`). Either path is real, deliberate network use by
RELEASE TOOLING ONLY — never by the test suite.

WHAT IT DOES: creates a throwaway venv, installs the current working tree
non-editably into it (exactly like an end user's `pip install ai-profile`
would, not `pip install -e .`), then drives the INSTALLED `aiprofile`
console script (not `python -m aiprofile`, so the packaging entry point
itself is exercised) through init -> scan -> aggregate -> render against a
synthetic git repository, and finally re-runs the same privacy canary
byte-sweep the integration suite runs against every dist/ file (see
tests/integration/test_end_to_end.py's leak tests and docs/PRIVACY.md).

Usage:

    python scripts/release_smoke.py

Prints PASS/FAIL for each step as it runs. Exit code 0 only if every step
passed; exit code 1 on the first failure (fail-fast: later steps depend on
earlier ones, so there is nothing useful to attempt once install or scan
fails).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import venv
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TIMEOUT_SHORT = 60
TIMEOUT_INSTALL = 600

FIXTURE_AUTHOR_EMAIL = "smoke-fixture@example.com"
FIXTURE_AUTHOR_NAME = "Smoke Fixture"

_PASS = "PASS"
_FAIL = "FAIL"

_EXPECTED_DIST_FILES = ["profile.json", "summary-dark.svg", "summary-light.svg"]


class SmokeFailure(RuntimeError):
    """Raised by a step to abort the run; the message is the failure reason."""


def step(name: str, fn):
    """Run one step, print PASS/FAIL, and re-raise (as SmokeFailure) on
    failure so the caller can fail fast."""
    print(f"[STEP] {name}", flush=True)
    try:
        result = fn()
    except SmokeFailure as exc:
        print(f"{_FAIL}: {name}\n  {exc}", flush=True)
        raise
    except Exception as exc:  # convert any unexpected error into a clear FAIL
        print(f"{_FAIL}: {name}\n  unexpected error: {exc}", flush=True)
        raise SmokeFailure(str(exc)) from exc
    else:
        print(f"{_PASS}: {name}", flush=True)
        return result


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None,
          timeout: int = TIMEOUT_SHORT) -> subprocess.CompletedProcess:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    if result.returncode != 0:
        raise SmokeFailure(
            f"command failed (rc={result.returncode}): {' '.join(cmd)}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def _venv_python_path(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _console_script_path(venv_dir: Path) -> Path:
    if os.name == "nt":
        exe = venv_dir / "Scripts" / "aiprofile.exe"
    else:
        exe = venv_dir / "bin" / "aiprofile"
    if not exe.exists():
        raise SmokeFailure(
            f"installed console script not found at {exe} "
            "(pyproject.toml [project.scripts] entry point did not land)"
        )
    return exe


def _create_venv(venv_dir: Path) -> None:
    venv.EnvBuilder(with_pip=True, clear=True).create(str(venv_dir))
    python = _venv_python_path(venv_dir)
    if not python.exists():
        raise SmokeFailure(f"venv python not found at {python}")


def _hatchling_importable_here() -> bool:
    """Is the PEP 517 build backend already resolvable in THIS process
    (the one running release_smoke.py)? If so, its wheel is very likely
    already sitting in the local pip cache, so pre-installing it into the
    throwaway venv is cheap, and building with --no-build-isolation avoids
    pip spinning up a SECOND, separate isolated build environment that
    would fetch hatchling (and its own build deps) all over again."""
    return importlib.util.find_spec("hatchling") is not None


def _install_repo(venv_python: Path) -> str:
    if _hatchling_importable_here():
        try:
            _run(
                [str(venv_python), "-m", "pip", "install", "-q", "hatchling"],
                timeout=TIMEOUT_INSTALL,
            )
        except SmokeFailure:
            pass  # fall through to the plain, fully-isolated install below
        else:
            _run(
                [
                    str(venv_python), "-m", "pip", "install", "-q",
                    "--no-build-isolation", str(REPO_ROOT),
                ],
                timeout=TIMEOUT_INSTALL,
            )
            return (
                "pip install --no-build-isolation (hatchling importable in"
                " this interpreter; other build needs may still hit network)"
            )
    _run(
        [str(venv_python), "-m", "pip", "install", "-q", str(REPO_ROOT)],
        timeout=TIMEOUT_INSTALL,
    )
    return "plain pip install [NETWORK: PEP 517 isolated build env fetches hatchling]"


def _git(args: list[str], cwd: Path, *, env: dict | None = None) -> None:
    _run(["git", *args], cwd=cwd, env=env, timeout=TIMEOUT_SHORT)


def build_synthetic_repo(root: Path) -> Path:
    """A small, throwaway git repo covering unknown / ai / human / raw-
    unrecognized-provider commit shapes (mirrors the eight-commit fixture
    in tests/integration/test_end_to_end.py, trimmed for a fast smoke run)
    plus a distinctive directory name and remote org, both used as privacy
    canaries below."""
    repo = root / "secret-smoke-vault-42"
    repo.mkdir(parents=True)
    _git(["init", "-q"], repo)
    _git(["config", "user.email", FIXTURE_AUTHOR_EMAIL], repo)
    _git(["config", "user.name", FIXTURE_AUTHOR_NAME], repo)
    _git(["config", "core.autocrlf", "false"], repo)

    commits = [
        # a. plain commit, no trailers -> unknown
        ("plain commit, no trailers", "2026-01-01T12:00:00+00:00"),
        # b. Claude AI-* commit -> one ai actor presence
        (
            "Claude AI-* commit\n\n"
            "AI-Provider: Anthropic\nAI-Tool: Claude-Code\nAI-Role: implementation",
            "2026-01-02T12:00:00+00:00",
        ),
        # c. human-declared commit
        ("Human-declared commit\n\nAI-Mode: Human-Only", "2026-01-03T12:00:00+00:00"),
        # d. unrecognized-provider commit -> ai actor presence, unrecognized bucket
        (
            "Unrecognized-provider commit\n\nAI-Provider: Zzz-Custom-LLM-9000",
            "2026-01-04T12:00:00+00:00",
        ),
    ]
    target = repo / "content.txt"
    for index, (message, author_date_iso) in enumerate(commits):
        target.write_text(f"commit {index}\n", encoding="utf-8")
        _git(["add", "content.txt"], repo)
        env = dict(os.environ)
        env["GIT_AUTHOR_NAME"] = FIXTURE_AUTHOR_NAME
        env["GIT_AUTHOR_EMAIL"] = FIXTURE_AUTHOR_EMAIL
        env["GIT_AUTHOR_DATE"] = author_date_iso
        env["GIT_COMMITTER_NAME"] = FIXTURE_AUTHOR_NAME
        env["GIT_COMMITTER_EMAIL"] = FIXTURE_AUTHOR_EMAIL
        env["GIT_COMMITTER_DATE"] = author_date_iso
        _git(["commit", "-q", "-m", message], repo, env=env)

    _git(
        ["remote", "add", "origin",
         "https://github.com/secret-smoke-org/secret-smoke-repo.git"],
        repo,
    )
    return repo


def _run_cli(exe: Path, args: list[str], *, home: Path, cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["AIPROFILE_HOME"] = str(home)
    return _run([str(exe), *args], cwd=cwd, env=env, timeout=TIMEOUT_SHORT)


def _check_profile_json(out_dir: Path) -> dict:
    path = out_dir / "profile.json"
    if not path.exists():
        raise SmokeFailure(f"missing {path}")
    data = json.loads(path.read_text(encoding="utf-8"))

    # Hand-derived from build_synthetic_repo's four commits (same method as
    # test_end_to_end.py's happy-path derivation comment):
    #   a unknown(1)  b ai(1, anthropic)  c human(1)  d ai(1, unrecognized)
    expected_totals = {
        "commits_scanned": 4,
        "ai_attributed_commits": 2,  # b, d
        "ai_actor_presences": 2,  # b1 + d1
        "human_declared_commits": 1,  # c
        "unknown_commits": 1,  # a
        "active_ai_days": 2,  # Jan 2, Jan 4
    }
    if data.get("totals") != expected_totals:
        raise SmokeFailure(f"unexpected totals: {data.get('totals')!r} != {expected_totals!r}")
    return data


def _check_svgs(out_dir: Path) -> None:
    for name in ("summary-light.svg", "summary-dark.svg"):
        path = out_dir / name
        if not path.exists():
            raise SmokeFailure(f"missing {path}")
        try:
            ET.fromstring(path.read_text(encoding="utf-8"))
        except ET.ParseError as exc:
            raise SmokeFailure(f"{name} is not well-formed XML: {exc}") from exc


def _canary_sweep(out_dir: Path, home: Path, repo: Path) -> None:
    """Grep every published byte for values that must never appear there —
    the same class of check as test_privacy_leak / test_privacy_leak_
    remote_org_and_uid_canaries in tests/integration/test_end_to_end.py,
    re-run here against the actually-installed package's actual output."""
    config = json.loads((home / "config.json").read_text(encoding="utf-8"))
    salt = config.get("salt")
    if not salt:
        raise SmokeFailure("config.json has no salt to canary-check")

    forbidden = [
        repo.name,  # "secret-smoke-vault-42"
        "secret-smoke-org",
        "secret-smoke-repo",
        FIXTURE_AUTHOR_EMAIL,
        "Zzz-Custom-LLM-9000",  # raw unrecognized AI-Provider value
        salt,
    ]

    dist_files = sorted(p for p in out_dir.rglob("*") if p.is_file())
    names = [p.name for p in dist_files]
    if names != _EXPECTED_DIST_FILES:
        raise SmokeFailure(f"unexpected dist/ file set: {names} != {_EXPECTED_DIST_FILES}")

    for path in dist_files:
        blob = path.read_bytes().decode("utf-8", errors="replace")
        for needle in forbidden:
            if needle in blob:
                raise SmokeFailure(f"canary {needle!r} leaked into {path.name}")


def main() -> int:
    tmp_root = Path(tempfile.mkdtemp(prefix="aiprofile-release-smoke-"))
    print(f"[release_smoke] scratch directory: {tmp_root}")
    try:
        venv_dir = tmp_root / "venv"
        home = tmp_root / "home"
        out_dir = tmp_root / "dist"

        step("create throwaway venv", lambda: _create_venv(venv_dir))
        venv_python = _venv_python_path(venv_dir)

        mode = step(
            "pip-install ai-profile into venv (non-editable)",
            lambda: _install_repo(venv_python),
        )
        print(f"    install mode: {mode}")

        exe = step("locate installed console script", lambda: _console_script_path(venv_dir))

        repo = step("build synthetic trailer repo", lambda: build_synthetic_repo(tmp_root))

        step("aiprofile init", lambda: _run_cli(exe, ["init"], home=home, cwd=repo))
        step("aiprofile scan", lambda: _run_cli(exe, ["scan", str(repo)], home=home, cwd=repo))
        step("aiprofile aggregate", lambda: _run_cli(exe, ["aggregate"], home=home, cwd=repo))
        step(
            "aiprofile render",
            lambda: _run_cli(exe, ["render", "--out", str(out_dir)], home=home, cwd=repo),
        )

        step("profile.json structural sanity", lambda: _check_profile_json(out_dir))
        step("SVG well-formedness", lambda: _check_svgs(out_dir))
        step(
            "canary byte-sweep of dist outputs",
            lambda: _canary_sweep(out_dir, home, repo),
        )
    except SmokeFailure:
        print("\nRESULT: FAIL - see the FAIL step above", flush=True)
        return 1
    except Exception as exc:  # belt-and-suspenders: never traceback bare
        print(f"\nRESULT: FAIL - unexpected error: {exc}", flush=True)
        return 1
    else:
        print("\nRESULT: PASS - all steps green", flush=True)
        return 0
    finally:
        _cleanup_tmp(tmp_root)


def _cleanup_tmp(tmp_root: Path) -> None:
    """Windows-safe removal with an honest failure signal.

    git creates read-only loose objects under .git/objects/ that
    shutil.rmtree's default remover refuses to delete on Windows;
    ignore_errors=True previously hid that, silently littering %TEMP%
    with leftovers on every run while still printing PASS. Clear the
    read-only bit and retry per-path; if anything STILL remains, say so
    (synthetic fixture data only - never real user data - but a
    "throwaway" claim should be true or flagged)."""

    def _clear_readonly(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(tmp_root, onexc=_clear_readonly)
        else:  # onerror passes (func, path, exc_info-tuple)
            shutil.rmtree(
                tmp_root, onerror=lambda f, p, ei: _clear_readonly(f, p, ei[1])
            )
    except OSError as exc:
        print(f"WARN: cleanup incomplete under {tmp_root}: {exc}", flush=True)
    if tmp_root.exists():
        print(f"WARN: leftover files remain under {tmp_root}", flush=True)


if __name__ == "__main__":
    sys.exit(main())

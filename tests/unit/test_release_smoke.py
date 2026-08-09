"""Focused regressions for the packaged release smoke."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "release_smoke.py"
SPEC = importlib.util.spec_from_file_location("release_smoke", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def _profile(directory: Path, generated_on: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "profile.json").write_text(
        json.dumps({"generated_on": generated_on}),
        encoding="utf-8",
    )


def test_render_pair_retries_after_utc_date_rollover(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    _profile(first, "2026-07-26")
    _profile(second, "2026-07-27")
    calls: list[str] = []

    def render_first() -> None:
        calls.append("first")
        _profile(first, "2026-07-27")

    def render_second() -> None:
        calls.append("second")
        _profile(second, "2026-07-27")

    smoke._stabilize_render_dates(first, second, render_first, render_second)

    assert calls == ["first", "second"]


def test_determinism_diagnostic_lists_only_changed_files(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "same.svg").write_text("same", encoding="utf-8")
    (second / "same.svg").write_text("same", encoding="utf-8")
    (first / "changed.svg").write_text("before", encoding="utf-8")
    (second / "changed.svg").write_text("after", encoding="utf-8")

    try:
        smoke._assert_deterministic(first, second)
    except smoke.SmokeFailure as exc:
        assert str(exc) == "repeat render was not byte-identical: ['changed.svg']"
    else:
        raise AssertionError("expected deterministic comparison to fail")


# ---------------------------------------------------------------------------
# v0.7.0 Task A6: the smoke produces its asset bundle via `aiprofile
# refresh` (twice, for the byte-identical repeated-output check) plus one
# `--dry-run` faithfulness proof - and no longer relies on `aiprofile
# render` for asset production at all.
# ---------------------------------------------------------------------------


def test_smoke_source_produces_assets_via_refresh_not_render():
    source = SCRIPT.read_text(encoding="utf-8")
    # Two full refresh runs (out_dir + repeat_dir) feed the determinism
    # check; a further dry-run invocation proves wheel-level faithfulness.
    assert source.count('["refresh", "--out"') >= 2
    assert '"--dry-run"' in source
    # The render step is gone: the eight outputs come from refresh only.
    assert '["render"' not in source


def test_dry_run_no_change_output_contract():
    smoke._assert_no_change_output("no changes: published assets are up to date\n")
    for bad in ("would update: profile.json\n", ""):
        try:
            smoke._assert_no_change_output(bad)
        except smoke.SmokeFailure:
            pass
        else:
            raise AssertionError(f"expected SmokeFailure for stdout {bad!r}")


def test_dir_state_detects_byte_and_mtime_changes(tmp_path):
    target = tmp_path / "x.txt"
    target.write_text("same", encoding="utf-8")
    first = smoke._dir_state(tmp_path)
    assert smoke._dir_state(tmp_path) == first  # stable when untouched
    os.utime(target, ns=(123_456_789, 987_654_321))
    assert smoke._dir_state(tmp_path) != first  # mtime-only change caught
    target.write_text("different", encoding="utf-8")
    assert smoke._dir_state(tmp_path) != first  # byte change caught


def test_dir_state_exempts_the_lock_file(tmp_path):
    (tmp_path / "kept.txt").write_text("kept", encoding="utf-8")
    first = smoke._dir_state(tmp_path)
    # The advisory lock is touched by design on every refresh (dry-run
    # included) - it must not count as mutation.
    (tmp_path / ".refresh.lock").write_text("held", encoding="utf-8")
    assert smoke._dir_state(tmp_path) == first


def test_refresh_dry_run_pair_retries_one_utc_rollover_deterministically(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    out = tmp_path / "dist"
    repo = tmp_path / "repo"
    for directory in (home, out, repo):
        directory.mkdir()
    (home / "config.json").write_text("{}", encoding="utf-8")

    real_dates = iter(("2026-08-09", "2026-08-10"))
    dry_outputs = iter(
        (
            "would update: profile.json\n",
            "no changes: published assets are up to date\n",
        )
    )
    calls: list[str] = []

    def fake_run_cli(exe, args, *, home, cwd):
        if "--dry-run" in args:
            calls.append("dry")
            return SimpleNamespace(stdout=next(dry_outputs))
        calls.append("real")
        _profile(out, next(real_dates))
        return SimpleNamespace(stdout="")

    today = iter(("2026-08-10", "2026-08-10"))
    monkeypatch.setattr(smoke, "_run_cli", fake_run_cli)
    monkeypatch.setattr(smoke, "_utc_today", lambda: next(today))

    smoke._check_dry_run_faithful(
        tmp_path / "aiprofile", home, out, repo, max_retries=2
    )

    assert calls == ["real", "dry", "real", "dry"]

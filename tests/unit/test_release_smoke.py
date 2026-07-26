"""Focused regressions for the packaged release smoke."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

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

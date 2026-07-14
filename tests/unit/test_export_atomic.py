"""Gate-3 M-07 regression: dist/ publication is bundle-atomic — a failure
mid-bundle leaves every previous-generation asset untouched. Confirmed
failing pre-fix (SVGs were already overwritten when JSON serialization
failed)."""

from __future__ import annotations

import pytest

import aiprofile.export as export_mod
from aiprofile.errors import RenderError


def test_partial_failure_leaves_previous_generation_intact(tmp_path, monkeypatch):
    out = tmp_path / "dist"
    out.mkdir()
    (out / "summary-light.svg").write_text("OLD-LIGHT", encoding="utf-8")
    (out / "summary-dark.svg").write_text("OLD-DARK", encoding="utf-8")
    (out / "profile.json").write_text("OLD-JSON", encoding="utf-8")

    def boom(_stats):
        raise RuntimeError("serialization exploded")

    monkeypatch.setattr(export_mod, "dumps_stats", boom)
    with pytest.raises((RenderError, RuntimeError)):
        export_mod.write_outputs(object(), "NEW-LIGHT", "NEW-DARK", out)

    assert (out / "summary-light.svg").read_text(encoding="utf-8") == "OLD-LIGHT"
    assert (out / "summary-dark.svg").read_text(encoding="utf-8") == "OLD-DARK"
    assert (out / "profile.json").read_text(encoding="utf-8") == "OLD-JSON"

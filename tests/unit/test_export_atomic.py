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


def test_replacement_stage_failure_rolls_back_previous_generation(tmp_path, monkeypatch):
    """Verification-review round: a failure at the SECOND os.replace must
    not leave a mixed generation — already-replaced targets roll back.
    Confirmed failing pre-fix (summary-light.svg stayed new)."""
    import os as os_mod

    from aiprofile.viz import (
        EvidenceTotals,
        Period,
        PrivacySplit,
        Totals,
        VizStats,
    )

    stats = VizStats(
        schema_version="0.1.0",
        period=Period(None, None, "All time"),
        totals=Totals(0, 0, 0, 0, 0, 0),
        providers=(),
        provider_count=0,
        evidence=EvidenceTotals(0, 0, 0, 0, 0, 0),
        privacy=PrivacySplit(0, 0, False),
        generated_on="2026-07-14",
    )
    out = tmp_path / "dist"
    out.mkdir()
    (out / "summary-light.svg").write_text("OLD-LIGHT", encoding="utf-8")
    (out / "summary-dark.svg").write_text("OLD-DARK", encoding="utf-8")
    (out / "profile.json").write_text("OLD-JSON", encoding="utf-8")

    real_replace = os_mod.replace
    calls = {"n": 0}

    def flaky_replace(src, dst):
        # Fail only the NEW-content replace of the second target (models an
        # AV/permission lock on that file); backup moves and rollback
        # restores go through the real replace.
        if str(dst).endswith("summary-dark.svg") and str(src).endswith(".tmp"):
            calls["n"] += 1
            raise OSError("simulated replace failure")
        return real_replace(src, dst)

    monkeypatch.setattr(export_mod.os, "replace", flaky_replace)
    with pytest.raises(RenderError):
        export_mod.write_outputs(stats, "NEW-LIGHT", "NEW-DARK", out)
    assert calls["n"] >= 1, "the injected failure point was never reached"

    assert (out / "summary-light.svg").read_text(encoding="utf-8") == "OLD-LIGHT"
    assert (out / "summary-dark.svg").read_text(encoding="utf-8") == "OLD-DARK"
    assert (out / "profile.json").read_text(encoding="utf-8") == "OLD-JSON"


def test_first_ever_render_failure_publishes_nothing(tmp_path, monkeypatch):
    """Reviewer suggestion (verification round): on a FIRST-EVER render
    (no prior generation), a mid-bundle failure must retract any
    just-installed asset — nothing published or everything published.
    Confirmed failing pre-fix (summary-light.svg stayed NEW)."""
    import os as os_mod

    from aiprofile.viz import (
        EvidenceTotals,
        Period,
        PrivacySplit,
        Totals,
        VizStats,
    )

    stats = VizStats(
        schema_version="0.1.0",
        period=Period(None, None, "All time"),
        totals=Totals(0, 0, 0, 0, 0, 0),
        providers=(),
        provider_count=0,
        evidence=EvidenceTotals(0, 0, 0, 0, 0, 0),
        privacy=PrivacySplit(0, 0, False),
        generated_on="2026-07-14",
    )
    out = tmp_path / "dist"  # does not exist yet: first-ever render

    real_replace = os_mod.replace

    def flaky_replace(src, dst):
        if str(dst).endswith("summary-dark.svg") and str(src).endswith(".tmp"):
            raise OSError("simulated replace failure")
        return real_replace(src, dst)

    monkeypatch.setattr(export_mod.os, "replace", flaky_replace)
    with pytest.raises(RenderError):
        export_mod.write_outputs(stats, "NEW-LIGHT", "NEW-DARK", out)

    leftovers = sorted(p.name for p in out.iterdir()) if out.exists() else []
    assert leftovers == [], leftovers

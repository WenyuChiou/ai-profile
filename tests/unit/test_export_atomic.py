"""Gate-3 M-07 regression: dist/ publication is bundle-atomic — a failure
mid-bundle leaves every previous-generation asset untouched. Confirmed
failing pre-fix (SVGs were already overwritten when JSON serialization
failed)."""

from __future__ import annotations

import pytest

import aiprofile.export as export_mod
from aiprofile import ACE_SCHEMA_VERSION
from aiprofile.errors import RenderError


def _zero_stats():
    from aiprofile.viz import (
        EvidenceTotals,
        Period,
        PrivacySplit,
        Totals,
        VizStats,
    )
    return VizStats(
        schema_version=ACE_SCHEMA_VERSION,
        period=Period(None, None, "All time"),
        totals=Totals(0, 0, 0, 0, 0, 0),
        providers=(),
        provider_count=0,
        evidence=EvidenceTotals(0, 0, 0, 0, 0, 0),
        privacy=PrivacySplit(0, 0, False),
        generated_on="2026-07-14",
    )


def test_dashboard_is_allowlisted_but_arbitrary_html_is_rejected(tmp_path):
    out = tmp_path / "dist"
    paths = export_mod.write_outputs(
        _zero_stats(),
        {"dashboard.html": "<!doctype html><title>dashboard</title>"},
        out,
    )
    assert [path.name for path in paths] == ["dashboard.html", "profile.json"]
    assert (out / "dashboard.html").read_text(encoding="utf-8").startswith("<!doctype")

    with pytest.raises(RenderError, match="unexpected asset"):
        export_mod.write_outputs(
            _zero_stats(),
            {"arbitrary.html": "<script>not allowlisted</script>"},
            out,
        )


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
        export_mod.write_outputs(
            object(),
            {"summary-light.svg": "NEW-LIGHT", "summary-dark.svg": "NEW-DARK"},
            out,
        )

    assert (out / "summary-light.svg").read_text(encoding="utf-8") == "OLD-LIGHT"
    assert (out / "summary-dark.svg").read_text(encoding="utf-8") == "OLD-DARK"
    assert (out / "profile.json").read_text(encoding="utf-8") == "OLD-JSON"


def test_replacement_stage_failure_rolls_back_previous_generation(tmp_path, monkeypatch):
    """Verification-review round: a failure at the SECOND os.replace must
    not leave a mixed generation — already-replaced targets roll back.
    Confirmed failing pre-fix (summary-light.svg stayed new)."""
    import os as os_mod

    stats = _zero_stats()
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
        export_mod.write_outputs(
            stats,
            {"summary-light.svg": "NEW-LIGHT", "summary-dark.svg": "NEW-DARK"},
            out,
        )
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

    stats = _zero_stats()
    out = tmp_path / "dist"  # does not exist yet: first-ever render

    real_replace = os_mod.replace

    def flaky_replace(src, dst):
        if str(dst).endswith("summary-dark.svg") and str(src).endswith(".tmp"):
            raise OSError("simulated replace failure")
        return real_replace(src, dst)

    monkeypatch.setattr(export_mod.os, "replace", flaky_replace)
    with pytest.raises(RenderError):
        export_mod.write_outputs(
            stats,
            {"summary-light.svg": "NEW-LIGHT", "summary-dark.svg": "NEW-DARK"},
            out,
        )

    leftovers = sorted(p.name for p in out.iterdir()) if out.exists() else []
    assert leftovers == [], leftovers


def test_m6_preexisting_user_backup_sentinel_survives(tmp_path):
    """Gate-4 M-6: publication staging must own its artifacts — a
    successful render must never clobber a user's own `<target>.bak`
    file. Confirmed failing pre-fix (sentinel destroyed)."""
    out = tmp_path / "dist"
    out.mkdir()
    (out / "summary-light.svg").write_text("OLD", encoding="utf-8")
    sentinel = out / "summary-light.svg.bak"
    sentinel.write_text("USER-SENTINEL", encoding="utf-8")

    export_mod.write_outputs(
        _zero_stats(),
        {"summary-light.svg": "NEW-L", "summary-dark.svg": "NEW-D"},
        out,
    )

    assert sentinel.read_text(encoding="utf-8") == "USER-SENTINEL"
    assert (out / "summary-light.svg").read_text(encoding="utf-8") == "NEW-L"


def test_m3_restore_failure_still_restores_remaining_assets(tmp_path, monkeypatch):
    """Gate-4 M-3: a failure DURING rollback must not abandon the other
    restorations — remaining assets are restored and the failed asset's
    backup is retained as recovery data. Confirmed failing pre-fix
    (restore loop stopped at the first OSError)."""
    import os as os_mod

    out = tmp_path / "dist"
    out.mkdir()
    for name, content in (
        ("summary-light.svg", "OLD-LIGHT"),
        ("summary-dark.svg", "OLD-DARK"),
        ("profile.json", "OLD-JSON"),
    ):
        (out / name).write_text(content, encoding="utf-8")

    real_replace = os_mod.replace

    def flaky_replace(src, dst):
        s, d = str(src), str(dst)
        # fail installing the LAST target's new content...
        if d.endswith("profile.json") and ".tmp" in s:
            raise OSError("install failure")
        # ...and fail restoring the FIRST target during rollback
        if d.endswith("summary-light.svg") and ".bak" in s:
            raise OSError("restore failure")
        return real_replace(src, dst)

    monkeypatch.setattr(export_mod.os, "replace", flaky_replace)
    with pytest.raises(RenderError):
        export_mod.write_outputs(
            _zero_stats(),
            {"summary-light.svg": "NEW-L", "summary-dark.svg": "NEW-D"},
            out,
        )

    # dark restored despite light's restore failing:
    assert (out / "summary-dark.svg").read_text(encoding="utf-8") == "OLD-DARK"
    # json never replaced:
    assert (out / "profile.json").read_text(encoding="utf-8") == "OLD-JSON"
    # light's recovery data retained:
    baks = list(out.glob("summary-light.svg.*.bak"))
    assert baks and baks[0].read_text(encoding="utf-8") == "OLD-LIGHT"


def test_l1_cleanup_failure_does_not_report_publication_failure(tmp_path, monkeypatch):
    """Gate-4 L-1: once every new target is installed, publication has
    succeeded — a backup-cleanup unlink failure must not raise.
    Confirmed failing pre-fix (RenderError after full publication)."""
    out = tmp_path / "dist"
    out.mkdir()
    (out / "summary-light.svg").write_text("OLD", encoding="utf-8")

    from pathlib import Path as _P

    real_unlink = _P.unlink

    def flaky_unlink(self, missing_ok=False):
        if str(self).endswith(".bak"):
            raise OSError("cleanup failure")
        return real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(_P, "unlink", flaky_unlink)
    paths = export_mod.write_outputs(
        _zero_stats(),
        {"summary-light.svg": "NEW-L", "summary-dark.svg": "NEW-D"},
        out,
    )
    # D4: bundle order is sorted-by-name (deterministic), json last.
    assert [p.name for p in paths] == [
        "summary-dark.svg", "summary-light.svg", "profile.json"
    ]
    assert (out / "summary-light.svg").read_text(encoding="utf-8") == "NEW-L"


def test_m02_attempt_scoped_names_protect_recovery_data_within_process(
    tmp_path, monkeypatch
):
    """Gate-5 M-02: transaction artifacts must be ATTEMPT-owned, not
    process-owned — after a failed render retains a recovery `.bak`, a
    later successful render in the SAME process must not consume or
    destroy it. Confirmed failing pre-fix (pid-only names collide: the
    second render overwrote, then deleted, the recovery data)."""
    import os as os_mod

    out = tmp_path / "dist"
    out.mkdir()
    for name, content in (
        ("summary-light.svg", "OLD-LIGHT"),
        ("summary-dark.svg", "OLD-DARK"),
        ("profile.json", "OLD-JSON"),
    ):
        (out / name).write_text(content, encoding="utf-8")

    real_replace = os_mod.replace
    inject = {"on": True}

    def flaky_replace(src, dst):
        s, d = str(src), str(dst)
        if inject["on"]:
            if d.endswith("profile.json") and ".tmp" in s:
                raise OSError("install failure")
            if d.endswith("summary-light.svg") and ".bak" in s:
                raise OSError("restore failure")
        return real_replace(src, dst)

    monkeypatch.setattr(export_mod.os, "replace", flaky_replace)
    with pytest.raises(RenderError):
        export_mod.write_outputs(
            _zero_stats(),
            {"summary-light.svg": "NEW-L1", "summary-dark.svg": "NEW-D1"},
            out,
        )

    recovery = list(out.glob("summary-light.svg.*.bak"))
    assert len(recovery) == 1
    assert recovery[0].read_text(encoding="utf-8") == "OLD-LIGHT"

    inject["on"] = False
    export_mod.write_outputs(
        _zero_stats(),
        {"summary-light.svg": "NEW-L2", "summary-dark.svg": "NEW-D2"},
        out,
    )

    # The second render owned its own artifacts: the first attempt's
    # recovery backup survives byte-identical.
    assert recovery[0].exists(), "recovery .bak was consumed by a later render"
    assert recovery[0].read_text(encoding="utf-8") == "OLD-LIGHT"
    assert (out / "summary-light.svg").read_text(encoding="utf-8") == "NEW-L2"


def test_l01_failed_first_install_retraction_named_in_error(tmp_path, monkeypatch):
    """Gate-5 L-01: when rollback cannot RETRACT a first-ever installed
    target, the raised error must name the asset that remains published —
    a programmatic caller sees only the exception. Confirmed failing
    pre-fix (retraction failure was log-only)."""
    import os as os_mod
    from pathlib import Path as _P

    out = tmp_path / "dist"  # first-ever render: no previous generation

    real_replace = os_mod.replace

    # D4 bundle order is sorted-by-name: dark installs FIRST, so the
    # install failure targets light (second) and the retraction failure
    # targets dark (the already-installed first asset).
    def flaky_replace(src, dst):
        if str(dst).endswith("summary-light.svg") and ".tmp" in str(src):
            raise OSError("install failure")
        return real_replace(src, dst)

    real_unlink = _P.unlink

    def flaky_unlink(self, missing_ok=False):
        if str(self).endswith("summary-dark.svg"):
            raise OSError("retraction failure")
        return real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(export_mod.os, "replace", flaky_replace)
    monkeypatch.setattr(_P, "unlink", flaky_unlink)
    with pytest.raises(RenderError) as err:
        export_mod.write_outputs(
            _zero_stats(),
            {"summary-light.svg": "NEW-L", "summary-dark.svg": "NEW-D"},
            out,
        )

    assert "summary-dark.svg" in str(err.value)
    # the partial asset really is still published:
    assert (out / "summary-dark.svg").read_text(encoding="utf-8") == "NEW-D"


def test_gate6_stale_debris_from_pid_reuse_never_clobbered(tmp_path, monkeypatch):
    """Gate-6 M-01: `<pid>-<counter>` repeats after process restart plus
    PID reuse — a new process's first render must not overwrite a dead
    process's retained recovery artifact that happens to carry the same
    name. Simulated by resetting the counter while the PID stays
    constant. Confirmed failing pre-fix (recovery .bak overwritten, then
    deleted)."""
    import itertools
    import os as os_mod

    out = tmp_path / "dist"
    out.mkdir()
    (out / "summary-light.svg").write_text("CURRENT", encoding="utf-8")

    # A dead process with THIS pid left its first attempt's artifacts:
    stale_bak = out / f"summary-light.svg.{os_mod.getpid()}-1.bak"
    stale_bak.write_text("RECOVERY-ONLY-COPY", encoding="utf-8")

    # New process, same pid: counter restarts at 1.
    monkeypatch.setattr(export_mod, "_ATTEMPT_IDS", itertools.count(1))

    export_mod.write_outputs(
        _zero_stats(),
        {"summary-light.svg": "NEW-L", "summary-dark.svg": "NEW-D"},
        out,
    )

    assert stale_bak.exists(), "pid-reuse render consumed the recovery artifact"
    assert stale_bak.read_text(encoding="utf-8") == "RECOVERY-ONLY-COPY"
    assert (out / "summary-light.svg").read_text(encoding="utf-8") == "NEW-L"

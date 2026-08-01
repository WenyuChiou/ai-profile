"""P1 release-integrity regression (v0.4.8 review): the sanctioned direct
snapshot writers must fail CLOSED on a mismatched aiprofile import origin.

Incident: in a Windows multi-worktree layout with an editable install
pointing at the outer main checkout, `python tests/unit/test_render_summary.py`
silently imported the OTHER checkout's renderer and overwrote governed
snapshots/assets with stale output while printing success. The fix is a
tests-only provenance helper (`tests/unit/_snapshot_provenance.py`): direct
execution bootstraps this worktree's `src` ahead of any install, and every
governed write refuses unless the imported `aiprofile` package resolves
beneath THIS worktree's `src/aiprofile` tree.

The end-to-end test below is behavioral, not string-presence: it drives the
real writer entry points with a mismatched origin and proves zero governed
bytes change.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def _load_provenance():
    spec = importlib.util.spec_from_file_location(
        "_snapshot_provenance_under_test", HERE / "_snapshot_provenance.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prov = _load_provenance()

#: Every governed file the two sanctioned writers may write: the snapshot
#: families plus the committed docs sample assets. Banner/social assets are
#: hand-authored and deliberately excluded.
GOVERNED = sorted(
    list((ROOT / "tests" / "snapshots").glob("*.svg"))
    + list((ROOT / "docs" / "assets").glob("*-sample-*.svg"))
)


def _digests() -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in GOVERNED}


def test_governed_file_inventory_is_nonempty():
    # 8 summary + 4 heatmap + 4 badge snapshots, 6 sample assets.
    assert len(GOVERNED) >= 20


def test_worktree_src_resolves_this_worktree():
    assert prov.worktree_src(HERE / "test_render_summary.py") == ROOT / "src"
    assert prov.worktree_src(HERE / "test_heatmap_svg.py") == ROOT / "src"


def test_matching_origin_is_accepted():
    import aiprofile

    prov.assert_aiprofile_from(HERE / "test_render_summary.py", aiprofile.__file__)


def test_mismatched_origin_raises_actionable_error(tmp_path):
    fake = tmp_path / "other-checkout" / "src" / "aiprofile" / "__init__.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("", encoding="utf-8")

    with pytest.raises(SystemExit, match="REFUSING"):
        prov.assert_aiprofile_from(HERE / "test_render_summary.py", str(fake))
    # The error must be actionable: it names both the wrong and the
    # expected location so the operator can fix the environment.
    with pytest.raises(SystemExit, match=r"src.aiprofile"):
        prov.assert_aiprofile_from(HERE / "test_render_summary.py", str(fake))


def test_stale_import_origin_cannot_write_governed_files(monkeypatch, tmp_path):
    """END-TO-END: with aiprofile resolving outside this worktree, every
    sanctioned write entry point refuses BEFORE its first write and every
    governed byte stays untouched."""
    import aiprofile

    fake = tmp_path / "stale-checkout" / "src" / "aiprofile" / "__init__.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("", encoding="utf-8")

    summary_writer = importlib.import_module("test_render_summary")
    heatmap_writer = importlib.import_module("test_heatmap_svg")

    before = _digests()
    monkeypatch.setattr(sys.modules["aiprofile"], "__file__", str(fake))
    for write in (
        summary_writer._write_all_snapshots,
        summary_writer._write_sample_assets,
        heatmap_writer._write_all_snapshots,
        heatmap_writer._write_sample_assets,
    ):
        with pytest.raises(SystemExit, match="REFUSING"):
            write()
    monkeypatch.setattr(sys.modules["aiprofile"], "__file__", aiprofile.__file__)

    assert _digests() == before, "a governed file changed despite the refusal"

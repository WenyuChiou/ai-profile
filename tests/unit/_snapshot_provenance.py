"""Sanctioned-writer import provenance guard (P1, v0.4.8 review round).

Tests-only helper — never imported by production code and never a
dependency. Two jobs:

1. ``bootstrap_direct_execution``: when a sanctioned writer is EXECUTED
   DIRECTLY (``python tests/unit/test_render_summary.py`` /
   ``python tests/unit/test_heatmap_svg.py``), prepend that script's own
   worktree ``src`` to ``sys.path`` BEFORE the first ``aiprofile``
   import, so an editable/site install pointing at another checkout can
   never shadow the worktree being regenerated.
2. ``assert_aiprofile_from``: fail CLOSED before any governed
   snapshot/sample write unless the imported ``aiprofile`` package
   actually resolves beneath that exact worktree's ``src/aiprofile``
   tree — the belt to the bootstrap's braces, and the guard pytest runs
   share (pytest's own ``pythonpath = ["src"]`` resolves the correct
   worktree already, so under pytest this check simply passes).

Incident being pinned: on Windows with a multi-worktree layout and an
editable install from the outer main checkout, the sanctioned direct
command silently imported the OTHER checkout's renderer and overwrote
governed snapshots with stale output while printing success.
"""

from __future__ import annotations

import sys
from pathlib import Path


def worktree_src(test_file: str | Path) -> Path:
    """``<worktree-root>/src`` for the worktree CONTAINING ``test_file``
    (the sanctioned writers live at ``<root>/tests/unit/<writer>.py``)."""
    return Path(test_file).resolve().parents[2] / "src"


def bootstrap_direct_execution(test_file: str | Path) -> None:
    """Prepend this worktree's ``src`` ahead of every install path.

    Call ONLY from a writer's direct-execution branch, before the first
    ``aiprofile`` import. A no-op once ``aiprofile`` is already imported
    (e.g. under pytest), because redirecting ``sys.path`` then would be
    too late to matter and must not disturb the running interpreter.
    """
    if "aiprofile" in sys.modules:
        return
    sys.path.insert(0, str(worktree_src(test_file)))


def assert_aiprofile_from(test_file: str | Path, aiprofile_file: str) -> None:
    """Fail closed unless ``aiprofile_file`` (the imported package's
    ``__file__``) lies beneath this worktree's ``src/aiprofile`` tree.

    Raises ``SystemExit`` with an actionable message naming both the
    wrong and the expected location. Must be called BEFORE the first
    governed write.
    """
    expected = (worktree_src(test_file) / "aiprofile").resolve()
    actual = Path(aiprofile_file).resolve().parent
    if actual != expected and expected not in actual.parents:
        raise SystemExit(
            "REFUSING to write governed snapshots/assets: the imported"
            f" aiprofile package resolves to {actual}, not this worktree's"
            f" {expected} (src/aiprofile). A stale editable or site install"
            " from another checkout is shadowing this worktree. Remove or"
            " bypass that install (e.g. rerun with PYTHONPATH="
            f"{expected.parent}) and regenerate again; no file was written."
        )

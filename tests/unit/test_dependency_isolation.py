"""Architecture invariant (architecture.md section 2): the renderer and
exporter module graphs must be structurally unable to reach storage, git, or
sqlite — they consume the validated VizStats contract only.

Orchestrator-owned test: uses a fresh interpreter so previously-imported
modules in the test process cannot mask a violation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_PROBE = """
import sys
import aiprofile.render.summary_svg
import aiprofile.render.themes
import aiprofile.export

banned = ("sqlite3", "subprocess", "aiprofile.storage", "aiprofile.gitio")
loaded = sorted(
    m for m in sys.modules
    if any(m == b or m.startswith(b + ".") for b in banned)
)
if loaded:
    print("BANNED MODULES LOADED: " + ", ".join(loaded))
    sys.exit(1)
print("ISOLATED")
"""


def test_render_and_export_never_load_storage_git_or_sqlite():
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""),
        },
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ISOLATED" in proc.stdout

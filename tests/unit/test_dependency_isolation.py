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
import aiprofile.render.dashboard_html
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


def test_static_ast_import_contract_for_render_and_export():
    """G2-16 + gate-3 M-02: static AST check over EVERY render/export module
    (recursively discovered, not a hard-coded list), against the FULL
    forbidden-edge set from architecture.md section 2, including dynamic
    import calls (importlib.import_module / __import__) where the runtime
    module-graph test could be blind."""
    import ast

    banned_roots = {
        "sqlite3",
        "subprocess",
        "aiprofile.storage",
        "aiprofile.gitio",
        "aiprofile.schema",
        "aiprofile.adapters",
        "aiprofile.config",
        "aiprofile.privacy",
        "aiprofile.aggregate",
        "aiprofile.scanner",
        "aiprofile.registry",
        "aiprofile.cli",
    }
    render_dir = REPO_ROOT / "src" / "aiprofile" / "render"
    files = sorted(render_dir.rglob("*.py")) + [
        REPO_ROOT / "src" / "aiprofile" / "export.py"
    ]
    assert len(files) >= 4, "render module discovery looks broken"

    def resolve_relative(module_file, node):
        # level=1 -> package dir of the file, level=2 -> its parent, etc.
        parts = module_file.relative_to(REPO_ROOT / "src").parts[:-1]
        base = list(parts)[: len(parts) - (node.level - 1)]
        if node.module:
            base.append(node.module)
        return ".".join(base)

    violations = []
    for f in files:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = resolve_relative(f, node)
                    names = [base] + [f"{base}.{a.name}" for a in node.names]
                else:
                    names = [node.module or ""]
            elif isinstance(node, ast.Call):
                func = node.func
                is_dynamic = (isinstance(func, ast.Name) and func.id == "__import__") or (
                    isinstance(func, ast.Attribute)
                    and func.attr == "import_module"
                )
                if is_dynamic:
                    violations.append(f"{f.name}: dynamic import call")
                continue
            for name in names:
                if any(name == b or name.startswith(b + ".") for b in banned_roots):
                    violations.append(f"{f.name}: {name}")
    assert not violations, violations

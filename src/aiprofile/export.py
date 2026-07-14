"""Asset export: VizStats (+ rendered SVGs) → dist/ (mvp.md section 5).

Consumes only the viz contract and pre-rendered strings — never storage,
git, or config (architecture.md section 2).
"""

from __future__ import annotations

from pathlib import Path

from .errors import RenderError
from .viz import VizStats, dumps_stats


def write_outputs(
    stats: VizStats, svg_light: str, svg_dark: str, out_dir: Path
) -> list[Path]:
    """Write summary-light.svg, summary-dark.svg, profile.json. Returns the
    written paths."""
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        targets = [
            (out_dir / "summary-light.svg", svg_light),
            (out_dir / "summary-dark.svg", svg_dark),
            (out_dir / "profile.json", dumps_stats(stats)),
        ]
        for path, content in targets:
            path.write_text(content, encoding="utf-8", newline="\n")
        return [p for p, _ in targets]
    except OSError as exc:
        raise RenderError(f"cannot write assets to {out_dir}: {exc}") from exc

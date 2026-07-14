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
    """Write summary-light.svg, summary-dark.svg, profile.json as ONE
    bundle (gate M-07): every asset goes to a same-directory temp file
    first, and targets are replaced only after the whole bundle succeeded —
    a mid-bundle failure leaves the previous generation fully intact, so a
    later README publish can never mix statistics from different scans.
    Returns the written paths."""
    import os

    tmp_paths: list[Path] = []
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        targets = [
            (out_dir / "summary-light.svg", svg_light),
            (out_dir / "summary-dark.svg", svg_dark),
            (out_dir / "profile.json", dumps_stats(stats)),
        ]
        for path, content in targets:
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(content, encoding="utf-8", newline="\n")
            tmp_paths.append(tmp)
        for (path, _), tmp in zip(targets, tmp_paths, strict=True):
            os.replace(tmp, path)
        return [p for p, _ in targets]
    except OSError as exc:
        raise RenderError(f"cannot write assets to {out_dir}: {exc}") from exc
    finally:
        for tmp in tmp_paths:
            tmp.unlink(missing_ok=True)

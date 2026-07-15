"""Asset export: VizStats (+ rendered SVGs) → dist/ (mvp.md section 5).

Consumes only the viz contract and pre-rendered strings — never storage,
git, or config (architecture.md section 2).
"""

from __future__ import annotations

import os
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
    tmp_paths: list[Path] = []
    backups: list[tuple[Path, Path]] = []  # (target, backup) of moved-aside olds
    completed: list[Path] = []  # targets already replaced with new content
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
        # Replacement stage with best-effort rollback (verification review,
        # 2026-07-14): sequential replaces alone left a mixed generation
        # when replace #2 failed. Old targets are moved aside first, so a
        # replacement-stage failure restores every already-replaced target
        # from its backup before re-raising.
        try:
            for (path, _), tmp in zip(targets, tmp_paths, strict=True):
                if path.exists():
                    bak = path.with_name(path.name + ".bak")
                    os.replace(path, bak)
                    backups.append((path, bak))
                os.replace(tmp, path)
                completed.append(path)
        except OSError:
            # Retract first-ever installs (no prior generation to restore):
            # nothing published or everything published (reviewer
            # suggestion, verification round).
            backed = {p for p, _ in backups}
            for path in completed:
                if path not in backed:
                    path.unlink(missing_ok=True)
            # Restore moved-aside olds, overwriting any installed news.
            # Best-effort residual (documented): if a restore itself fails
            # here (e.g. the target is still locked), the secondary OSError
            # propagates wrapped in RenderError and a mix can remain — the
            # window is one os.replace per pre-existing asset.
            for path, bak in backups:
                if bak.exists():
                    os.replace(bak, path)
            raise
        for _, bak in backups:
            bak.unlink(missing_ok=True)
        return [p for p, _ in targets]
    except OSError as exc:
        raise RenderError(f"cannot write assets to {out_dir}: {exc}") from exc
    finally:
        for tmp in tmp_paths:
            tmp.unlink(missing_ok=True)

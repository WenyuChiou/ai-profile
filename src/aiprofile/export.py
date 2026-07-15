"""Asset export: VizStats (+ rendered SVGs) → dist/ (mvp.md section 5).

Consumes only the viz contract and pre-rendered strings — never storage,
git, or config (architecture.md section 2).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .errors import RenderError
from .viz import VizStats, dumps_stats

logger = logging.getLogger(__name__)


def write_outputs(
    stats: VizStats, svg_light: str, svg_dark: str, out_dir: Path
) -> list[Path]:
    """Write summary-light.svg, summary-dark.svg, profile.json as ONE
    bundle (gate M-07): every asset goes to a same-directory temp file
    first, and targets are replaced only after the whole bundle rendered.

    Failure guarantee (gate-4 M-3 — best-effort, stated exactly): a
    replacement-stage failure rolls back by restoring every moved-aside
    previous asset and retracting first-ever installs. Every restore is
    ATTEMPTED even when one fails; an asset whose restore itself fails
    keeps its previous content on disk in its `.bak` file (named in the
    raised error) — so a mix limited to the unrestorable assets can
    remain in the worst case. This is weaker than "previous generation
    fully intact" and is the honest contract.

    Ownership (gate-4 M-6): staging/backup artifacts are attempt-owned —
    `<target>.<pid>.tmp` / `<target>.<pid>.bak` — so a render never
    touches a user's own `<target>.bak` and two processes never consume
    each other's transaction files. Concurrent renders into one output
    directory remain unserialized: each publishes a whole generation, but
    which generation wins is undefined — run one render at a time per
    directory. A hard-killed process can leave its own stale
    `.<pid>.tmp`/`.<pid>.bak` files behind; later renders never touch
    other attempts' artifacts, so such debris is harmless but requires
    manual cleanup.

    Returns the written paths."""
    suffix = f".{os.getpid()}"
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
            tmp = path.with_name(path.name + suffix + ".tmp")
            tmp.write_text(content, encoding="utf-8", newline="\n")
            tmp_paths.append(tmp)
        # Replacement stage with rollback (verification review, 2026-07-14):
        # sequential replaces alone left a mixed generation when replace #2
        # failed. Old targets are moved aside first, so a replacement-stage
        # failure can restore every already-replaced target from its backup.
        try:
            for (path, _), tmp in zip(targets, tmp_paths, strict=True):
                if path.exists():
                    bak = path.with_name(path.name + suffix + ".bak")
                    os.replace(path, bak)
                    backups.append((path, bak))
                os.replace(tmp, path)
                completed.append(path)
        except OSError as exc:
            # Retract first-ever installs (no prior generation to restore):
            # nothing published or everything published (reviewer
            # suggestion, verification round). Each retraction is
            # independent — a failed unlink must not abandon the rest.
            backed = {p for p, _ in backups}
            for path in completed:
                if path in backed:
                    continue
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("rollback could not retract %s", path.name)
            # Restore moved-aside olds, overwriting any installed news.
            # Gate-4 M-3: a restore failure no longer stops the loop —
            # every backup is attempted, and an unrestorable asset keeps
            # its .bak as recovery data, named in the raised error.
            unrestored: list[str] = []
            for path, bak in backups:
                if not bak.exists():
                    continue
                try:
                    os.replace(bak, path)
                except OSError:
                    unrestored.append(path.name)
            if unrestored:
                raise RenderError(
                    f"cannot write assets to {out_dir}: {exc} — rollback"
                    f" could not restore {', '.join(sorted(unrestored))};"
                    f" previous content retained in the matching"
                    f" *{suffix}.bak file(s)"
                ) from exc
            raise
        # Publication is complete once every new target is installed.
        # Backup cleanup happens after the point of success, so a cleanup
        # failure must not surface as a publication failure (gate-4 L-1):
        # warn and leave the debris.
        for _, bak in backups:
            try:
                bak.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                logger.warning(
                    "published OK, but could not remove backup %s: %s",
                    bak,
                    cleanup_exc,
                )
        return [p for p, _ in targets]
    except OSError as exc:
        raise RenderError(f"cannot write assets to {out_dir}: {exc}") from exc
    finally:
        for tmp in tmp_paths:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                logger.warning("could not remove staging file %s", tmp)

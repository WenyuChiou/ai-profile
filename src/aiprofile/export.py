"""Asset export: VizStats (+ rendered public assets) → dist/.

Consumes only the viz contract and pre-rendered strings — never storage,
git, or config (architecture.md section 2).
"""

from __future__ import annotations

import itertools
import logging
import os
import threading
from pathlib import Path

from .errors import RenderError
from .viz import VizStats, dumps_stats

logger = logging.getLogger(__name__)

#: Per-invocation transaction ids (gate-5 M-02): a pid alone identifies a
#: PROCESS, not a call — same-process concurrent/re-entrant renders would
#: share transaction filenames. The counter is lock-protected (gate-6: no
#: reliance on CPython bytecode atomicity) — but it restarts with the
#: process, so pid reuse could replay a dead process's names:
#: _transaction_suffix additionally probes the output directory and skips
#: any suffix with surviving artifacts (gate-6 M-01).
_ATTEMPT_IDS = itertools.count(1)
_ATTEMPT_LOCK = threading.Lock()


def _transaction_suffix(out_dir: Path, names: list[str]) -> str:
    """A transaction suffix owned by THIS invocation: unique among live
    processes (pid), unique within this process (counter), and — because
    a reused pid restarts the counter — verified against the output
    directory so a dead process's retained recovery artifacts are never
    adopted (gate-6 M-01)."""
    pid = os.getpid()
    while True:
        with _ATTEMPT_LOCK:
            n = next(_ATTEMPT_IDS)
        suffix = f".{pid}-{n}"
        stale = any(
            (out_dir / f"{name}{suffix}{ext}").exists()
            for name in names
            for ext in (".tmp", ".bak")
        )
        if not stale:
            return suffix


#: Exact filenames the bundle may publish. A closed allowlist, not a
#: pattern: the bundle writes into a user directory, so an unexpected
#: name is a caller bug worth failing loudly on. ``dashboard.html`` is
#: self-contained and receives only the same validated VizStats contract
#: as the SVG family (ADR-021).
_ALLOWED_ASSET_NAMES = frozenset(
    {
        "summary-light.svg",
        "summary-dark.svg",
        "heatmap-light.svg",
        "heatmap-dark.svg",
        "badge-light.svg",
        "badge-dark.svg",
        "dashboard.html",
    }
)


def write_outputs(stats: VizStats, assets: dict[str, str], out_dir: Path) -> list[Path]:
    """Write the rendered ``assets`` (filename -> markup, names from
    the closed ``_ALLOWED_ASSET_NAMES`` set) plus profile.json as ONE
    bundle (gate M-07): every asset goes to a same-directory temp file
    first, and targets are replaced only after the whole bundle rendered.

    Failure guarantee (gate-4 M-3 — best-effort, stated exactly): a
    replacement-stage failure rolls back by restoring every moved-aside
    previous asset and retracting first-ever installs. Every restore and
    every retraction is ATTEMPTED even when one fails; the raised error
    names each asset the rollback could NOT undo — an unrestorable asset
    keeps its previous content in its `.bak` file, and an unretractable
    first-install remains published (gate-5 L-01). This is weaker than
    "previous generation fully intact" and is the honest contract.

    Ownership (gate-4 M-6, gate-5 M-02): staging/backup artifacts are
    attempt-owned — `<target>.<pid>-<n>.tmp` / `<target>.<pid>-<n>.bak`
    with a per-invocation transaction id — so a render never touches a
    user's own `<target>.bak`, and overlapping calls (across processes OR
    within one) never consume each other's transaction files. The suffix
    is additionally probed against the output directory and created
    exclusively, so even a REUSED pid whose counter replays a dead
    process's numbers skips that process's surviving recovery artifacts
    (gate-6 M-01). The
    PUBLISHED targets carry no such protection: they are replaced
    independently with no directory lock, so concurrent publication into
    one output directory is NOT SUPPORTED — overlapping writers can
    interleave installs and rollbacks and leave a MIXED generation. Run
    one render at a time per directory. A hard-killed process can leave
    its own stale `.<pid>-<n>.tmp`/`.bak` files behind; later renders
    never touch other attempts' artifacts, so such debris is harmless but
    requires manual cleanup.

    Returns the written paths."""
    tmp_paths: list[Path] = []
    backups: list[tuple[Path, Path]] = []  # (target, backup) of moved-aside olds
    completed: list[Path] = []  # targets already replaced with new content
    unexpected = sorted(set(assets) - _ALLOWED_ASSET_NAMES)
    if unexpected:
        raise RenderError(
            f"refusing to publish unexpected asset name(s): {', '.join(unexpected)}"
        )
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        targets = [(out_dir / name, content) for name, content in sorted(assets.items())]
        targets.append((out_dir / "profile.json", dumps_stats(stats)))
        suffix = _transaction_suffix(out_dir, [p.name for p, _ in targets])
        for path, content in targets:
            tmp = path.with_name(path.name + suffix + ".tmp")
            # exclusive creation ("x"): if the name exists after all, the
            # attempt aborts rather than adopting foreign artifacts.
            with open(tmp, "x", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
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
            # independent — a failed unlink must not abandon the rest, and
            # the surviving partial asset is reported in the raised error
            # (gate-5 L-01), not only in logs.
            backed = {p for p, _ in backups}
            unretracted: list[str] = []
            for path in completed:
                if path in backed:
                    continue
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    unretracted.append(path.name)
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
            if unrestored or unretracted:
                problems = []
                if unrestored:
                    problems.append(
                        f"could not restore {', '.join(sorted(unrestored))}"
                        f" (previous content retained in the matching"
                        f" *{suffix}.bak file(s))"
                    )
                if unretracted:
                    problems.append(
                        f"could not retract {', '.join(sorted(unretracted))}"
                        " (the partial new content remains published)"
                    )
                raise RenderError(
                    f"cannot write assets to {out_dir}: {exc} - rollback"
                    f" incomplete: {'; '.join(problems)}"
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

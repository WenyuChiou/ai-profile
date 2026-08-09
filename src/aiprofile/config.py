"""Configuration: identities, salt, repository publication policy.

config.json is the ONLY home of publication policy (schema.md section 9,
ADR-009): the database stores none, events carry none, and aggregation
resolves levels from here at query time. This module is deliberately
git-free (identity seeding happens in cli.py).
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError, diagnostic_text
from .schema.vocab import PUBLICATION_RESTRICTIVENESS, PublicationLevel

CONFIG_NAME = "config.json"
DB_NAME = "aiprofile.db"

#: POSIX chmod failures get a stderr signal (a failing privacy feature
#: deserves one); Windows stays quiet (os.chmod there is a documented
#: no-op, not a failure). Module-level so tests can force the warning
#: branch deterministically on any platform.
_WARN_ON_CHMOD_FAILURE = sys.platform != "win32"


@dataclass
class RepoEntry:
    path: str
    repository_uid: str
    publication_level: PublicationLevel


@dataclass
class Config:
    identities: list[str] = field(default_factory=list)
    salt: str = ""
    repositories: list[RepoEntry] = field(default_factory=list)


def aiprofile_home() -> Path:
    env = os.environ.get("AIPROFILE_HOME")
    return Path(env) if env else Path.home() / ".aiprofile"


def config_path(home: Path) -> Path:
    return home / CONFIG_NAME


def db_path(home: Path) -> Path:
    return home / DB_NAME


def _restrict_to_owner(path: Path, mode: int) -> None:
    """Best-effort owner-only permissions (ROADMAP "owner-only file
    permissions where supported").

    POSIX: sets the requested mode (0o700 for directories, 0o600 for
    files) exactly. Windows: ``os.chmod`` cannot express POSIX owner/
    group/other bits at all - it only toggles the read-only attribute,
    and clearing it (which is what any mode with the owner-write bit set
    does) is a no-op against the default-writable files this code
    creates. Real Windows access control needs the ACL APIs (icacls /
    win32security), which is out of scope for v0.1. We call ``os.chmod``
    unconditionally anyway rather than branching on platform: on POSIX it
    does the real work, on Windows it is a harmless no-op, and every call
    site stays uniform. A failure (e.g. a filesystem that rejects chmod
    entirely) must never break config/db creation, so it is swallowed.
    """
    try:
        os.chmod(path, mode)
    except OSError:
        # On POSIX (where the bits are real) a failure deserves a signal,
        # not silence - this is a privacy feature. Windows stays quiet:
        # chmod there is a documented no-op, not a failure.
        if _WARN_ON_CHMOD_FAILURE:
            print(
                diagnostic_text(
                    "warning: could not restrict permissions on a private profile file",
                    f"warning: could not restrict permissions on {path}",
                ),
                file=sys.stderr,
            )


def init_home(home: Path, identities: list[str]) -> tuple[Config, bool]:
    """Create AIPROFILE_HOME with a fresh salt. Idempotent: an existing
    config is loaded and returned unchanged (created=False)."""
    if config_path(home).exists():
        return load_config(home), False
    # mode= narrows the creation-time window (no interval at umask-default
    # 0o755); the follow-up chmod covers pre-existing dirs (retrofit) and
    # platforms where mkdir's mode is umask-masked.
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    _restrict_to_owner(home, 0o700)
    cfg = Config(
        identities=[i.strip().lower() for i in identities if i.strip()],
        salt=secrets.token_hex(32),
        repositories=[],
    )
    save_config(home, cfg)
    return cfg, True


def load_config(home: Path) -> Config:
    path = config_path(home)
    if not path.exists():
        raise ConfigError(
            f"no configuration at {path} - run 'aiprofile init' first"
        )
    # Retrofit owner-only permissions on every load (gate-11 M-01): an
    # installation whose config.json predates the permission hardening
    # never passes through init_home's creation path, so this is the
    # choke point that reaches existing users - mirroring db.connect's
    # restrict-on-every-call. Cheap and idempotent.
    _restrict_to_owner(home, 0o700)
    _restrict_to_owner(path, 0o600)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be an object")
    salt = data.get("salt")
    if not isinstance(salt, str) or not salt:
        raise ConfigError(f"{path}: 'salt' missing or empty")
    identities = data.get("identities", [])
    if not isinstance(identities, list) or not all(
        isinstance(i, str) for i in identities
    ):
        raise ConfigError(f"{path}: 'identities' must be a list of strings")

    repos: list[RepoEntry] = []
    for i, raw in enumerate(data.get("repositories", [])):
        if not isinstance(raw, dict):
            raise ConfigError(f"{path}: repositories[{i}] must be an object")
        try:
            level = PublicationLevel(raw.get("publication_level"))
        except ValueError:
            allowed = ", ".join(
                lv.value
                for lv in PublicationLevel
                if lv is not PublicationLevel.REPOSITORY_ANONYMOUS
            )
            raise ConfigError(
                f"{path}: repositories[{i}].publication_level"
                f" {raw.get('publication_level')!r} is not one of [{allowed}]"
            ) from None
        if level is PublicationLevel.REPOSITORY_ANONYMOUS:
            raise ConfigError(
                f"{path}: repositories[{i}].publication_level"
                " 'repository_anonymous' is reserved for post-v0.1 (anonymous"
                " per-repository views do not exist yet - G2-12); use"
                " 'aggregate_only'"
            )
        p, uid = raw.get("path"), raw.get("repository_uid")
        if not isinstance(p, str) or not p or not isinstance(uid, str) or not uid:
            raise ConfigError(
                f"{path}: repositories[{i}] requires non-empty 'path' and"
                " 'repository_uid'"
            )
        repos.append(RepoEntry(path=p, repository_uid=uid, publication_level=level))
    return Config(
        identities=[i.strip().lower() for i in identities], salt=salt, repositories=repos
    )


def save_config(home: Path, cfg: Config) -> None:
    """Atomic write (tmp + replace); human-editable layout."""
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    _restrict_to_owner(home, 0o700)
    data = {
        "identities": cfg.identities,
        "repositories": [
            {
                "path": r.path,
                "repository_uid": r.repository_uid,
                "publication_level": r.publication_level.value,
            }
            for r in cfg.repositories
        ],
        "salt": cfg.salt,
    }
    path = config_path(home)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Restrict BEFORE the rename: os.replace is atomic and preserves the
    # source inode's mode bits on POSIX, so config.json never has a window
    # at default permissions after the swap.
    _restrict_to_owner(tmp, 0o600)
    os.replace(tmp, path)


def resolve_publication_levels(cfg: Config) -> dict[str, PublicationLevel]:
    """uid -> effective level; duplicate uids resolve to the MOST restrictive
    (schema.md section 9). A uid absent from the result is excluded
    (fail-closed) - callers must treat missing as EXCLUDED."""
    resolved: dict[str, PublicationLevel] = {}
    for entry in cfg.repositories:
        current = resolved.get(entry.repository_uid)
        if current is None or (
            PUBLICATION_RESTRICTIVENESS[entry.publication_level]
            > PUBLICATION_RESTRICTIVENESS[current]
        ):
            resolved[entry.repository_uid] = entry.publication_level
    return resolved


def effective_level(cfg: Config, repository_uid: str) -> PublicationLevel:
    """Effective level for one uid; EXCLUDED when unconfigured (fail-closed)."""
    return resolve_publication_levels(cfg).get(
        repository_uid, PublicationLevel.EXCLUDED
    )


def upsert_repository(
    cfg: Config, *, path: str, repository_uid: str, make_full: bool
) -> RepoEntry:
    """Register or update a repository entry at scan time (mvp.md section 3):
    new entries default to aggregate_only; --full raises to full; a repeat
    scan without --full never downgrades."""
    for entry in cfg.repositories:
        if entry.path == path:
            entry.repository_uid = repository_uid
            if make_full:
                entry.publication_level = PublicationLevel.FULL
            return entry
    entry = RepoEntry(
        path=path,
        repository_uid=repository_uid,
        publication_level=(
            PublicationLevel.FULL if make_full else PublicationLevel.AGGREGATE_ONLY
        ),
    )
    cfg.repositories.append(entry)
    return entry

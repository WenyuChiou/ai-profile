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
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError
from .schema.vocab import PUBLICATION_RESTRICTIVENESS, PublicationLevel

CONFIG_NAME = "config.json"
DB_NAME = "aiprofile.db"


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


def init_home(home: Path, identities: list[str]) -> tuple[Config, bool]:
    """Create AIPROFILE_HOME with a fresh salt. Idempotent: an existing
    config is loaded and returned unchanged (created=False)."""
    if config_path(home).exists():
        return load_config(home), False
    home.mkdir(parents=True, exist_ok=True)
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
            f"no configuration at {path} — run 'aiprofile init' first"
        )
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
            allowed = ", ".join(lv.value for lv in PublicationLevel)
            raise ConfigError(
                f"{path}: repositories[{i}].publication_level"
                f" {raw.get('publication_level')!r} is not one of [{allowed}]"
            ) from None
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
    home.mkdir(parents=True, exist_ok=True)
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
    os.replace(tmp, path)


def resolve_publication_levels(cfg: Config) -> dict[str, PublicationLevel]:
    """uid -> effective level; duplicate uids resolve to the MOST restrictive
    (schema.md section 9). A uid absent from the result is excluded
    (fail-closed) — callers must treat missing as EXCLUDED."""
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

"""Private, explicit per-commit declarations that survive full rescans.

The ledger is never an output asset. Each entry is bound to a canonical Git
origin (or a local root when there is no usable origin) and a reachable SHA.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from . import gitio
from .adapters.trailers import ParticipationSpec
from .errors import ConfigError
from .registry import normalize_provider, resolve_tool
from .schema.event import ProvenanceSource
from .schema.vocab import ActorType, ContributionMode, EvidenceLevel, SourceType

LEDGER_NAME = "attestations.json"
SECRET_LIMIT = 48 * 1024
LOCAL_LEDGER_LIMIT = 8 * 1024 * 1024
_SHA = re.compile(r"^[0-9a-f]{40}$")
_GITHUB_REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}/[A-Za-z0-9._-]{1,100}$")
_LABEL = re.compile(r"^[^\x00-\x1f\x7f:]{1,100}$")


def repository_key(path: Path) -> str:
    gitio.assert_repository(path)
    remote = gitio.get_origin_url(path)
    canonical = gitio.canonicalize_remote(remote) if remote else None
    return canonical if canonical is not None else f"local:{path.resolve()}"


def _validate_entry(value: object) -> dict[str, str | None]:
    if type(value) is not dict or set(value) != {"repo", "sha", "provider", "tool", "mode"}:
        raise ConfigError("private attestation has invalid fields")
    repo, sha, provider, tool, mode = (
        value[k] for k in ("repo", "sha", "provider", "tool", "mode")
    )
    if type(repo) is not str or not repo or len(repo) > 2048:
        raise ConfigError("private attestation has invalid repository identity")
    if repo.startswith("github.com/") and repo != repo.lower():
        raise ConfigError("private attestation repository identity is not canonical")
    if type(sha) is not str or _SHA.fullmatch(sha) is None:
        raise ConfigError("private attestation has invalid commit ID")
    if provider is not None and (
        type(provider) is not str
        or _LABEL.fullmatch(provider) is None
        or provider.strip() != provider
    ):
        raise ConfigError("private attestation has invalid provider")
    if tool is not None and (
        type(tool) is not str or _LABEL.fullmatch(tool) is None or tool.strip() != tool
    ):
        raise ConfigError("private attestation has invalid tool")
    if provider is None and tool is None:
        raise ConfigError("private attestation needs a provider or tool")
    if mode not in {"ai_assisted", "ai_generated", "ai_reviewed"}:
        raise ConfigError("private attestation has invalid contribution mode")
    resolved = resolve_tool(tool) if tool else None
    if provider is None and tool is not None and resolved is None:
        raise ConfigError("unrecognized tool needs an explicit AI provider")
    if (
        provider is not None
        and resolved is not None
        and normalize_provider(provider) not in {None, resolved[1]}
    ):
        raise ConfigError("private attestation provider and tool disagree")
    return {"repo": repo, "sha": sha, "provider": provider, "tool": tool, "mode": mode}


def load(home: Path) -> list[dict[str, str | None]]:
    path = home / LEDGER_NAME
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file():
        raise ConfigError("private attestation ledger is not a regular file")
    try:
        raw = path.read_bytes()
        if len(raw) > LOCAL_LEDGER_LIMIT:
            raise ConfigError("private attestation ledger exceeds the local 8 MB safety limit")
        data = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError("private attestation ledger cannot be read or parsed") from exc
    if type(data) is not dict or set(data) != {"version", "entries"} or data["version"] != 1:
        raise ConfigError("private attestation ledger has unsupported format")
    if type(data["entries"]) is not list:
        raise ConfigError("private attestation entries must be a list")
    entries = [_validate_entry(item) for item in data["entries"]]
    keys = [(entry["repo"], entry["sha"]) for entry in entries]
    if len(set(keys)) != len(keys):
        raise ConfigError("private attestation ledger has duplicate commits")
    return entries


def save(home: Path, entries: list[dict[str, str | None]]) -> None:
    home.mkdir(parents=True, exist_ok=True)
    target = home / LEDGER_NAME
    if target.is_symlink():
        raise ConfigError("private attestation ledger must not be a symlink")
    checked = [_validate_entry(item) for item in entries]
    checked.sort(key=lambda item: (str(item["repo"]), str(item["sha"])))
    if len({(item["repo"], item["sha"]) for item in checked}) != len(checked):
        raise ConfigError("private attestation ledger has duplicate commits")
    payload = (
        json.dumps({"version": 1, "entries": checked}, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if len(payload) > LOCAL_LEDGER_LIMIT:
        raise ConfigError("private attestation ledger exceeds the local 8 MB safety limit")
    fd, name = tempfile.mkstemp(prefix=".attestations-", dir=home)
    try:
        with os.fdopen(fd, "wb") as stream:
            if os.name == "posix":
                os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def confirm_reachable(path: Path, sha: str, identities: list[str]) -> None:
    validate_commit_id(sha)
    gitio.assert_repository(path)
    if gitio.object_format(path) != "sha1":
        raise ConfigError("only SHA-1 repositories are supported")
    check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
        cwd=path,
        capture_output=True,
        check=False,
    )
    if check.returncode != 0:
        raise ConfigError("commit is not reachable from HEAD")
    author = subprocess.run(
        ["git", "show", "-s", "--format=%ae", sha],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    if author.returncode != 0 or author.stdout.strip().lower() not in {
        i.lower() for i in identities
    }:
        raise ConfigError("commit author is not a configured identity")


def validate_commit_id(sha: str) -> None:
    if _SHA.fullmatch(sha) is None:
        raise ConfigError("commit ID must be a full 40-character SHA-1")


def spec_for(entry: dict[str, str | None]) -> ParticipationSpec:
    provider_raw = entry["provider"]
    tool_raw = entry["tool"]
    resolved = resolve_tool(tool_raw) if tool_raw else None
    provider = (
        normalize_provider(provider_raw) if provider_raw else resolved[1] if resolved else None
    )
    return ParticipationSpec(
        actor_type=ActorType.AI,
        provider=provider,
        provider_raw=provider_raw,
        model=None,
        model_raw=None,
        tool=resolved[0] if resolved else None,
        tool_raw=tool_raw,
        roles=(),
        contribution_mode=ContributionMode(entry["mode"]),
        human_reviewed=None,
        source=ProvenanceSource(SourceType.MANUAL_DECLARATION, EvidenceLevel.DECLARED),
    )


def sync_github(home: Path, profile_repo: str) -> int:
    """Send the complete ledger through gh's stdin-only secret channel."""
    if _GITHUB_REPO.fullmatch(profile_repo) is None:
        raise ConfigError("Profile repository must be OWNER/REPO")
    entries = load(home)
    if any(
        not str(entry["repo"]).startswith("github.com/")
        or _GITHUB_REPO.fullmatch(str(entry["repo"])[len("github.com/") :]) is None
        for entry in entries
    ):
        raise ConfigError("cloud ledger contains a non-GitHub source; sync refused")
    path = home / LEDGER_NAME
    if not path.is_file():
        # Empty but explicit ledger, so removal of the last local entry does
        # not leave stale cloud backfill behind.
        save(home, [])
    payload = path.read_bytes()
    if len(payload) > SECRET_LIMIT:
        raise ConfigError("private attestation ledger exceeds GitHub's 48 KB secret limit")
    try:
        result = subprocess.run(
            ["gh", "secret", "set", "AIPROFILE_ATTESTATIONS", "--repo", profile_repo],
            input=payload,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConfigError("could not send private attestation secret") from exc
    if result.returncode:
        raise ConfigError("GitHub rejected the private attestation secret")
    return len(entries)

"""Opt-in, one-commit provenance marks and non-overwriting Git hooks."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .adapters.trailers import parse_commit_trailers
from .errors import ConfigError
from .registry import normalize_provider, resolve_tool
from .schema.vocab import ActorType, ContributionMode

MARKS_NAME = "pending_marks.json"
_LABEL = re.compile(r"^[^\x00-\x1f\x7f:]{1,100}$")
_OID = re.compile(r"^[0-9a-f]{40}$")
_REPO_ID = re.compile(r"^[0-9a-f]{64}$")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    if result.returncode:
        raise ConfigError("Git state check failed; provenance mark was not used")
    return result.stdout.strip()


def _repo_root(repo: Path) -> Path:
    root = Path(_git(repo, "rev-parse", "--show-toplevel")).resolve()
    if root != repo.resolve():
        raise ConfigError("provenance commands require the repository root")
    return root


def _repo_id(root: Path) -> str:
    return hashlib.sha256(os.fsencode(str(root))).hexdigest()


def _head_and_tree(root: Path) -> tuple[str, str]:
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if head.returncode not in (0, 128):
        raise ConfigError("could not inspect HEAD")
    return head.stdout.strip() if head.returncode == 0 else "ROOT", _git(root, "write-tree")


def _read(home: Path) -> dict[str, dict[str, str]]:
    path = home / MARKS_NAME
    if not path.exists():
        return {}
    if path.is_symlink() or not path.is_file():
        raise ConfigError("pending provenance marks are not a regular file")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError("pending provenance marks are invalid") from exc
    if type(raw) is not dict or raw.get("version") != 1 or type(raw.get("marks")) is not dict:
        raise ConfigError("pending provenance marks have unsupported format")
    marks = raw["marks"]
    for key, value in marks.items():
        if (
            type(key) is not str
            or type(value) is not dict
            or set(value) != {"head", "tree", "provider", "tool", "mode"}
            or any(type(v) is not str for v in value.values())
        ):
            raise ConfigError("pending provenance mark is malformed")
        if (
            _REPO_ID.fullmatch(key) is None
            or (value["head"] != "ROOT" and _OID.fullmatch(value["head"]) is None)
            or _OID.fullmatch(value["tree"]) is None
            or _LABEL.fullmatch(value["provider"]) is None
            or (value["tool"] and _LABEL.fullmatch(value["tool"]) is None)
            or value["mode"] not in {"AI-Assisted", "AI-Generated", "AI-Reviewed"}
        ):
            raise ConfigError("pending provenance mark is malformed")
    return marks


def _write(home: Path, marks: dict[str, dict[str, str]]) -> None:
    home.mkdir(parents=True, exist_ok=True)
    target = home / MARKS_NAME
    if target.is_symlink():
        raise ConfigError("pending provenance marks must not be a symlink")
    payload = (json.dumps({"version": 1, "marks": marks}, sort_keys=True) + "\n").encode()
    fd, name = tempfile.mkstemp(prefix=".pending-marks-", dir=home)
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


def mark(home: Path, repo: Path, provider: str | None, tool: str | None, mode: str) -> None:
    root = _repo_root(repo)
    provider_slug = normalize_provider(provider) if provider else None
    resolved = resolve_tool(tool) if tool else None
    if any(
        _LABEL.fullmatch(value) is None or value.strip() != value
        for value in (provider, tool)
        if value is not None
    ):
        raise ConfigError("provider or tool label is invalid")
    if provider is None and resolved is None:
        raise ConfigError("specify an actual participating provider or tool")
    if provider_slug and resolved and provider_slug != resolved[1]:
        raise ConfigError("provider and tool disagree")
    if mode not in {"AI-Assisted", "AI-Generated", "AI-Reviewed"}:
        raise ConfigError("invalid AI participation mode")
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root, check=False)
    if changed.returncode != 1:
        raise ConfigError("stage the exact changes before marking provenance")
    head, tree = _head_and_tree(root)
    marks = _read(home)
    marks[_repo_id(root)] = {
        "head": head,
        "tree": tree,
        "provider": provider_slug or provider or resolved[1],
        "tool": resolved[0] if resolved else tool or "",
        "mode": mode,
    }
    _write(home, marks)


def clear(home: Path, repo: Path) -> bool:
    root = _repo_root(repo)
    marks = _read(home)
    found = marks.pop(_repo_id(root), None) is not None
    if found:
        _write(home, marks)
    return found


def _committed_mark_present(root: Path, entry: dict[str, str]) -> bool:
    """Check the final trailer paragraph, after all other message hooks ran."""
    lines = _git(root, "log", "-1", "--format=%(trailers:only,unfold)").splitlines()
    specs, _ = parse_commit_trailers(lines)
    provider = normalize_provider(entry["provider"]) or entry["provider"].casefold()
    resolved_tool = resolve_tool(entry["tool"]) if entry["tool"] else None
    tool = resolved_tool[0] if resolved_tool else entry["tool"].casefold()
    mode = ContributionMode(entry["mode"].lower().replace("-", "_"))
    return any(
        spec.actor_type is ActorType.AI
        and (spec.provider or (spec.provider_raw or "").casefold()) == provider
        and (spec.tool or (spec.tool_raw or "").casefold()) == tool
        and spec.contribution_mode is mode
        for spec in specs
    )


def _parse_message_trailers(root: Path, body: bytes):
    result = subprocess.run(
        ["git", "interpret-trailers", "--parse", "--no-divider"],
        cwd=root, input=body, capture_output=True, check=False,
    )
    if result.returncode:
        raise ConfigError("could not inspect commit trailers; mark retained")
    try:
        return parse_commit_trailers(result.stdout.decode("utf-8").splitlines())
    except UnicodeError as exc:
        raise ConfigError("commit trailers are not UTF-8; mark retained") from exc


def _prepare_marked_message(root: Path, message: Path, entry: dict[str, str]) -> None:
    try:
        original = message.read_bytes()
    except OSError as exc:
        raise ConfigError("commit message file cannot be read") from exc
    previous_specs, previous_warnings = _parse_message_trailers(root, original)
    trailers = [f"AI-Provider: {entry['provider']}"]
    if entry["tool"]:
        trailers.append(f"AI-Tool: {entry['tool']}")
    trailers.append(f"AI-Mode: {entry['mode']}")

    # A repeated non-empty key is the ADR-005 group boundary. Try each
    # ordering against Git's real trailer serializer before touching the
    # message. Existing actors, warnings, and the new actor must remain
    # distinct; some pre-existing incomplete groups have no safe ordering.
    for ordering in itertools.permutations(trailers):
        args = [
            "git", "interpret-trailers", "--no-divider", "--where=end",
            "--if-exists=add", "--if-missing=add",
            *[x for trailer in ordering for x in ("--trailer", trailer)],
        ]
        result = subprocess.run(args, cwd=root, input=original, capture_output=True, check=False)
        if result.returncode:
            raise ConfigError("could not add provenance trailers; commit aborted")
        specs, warnings = _parse_message_trailers(root, result.stdout)
        if (
            specs[:len(previous_specs)] != previous_specs
            or warnings != previous_warnings
            or len(specs) != len(previous_specs) + 1
        ):
            continue
        marked = specs[-1]
        provider = normalize_provider(entry["provider"]) or entry["provider"].casefold()
        resolved_tool = resolve_tool(entry["tool"]) if entry["tool"] else None
        tool = resolved_tool[0] if resolved_tool else entry["tool"].casefold()
        if not (
            marked.actor_type is ActorType.AI
            and (marked.provider or (marked.provider_raw or "").casefold()) == provider
            and (marked.tool or (marked.tool_raw or "").casefold()) == tool
            and marked.contribution_mode
            is ContributionMode(entry["mode"].lower().replace("-", "_"))
            and marked.model is None
            and not marked.roles
            and marked.human_reviewed is None
        ):
            continue
        if message.read_bytes() != original:
            raise ConfigError("commit message changed during provenance hook; mark retained")
        message.write_bytes(result.stdout)
        return
    raise ConfigError("existing trailers cannot safely separate the AI actor; mark retained")


def hook_run(
    home: Path, repo: Path, phase: str, message: Path | None = None, source: str | None = None
) -> None:
    root = _repo_root(repo)
    marks = _read(home)
    entry = marks.get(_repo_id(root))
    if entry is None:
        return
    if phase == "post":
        # A successful commit consumes the mark only when its tree and parent
        # are precisely the staged state confirmed by the user. Failed commits
        # keep the mark, but a changed HEAD cannot silently reuse it.
        if _git(root, "rev-parse", "HEAD^{tree}") != entry["tree"]:
            return
        parents = _git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()
        parent = parents[1] if len(parents) == 2 else "ROOT"
        if parent == entry["head"]:
            if not _committed_mark_present(root, entry):
                raise ConfigError(
                    "committed message lost the confirmed AI trailers; mark retained; run doctor"
                )
            clear(home, root)
        return
    if phase != "prepare":
        raise ConfigError("unsupported hook phase")
    if source in {"commit", "merge", "squash"}:
        raise ConfigError("pending provenance mark does not apply to amend/merge/squash")
    if _head_and_tree(root) != (entry["head"], entry["tree"]):
        raise ConfigError("HEAD or staged content changed; clear and re-mark before committing")
    if message is None or not message.is_file() or message.is_symlink():
        raise ConfigError("commit message file is unavailable")
    _prepare_marked_message(root, message, entry)


def hook_status(repo: Path) -> str:
    root = _repo_root(repo)
    custom = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if custom.returncode == 0 and custom.stdout.strip():
        return "custom hooksPath active; use manual hook integration"
    directory = Path(_git(root, "rev-parse", "--git-path", "hooks"))
    if not directory.is_absolute():
        directory = root / directory
    names = ("prepare-commit-msg", "post-commit")
    present = [(directory / name).exists() for name in names]
    return (
        "installed" if all(present) else "partially installed" if any(present) else "not installed"
    )


def install_hooks(home: Path, repo: Path) -> None:
    root = _repo_root(repo)
    if hook_status(root) != "not installed":
        raise ConfigError("existing/custom hooks detected; no files changed; integrate manually")
    directory = Path(_git(root, "rev-parse", "--git-path", "hooks"))
    if not directory.is_absolute():
        directory = root / directory
    directory.mkdir(parents=True, exist_ok=True)
    # POSIX sh quoting: a single quote in an absolute home path is escaped.
    quoted_home = str(home.resolve()).replace("'", "'\\''")
    quoted_python = Path(sys.executable).as_posix().replace("'", "'\\''")
    scripts = {
        "prepare-commit-msg": (
            "#!/bin/sh\n"
            f"AIPROFILE_HOME='{quoted_home}'\nexport AIPROFILE_HOME\n"
            f'\'{quoted_python}\' -m aiprofile provenance hook-run prepare "$1" "${{2:-}}"\n'
        ),
        "post-commit": (
            "#!/bin/sh\n"
            f"AIPROFILE_HOME='{quoted_home}'\nexport AIPROFILE_HOME\n"
            f"'{quoted_python}' -m aiprofile provenance hook-run post\n"
        ),
    }
    created: list[Path] = []
    try:
        for name, content in scripts.items():
            target = directory / name
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
            created.append(target)
            target.chmod(0o755)
    except (OSError, FileExistsError) as exc:
        for path in created:
            path.unlink(missing_ok=True)
        raise ConfigError("hook installation conflict; no existing hooks were overwritten") from exc


def check_squash_message(repo: Path, base: str, head: str, message: Path) -> tuple[int, int]:
    """Check a proposed final message against explicit source-commit evidence.

    This is advisory before merging; it never infers AI from the PR body or
    changes merge state. Only reachable source commits and Git-parsed trailers
    are considered. Return (source AI identities, final AI identities).
    """
    from .adapters.trailers import parse_commit_trailers
    from .schema.vocab import ActorType

    root = _repo_root(repo)
    if message.is_symlink() or not message.is_file():
        raise ConfigError("proposed squash message file is unavailable")
    refs = _git(root, "rev-list", "--max-count=5001", f"{base}..{head}").splitlines()
    if len(refs) > 5000:
        raise ConfigError("PR range is too large for provenance check")

    def identities(lines: list[str]) -> set[tuple[str | None, str | None]]:
        specs, _ = parse_commit_trailers(lines)
        return {(spec.provider, spec.tool) for spec in specs if spec.actor_type is ActorType.AI}

    source: set[tuple[str | None, str | None]] = set()
    for sha in refs:
        trailers = _git(root, "show", "-s", "--format=%(trailers:only,unfold)", sha)
        source.update(identities(trailers.splitlines()))
    proposed = subprocess.run(
        ["git", "interpret-trailers", "--parse"],
        cwd=root,
        input=message.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        check=False,
    )
    if proposed.returncode:
        raise ConfigError("could not parse proposed squash message")
    final = identities(proposed.stdout.splitlines())
    if source and not final:
        raise ConfigError("source commits declare AI; proposed squash message loses the evidence")
    if any(identity not in final for identity in source if identity != (None, None)):
        raise ConfigError("proposed squash message omits a source AI provider/tool")
    return len(source), len(final)

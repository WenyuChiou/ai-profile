"""Git subprocess abstraction (collection layer; architecture.md section 4).

One enumeration pass per repository using the pinned format (ADR-005):
record separator %x1e, field separator %x1f, trailers via the portable
%(trailers:only,unfold) form (git >= 2.17; validated on 2.47.1).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import GitError

#: Fields: sha, author name, author email, author date (ISO), trailer block.
PRETTY_FORMAT = "%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%(trailers:only,unfold)"

_RECORD_SEP = "\x1e"
_FIELD_SEP = "\x1f"

_EMPTY_REPO_MARKERS = (
    "does not have any commits yet",
    "bad default revision",
    "unknown revision or path not in the working tree",
)


@dataclass(frozen=True)
class CommitRecord:
    sha: str
    author_name: str
    author_email: str
    author_date: str  # ISO 8601, author's own UTC offset
    trailer_lines: tuple[str, ...]


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except FileNotFoundError as exc:
        raise GitError("git executable not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git timed out: {' '.join(cmd)}") from exc


def assert_repository(repo_path: Path) -> None:
    """Raise GitError unless repo_path is the ROOT of a git work tree.

    Root-only on purpose: `scan <path>` must mean "this repository", never
    "whatever repository happens to contain this path" — on machines whose
    home directory is itself a work tree (dotfiles repos), accepting inner
    paths would silently import the containing repository's history."""
    if not repo_path.exists():
        raise GitError(f"path does not exist: {repo_path}")
    proc = _run_git(["rev-parse", "--show-toplevel"], repo_path)
    if proc.returncode != 0:
        raise GitError(
            f"not a git repository: {repo_path}"
            f" (git rev-parse said: {proc.stderr.strip() or proc.stdout.strip()})"
        )
    toplevel = Path(proc.stdout.strip())
    try:
        is_root = toplevel.exists() and repo_path.resolve().samefile(toplevel)
    except OSError as exc:
        raise GitError(f"cannot resolve repository root for {repo_path}: {exc}") from exc
    if not is_root:
        raise GitError(
            f"{repo_path} is inside the repository at {toplevel} —"
            " scan the repository root instead"
        )


def enumerate_commits(repo_path: Path) -> list[CommitRecord]:
    """All HEAD-reachable commits, newest first. Empty list for a repository
    with no commits yet; GitError for a non-repository or git failure."""
    assert_repository(repo_path)
    proc = _run_git(["log", "HEAD", f"--pretty=format:{PRETTY_FORMAT}"], repo_path)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        if any(marker in stderr for marker in _EMPTY_REPO_MARKERS):
            return []
        raise GitError(f"git log failed in {repo_path}: {stderr}")

    records: list[CommitRecord] = []
    for chunk in proc.stdout.split(_RECORD_SEP):
        if not chunk.strip():
            continue
        fields = chunk.split(_FIELD_SEP)
        if len(fields) != 5:
            raise GitError(
                f"unexpected git log record shape in {repo_path}"
                f" ({len(fields)} fields)"
            )
        sha, name, email, adate, trailer_block = fields
        trailers = tuple(
            line for line in trailer_block.splitlines() if line.strip()
        )
        records.append(
            CommitRecord(
                sha=sha.strip().lower(),
                author_name=name,
                author_email=email,
                author_date=adate.strip(),
                trailer_lines=trailers,
            )
        )
    return records


def get_origin_url(repo_path: Path) -> str | None:
    proc = _run_git(["remote", "get-url", "origin"], repo_path)
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    return url or None


_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_HOST_PATH = re.compile(r"^(?:[^@/]+@)?([^:/]+)[:/](.+)$")


def normalize_remote_url(url: str) -> str | None:
    """Lowercased host/path with scheme, credentials, trailing '/' and '.git'
    stripped (schema.md section 7). None when the URL shape is unusable."""
    u = _SCHEME.sub("", url.strip())
    m = _HOST_PATH.match(u)
    if not m:
        return None
    host, path = m.group(1), m.group(2)
    path = path.rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    if not host or not path:
        return None
    return f"{host.lower()}/{path.lower()}"


def repository_uid(repo_path: Path, salt: str) -> str:
    """Stable repository identity (schema.md section 7): remote-based when an
    origin exists, else salted full-sha256 of the resolved path."""
    origin = get_origin_url(repo_path)
    if origin:
        normalized = normalize_remote_url(origin)
        if normalized:
            return f"remote:{normalized}"
    resolved = str(repo_path.resolve()).lower()
    digest = hashlib.sha256(f"{salt}\n{resolved}".encode()).hexdigest()
    return f"local:{digest}"


def config_user_email(cwd: Path) -> str | None:
    """The effective git user.email (identity seeding at init; ADR-015)."""
    proc = _run_git(["config", "--get", "user.email"], cwd)
    if proc.returncode != 0:
        return None
    email = proc.stdout.strip()
    return email or None

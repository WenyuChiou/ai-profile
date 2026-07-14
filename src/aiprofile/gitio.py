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
        sha = sha.strip().lower()
        if len(sha) == 64:
            raise GitError(
                f"{repo_path} uses the SHA-256 object format, which v0.1 does"
                " not support (SHA-1 repositories only — ADR-005/G2-13); no"
                " data was imported"
            )
        trailers = tuple(
            line for line in trailer_block.splitlines() if line.strip()
        )
        records.append(
            CommitRecord(
                sha=sha,
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


#: uid algorithm version (ADR-016). Any rule change bumps this; uids with
#: different versions never compare equal.
UID_ALGORITHM = "v2"

#: Hosts whose repository paths are case-insensitively unique, so lowering
#: the path MERGES aliases safely; everywhere else path case is preserved
#: (lowering could merge DISTINCT repositories — G2-01).
_CASE_INSENSITIVE_PATH_HOSTS = frozenset({"github.com"})

#: Default ports per scheme: a matching explicit port is redundant identity.
_DEFAULT_PORTS = {"ssh": "22", "git+ssh": "22", "http": "80", "https": "443", "git": "9418"}

_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*)://")
_SCP_FORM = re.compile(
    r"^(?:(?P<user>[^@/]+)@)?(?P<host>\[[^\]]+\]|[^:/]+):(?P<path>[^/].*)$"
)
#: Origin strings shaped like local filesystem paths (relative, drive-letter,
#: home-relative, UNC). These are NOT remote identities: two unrelated repos
#: can share the same relative-origin string, and using it verbatim would
#: merge their uids — a replace-by-uid data-loss path (gate round-2 P0).
#: They return None so repository_uid falls through to the local: branch,
#: which hashes the repository's own resolved path.
_LOCAL_PATH_SHAPE = re.compile(r"^(?:[A-Za-z]:[\\/]|\.{1,2}[\\/]|~[\\/]|\\\\|/)")


def canonicalize_remote_v2(url: str) -> str | None:
    """ADR-016 algorithm v2: canonical `host[_port]/path` identity for an
    origin URL, or None when the shape is unusable or filesystem-local.

    Host lowercased (IPv6 brackets kept); credentials stripped; query and
    fragment dropped; non-default port retained as `host_<port>`; path case
    preserved except on documented case-insensitive hosts; trailing '/' and
    one '.git' stripped. Local-filesystem-shaped origins yield None (see
    _LOCAL_PATH_SHAPE).
    """
    u = url.strip()
    if not u or _LOCAL_PATH_SHAPE.match(u):
        return None

    scheme_match = _SCHEME.match(u)
    if scheme_match:
        scheme = scheme_match.group(1).lower()
        if scheme == "file":
            return None  # local transport, never a remote identity
        u = u[scheme_match.end():]
        # URL form: [user[:pass]@]host[:port]/path[?q][#f]
        u = u.split("#", 1)[0].split("?", 1)[0]
        if "@" in u.split("/", 1)[0]:
            u = u.split("@", 1)[1]  # strip credentials; never identity
        m = re.match(r"^(\[[^\]]+\]|[^:/]+)(?::(\d+))?/(.+)$", u)
        if not m:
            return None
        host, port, path = m.group(1), m.group(2), m.group(3)
        if port and _DEFAULT_PORTS.get(scheme) == port:
            port = None
        return _finish_canonical(host, port, path)

    # No scheme: the ONLY positive remote marker is a colon before the
    # first slash (git's own scp rule). Everything else defaults to LOCAL
    # (gate round-3): misclassifying a remote as local merely splits a uid
    # (safe); misclassifying a local path as remote collides uids across
    # unrelated repositories and destroys data via replace-by-uid.
    head = u.split("/", 1)[0]
    if ":" not in head:
        return None
    m = _SCP_FORM.match(u)
    if not m:
        return None
    if re.fullmatch(r"[A-Za-z]", m.group("host")):
        return None  # drive-relative form like C:foo — local, mirroring git
    return _finish_canonical(m.group("host"), None, m.group("path"))


def _finish_canonical(host: str, port: str | None, path: str) -> str | None:
    host = host.lower()
    path = path.rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    if not host or not path:
        return None
    if host in _CASE_INSENSITIVE_PATH_HOSTS:
        path = path.lower()
    host_part = f"{host}_{port}" if port else host
    return f"{host_part}/{path}"


def repository_uid(repo_path: Path, salt: str) -> str:
    """Stable, versioned repository identity (schema.md section 7, ADR-016):
    remote-based when an origin exists, else salted full-sha256 of the
    resolved path."""
    origin = get_origin_url(repo_path)
    if origin:
        normalized = canonicalize_remote_v2(origin)
        if normalized:
            return f"remote:{UID_ALGORITHM}:{normalized}"
    resolved = str(repo_path.resolve()).lower()
    digest = hashlib.sha256(f"{salt}\n{resolved}".encode()).hexdigest()
    return f"local:{UID_ALGORITHM}:{digest}"


def config_user_email(cwd: Path) -> str | None:
    """The effective git user.email (identity seeding at init; ADR-015)."""
    proc = _run_git(["config", "--get", "user.email"], cwd)
    if proc.returncode != 0:
        return None
    email = proc.stdout.strip()
    return email or None

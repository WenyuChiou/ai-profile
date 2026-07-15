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
            # Defense in depth behind object_format(); path-free by design
            # (gate H-04: default errors must not leak repository paths).
            raise GitError(
                "this repository uses the SHA-256 object format, which v0.1"
                " does not support (SHA-1 repositories only — ADR-005); no"
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


def object_format(repo_path: Path) -> str:
    """The repository's object format ("sha1" / "sha256"). Git builds too
    old to know the flag cannot host SHA-256 repositories, so a failed
    probe safely reports "sha1" (gate H-04: this preflight runs BEFORE any
    config/database mutation, and catches empty SHA-256 repositories that
    the 64-hex commit-ID check can never see)."""
    proc = _run_git(["rev-parse", "--show-object-format"], repo_path)
    if proc.returncode != 0:
        return "sha1"
    return proc.stdout.strip() or "sha1"


def get_origin_url(repo_path: Path) -> str | None:
    proc = _run_git(["remote", "get-url", "origin"], repo_path)
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    return url or None


#: uid algorithm version (ADR-016). Any rule change bumps this; uids with
#: different versions never compare equal.
UID_ALGORITHM = "v4"

#: Hosts whose repository namespace is BOTH path-case-insensitive AND
#: transport-convergent — documented exceptions only (gate C-01): for every
#: other host, scheme and port are identity, because SSH and HTTPS
#: namespaces on a self-hosted service are not guaranteed to serve the
#: same repositories.
_ALIAS_CONVERGENT_HOSTS = frozenset({"github.com"})

#: The DOCUMENTED endpoints of the alias-convergent hosts (verification
#: review, 2026-07-14): convergence applies ONLY to these (scheme,
#: effective-port) pairs — GitHub's published git transports on their
#: standard ports. `ftp://github.com`, `https://github.com:444`, etc. are
#: NOT the documented namespace and retain structured scheme/port identity
#: (safe split), otherwise the host check alone would collapse every
#: scheme x port combination into one uid — the exact distinct-repository
#: collision class the uid algorithm exists to eliminate.
_ALIAS_ALLOWED_ENDPOINTS = frozenset({("ssh", "22"), ("https", "443"), ("git", "9418")})

#: Default ports per scheme: an absent port resolves to the scheme default
#: so `https://h/x` and `https://h:443/x` converge WITHIN one scheme.
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


def canonicalize_remote(url: str) -> str | None:
    """ADR-016 algorithm (version UID_ALGORITHM): INJECTIVE canonical identity for an origin
    URL, or None when the shape is unusable or filesystem-local.

    Structure (gate C-01 — v2's `host_<port>` concatenation was forgeable
    by literal-underscore hosts, and global scheme erasure merged ssh and
    https namespaces on arbitrary self-hosted services):

    - alias-convergent hosts (documented list): `host/path` with the path
      case-folded — transports and standard ports deliberately merge;
    - every other host: `scheme://host:port/path` with the port always
      explicit when the scheme has a known default. The `://`/`:`/`/`
      delimiters cannot be produced by host or port components, so the
      encoding parses back unambiguously.

    Credentials stripped at the LAST `@` (RFC 3986 authority; gate H-01);
    query/fragment stripped for every syntax (gate M-04); trailing `/` and
    one `.git` suffix stripped (case-folded hosts fold BEFORE the suffix
    strip, so `.GIT` converges — gate M-04). Local-filesystem-shaped
    origins yield None (see _LOCAL_PATH_SHAPE).
    """
    u = url.strip()
    if not u or _LOCAL_PATH_SHAPE.match(u):
        return None

    scheme_match = _SCHEME.match(u)
    if scheme_match:
        scheme = scheme_match.group(1).lower()
        if scheme == "file":
            return None  # local transport, never a remote identity
        if scheme in _ALIAS_CONVERGENT_HOSTS:
            # Defense in depth (gate-3 reviewer suggestion): a fabricated
            # scheme named after an alias-convergent host (github.com://x)
            # cannot collide with the alias branch's output structurally,
            # but there is no legitimate scheme by that name — reject.
            return None
        u = u[scheme_match.end():]
        u = u.split("#", 1)[0].split("?", 1)[0]
        first_seg, sep, remainder = u.partition("/")
        if "@" in first_seg:
            first_seg = first_seg.rpartition("@")[2]
        u = first_seg + sep + remainder
        m = re.match(r"^(\[[^\]]+\]|[^:/]+)(?::(\d+))?/(.+)$", u)
        if not m:
            return None
        return _canonical_identity(scheme, m.group(1), m.group(2), m.group(3))

    # No scheme: the ONLY positive remote marker is a colon before the
    # first slash (git's own scp rule); scp transport IS ssh. Everything
    # else defaults to LOCAL (gate round-3): misclassifying a remote as
    # local merely splits a uid (safe); misclassifying a local path as
    # remote collides uids across unrelated repositories and destroys data
    # via replace-by-uid.
    u = u.split("#", 1)[0].split("?", 1)[0]
    # Strip credentials at the LAST @ before the first slash (H-01): scp
    # userinfo may itself contain ':' and '@', so this must happen BEFORE
    # the host:path colon is located.
    pre_slash, sep, post_slash = u.partition("/")
    if "@" in pre_slash:
        pre_slash = pre_slash.rpartition("@")[2]
    u = pre_slash + sep + post_slash
    if ":" not in pre_slash:
        return None
    m = _SCP_FORM.match(u)
    if not m:
        return None
    if re.fullmatch(r"[A-Za-z]", m.group("host")):
        return None  # drive-relative form like C:foo — local, mirroring git
    return _canonical_identity("ssh", m.group("host"), None, m.group("path"))


def _canonical_identity(
    scheme: str, host: str, port: str | None, path: str
) -> str | None:
    host = host.lower()
    if port:
        # Numeric normalization (gate-4 M-5): ':0443' and ':443' are the
        # same endpoint; compare and serialize in canonical decimal form.
        port = str(int(port))
    if host in _ALIAS_CONVERGENT_HOSTS:
        # Path-case insensitivity is a property of the HOST's namespace,
        # so fold regardless of transport — and BEFORE the suffix strip so
        # `.GIT` converges (gate M-04).
        path = path.lower()
    path = path.rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    if not host or not path:
        return None
    resolved_port = port or _DEFAULT_PORTS.get(scheme)
    if (
        host in _ALIAS_CONVERGENT_HOSTS
        and (scheme, resolved_port) in _ALIAS_ALLOWED_ENDPOINTS
    ):
        # Documented endpoint on its standard port: transports converge.
        return f"{host}/{path}"
    # Everything else — including undocumented schemes or non-standard
    # ports on an alias host — keeps structured scheme/port identity.
    netloc = f"{host}:{resolved_port}" if resolved_port else host
    return f"{scheme}://{netloc}/{path}"


def repository_uid(repo_path: Path, salt: str) -> str:
    """Stable, versioned repository identity (schema.md section 7, ADR-016):
    remote-based when an origin exists, else salted full-sha256 of the
    resolved path."""
    origin = get_origin_url(repo_path)
    if origin:
        normalized = canonicalize_remote(origin)
        if normalized:
            return f"remote:{UID_ALGORITHM}:{normalized}"
    # Case-PRESERVED resolved path (gate C-02): lowercasing merged distinct
    # case-sensitive-filesystem directories; Path.resolve() already
    # canonicalizes spelling on case-insensitive filesystems.
    resolved = str(repo_path.resolve())
    digest = hashlib.sha256(f"{salt}\n{resolved}".encode()).hexdigest()
    return f"local:{UID_ALGORITHM}:{digest}"


def config_user_email(cwd: Path) -> str | None:
    """The effective git user.email (identity seeding at init; ADR-015)."""
    proc = _run_git(["config", "--get", "user.email"], cwd)
    if proc.returncode != 0:
        return None
    email = proc.stdout.strip()
    return email or None

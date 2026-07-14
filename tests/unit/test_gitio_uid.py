"""ADR-016 repository-identity canonicalization fixtures (G2-01; mvp.md
section 7 test 18): equal repositories converge across URL spellings,
DISTINCT repositories never merge through case folding, and the algorithm
version is embedded in the uid."""

from __future__ import annotations

import subprocess

import pytest

from aiprofile.gitio import UID_ALGORITHM, canonicalize_remote_v3, repository_uid


def test_scp_and_https_forms_converge():
    assert canonicalize_remote_v3("git@github.com:Owner/Repo.git") == (
        canonicalize_remote_v3("https://github.com/owner/repo")
    )


def test_github_path_case_merges_aliases():
    # github.com owner/repo names are case-insensitively unique: lowering
    # merges alias spellings of the SAME repository.
    assert canonicalize_remote_v3("https://GitHub.com/OwNeR/RePo") == "github.com/owner/repo"


def test_case_sensitive_host_path_case_splits():
    # Anywhere else, path case is identity: distinct repositories must not
    # merge (the v1 lowercase-everything bug this ADR exists to fix).
    a = canonicalize_remote_v3("https://git.example.com/Team/Proj")
    b = canonicalize_remote_v3("https://git.example.com/team/proj")
    assert a == "https://git.example.com:443/Team/Proj"
    assert a != b


def test_credentials_stripped_and_never_identity():
    assert canonicalize_remote_v3("https://user:secret@github.com/o/r") == (
        canonicalize_remote_v3("https://github.com/o/r")
    )


def test_default_port_dropped_nondefault_retained():
    assert canonicalize_remote_v3("https://github.com:443/o/r") == (
        canonicalize_remote_v3("https://github.com/o/r")
    )
    with_port = canonicalize_remote_v3("ssh://git@git.example.com:2222/o/r")
    without = canonicalize_remote_v3("ssh://git@git.example.com/o/r")
    assert with_port == "ssh://git.example.com:2222/o/r"
    assert with_port != without


def test_query_fragment_trailing_slash_and_git_suffix_stripped():
    assert canonicalize_remote_v3("https://github.com/o/r.git?ref=main#readme") == (
        "github.com/o/r"
    )
    assert canonicalize_remote_v3("https://github.com/o/r/") == "github.com/o/r"


def test_unusable_shapes_yield_none():
    assert canonicalize_remote_v3("not a url") is None
    assert canonicalize_remote_v3("https://hostonly") is None


def test_uid_carries_algorithm_version(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True)
    uid = repository_uid(repo, salt="s" * 64)
    assert uid.startswith(f"local:{UID_ALGORITHM}:")

    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:Owner/Repo.git"],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )
    uid_remote = repository_uid(repo, salt="s" * 64)
    assert uid_remote == f"remote:{UID_ALGORITHM}:github.com/owner/repo"


def test_two_clones_of_one_remote_share_a_uid(tmp_path):
    uids = []
    for name, url in (
        ("a", "https://github.com/Owner/Repo.git"),
        ("b", "git@github.com:owner/repo"),
    ):
        repo = tmp_path / name
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", url],
            cwd=str(repo),
            check=True,
            capture_output=True,
        )
        uids.append(repository_uid(repo, salt="x" * 64))
    assert uids[0] == uids[1]


@pytest.mark.parametrize(
    "url,expected",
    [
        ("ssh://git@github.com:22/o/r", "github.com/o/r"),  # default ssh port dropped
        ("git://host.example/o/r", "git://host.example:9418/o/r"),
        ("https://[2001:db8::1]/o/r", "https://[2001:db8::1]:443/o/r"),
    ],
)
def test_additional_forms(url, expected):
    assert canonicalize_remote_v3(url) == expected


# ---------------------------------------------------------------------------
# Gate-review round 2 (P0): local-filesystem-shaped origins must NOT be
# treated as remote identities — they fall through to the local: branch,
# which hashes the repository's own resolved path (collision-safe).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "origin",
    [
        "../sibling-repo",
        "../sibling-repo.git",
        "./local-template",
        r"C:\Users\someone\repo",
        "C:/Users/someone/repo",
        "~/repos/thing",
        r"\\server\share\repo",
    ],
)
def test_filesystem_shaped_origins_are_not_remote_identities(origin):
    assert canonicalize_remote_v3(origin) is None


def test_relative_origin_repos_do_not_collide(tmp_path):
    """Two unrelated repos with the SAME relative origin string must get
    DIFFERENT uids (pre-fix: identical remote uid -> silent replace-by-uid
    data loss in storage)."""
    uids = []
    for name in ("a", "b"):
        repo = tmp_path / name
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "../shared-template"],
            cwd=str(repo),
            check=True,
            capture_output=True,
        )
        uids.append(repository_uid(repo, salt="y" * 64))
    assert uids[0] != uids[1]
    assert all(u.startswith(f"local:{UID_ALGORITHM}:") for u in uids)


def test_windows_drive_origin_spellings_converge(tmp_path):
    r"""C:\ and C:/ spellings of the same origin must land in the same uid
    namespace (pre-fix: backslash form parsed as scp host 'C')."""
    uids = []
    for name, origin in (
        ("bs", r"C:\Users\someone\repo"),
        ("fs", "C:/Users/someone/repo"),
    ):
        repo = tmp_path / name
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", origin],
            cwd=str(repo),
            check=True,
            capture_output=True,
        )
        uids.append(repository_uid(repo, salt="z" * 64))
    # Different repos, so uids differ — but BOTH must be local:, never remote:
    assert all(u.startswith(f"local:{UID_ALGORITHM}:") for u in uids)


def test_scp_ipv6_bracket_host_parses_and_splits_from_https():
    # v3 (gate C-01): cross-transport convergence is reserved for documented
    # alias-convergent hosts; an IPv6 literal is not one, so scp(ssh) and
    # https identities BOTH parse but deliberately differ.
    scp = canonicalize_remote_v3("git@[2001:db8::1]:owner/repo.git")
    https = canonicalize_remote_v3("https://[2001:db8::1]/owner/repo")
    assert scp == "ssh://[2001:db8::1]:22/owner/repo"
    assert https == "https://[2001:db8::1]:443/owner/repo"
    assert scp != https


# ---------------------------------------------------------------------------
# Gate round 3 (reviewer-constructed survivor): remote identity requires a
# POSITIVE marker (non-file scheme, or a colon before the first slash).
# Anything else is a local shape by default — misclassifying remote-as-local
# only splits a uid (safe); local-as-remote collides uids (data loss).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "origin",
    [
        "vendor/upstream",          # bare relative subdir — the round-2 survivor
        "vendor/upstream.git",
        "template",                 # bare name, git resolves relative to cwd
        "file:///C:/Users/x/repo",  # file scheme is a local transport
        "file:///home/x/repo",
        "C:relative-no-slash",      # drive-relative — git treats as a path
    ],
)
def test_originless_of_positive_remote_markers_are_local(origin):
    assert canonicalize_remote_v3(origin) is None


def test_bare_relative_origin_repos_do_not_collide(tmp_path):
    """Round-3 regression mirroring the reviewer's live repro: two repos
    with origin `vendor/upstream` must never share a uid."""
    uids = []
    for name in ("c1", "c2"):
        repo = tmp_path / name
        (repo / "vendor" / "upstream").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True)
        subprocess.run(
            ["git", "init", "-q"], cwd=str(repo / "vendor" / "upstream"),
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", "vendor/upstream"],
            cwd=str(repo), check=True, capture_output=True,
        )
        uids.append(repository_uid(repo, salt="w" * 64))
    assert uids[0] != uids[1]
    assert all(u.startswith(f"local:{UID_ALGORITHM}:") for u in uids)


def test_scp_ambiguous_dir_colon_name_follows_git_semantics():
    # git itself treats `dir:name` as ssh host `dir` — we mirror git, so the
    # colon IS the positive remote marker here (documented, deliberate).
    assert canonicalize_remote_v3("dir:name") == "ssh://dir:22/name"


# ---------------------------------------------------------------------------
# Gate-3 regressions (gate-review.md C-01/C-02/H-01/M-04): uid v3 must be
# INJECTIVE. Each test below was confirmed failing against v2.
# ---------------------------------------------------------------------------


def test_c01_literal_underscore_host_never_collides_with_port_encoding():
    a = canonicalize_remote_v3("https://example.com:8443/o/r")
    b = canonicalize_remote_v3("https://example.com_8443/o/r")
    assert a is not None and b is not None
    assert a != b


def test_c01_cross_transport_split_for_arbitrary_hosts():
    # SSH and HTTPS namespaces are not guaranteed to address the same
    # repository on self-hosted services: they must NOT converge.
    ssh = canonicalize_remote_v3("ssh://git.example/o/r")
    https = canonicalize_remote_v3("https://git.example/o/r")
    assert ssh is not None and https is not None
    assert ssh != https


def test_c01_github_transport_convergence_is_documented_exception():
    # github.com ssh/https/scp address one namespace on standard ports.
    assert (
        canonicalize_remote_v3("git@github.com:o/r.git")
        == canonicalize_remote_v3("https://github.com/o/r")
        == canonicalize_remote_v3("ssh://git@github.com/o/r")
    )


def test_h01_multi_at_credentials_fully_stripped():
    # rsplit at the LAST @ (RFC 3986): no userinfo fragment may survive.
    poisoned = canonicalize_remote_v3("https://user:tok@en@host.example/o/r")
    clean = canonicalize_remote_v3("https://host.example/o/r")
    assert poisoned == clean
    assert "tok" not in (poisoned or "")
    assert "en@" not in (poisoned or "")


def test_h01_scp_multi_at_credentials_fully_stripped():
    poisoned = canonicalize_remote_v3("user:tok@en@host.example:o/r")
    clean = canonicalize_remote_v3("host.example:o/r")
    assert poisoned == clean


def test_m04_scp_query_fragment_parity_with_url_form():
    assert canonicalize_remote_v3("git@github.com:o/r.git?x=1#frag") == (
        canonicalize_remote_v3("https://github.com/o/r")
    )


def test_m04_github_uppercase_git_suffix_folds_before_strip():
    assert canonicalize_remote_v3("https://github.com/O/R.GIT") == (
        canonicalize_remote_v3("https://github.com/o/r")
    )


@pytest.mark.skipif(
    __import__("os").name == "nt",
    reason="needs a case-sensitive filesystem; this is the C-02 falsifier"
    " (v2's .lower() provably merged these by inspection of the hash input)",
)
def test_c02_case_distinct_local_repos_split_on_posix(tmp_path):
    uids = []
    for name in ("Repo", "repo"):
        repo = tmp_path / name
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True)
        uids.append(repository_uid(repo, salt="c" * 64))
    assert uids[0] != uids[1]


def test_c02_same_local_repo_spellings_converge_via_resolve(tmp_path):
    # Case-insensitive filesystems canonicalize through Path.resolve(), so
    # convergence does not need lossy lowercasing.
    repo = tmp_path / "MixedCase"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True)
    a = repository_uid(repo, salt="d" * 64)
    other_spelling = tmp_path / "mixedcase"
    if not other_spelling.exists():
        pytest.skip("filesystem is case-sensitive; covered by the POSIX split test")
    b = repository_uid(other_spelling, salt="d" * 64)
    assert a == b


def test_fabricated_alias_host_scheme_rejected():
    """Gate-3 reviewer hardening suggestion: a scheme literally named after
    an alias-convergent host is not a legitimate transport and is rejected
    outright (structural non-collision was proven, this is belt+braces)."""
    assert canonicalize_remote_v3("github.com://owner/repo") is None

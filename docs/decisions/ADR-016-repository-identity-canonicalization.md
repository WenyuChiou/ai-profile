# ADR-016: Versioned repository identity canonicalization

Status: accepted (2026-07-14; created resolving Gate 2 finding G2-01)

## Context

`repository_uid` deduplicates repositories and keys publication policy.
The v1 rule ("lowercase host and path") could merge DISTINCT repositories
on hosts with case-sensitive paths — corrupting counts and, worse, letting
one repository's most-restrictive policy silently govern another
(a privacy-boundary error). Ports, IPv6, query/fragment parts, and
credential handling were unspecified.

## Decision

Repository identity is a **pure, versioned domain function** in
`gitio.py`; the algorithm version is part of the uid:

```text
remote:v2:<canonical-host>/<canonical-path>
local:v2:<full 64-hex sha256(salt || resolved-path-lowercased)>
```

Algorithm v2 canonicalization of the `origin` URL:

1. Strip scheme; normalize scp form (`user@host:path` → host + path).
2. Strip credentials (`user[:pass]@`); credentials never enter identity.
3. **Host lowercased** (DNS is case-insensitive). IPv6 bracket hosts kept
   verbatim inside brackets, lowercased.
4. **Non-default port retained** as `host_port` (`:` is not filesystem- or
   uid-safe context; encode as `host_8443` only when a port is present and
   not 22/80/443 for ssh/http/https respectively — pinned in code).
5. Strip query (`?...`) and fragment (`#...`) — they never identify a repo.
6. **Path case preserved by default**; lowercased ONLY for hosts documented
   case-insensitive (v2 list: `github.com` — GitHub owner/repo names are
   case-insensitively unique, so lowercasing prevents alias-splitting
   there and is unsafe elsewhere).
7. Trailing `/` and one trailing `.git` stripped; empty host or path →
   unusable → fall back to the `local:` form.
8. **Remote identity requires a POSITIVE marker; everything else is local
   by default** (gate rounds 2–3). Markers: a non-`file` scheme, or —
   with no scheme — a colon before the first slash (git's own scp rule,
   excluding single-letter drive hosts). Bare relative paths
   (`vendor/upstream`), dotted relatives (`../x`), drive-letter forms
   (`C:\x`, `C:/x`, `C:foo`), home-relative (`~/x`), UNC (`\\srv\x`),
   absolute POSIX (`/x`), and `file://` URLs all yield no remote identity
   and fall through to the `local:` form, which hashes the repository's
   own resolved path. The failure directions are asymmetric, so the guard
   fails toward local: misclassifying a remote as local merely splits a
   uid (two clones stop deduplicating — safe); misclassifying a local
   path as remote collides uids across unrelated repositories, and the
   storage layer's replace-by-uid then silently destroys one repository's
   history with the other's scan (round-2/round-3 reviewer repros:
   `../template`, `vendor/upstream`).

Changing any rule requires a version bump (v3, ...) and a documented
reconciliation path; uids with different algorithm versions never compare
equal. The local database is a disposable cache (ADR-014) and config
entries update their uid at scan time, so v1→v2 migration is "rescan".

Collision/alias fixtures are mandatory: path case (case-sensitive host
split vs github.com merge), port variants, scp vs https equivalence,
credentials, trailing slash/.git, two clones of one remote.

## Consequences

- Distinct repositories can no longer merge through case folding; equal
  repositories still converge across URL spellings.
- The uid is longer and carries its version — acceptable, it is local-only
  and never published (schema.md §7).

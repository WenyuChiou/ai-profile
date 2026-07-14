# ADR-016: Versioned repository identity canonicalization

Status: accepted (2026-07-14; **v3** — revised twice: Gate 2 conformance
review created v2 closing G2-01's case-folding merges; the Gate-3
implementation review then proved v2 itself unsafe (findings C-01, C-02,
H-01, M-04) and v3 replaces it)

## Context

`repository_uid` deduplicates repositories and keys publication policy.
Because storage replaces rows BY uid and policy resolves BY uid, a uid
collision between distinct repositories is simultaneously silent data
loss, count corruption, and a privacy-policy boundary failure. The v2
design had four proven defects: `host_<port>` string concatenation was
forgeable by literal-underscore hostnames; global scheme erasure merged
ssh/https namespaces that arbitrary self-hosted services do not guarantee
to be the same; local-path lowercasing merged case-distinct directories
on case-sensitive filesystems; and credential stripping at the FIRST `@`
retained secret fragments.

## Decision — algorithm v3

Identity is a pure, versioned function in `gitio.py`; the algorithm
version is embedded and different versions never compare equal:

```text
remote:v3:<canonical>      # see below
local:v3:<full 64-hex sha256(salt || case-preserved resolved path)>
```

### Remote canonical form (injective by construction — C-01)

1. **Positive remote markers only** (unchanged from v2 round-3): a
   non-`file` scheme, or — schemeless — a colon before the first slash
   (git's scp rule, excluding single-letter drive hosts). Everything
   else, including bare relative paths, `file://` URLs, drive-letter,
   home-relative, UNC, and absolute paths, is LOCAL by default (the
   fail-safe direction: remote-as-local splits a uid; local-as-remote
   destroys data through replace-by-uid).
2. **Credentials are stripped at the LAST `@` before the first slash**
   (RFC 3986 authority; H-01) in both URL and scp syntaxes — no userinfo
   substring can enter identity.
3. **Query and fragment are stripped for every syntax** (M-04).
4. **Alias-convergent hosts** (documented list, v3: `github.com`, whose
   ssh/https/git endpoints serve one namespace on standard ports):
   canonical = `host/path` with the path case-folded BEFORE the `.git`
   suffix strip (so `Repo.GIT` converges — M-04). Scheme and port are
   deliberately dropped for these hosts only.
5. **Every other host**: canonical = `scheme://host:port/path` — scheme
   retained (ssh and https identities deliberately split; C-01), port
   always explicit when the scheme has a known default (so
   `https://h/x == https://h:443/x` within one scheme), path case
   preserved. The `://`, `:`, `/` delimiters cannot be produced by host
   or port components, so the encoding parses back unambiguously — no
   concatenation forgery is possible.
6. scp syntax is the `ssh` scheme (port 22); bracketed IPv6 hosts are
   handled in both syntaxes.

### Local form (C-02)

The salted hash covers the **case-preserved** `Path.resolve()` result:
`resolve()` already canonicalizes spelling on case-insensitive
filesystems (so `C:\Repo` and `c:\repo` converge on Windows), while
case-distinct directories on POSIX correctly split. A safe split is
always preferred over a destructive merge.

### Migration (C-03)

Rescanning a path whose uid changes migrates its WHOLE alias group in the
same operation: every config entry holding the old uid is re-derived
(halting fail-closed if a sibling cannot be re-derived), and the old
uid's database rows are purged inside the same scan transaction. If the
migrated group resolves `excluded`, nothing is scanned or persisted —
policy can never weaken through a partial migration (C-04 ordering).

## Consequences

- Distinct repositories cannot merge through case folding, port
  encodings, scheme erasure, or credential fragments; equal repositories
  still converge across spellings (within a transport, plus full
  cross-transport convergence on documented hosts).
- Self-hosted ssh+https pairs of the SAME repository split into two uids
  (safe; totals split rather than either repo's data being destroyed) —
  users can converge them by using one remote URL form, and future
  documented-host additions can widen rule 4.
- Collision/alias fixtures are mandatory and adversarial: underscore
  hosts vs ports, cross-transport pairs, IPv6 in both syntaxes,
  multi-`@` credentials, query/fragment parity, `.GIT` case, relative and
  bare-relative paths, POSIX case-distinct locals, migration groups with
  conflicting policies.

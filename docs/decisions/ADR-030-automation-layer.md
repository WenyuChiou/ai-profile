# ADR-030: Automation layer boundary and security

- Status: Accepted for v0.7.0; Windows normalization amended in v0.7.1;
  clean remote-ahead fast-forward amended in v0.7.2; scheduler metadata
  version tracks the current package (v0.8.2, 2026-08-23; previously
  v0.8.1, 2026-08-23)
- Deciders: maintainer
- Supersedes: the assumption that multi-repository refresh and a reusable
  GitHub Action are future-only

## Context

The eight public assets can already be regenerated deterministically, but a
user must rescan configured repositories and publish those bytes manually.
Daily automation has two materially different trust boundaries:

1. private, local, or `aggregate_only` repositories must stay on the user's
   machine; and
2. repositories that are already public may be scanned on a GitHub-hosted
   runner if the user opts in explicitly.

Automation must not weaken publication policy, add a ninth output, introduce
model-by-day inference, or reverse the rule that renderers accept validated
`VizStats` only. It must also avoid turning repository paths, identities, Git
object IDs, or tool diagnostics into public logs.

## Decision

### Application refresh service

`aiprofile refresh --out DIR` is an application service outside `render/`.
It loads configured repositories, deduplicates aliases of one path, rescans
each non-excluded repository through the existing scanner, builds `VizStats`,
calls the existing pure renderers, and passes those assets to the existing
exact-eight exporter. Renderers remain pure and gain no Git, storage, SQLite,
network, or clock dependency.

Planning resolves every configured path before scan or cache access. Repeating
one resolved path under different repository UIDs is ambiguous and rejects the
entire real or dry run before mutation; silently skipping one UID could retain
publishable stale rows under a different policy.

A tool-owned, nonblocking lock serializes refreshes for one canonical
`AIPROFILE_HOME`. A failure before export publishes no new generation. The
exporter's existing transactional rollback is best effort: if rollback is
incomplete, the CLI reports—without a path—that partial generated assets or
recovery backups may remain. A lock-finalization failure after successful
publication says that publication completed rather than claiming the old
generation is intact.

`--dry-run` performs a faithful scan in an isolated shadow home and uses a
read-only SQLite backup as its source. It reports an ordered subset of the
eight allowlisted filenames while leaving configuration, publication policy,
recorded database/WAL content, and output assets unchanged. Acquiring the
advisory lock may create/use its tool-owned file, and a WAL-aware SQLite read
may update transient `-shm` coordination bytes; neither changes recorded data
or the publication contract.

### Local scheduler

`aiprofile schedule install|status|remove` manages an OS-native user schedule:
Windows Task Scheduler, macOS launchd, or a Linux systemd user timer. Platform
adapters sit behind a narrow stdlib-only interface. Their native identity is
derived from a one-way digest of the canonical home, so two homes do not own
or remove each other's jobs; the digest and home path are never logged.

On Windows, the authored task uses the exact six-setting shape observed after
real `schtasks` registration: `IgnoreNew`, battery stop/start defaults,
`StartWhenAvailable=true`, the two exact idle defaults, and
`UseUnifiedSchedulingEngine=true`. A disabled registered task is the same
shape plus `Enabled=false`. Status also recognizes the two complete
16-setting COM in-memory round-trip variants produced by the v0.7.0 and v0.7.1
authored payloads. These are explicit whole-shape allowlists, not per-field
wildcards. The current process-token SID is required when Task Scheduler
normalizes the principal and omits the default least-privilege node; any other
principal, setting, value, namespace, trigger, or action fails closed.
Removal performs the same full XML ownership proof before deleting a
same-name task; an absent task remains an idempotent no-op, while an
unverifiable or altered task is retained for explicit operator resolution.

The scheduler-config schema did not change in v0.7.1, v0.7.2, v0.8.0,
v0.8.1, or v0.8.2. Readers accept exactly v0.7.0, v0.7.1, v0.7.2, v0.8.0,
v0.8.1, and v0.8.2 metadata so an existing installation can be inspected and
reinstalled in place; writers always emit v0.8.2. Earlier, unrelated, and
future versions fail closed.

The launcher and scheduler state live below `AIPROFILE_HOME`, not inside the
public Profile repository. On POSIX, a temporary Git index is confined inside
a tool-owned `0700` directory, reset to `0600` after every Git operation, and
removed immediately. Git may transiently rewrite the index with the
repository's configured shared-file mode, so the enclosing `0700` directory is
the confidentiality boundary. Git object creation keeps the repository's
ambient permission policy. Windows relies on the inherited ACL of the user's
home because chmod-style owner bits are not available. The launcher refreshes
`<profile>/dist`.
By default it publishes only byte changes: it builds a commit from the exact
eight paths with that confined temporary index (inherited user-home ACL on
Windows), uses `commit-tree`, advances
the recorded branch with a compare-and-swap `update-ref`, and pushes the
captured immutable commit with an exact expected-old lease bound to the
recorded parent. This is not an unconditional force push: a remote rewind,
advance, or deletion at the push boundary fails closed. It never runs with
`shell=True`, broadly stages/resets the index, unconditionally force-pushes,
or stores a token; Git index/ref mutations are bounded to the exact eight paths
and the one recorded branch through a forward compare-and-swap plus an optional
inverse rollback compare-and-swap. `--no-push` still creates and
compare-and-swap advances the local exact-eight commit, but skips the remote
push.

All scheduler-owned Git subprocesses use one sanitized environment boundary.
Ambient repository-selection, object-store, namespace, replacement-ref,
shallow/graft, alternate-index, tracing, and injected-config variables are
removed; only explicit private-index state and ordinary credential transports
needed by the user's configured remote are allowed. Shallow and partial
repositories are rejected before refresh or pending retry because the isolated
private Git directory requires a complete local object graph. Before a
push-capable refresh, a clean checkout may be fast-forwarded when the actual
remote branch is a verified descendant of the captured local parent OID. The
fetch occurs through the already-captured isolated destination transport, then
a branch compare-and-swap and hook-free worktree/index update are required
before refresh. Missing, behind, dirty, diverged, or unverifiable tips still
reject the run before refresh; a remote that changes while it is being fetched
is retried only within a bounded probe and must resolve to a locally present
commit. The remote must resolve to exactly one fetch destination
and the same one push destination; multiple, different, or unverifiable
destinations reject before refresh. That destination is captured once and
bound to a fixed alias in a private bare Git context. Relative local paths are
first resolved against the Profile repository. Only eight exact allowlisted
credential-helper, TLS, and SSH keys are queried individually and carried into that context;
system/global config and all URL rewrite, proxy, and authorization-header
settings plus ambient proxy variables are excluded. Push/query argv never contains the destination, and
later local/global `insteadOf`, `pushInsteadOf`, remote-alias, or config changes
cannot redirect publication. Credential-bearing URLs, query strings,
fragments, controls, and option-like values fail closed. The same parent is the exact expected-old lease
at the actual push boundary, and a fresh query of the captured destination must
confirm the immutable commit before success is reported.

The completed refresh returns a private in-memory SHA-256 commitment over the
same exact eight generated byte strings. The scheduler verifies the private
index's eight regular blobs against that commitment before `write-tree`; this
is not a ninth output or an ACE/VizStats contract. A lock in the target
repository's canonical Git common directory serializes cooperating homes that
target the same Profile, in addition to each home's scheduler lock.

For push-capable publication, the immutable commit/parent/tree/branch/remote
retry record includes a SHA-256 commitment of the captured destination (never
the URL) and is written privately before the forward branch CAS. A push
failure retains that record. Atomic replacement is the pending writer's last
fallible step, so its result cannot contradict whether the record exists. A
later run retries only the recorded immutable commit when local and remote
state and the current single-destination commitment still match its exact
contract. If the original process stopped before
the forward CAS, retry may complete that CAS only when local and remote both
still equal the recorded parent. It then repairs and verifies the exact-eight
real index, uses the recorded parent as the exact expected-old push lease, and
clears the record only after a fresh remote query confirms the commit.
Any divergence or index-repair failure retains the pending record, refuses
push, and reports possible index/ref/pending residuals. On POSIX,
`pending-push.json` and `last-run.log` are maintained at `0600`; Windows uses
the inherited user-profile ACL.

The plumbing commit deliberately bypasses user commit hooks and signing. This
is the Public Beta tradeoff for binding the exact tree and parent across Git
reference races while preserving unrelated staged content. Branch/ref drift,
detached HEAD, native/local schedule mismatch, registration failure, and
rollback failure fail closed. Where rollback cannot be proven complete, the
fixed diagnostic names the possible local-index, native-schedule, or local-ref
residual without including its value or path.

Native status proves ownership before reinstall or removal. The Windows task
must retain the tool-authored principal, interactive-token logon,
least-privilege run level, single daily trigger/action, instance policy,
exact local date/time boundary without timezone drift, start behavior, enabled
state, and no extra settings children. The launchd
plist must retain exactly the
four tool-owned keys and their exact program arguments and calendar interval;
extra execution keys are treated as unverifiable drift.

### Public GitHub Action

The reusable workflow accepts only explicit public `owner/repo` identifiers.
It checks visibility before a credential-disabled anonymous clone and never
falls back to a PAT, GitHub App, or broader token. Identity emails are a
required secret, not a normal workflow input. Each source is scanned as
`full` in an ephemeral `AIPROFILE_HOME`; therefore this path is not suitable
for private or `aggregate_only` sources.

Permissions are split: read-only collection/rendering, then a separate
`contents: write` exact-eight publication job. Workflow-owned `gh api`, source
`git clone`, and publication `git commit`/`git push` output is suppressed;
their failures use fixed, ordinal- or count-only messages. Pinned setup,
checkout, and Pages actions may emit ordinary metadata about the already-public
caller and revision. Destination links and nonregular files are rejected. The
reusable workflow exposes the
immutable published commit as `published-sha` on both changed and unchanged
paths.

The caller template pins the reusable workflow to the full commit
`18fb08eb6bca4fac6cb4cd1058cc7641452e7bf3`, whose package contract is exactly
`ai-profile-cli==0.8.1`. Caller-level concurrency spans refresh through Pages
deployment. Pages checks out the exact `published-sha` and uses separately
pinned official Pages actions with `contents: read`, `pages: write`, and
`id-token: write`. This explicit same-run deployment is required because a
commit made with `GITHUB_TOKEN` does not trigger ordinary push workflows or a
Pages build. Branch protection may reject direct publication; no PAT bypass
is added.

The maintainer Profile continues to use the local scheduler because its
configured publication set includes an `aggregate_only` source. Migrating it
to the public workflow would silently drop or elevate that policy.

## Consequences

- Users can regenerate the same eight assets daily without changing ACE,
  aggregation, `VizStats`, renderer semantics, or the output contract.
- Public automation is intentionally narrower than local automation and makes
  its already-public source list visible in caller configuration.
- Scheduler availability follows the host OS: the user scheduler and machine
  must be available, and launchd does not replay a time missed while powered
  off.
- The reusable workflow's commit pin is immutable. A future workflow change
  requires a new reviewed pin and caller-template update.
- Private hosted scanning, GitHub App/PAT support, repository discovery,
  model-by-day attribution, a manifest, and a hosted analytics service remain
  out of scope.

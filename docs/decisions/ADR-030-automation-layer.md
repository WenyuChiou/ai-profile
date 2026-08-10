# ADR-030: Automation layer boundary and security

- Status: Accepted for the v0.7.0 candidate (2026-08-09)
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

The launcher and scheduler state live below `AIPROFILE_HOME`, not inside the
public Profile repository. POSIX enforces owner-only modes; Windows relies on
the inherited ACL of the user's home because chmod-style owner bits are not
available. The launcher refreshes `<profile>/dist`.
By default it publishes only byte changes: it builds a commit from the exact
eight paths with a temporary index (0600 on POSIX; inherited user-home ACL on
Windows), uses `commit-tree`, advances
the recorded branch with a compare-and-swap `update-ref`, and non-force pushes
the captured immutable commit object to the recorded remote and branch. It
never runs with `shell=True`, broadly stages/resets the index, force-pushes,
or stores a token; Git index/ref mutations are bounded to the exact eight paths
and the one recorded branch through a forward compare-and-swap plus an optional
inverse rollback compare-and-swap. `--no-push` still creates and
compare-and-swap advances the local exact-eight commit, but skips the remote
push.

The plumbing commit deliberately bypasses user commit hooks and signing. This
is the Public Beta tradeoff for binding the exact tree and parent across Git
reference races while preserving unrelated staged content. Branch/ref drift,
detached HEAD, native/local schedule mismatch, registration failure, and
rollback failure fail closed. Where rollback cannot be proven complete, the
fixed diagnostic names the possible local-index, native-schedule, or local-ref
residual without including its value or path.

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
`9c4f276cb437f1866a2c1b407efe54d3790ce811`, whose package contract is exactly
`ai-profile-cli==0.7.0`. Caller-level concurrency spans refresh through Pages
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

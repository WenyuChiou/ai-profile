# ADR-015: Identity matching (whose commits count)

Status: accepted (2026-07-14)

## Context

A profile-level tool must count *the user's* commits in shared
repositories, without a GitHub API in v0.1.

## Decision

- Config holds a list of the user's author emails (`identities`), seeded by
  `aiprofile init` from `git config user.email` (with what was found shown
  to the user); users add historical/work emails by editing config.
- A commit counts iff its **author email** case-insensitively equals a
  configured identity. Author *names* are not matched (ambiguous,
  spoofable); committer email is not matched (merge/rebase noise).
- Non-matching commits are not stored; the scan summary reports how many
  were skipped so a mis-configured identity is visible, not silent.
- GitHub-login matching (noreply address forms
  `<id>+<login>@users.noreply.github.com` resolution, API identity) is
  post-v0.1; the config shape already accommodates it.

## Consequences

- Deterministic, offline, explainable inclusion rule.
- Users with unconfigured historical emails will see commits skipped —
  surfaced by the scan summary count rather than silently wrong stats.

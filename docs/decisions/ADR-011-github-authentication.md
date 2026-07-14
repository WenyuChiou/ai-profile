# ADR-011: GitHub authentication strategy

Status: accepted (2026-07-14) — v0.1 decision is "none"; future posture fixed

## Context

v0.1 is local-only. Later phases add GitHub discovery (proposal §11, §14,
§30). Authentication posture should be decided before any network code
exists, so it constrains that code rather than being retrofitted.

## Decision

- v0.1: no network calls anywhere; no tokens read, stored, or logged. Core
  unit tests must never touch the network (enforced by review, and by the
  zero-dependency stdlib design — there is no HTTP client in the package).
- Future order of preference: (1) anonymous public API for public-only
  mode; (2) fine-grained PAT, read-only `contents` + `metadata`, supplied
  via environment variable, never persisted to config; (3) GitHub App with
  installation tokens for org scanning. Never classic broad PATs; never
  write scopes for analytics; never a token inside generated assets
  (mandatory leak test when this lands).
- CI/Action log hygiene (future): a GitHub Action running against private
  data writes world-readable logs on a public profile repo. The Action
  mode must run at default verbosity (architecture §10's diagnostics rule:
  sha + trailer key only, no values/paths/repo names), must never echo
  config contents, and its docs must say so before it ships.

## Consequences

- Nothing to secure in v0.1 — the safest auth code is none.
- Phase-4 implementers inherit a pinned, minimal-permission posture.

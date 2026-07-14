# ADR-006: Git Notes namespace

Status: accepted (2026-07-14) — reserved, not implemented in v0.1

## Context

Richer structured metadata than trailers will live in Git Notes (proposal
§8). The namespace must be fixed early so future writers/readers agree.

## Decision

- Namespace: `refs/notes/ai-collaboration`.
- Payload (future): one JSON document per commit, containing ACE
  participation records conforming to `docs/schema.md`, with
  `schema_version` embedded.
- v0.1 neither reads nor writes notes; the reservation exists so nothing
  else squats on the ref and so the git-ai importer (which uses its own
  notes refs) maps *into* this project's schema rather than shares a ref.

## Consequences

- No interop code to maintain yet; the decision removes a future
  bikeshed and prevents accidental ref collisions.

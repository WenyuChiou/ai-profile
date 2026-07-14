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
- **Consume-first posture (Gate 2 finding G2-17):** this project reads
  existing notes formats (git-ai's versioned standard first) before ever
  writing its own. Nothing is written to `refs/notes/ai-collaboration`
  until a concrete field cannot be represented by existing formats or
  trailers AND real interoperability tests justify a new format — creating
  yet another attribution notes convention is exactly the duplication this
  project exists to avoid.

## Consequences

- No interop code to maintain yet; the decision removes a future
  bikeshed and prevents accidental ref collisions.

# ADR-012: Schema versioning

Status: accepted (2026-07-14)

## Context

ACE will evolve (notes payloads, new activity types, metrics). Stored
events must stay readable and version drift must fail loudly, not
silently.

## Decision

- ACE version is semver, `"0.1.0"` now; every event stores the version it
  was written with.
- Pre-1.0 policy: additive optional fields → minor bump; breaking changes
  → minor bump + explicit migration of stored events; patch = doc-only.
- Readers declare a supported set; encountering a stored event above the
  supported `major.minor` aborts aggregation with a clear "upgrade
  aiprofile" error (never silent skipping — silent skipping would corrupt
  counts).
- The SQLite migration sequence (ADR-004) versions the *database layout*
  independently, as plain integers.
- `profile.json` embeds the ACE schema version; the viz data contract
  changes only alongside a schema version bump.

## Consequences

- Version checks are cheap rows/fields, and the failure mode is loud.
- Two version sequences to keep straight — mitigated by naming (`ace
  schema_version` vs `db migration version`) and tests.

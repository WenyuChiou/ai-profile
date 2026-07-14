# ADR-003: Data validation library

Status: accepted (2026-07-14)

## Context

ACE events need strict validation (unknown enum values rejected, required
fields enforced) and deterministic serialization. Candidates: pydantic v2,
attrs+cattrs, stdlib dataclasses with explicit validators.

## Decision

Frozen stdlib `dataclasses` + `enum.Enum` vocabularies + explicit
validation in constructors/factories, raising `SchemaValidationError` with
field-specific messages. Canonical serialization: `json.dumps(...,
sort_keys=True, ensure_ascii=False, separators=(",", ":"))` over an
explicitly-built dict.

Rationale: keeps runtime deps at zero (ADR-001); the vocabulary is small
and stable; validation logic *is* attribution-correctness logic and should
be plainly readable in this repo rather than expressed through a
framework's coercion rules (pydantic's default coercions are exactly what
we must not do — e.g. silently stringifying unknowns).

## Consequences

- ~200 lines of hand-written validation owned and tested here (WP-A).
- No JSON-Schema artifact is shipped in v0.1; `docs/schema.md` is the
  normative spec (a generated JSON Schema can be added later without
  changing the models).

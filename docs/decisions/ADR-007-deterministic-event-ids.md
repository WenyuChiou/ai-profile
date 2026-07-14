# ADR-007: Deterministic event IDs and deduplication identity

Status: accepted (2026-07-14)

## Context

The same participation may surface from several sources (trailer, note,
session log). Counts must not inflate; IDs must be reproducible across
machines and scans (no UUIDs, no clock).

## Decision

Identity fields (schema.md §8): `repository_uid`, `commit_sha`,
`actor.type`, canonical-or-raw `provider`, canonical-or-raw `tool`,
`activity.type`.

```text
event_id = "ace_" + sha256("ace-identity-v1\n" + fields joined by "\n")[:24 hex]
```

**Deviation from proposal §29 (which also lists model and activity role):**
`model` and `roles` are attributes, not identity — two sources describing
the same participation at different precision (model stated vs not; role
list vs superset) must merge into one event, or duplicate evidence inflates
participation counts (violating test invariant 5). Merge rules: role
union, evidence-precedence for scalar attributes, provenance sources
retained (schema.md §8.3).

A participation event therefore means: **this actor tuple (type, provider,
tool) participated in this commit**.

## Consequences

- Idempotent re-scans and future multi-source merging by construction.
- One commit where the same provider+tool genuinely acted twice in
  different roles collapses to one event with the role union — accepted;
  the per-role event split can be revisited with real multi-source data.

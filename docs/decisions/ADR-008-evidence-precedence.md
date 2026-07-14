# ADR-008: Evidence precedence

Status: accepted (2026-07-14)

## Context

When several provenance sources describe one event, which wins? And what
does the event's headline evidence level mean?

## Decision

Precedence (high → low): `verified > declared > imported > inferred >
unknown`.

- An event's `evidence_level` = max over its provenance sources.
- Scalar attribute conflicts (model, mode, human_reviewed) resolve to the
  highest-precedence source's value; ties keep the existing value
  (deterministic first-write-wins under stable scan order).
- **All** sources are retained in `provenance_sources`, including
  superseded ones — stronger evidence takes precedence; weaker evidence
  stays auditable (proposal §29).
- v0.1 producers: `declared` (both trailer forms) and `unknown` (the
  no-evidence marker). `verified`/`imported`/`inferred` are vocabulary with
  no producer yet; renderers must always show inferred separately from
  verified when they do appear.

## Consequences

- Adding the git-ai importer later (`imported`) or signed hooks
  (`verified`) requires no schema change and no re-ranking debate.

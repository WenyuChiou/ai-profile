# ADR-013: Provider and model normalization registry

Status: accepted (2026-07-14)

## Context

Trailer values arrive as free text (`Anthropic`, `anthropic`,
`Claude-Code`); co-author identities arrive as name+email. Aggregation
needs stable grouping without ever guessing.

## Decision

- `registry.py` holds three data tables (plain dicts, reviewed like code):
  1. provider aliases → canonical slug (`anthropic`, `openai`, `google`,
     `github`, `amazon`, ...) + display names (`Claude`, `Codex`, ...);
  2. tool aliases → canonical tool slug + owning provider (lets
     `AI-Tool: Claude-Code` resolve a group with no `AI-Provider`);
  3. known-AI co-author identities: **exact email match**, plus an
     optional per-entry **display-name-prefix condition** for identities
     whose email alone would over-claim (v0.1: `noreply@google.com`
     requires a name starting "Gemini") → provider (+ tool when the
     identity implies it).
- Matching is case-insensitive on the alias; the raw string is always
  preserved in `*_raw` fields.
- Unrecognized values: canonical stays `null` — never dropped, never
  guessed into a known provider. Locally (`aggregate -v`) they are listed
  by raw string; in **public outputs** they collapse into the single
  reserved slug `unrecognized` (schema.md §10 — raw commit-message text
  must not reach published artifacts). `unrecognized` may not be used as
  a registry alias.
- Registry seeds come only from claims **confirmed** by the landscape
  verification lane (docs/landscape.md); unverified strings stay out of
  the registry and are listed as candidates in landscape.md.
- Model names normalize by lowercasing + trimming only; no model alias
  table in v0.1 (model is display data, not identity — ADR-007).

## Consequences

- Adding a tool is a data edit + test, not a code change.
- Rare spellings show up as unrecognized raw values first; users can see
  exactly what string their history contains and file a registry addition.

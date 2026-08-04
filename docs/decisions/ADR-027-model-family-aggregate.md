# ADR-027: Closed model-family aggregate

Status: accepted (2026-08-04)

## Context

ACE events have carried an optional canonical `model` and local-only
`model_raw` value since the first schema.  Before v0.5, aggregation exposed
only provider rows, so a public profile could not answer which model families
were present.  Inferring a model from provider, tool, author, commit message,
or source style would be both a data-contract error and a privacy risk.

The model dimension also has different counting semantics from a headline
commit total: one commit may contain multiple model-family presences and must
be credited to each applicable family without inflating the unique-commit
headline.

## Decision

### Version strategy

The additive model-family visualization contract ships as ACE schema
`0.3.0` (package release `0.5.0`).  `schema_version` remains the shared field
in events, `VizStats`, and `profile.json`: the event payload and the public
aggregate contract move together for this release, so a second version field
would add no information.  The aggregator continues to read stored `0.1.x`,
`0.2.x`, and `0.3.x` events; a stored `major.minor` above that set fails
loudly before any rows are counted.  No SQLite layout migration is needed.
New scans write `0.3.0` events.

If a future public visualization change must evolve independently of the ACE
event payload, it must introduce an explicit `viz_schema_version` field in a
new ADR; it may not silently reuse or relabel `schema_version`.

### Closed vocabulary and normalization

The public family vocabulary is schema-owned and deliberately low-cardinality:

```text
claude, gpt, gemini, llama, mistral, deepseek, qwen, grok, kimi,
other, unknown
```

`normalize_model_category` receives only the canonical ACE `model` value.  A
missing or blank canonical value maps to `unknown`; an explicit value matching
the reviewed family prefix/alias table maps to that family; every other
explicit value maps to `other`.  Provider, tool, author, commit-message,
source-style, and `model_raw` values are never consulted.  The display label
for every category is fixed by `MODEL_DISPLAY` and is validated at the
`VizStats` boundary.

### Aggregate and publication units

`RepoAggregates.models` is an internal dictionary of `ModelAgg` rows.  For one
category:

- `attributed_commits` is a distinct commit count with at least one AI/mixed
  event in that category.  It is non-exclusive across categories.
- `actor_presences` is the number of AI/mixed ACE event records in the
  category.  All model-row presence counts reconcile exactly to
  `totals.ai_actor_presences`, including the `unknown` category.
- `active_dates` is the author-local date set for those presences.

Human and unknown actor commits never create model rows.  An AI/mixed event
with no canonical model creates an `unknown` model presence; it is not
converted to a human commit.  `model_raw` is retained only in the local
aggregation details used by `aggregate -v` and is not representable in
`ModelRow`, `VizStats`, JSON, SVG, HTML, URLs, or alt text.

The privacy builder applies repository publication policy before merging model
rows.  `full` and `aggregate_only` repositories contribute aggregate counts;
excluded repositories contribute nothing.  Repository identity and raw model
strings never cross the boundary.  `VizStats.models` is a validated tuple
ranked by `attributed_commits` descending and category ascending.  It may
include the independent `unknown` row.  `model_count` counts rows other than
`unknown`, so it reports known/other model families rather than treating
missing model evidence as a family.

## Consequences

- Renderers and exporters consume one privacy-safe, schema-owned model ledger;
  they do not read SQLite or raw ACE events.
- Model attributed-commit rows may sum above the unique AI-attributed total;
  consumers must display them as non-exclusive evidence, not as a headline
  total.
- Presence totals are additive and provide a cross-check against the ACE
  population.  Unknown model evidence remains visible and auditable without
  claiming a family.
- Adding a new family, alias, display label, or count unit is a schema/public
  contract change and requires a versioned ADR and regression tests.

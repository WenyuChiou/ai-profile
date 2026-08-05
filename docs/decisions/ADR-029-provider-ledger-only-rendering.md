# ADR-029: Provider-ledger-only rendering

- **Status:** Accepted
- **Date:** 2026-08-05
- **Decision owners:** ai-profile maintainers
- **Supersedes:** the presentation portions of ADR-027 and ADR-028

## Context

The ACE schema, aggregation pipeline, privacy builder, and `VizStats` contract
retain validated model-family evidence. The summary SVG and dashboard also
rendered a separate model-family ledger beside the provider ledger. These two
views repeat overlapping commit evidence and make the provider ledger harder
to scan; the duplicate model panel is presentation noise, not missing data.

## Decision

Keep model-family rows in `VizStats.models`, `profile.json`, and all
schema/aggregation/storage paths. The summary SVG and self-contained dashboard
render only the provider ledger as the public contribution ledger:

- remove the summary's `Model contribution` section and model-dependent height;
- remove the dashboard model panel, model CSS, and model rendering JavaScript;
- keep the provider ledger, evidence rail, daily matrix, deterministic layout,
  and empty/unpublished states unchanged in meaning; and
- keep canonical model rows available to machine-readable consumers without
  claiming that a model visual or model filter exists.

This is a renderer presentation change only. It does not change the ACE schema,
schema version, aggregation units, privacy redaction, storage, or the eight
published output files.

## Consequences

Provider breadth and overlap are represented once in the visual hierarchy,
while canonical model evidence remains available for `profile.json`, local
diagnostics, and future scoped views. Summary snapshots and README sample
assets change because cards become shorter when model rows are present. Tests
must assert both the absence of model visual markup and the continued presence
of provider markup and machine-readable model rows.

## Verification

- renderer tests cover model-rich, model-empty, and deterministic-height cases;
- dashboard tests parse `profileData` to verify model rows remain serialized;
- the sanctioned summary snapshot writer regenerates all affected SVGs; and
- full pytest, Ruff, and README parity checks remain green.

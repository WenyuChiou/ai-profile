# ADR-001: Implementation language and packaging

Status: accepted (2026-07-14)

## Context

The tool must be small enough to install, audit, and maintain; local-first;
cross-platform; and heavy on text/subprocess/SQLite work. The proposal
assumes Python (`pyproject.toml`, `src/aiprofile/`).

## Decision

- Python ≥ 3.11 (dataclass/typing features, broad availability; tested on
  3.11–3.14).
- `src/` layout, single package `aiprofile`, distribution name `ai-profile`.
- Build backend: `hatchling` (modern default, trivial src-layout config).
- **Zero runtime dependencies** — stdlib only (`argparse`, `sqlite3`,
  `subprocess`, `dataclasses`, `json`, `hashlib`, `logging`). Dev extras:
  `pytest`, `ruff`.
- Console entry point: `aiprofile`.
- LICENSE: recommendation is MIT; the actual license grant is the
  repository owner's legal decision and is intentionally left to them
  (flagged in progress.md).

## Consequences

- `pip install ai-profile` pulls nothing else; the whole attribution path
  is auditable in one package.
- Some conveniences (pydantic validation, click UX, rich output) are
  foregone; validation code is written and tested by hand (ADR-003).

# ADR-002: CLI framework

Status: accepted (2026-07-14)

## Context

v0.1 has four subcommands (`init`, `scan`, `aggregate`, `render`) with a
handful of flags. ADR-001 targets zero runtime dependencies.

## Decision

Stdlib `argparse` with subparsers. Exit codes: 0 success, 1 operational
error (`AiProfileError`), 2 usage. `-v/--verbose` toggles logging level.

Rejected: click/typer — pleasant, but a dependency and an idiom for a CLI
this small; adopting one is a reversible later choice if the surface grows.

## Consequences

- Slightly more verbose wiring code, owned in one module (`cli.py`).
- Help text is written manually and tested by smoke tests.

# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html) on the CLI
package. The ACE event schema carries its own semver (ADR-012) and the
SQLite store its own migration chain (ADR-004) — see the upgrade policy
below.

## Upgrade policy

- **Within a minor line (0.1.x):** drop-in. The database migration
  runner applies any pending migrations automatically on the next
  command; config.json is read-compatible; no action needed.
- **Across minors (0.1 → 0.2):** read the release notes first. The ACE
  schema refuses aggregation across incompatible `major.minor` payload
  versions by design (ADR-012) — a release that bumps the event schema
  states explicitly whether existing scanned data re-aggregates or a
  rescan is needed. Your raw repositories are always the source of
  truth: worst case, `aiprofile scan` re-derives everything.
- **Downgrades are unsupported:** the migration chain is forward-only.
  If you must roll back the CLI, delete `~/.aiprofile` (or your
  `AIPROFILE_HOME`) and re-init + rescan — nothing in it is
  irreplaceable (config identities/policy aside, which are a few lines
  of JSON you can note down first).

## [0.1.0] — 2026-07-22

First public release.

### Added

- Vertical slice: `aiprofile init` / `scan` / `aggregate` / `render` —
  explicit AI provenance (AI-* trailers + verified co-author registry)
  from local git repositories into a local SQLite store, rendered as
  privacy-safe SVG cards (light/dark) + `profile.json`.
- Privacy model: local-first (zero network, zero telemetry),
  `aggregate_only` by default, `aggregate` output IS the publish
  preview, structurally sealed `VizStats` publication boundary
  (ten adversarial gate rounds, gates 2–11, each independently
  verified; see `docs/reviews/`).
- Evidence-quality ladder (`verified > declared > imported > inferred
  > unknown`); honest `unknown` for commits without explicit evidence —
  never inferred from code style.
- Pre-release hardening: owner-only file permissions (POSIX-enforced,
  retrofitted to existing installations on every load), git-worktree
  placement warning, cp950-safe console text, packaged-install release
  smoke script, cherry-pick counting semantics documented + tested,
  console (stdout/stderr) canary sweeps, hypothesis property fuzzing
  over the schema invariants.

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

## [Unreleased]

### Added

- Provider brand marks for **OpenAI** and **Grok (xAI)**, vendored from
  a second icon source (lobe-icons, MIT, pinned commit) via
  `vendor_brand_icons.py --source lobe` — both render as proper glyph
  tiles instead of letter tiles. New `THIRD_PARTY_NOTICES.md` carries
  the MIT license text (ADR-017 D5 addendum).

- Two-tier provider model (ADR-019): the DECLARATION tier grows by ten
  providers - Kimi (moonshot), DeepSeek, Qwen (alibaba), Mistral, Grok
  (xai), GLM (zhipu), Ollama, Llama (meta), Replit, Amp - so
  hand-written `AI-Provider:` trailers resolve and rank; the AUTO-MATCH
  tier stays evidence-gated and gains exactly one identity: Amp
  (`amp@ampcode.com`, documented default-on co-author trailer).
- Eight new provider marks vendored mechanically from the pinned CC0
  simple-icons commit via the new `scripts/vendor_brand_icons.py`
  (byte-verified provenance; Amp and Grok have no mark and keep the
  honest letter tile).
- Calendar band polish: intensity-bin legend + "publishable repos only"
  cue, clock-free month boundary labels, and clearer provider-overflow
  wording.
- Repo social-preview card (docs/assets/social-preview.{svg,png}) in
  the banner's visual language.

## [0.2.0] — 2026-07-23

### Added

- Provider brand identity on the summary card (round D1, ADR-017):
  official marks for Claude / Gemini / GitHub Copilot / Cursor /
  Windsurf (CC0 simple-icons subset, byte-verified) with per-theme
  brand-colored bars; honest letter-tile fallback for providers with
  no CC0 mark (OpenAI, Amazon Q, Aider, Roo Code, OpenHands, Devin).
- README banner (docs/assets/banner-{light,dark}.svg): deterministic
  generated hero in the card's own visual language (isometric brand
  stacks), theme-paired.
- Tag-triggered PyPI publish workflow (.github/workflows/publish.yml)
  via PyPI Trusted Publishing (OIDC, no stored secrets); gated on the
  full test suite + ruff before build/upload.
- Isometric daily AI-collaboration calendar (round D2, ADR-018):
  a 12-week 3D activity grid, stacked by provider color, built ONLY
  from explicitly-publishable repositories — aggregate-only
  repositories never surface their activity dates. Fully static SVG
  (no animation - two entrance attempts were invisible in static
  captures and were removed).

### Changed

- ACE schema version 0.1.0 -> 0.2.0: `profile.json` and the internal
  visualization contract gain the additive `daily` series (ADR-012's
  minor-bump rule for additive optional fields, binding post-v0.1.0).
  Databases scanned under 0.1 remain fully aggregatable; new scans
  stamp 0.2.0.

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

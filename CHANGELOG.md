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

No unreleased changes yet.

## [0.4.9] — 2026-08-04 (Public Beta candidate)

### Changed

- Document the Flat Evidence Ledger visual system in `DESIGN.md` and ADR-025,
  including semantic role tokens, local fallback typography, evidence-first
  hierarchy, and the no-network/no-inference boundary.
- Replace the presentation-only perspective daily treatment with a flat
  12-column by 7-row matrix. Daily bar height/share bins, provider overlap,
  privacy semantics, and all eight output filenames/contracts remain unchanged
  (the two summary assets are regenerated with the presentation update).

## [0.4.8] — 2026-08-01

### Changed

- Redesign the summary card as the recruiter-first `AI Collaboration
  Record` (ADR-022): hero AI-attributed commits with share of scanned
  commits, a secondary ledger (active AI days, providers, actor
  presences, unattributed commits), a prominent 12-week isometric
  collaboration terrain, the top-six provider ledger with an explicit
  non-exclusive note, and a compact evidence rail with the existing
  privacy cue and footnote. Width, themes, zero state, and the privacy
  wording are unchanged.
- Make the terrain semantically honest: prism height now encodes the
  day's total commits through the fixed 1 / 2-4 / 5-7 / 8+ bins and the
  top-face hue encodes the day's AI share through the heatmap card's own
  fixed share bins (shared bin arithmetic in `render/_bins.py`).
  Provider counts no longer influence terrain geometry, and a day with
  zero attributed AI commits (not provably human — unattributed history
  counts toward the day's total) is a visible neutral prism instead of
  being indistinguishable from a no-data day. A profile with nonzero
  totals but no published daily series states exactly `Daily activity is
  not published for this profile`.
- Align the dashboard headline (`Evidence-backed AI collaboration.`) and
  the summary card's local IBM Plex display/body/mono type stacks with
  the shared editorial system; refresh the README banner and social
  preview to the same wording. No new fonts, dependencies, network
  access, or active SVG content.
- Show only the Summary Card as the real Profile example in both READMEs
  and move the heatmap preview to "What gets generated".

## [0.4.7] — 2026-07-30

### Fixed

- Exclude generated test, coverage, environment, and bytecode caches from
  source distributions, and make the release artifact contract reject any
  archive containing them.
- Reject non-canonical, duplicate, linked, and special archive members before
  release so wheel and source-distribution paths remain contained and regular.
- Correct the immutable v0.4.6 source-distribution packaging issue, which
  included non-sensitive Hypothesis cache data. The v0.4.6 wheel and runtime
  package were unaffected.

## [0.4.6] — 2026-07-26

### Changed

- Establish the Product Studio visual system across the self-contained
  dashboard, generated SVG family, README banner, and repository social
  preview: ice-blue interaction surfaces, a restrained warm-yellow evidence
  surface, dark-indigo contrast, and the commercially usable IBM Plex
  fallback stack without downloading or embedding fonts.
- Add local, vendored provider glyphs beside visible provider names in the
  dashboard filters and provider ledger. Selection remains available by
  keyboard and is conveyed by text, border, and state as well as color.
- Present evidence-less commits as **Unattributed** in public UI copy, with
  an honest explanation and a future-facing `AI-*` trailer suggestion;
  `unknown` remains distinct from human-declared activity in the schema and
  every aggregate.
- Refresh the public README banner and synthetic output previews, plus the
  1280×640 repository social-preview artwork.

## [0.4.5] — 2026-07-26

### Changed

- Introduce a soft editorial palette that uses pale blue for participation
  and interaction, pale yellow for evidence and attribution context, and
  high-contrast ink colors for labels, data marks, and selection boundaries.
- Increase dashboard reading sizes and touch targets, improve mobile and
  provider-heavy layouts, and use the Candara/Corbel/Avenir humanist stack
  without downloading or embedding fonts.
- Use fixed daily-volume bins (`1`, `2–4`, `5–7`, `8+`) across provider
  filters so identical commit counts retain the same visual intensity.
- Open the horizontally scrollable activity calendar at the newest dates
  while preserving an intentionally selected earlier position.
- Soften the summary card's isometric calendar faces and enlarge provider,
  evidence, and count typography for Profile-scale readability.

### Fixed

- Remove the decorative hero grid on narrow screens so it cannot overlap
  metric context, progress, or ratio labels.
- Use complete provider-row borders and tinted surfaces instead of a
  side-stripe selection treatment.

## [0.4.4] — 2026-07-26

### Changed

- Give the dashboard, GitHub SVGs, README banner, and social preview one
  technical-editorial type system with local Windows, macOS, and Linux
  fallbacks; no font is downloaded or embedded.
- Replace the dashboard's decorative glow, oversized serif voice, pill
  controls, and heavily rounded surfaces with a restrained evidence-ledger
  grid, condensed industrial headings, humanist body text, tabular numerals,
  and explicit structural selection marks.

### Fixed

- Keep the mobile provider-filter grid at full available width so its
  equal-width controls do not collapse into a narrow single column.

## [0.4.3] — 2026-07-26

### Fixed

- Allow the dashboard root to shrink below 320 CSS pixels so classic
  scrollbars do not create page-level horizontal overflow.
- Expose every rendered calendar date through one roving keyboard entry,
  arrow-key navigation, focus/touch detail, repeat-to-close, and Escape,
  instead of hiding mouse-only cells behind a single image role.
- Give active calendar and legend marks a theme-specific high-contrast
  boundary, and raise generated metadata to the normal muted-text token.
- Pass explicit repository context to every checkout-free GitHub Release
  recovery command. The v0.4.2 PyPI files and recovered GitHub Release remain
  immutable.

## [0.4.2] — 2026-07-26

### Fixed

- Include `THIRD_PARTY_NOTICES.md` in both wheel and sdist artifacts. The
  v0.4.1 sdist contained the notice, but its wheel did not; existing releases
  remain available and unmodified.
- Keep selected provider names in the dashboard's normal text color while
  retaining provider accents on marks, borders, bars, and the hero value.
- Wrap provider filters into an equal-width mobile grid so every control
  remains visible without horizontal scrolling at 320 px.

### Changed

- Build, inspect, Twine-check, clean-install, privacy-sweep, and
  determinism-test the exact wheel before uploading those same bytes.
- Freeze the canonical Ubuntu build timestamp in the promotion manifest, and
  fail release recovery unless PyPI serves exactly the retained wheel and
  sdist filenames with matching SHA-256 digests. GitHub Release recovery also
  rejects extra assets and re-downloads the authorized set for checksum
  verification.
- Add Python 3.12 wheel-onboarding smoke coverage on Ubuntu, Windows, and
  macOS.
- Rework English and Traditional Chinese onboarding around a real Profile
  example, explicit product positioning, safe manual configuration, complete
  GitHub Pages instructions, and honest current limitations.
- Add a release runbook and GitHub issue/pull-request templates.

## [0.4.1] — 2026-07-25

### Fixed

- Clarified that provider filters operate within the published record
  and that the unknown-commit count remains global in every provider
  view.

## [0.4.0] — 2026-07-25

### Added

- Self-contained `dashboard.html` generated by `aiprofile render`
  (ADR-021): switch between all AI and one provider, inspect the
  publishable daily record, and toggle light/dark/system themes.
- Dashboard privacy and integrity gates: exact embedded `VizStats`
  payload, restrictive CSP, no external resources or network APIs,
  deterministic bytes, responsive/mobile checks, accessible filter state,
  zero-state coverage, and end-to-end canary sweeps.

### Changed

- The transactional render bundle now publishes six SVG cards,
  `dashboard.html`, and `profile.json` together.
- Refined the dashboard around an editorial evidence-ledger visual system:
  responsive serif display type, monospaced aligned metrics, one
  provider accent at a time, clearer spacing, and balanced light/dark
  surfaces.

## [0.3.1] — 2026-07-25

### Added

- Public `SECURITY.md` with a private vulnerability-reporting path.
- CI coverage for every documented Python version (3.11–3.14).

### Changed

- Reworked the English and Traditional Chinese READMEs around the
  end-user path: install, scan, privacy preview, render, commit `dist/`,
  and refresh. Removed internal design history and development-only
  setup from the public landing page.
- Package maturity classifier advanced from Alpha to Beta.
- Heatmap aesthetic pass: day cells are larger (11px on the same
  grid) with SOLID background-mixed hexes replacing fill-opacity —
  low-volume days no longer wash out against the dark card and every
  final pixel color is a flat deterministic hex; styled stat line
  (counts emphasized, AI share in accent, window range right-aligned);
  cleaner two-axis legend (numeric volume bins kept, AI-share strip
  with end labels only).

## [0.3.0] — 2026-07-23

### Added

- **Collaboration-ratio heatmap** (`heatmap-{light,dark}.svg`,
  ADR-020): GitHub-style year grid where intensity = total commits
  that day — your own human commits included — and hue = the day's
  AI-collaboration share (five quantized bins, neutral → accent). The
  daily series window widens to 365 days (ADR-018 addendum);
  `profile.json` day cells gain `total_commits`/`ai_commits`
  (additive).
- **AI-collaboration badge** (`badge-{light,dark}.svg`): a small flat
  shield — "AI-assisted | K% · verified by git" — using the summary
  card's own headline share and rounding. `aiprofile render` now
  writes all six SVG assets plus profile.json in one atomic bundle.
- Provider brand marks for **OpenAI** and **Grok (xAI)** from a second
  icon source (lobe-icons, MIT, pinned commit) via
  `vendor_brand_icons.py --source lobe`; new `THIRD_PARTY_NOTICES.md`
  carries the MIT text (ADR-017 D5 addendum).
- Two-tier provider model (ADR-019): the DECLARATION tier grows by ten
  providers - Kimi (moonshot), DeepSeek, Qwen (alibaba), Mistral, Grok
  (xai), GLM (zhipu), Ollama, Llama (meta), Replit, Amp - so
  hand-written `AI-Provider:` trailers resolve and rank; the AUTO-MATCH
  tier stays evidence-gated and gains exactly one identity: Amp
  (`amp@ampcode.com`, documented default-on co-author trailer).
- Eight new provider marks vendored mechanically from the pinned CC0
  simple-icons commit via the new `scripts/vendor_brand_icons.py`
  (byte-verified provenance; Amp keeps the honest letter tile - its
  lobe icon is multi-path - and Grok gained its mark via the second
  source above).
- Calendar band polish: intensity-bin legend + "publishable repos only"
  cue, clock-free month boundary labels, and clearer provider-overflow
  wording.
- Repo social-preview card (docs/assets/social-preview.{svg,png}) in
  the banner's visual language.

### Fixed

- Display-name provider declarations resolve (latent since v0.1):
  `AI-Provider: Claude` / `Gemini` / `Copilot` / `Kimi` / `Qwen` /
  `Grok` / `GLM` / `Llama` etc. previously produced canonical-null
  events that published as "Unrecognized". `PROVIDER_ALIASES` now
  derives an entry from every schema-owned display name plus common
  spacing/punctuation variants (Mistral AI, Meta AI, x.ai, Z.ai,
  Moonshot AI), closing the class for future providers too.
- `aiprofile --version` now reports the real version: 0.2.0 bumped
  `pyproject.toml` but not `__version__`, so the CLI kept saying
  0.1.0. Both sources are now pinned together by a regression test.

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

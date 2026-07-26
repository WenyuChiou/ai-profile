# ADR-021 — Self-contained interactive dashboard

Status: accepted
Date: 2026-07-25

## Context

GitHub Profile READMEs cannot execute arbitrary JavaScript. The existing
summary, heatmap, and badge therefore remain static SVG assets. Users also
need a deeper view that can switch between the all-provider record and one
AI provider without publishing repository identities or introducing a
hosted analytics service.

The existing `VizStats` contract already carries the required aggregate
units:

- unique AI-attributed commits;
- AI actor presences;
- provider-attributed commits, presences, and active days;
- publishable daily total/AI/provider counts;
- global evidence totals and privacy metadata.

No raw ACE event, repository row, Git access, or SQLite query is needed.

## Decision

`aiprofile render` adds one optional-to-display but default-generated
artifact: `dashboard.html`.

1. `render_dashboard(stats: VizStats) -> str` is a deterministic pure
   renderer under `aiprofile.render`.
2. The dashboard accepts only the sealed, validated `VizStats` graph. It
   never imports or accesses Git, SQLite, storage, config, aggregation, or
   raw ACE events.
3. CSS, JavaScript, and the exact `profile.json`-equivalent aggregate
   payload are embedded in one HTML file. The page makes no network
   requests, loads no external fonts or scripts, sends no telemetry, and
   carries a restrictive Content Security Policy.
4. Interactions are limited to views the existing contract can express
   honestly:
   - all AI providers;
   - one provider at a time;
   - light, dark, or system color theme;
   - daily activity inspection and provider/evidence ledgers.
5. Filtering selects existing aggregate fields. It does not infer
   attribution or recompute unique-commit semantics:
   - all-provider headline = `totals.ai_attributed_commits`;
   - provider headline = `ProviderRow.attributed_commits`;
   - all/provider presences and active days come from their corresponding
     validated fields;
   - daily cells select `DayCell.ai_commits` or the matching
     `DayCount.attributed_commits`;
   - evidence remains explicitly labelled “All ACE records” because the
     contract does not carry provider-scoped evidence totals.
6. Model, tool, evidence-level, date-range, and repository filters are not
   exposed. Adding them before the contract carries matching scoped
   aggregates would invite renderer-side statistics or misleading labels.
7. The static SVGs remain the GitHub README surface. A README may link to
   `dashboard.html` hosted on GitHub Pages or any static host. This project
   does not provide a hosted database, account service, or analytics
   backend.
8. `profile.json` and ACE schema `0.2.0` are unchanged. The dashboard is an
   additive renderer/output, not a data-contract change.

## Visual system

The dashboard uses an editorial evidence-ledger direction:

- a restrained GitHub Primer-derived palette with one active-provider
  accent at a time;
- a technical-editorial local type system: condensed industrial display,
  humanist UI, and monospaced numeric stacks with Windows, macOS, and Linux
  fallbacks and no external font request;
- responsive type via `clamp()`, minimum 12px supporting text, strong
  number alignment, and generous negative space;
- native buttons, visible focus states, `aria-pressed` filter state,
  live-region selection announcements, text equivalents for chart
  semantics, and reduced-motion support;
- color never changes a metric definition and is not the only carrier of
  meaning.

## Consequences

- Users receive an interactive dashboard without installing a web
  framework or operating a service.
- Publishing `dashboard.html` reveals the same aggregate data already
  present in `profile.json`; it does not create a new privacy tier.
- The generated bundle grows by one file and remains transactionally
  published.
- GitHub README interaction remains a link-out because JavaScript inside
  README content is not feasible.
- The renderer is intentionally plain HTML/CSS/JavaScript. A component
  framework, chart dependency, plugin system, and dashboard backend remain
  unnecessary.

## Verification

- deterministic byte equality for identical `VizStats`;
- exact embedded payload equality with `to_json_dict(stats)`;
- no network APIs or external resource references;
- CSP, responsive, theme, reduced-motion, and accessibility-contract tests;
- all/provider metric-unit tests;
- zero-state and script-data escaping tests;
- end-to-end privacy canary sweep over every generated output;
- browser interaction probes at desktop and mobile widths.

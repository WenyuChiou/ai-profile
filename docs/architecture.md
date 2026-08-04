# Architecture — v0.1

Status: finalized for v0.1 (2026-07-14; revised same day after the Phase 0
three-lens adversarial review). Scope: the first vertical slice
(`docs/mvp.md`); future layers are sketched only where a v0.1 decision must
not paint them out.

## 1. Layers and data flow

```text
 local Git repository (configured explicitly)
        │
        ▼
 collection  ──────  gitio.py: one `git log HEAD` pass per repo
        │            → CommitRecord stream (sha, author, dates, trailers)
        ▼
 adapters    ──────  adapters/trailers.py: AI-* trailer groups +
        │            known-AI Co-authored-by → ParticipationSpec[]
        │            (uses registry.py for provider/tool normalization)
        ▼
 normalization ────  schema/: build validated ACE events
        │            (deterministic event_id, schema.md §8;
        │             zero-evidence commits → one unknown event;
        │             human-only declarations → one human event)
        ▼
 storage     ──────  storage/: atomic per-repo replace of scan-derived
        │            rows (ADR-014) — idempotent, rewrite-safe
        ▼
 aggregation ──────  aggregate.py: SQL over events/commits →
        │            RepoAggregates (internal, per-repo, uid-keyed)
        ▼
 privacy     ──────  privacy.py: RepoAggregates + config policy → VizStats
        │            (THE redaction boundary — see §3)
        ▼
  render / export ──  render/: VizStats → summary, badge, heatmap SVGs
                              + self-contained interactive dashboard HTML
                     export.py: VizStats → SVG/HTML/profile.json artifact set
```

## 2. Module map and dependency direction

```text
src/aiprofile/
  __init__.py          version
  errors.py            exception hierarchy
  config.py            config model + load/save (AIPROFILE_HOME);
                       publication-policy resolution (schema.md §9)
  gitio.py             git subprocess abstraction (collection) +
                       versioned repository-identity canonicalizer
                       (pure function; ADR-016)
  registry.py          provider/tool + AI co-author registry
  schema/
    vocab.py           enums / controlled vocabularies
    event.py           ACE dataclasses, validation, event_id, to_dict()
  adapters/
    trailers.py        trailer parsing → ParticipationSpec
  scanner.py           orchestrates gitio→adapters→schema→storage per repo
  storage/
    db.py              connection + migration runner
    migrations.py      ordered SQL migrations
    store.py           persistence ops (atomic per-repo replace; queries)
  aggregate.py         RepoAggregates (internal dataclass, defined here)
                       from SQL, per schema.md §15 definitions
  privacy.py           RepoAggregates + config → VizStats (redaction)
  viz.py               VizStats dataclasses (the visualization contract)
  render/
    themes.py          theme tokens (github-light / github-dark)
    _bins.py           shared day-cell volume/AI-share bin arithmetic
                       (ADR-020/ADR-022; summary matrix and heatmap must
                       never disagree about a bin)
    brand.py           vendored provider marks + per-theme brand palette
                       (CC0 simple-icons subset; ADR-017; schema-free by
                       design - drift-tested mirror of the vocab set)
    summary_svg.py     deterministic summary card renderer
    heatmap_svg.py     deterministic collaboration-ratio heatmap
    badge_svg.py       deterministic compact collaboration badge
    dashboard_html.py  deterministic self-contained interactive dashboard
                       (post-v0.1 additive renderer; ADR-021)
  export.py            transactional public-asset + profile.json writer
  cli.py               argparse wiring: init / scan / aggregate / render
```

Allowed dependency direction (→ = may import):

```text
cli → everything below
scanner → gitio, adapters, schema, storage, config, errors
adapters → registry, schema.vocab, errors
schema → (stdlib only)
storage → schema, errors
aggregate → storage, errors          # defines RepoAggregates
privacy → aggregate, viz, config, registry*, errors
render → viz, themes, errors          # NEVER storage, gitio, schema, sqlite3
export → viz, errors                  # NEVER storage, gitio
```

(*) The privacy → registry edge (gate M-08) is display-name resolution
ONLY, applied strictly AFTER the canonical-slug collapse — registry
fallback behavior can never become publication behavior for a
non-canonical key (gate H-02).

Enforced two ways (G2-16): a runtime test imports `render` and `export`
in a fresh interpreter and asserts `sqlite3`, `subprocess`,
`aiprofile.storage`, `aiprofile.gitio` are absent from the module graph,
AND a static AST test walks their import statements (catches lazy/dynamic
imports the runtime check could miss). Renderers consume validated
`VizStats` only; they cannot recalculate attribution because they never
see events.

No hidden global state: configuration and database handles are constructed
in `cli.py` and passed explicitly.

The presentation contract is documented in the repository-root `DESIGN.md`
and governed by ADR-025 (Flat Evidence Ledger). This is a
maintainer-facing visual source of truth only; it is not runtime configuration
and cannot carry event or repository identity data.

## 3. Privacy enforcement (the redaction boundary)

`VizStats` is the only object renderers and exporters accept. Its fields
are counts, canonical provider/model slugs/display names, evidence totals,
period, boolean flags, and a UTC generation date. No repository
uid/name/path, no author emails, no commit shas, no messages, no local
paths, no raw trailer strings exist in the type — and since gate-7 H-01
this is VALIDATED, not conventional: `VizStats.__post_init__` pins every
string field to a closed public vocabulary (the supported ACE schema
version, the fixed v0.1 all-time period, canonical provider/model slugs from
schema.md §10 and ADR-027, and the schema-owned display name for each slug),
so a validated instance structurally cannot carry arbitrary private text into
SVG or JSON regardless of who constructed it. Since gate-8 H-01 the
GRAPH is immutable too: validation requires the exact frozen contract
types (never subclasses or duck types) for every nested record, the
tuple container, and exact `str` for every string leaf — so
post-construction mutation of anything a validated instance references
raises rather than republishing. Since gate-9 H-01, `VizStats` is SEALED against subclassing at
class-definition time (`__init_subclass__` raises): a plain subclass is
an ordinary Python construct that defeats every in-method guard — it can
override `__getattribute__` to hand render/export a private-canary row,
or simply override `__post_init__` to skip validation entirely — so the
boundary type itself, not just its fields, must be exact, and no subclass
can even be defined (a `type(s) is VizStats` backstop remains inside
validation). Nothing legitimate subclasses `VizStats`
(`dataclasses.replace`/`copy`/`pickle` all yield exact `VizStats`).
Scope (honest limit): this protects against ordinary attribute
assignment, duck-typed construction, and all subclassing; deliberate
low-level bypasses
(`object.__setattr__`, ctypes, pickle surgery) are out of scope,
consistent with the `merged`-marker precedent — a local single-user CLI
has no adversarial multi-tenant threat model.

`privacy.py::build_viz_stats(repo_aggs, config, generated_on) -> VizStats`
is the single constructor, and applies exactly these rules:

1. **Policy resolution from config only** (schema.md §9): each per-repo
   aggregate row joins to the current config entry by `repository_uid`.
   No entry → treated as `excluded`. Multiple entries for one uid → most
   restrictive level wins.
2. **Exclusion**: `excluded` rows are dropped (they were already skipped
   at scan time; this covers rows stored before a level flip —
   defense in depth). No excluded-repository count appears in `VizStats`
   or any public artifact (existence metadata is what exclusion hides);
   it is reported only in local terminal output.
3. **Publishable split** (unit: commits, schema.md §15; policy-based
   labels, never visibility claims — G2-04): `full` → explicitly
   publishable commits; `aggregate_only` → anonymous aggregate commits;
   `includes_anonymous_aggregate` flag set when the latter is nonzero.
4. **Unrecognized/model collapse** (schema.md §10, ADR-027): all
   canonical-`null` provider groups merge into the reserved `unrecognized`
   bucket; model rows use only the closed family vocabulary, with missing
   canonical models in `unknown` and explicit unmatched values in `other`.
   Raw provider/model strings never cross this boundary.
5. **Identity stripping**: repo-level rows are summed; nothing uid-keyed
   survives into `VizStats`.

Two mandatory integration tests pin this boundary: (a) scan a "private"
fixture repo with a distinctive name/path/author and assert name, path,
uid, and author email appear nowhere in any byte under `dist/`; (b) give
a fixture commit a distinctive unrecognized `AI-Provider` value and
assert that string appears nowhere under `dist/` while the
`unrecognized` bucket counts it.

## 4. Collection layer (v0.1)

- Explicit configuration only: `aiprofile scan <path>` registers (or
  re-scans) one local repository. No directory-tree discovery in v0.1.
- `gitio.py` shells out to the system `git` (no Git library) with one
  enumeration pass per repo:

  ```text
  git log HEAD --pretty=format:%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%(trailers:only,unfold)
  ```

  (Fields: sha, author name, author email, author date, trailers — each a
  documented consumer; committer date is deliberately not collected.)

  `%x1e`/`%x1f` are record/field separators; `%(trailers:only,unfold)` is
  the portable ≥ 2.17 boolean-bare form (byte-identical to the `=true`
  form on 2.47.1 — validated locally; minimum supported git pinned at
  2.17, documented in README).
- HEAD-reachable commits only, matching ADR-014's semantics.
- Non-repo path, corrupt repo, or missing git binary → `GitError` with the
  failing command and stderr excerpt; the CLI reports and exits nonzero.
  (Terminal-only; see §10 diagnostics rules.)

## 5. Adapter layer (v0.1)

One adapter: the Git trailer adapter (`adapters/trailers.py`), covering:

- `AI-*` trailer groups (grouping rule pinned in ADR-005, including the
  human-only exception and the contradiction rule);
- `Co-authored-by:` values matching the known-AI registry (exact email
  match, plus a display-name-prefix condition where the entry requires
  one — ADR-013).

Adapters return `ParticipationSpec` values (plain data: actor fields, roles,
mode, human_reviewed, provenance source) plus parse warnings. They never
touch the database, never guess, and never emit anything for evidence they
did not see. The `AttributionAdapter` protocol from the proposal §28 is
deliberately **not** introduced yet — one concrete adapter does not justify
an abstraction (it will be extracted when the second adapter lands,
post-v0.1).

## 6. Local storage

SQLite (stdlib `sqlite3`), file at `<AIPROFILE_HOME>/aiprofile.db`.
Migrations: ordered, numbered SQL scripts applied in one transaction each,
recorded in `schema_migrations` (ADR-004). Tables (v0.1):

```text
schema_migrations(version PK, applied_at)
repositories(id PK, repository_uid UNIQUE, display_name, local_path,
             last_scanned_at)
commits(id PK, repository_id FK, sha, author_email, author_date,
        UNIQUE(repository_id, sha))
events(id PK, event_id UNIQUE, repository_id FK, commit_id FK,
       actor_type, provider, provider_raw, model, model_raw, tool, tool_raw,
       roles_json, contribution_mode, human_reviewed, evidence_level,
       activity_type, activity_timestamp, recorded_at, schema_version)
provenance_sources(id PK, event_id FK, source_type, source_reference,
                   evidence_level,
                   UNIQUE(event_id, source_type, source_reference))
```

Notes:

- **Publication level is deliberately absent** — it lives only in config
  (schema.md §9). The database is a disposable cache of scan results;
  policy must not live in a cache.
- `display_name` = directory basename captured at scan registration;
  consumed only by local terminal output (scan/aggregate summaries).
  `local_path`/`author_email` likewise live only in this local, private
  database (identity filtering, future reconciliation).
- Scan write path (ADR-014): one transaction per repo per scan —
  delete the repo's commits/events/provenance rows, reinsert from the
  fresh enumeration, update `last_scanned_at`. Idempotent and
  rewrite-safe by construction.
- No `daily_aggregates` table in v0.1 — aggregates are computed on demand;
  materialization is a measured optimization for later, not a default.

## 7. Aggregation

`aggregate.py` computes `RepoAggregates` — an internal dataclass defined
in this module, one row per repository uid, holding the schema.md §15
counts (commits scanned, AI-attributed commits, actor presences,
human/unknown commits, per-provider commit/event/day counts keyed by
canonical slug or `None`, per-model-family commit/event/day counts keyed by
the closed ADR-027 category vocabulary, evidence totals in events, and
active-day date sets). It is internal to the pipeline: only `privacy.py` may
consume it, and it never reaches renderers, exports, or stdout.  Model
projection reads only the canonical `events.model` column; `model_raw` remains
local diagnostic data on `ModelAgg`.

Period filtering is post-v0.1 (all-time only; schema.md §15).

## 8. Visualization data contract

`viz.py` defines `VizStats` (dataclasses, validated on construction):

```text
VizStats
  schema_version: str
  period: {from_date: None, to_date: None, label: "All time"}   # v0.1
  totals: {commits_scanned, ai_attributed_commits, ai_actor_presences,
           human_declared_commits, unknown_commits, active_ai_days}
  providers: [ {provider, display_name, attributed_commits,
                actor_presences, active_days} ]
      # ranked by attributed_commits desc, then slug asc (deterministic);
      # may include the reserved `unrecognized` bucket, ranked like any row
  provider_count: int        # distinct providers excluding `unrecognized`
  models: [ {category, display_name, attributed_commits,
             actor_presences, active_days} ]
      # ranked by attributed_commits desc, then category asc (deterministic);
      # closed ADR-027 categories; may include `unknown`
  model_count: int            # model rows excluding `unknown`
  evidence: {verified, declared, imported, inferred, unknown,
             total_records}  # population: ALL ACE records (G2-05)
  privacy: {explicitly_publishable_commits, anonymous_aggregate_commits,
            includes_anonymous_aggregate: bool}   # policy labels (G2-04)
  generated_on: str          # UTC date, YYYY-MM-DD, injected by the caller
```

Construction-time invariants (validated, G2-05/§9 of the Gate 2 review):
evidence categories sum to `total_records`; publishable + anonymous
aggregate commits equal `commits_scanned`; provider `actor_presences`
rows sum to `totals.ai_actor_presences`; when model rows are present, their
`actor_presences` rows also sum to `totals.ai_actor_presences`; each provider
and model row's `attributed_commits` ≤ `totals.ai_attributed_commits`;
`ai_attributed_commits` ≤ `commits_scanned`.

This is the contract consumed by `render/` and `export.py` and serialized
(sorted keys, deterministic) into `profile.json`. The v0.5 model ledger is an
additive ACE `0.3.0` change (ADR-027); future contract changes require the
schema-version strategy in ADR-012/ADR-027. `generated_on` is date-only by
design (a full
timestamp would disclose timezone/working hours in a published artifact —
supersedes the proposal §24 example). No `manifest.json` in v0.1 (nothing
consumes it until the GitHub Action lands).

## 9. Rendering

- Pure functions: `render_summary(stats: VizStats, theme: Theme) -> str`.
- Deterministic output: byte-identical SVG for identical inputs (snapshot
  tests); no clock reads inside render (only `generated_on` from the
  contract); no randomness; fixed decimal formatting.
- Provider table: top 6 rows; remaining providers collapse to one
  "+N providers not shown" line (counts included in totals regardless),
  with an explicit
  non-exclusive note (ADR-022). The post-v0.4.8 evidence-ledger refinement
  keeps count and percentage in separate right-aligned columns and uses a
  quiet border-token section marker; this is presentation-only (ADR-023).
- Model-family table: top 4 explicit model categories; remaining categories
  collapse to one "+N model categories not shown" line. It is an all-time,
  non-exclusive ledger sourced from `VizStats.models`; it never changes daily
  terrain geometry and never offers a model filter without a matching scoped
  aggregate contract (ADR-027). Its two-character category marks and neutral
  model bar token are presentation-only; the collaboration accent remains
  reserved for the hero, share bar, provider bars, and header mark.
- The Flat Evidence Ledger refinement (ADR-025) supersedes the perspective
  treatment for the summary's daily visual. It renders a 12-column by 7-row
  matrix of neutral tracks; each published day adds a bottom-anchored bar
  whose height comes from `DayCell.total_commits` (fixed 1 / 2-4 / 5-7 / 8+
  bins) and whose fill comes from the day's AI share — the same fixed bins as
  the heatmap card, shared via the private `render/_bins.py` helper. Provider
  counts never influence matrix geometry. Publishable-only; an unpublished
  daily series renders an explicit notice, never a fabricated grid.
- Two assets in v0.1: `summary-light.svg`, `summary-dark.svg` (embedding via
  `<picture>` in the README — documented in mvp.md). Accessibility:
  `<title>`, `<desc>`, ≥11px labels, non-color distinctions, explicit metric
  labels and definitions footer.
- Text width handled with a conservative character-width table (no font
  dependencies); layout truncates provider names with an ellipsis rather
  than overflowing.

Post-v0.1, ADR-021 adds
`render_dashboard(stats: VizStats) -> str`. It obeys the same dependency
and privacy boundary as the SVG renderers and embeds only the exact
`profile.json`-equivalent aggregate payload. The resulting
`dashboard.html` is self-contained: no external fonts, scripts, network
requests, telemetry, storage access, or Git access. Its JavaScript selects
existing all-provider or provider-scoped aggregate fields; it does not
infer attribution or rebuild statistics. GitHub READMEs continue to use
static SVG because GitHub does not execute arbitrary JavaScript; users may
link those cards to the HTML file on a static host.

## 10. Error handling and diagnostics hygiene

- `errors.py`: `AiProfileError` → `ConfigError`, `GitError`,
  `StorageError`, `SchemaValidationError`, `RenderError`.
- CLI: catches `AiProfileError`, prints one clear actionable line (plus
  stderr detail with `--verbose`), exits 1; usage errors exit 2; success 0.
- Parse-level problems in commit messages are **warnings, not errors**
  (collected per scan, summarized at the end). A malformed trailer never
  aborts a scan and never invents data.
- **Pinned diagnostics rule (privacy):** default-verbosity warnings may
  reference a **scan-local commit ordinal** ("commit #17") and the
  trailer *key* only — never commit SHAs (stable cross-system
  correlators; G2-08), trailer values, commit-message text, repository
  names, or paths. SHAs and trailer values appear only under
  `--verbose`, which the future CI/Action mode must not enable (ADR-011). `GitError` messages may include the failing command
  and paths — they go to the terminal only; nothing from the error/warning
  path can reach `dist/`, whose writers accept `VizStats` alone (§3).
- Structured logging via stdlib `logging` (`aiprofile.*` loggers); `-v`
  raises verbosity; no log files by default.

## 11. Incremental scanning strategy

v0.1 re-enumerates the full history on every scan and atomically replaces
the repository's scan-derived rows (correct, simple, idempotent,
rewrite-safe). `repositories.last_scanned_at` exists for display only.
An incremental walk is a post-v0.1 optimization that must preserve the
same observable semantics (and must land together with the
manual-event-preservation change noted in schema.md §14); measured
performance, not speculation, will decide when.

## 12. Optional future GitHub integration (not in v0.1)

Phase 4+ (proposal §11, §14, §30): public-API discovery, fine-grained PAT
or GitHub App (read-only contents+metadata), incremental commit retrieval,
and a reusable Action. The v0.1 design keeps this pluggable by making the
collection layer the only place that knows where commits come from;
everything from adapters down is source-agnostic. No auth code, no tokens,
no network in v0.1 (and no network in any core unit test, ever).

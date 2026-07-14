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
 render / export ──  render/: VizStats → summary SVGs (light/dark)
                     export.py: VizStats → profile.json
```

## 2. Module map and dependency direction

```text
src/aiprofile/
  __init__.py          version
  errors.py            exception hierarchy
  config.py            config model + load/save (AIPROFILE_HOME);
                       publication-policy resolution (schema.md §9)
  gitio.py             git subprocess abstraction (collection)
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
    summary_svg.py     deterministic summary card renderer
  export.py            profile.json writer
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
privacy → aggregate, viz, config, errors
render → viz, themes, errors          # NEVER storage, gitio, schema, sqlite3
export → viz, errors                  # NEVER storage, gitio
```

Enforced by a unit test that imports `render` and `export` modules and
asserts `sqlite3`, `subprocess`, `aiprofile.storage`, `aiprofile.gitio` are
absent from their module graphs. Renderers consume validated `VizStats`
only; they cannot recalculate attribution because they never see events.

No hidden global state: configuration and database handles are constructed
in `cli.py` and passed explicitly.

## 3. Privacy enforcement (the redaction boundary)

`VizStats` is the only object renderers and exporters accept. Its fields
are counts, canonical provider slugs/display names, evidence totals,
period, boolean flags, and a UTC generation date. No repository
uid/name/path, no author emails, no commit shas, no messages, no local
paths, no raw trailer strings exist in the type.

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
3. **Public/private split** (unit: commits, schema.md §15): `full` →
   public commits; `aggregate_only`/`repository_anonymous` → private
   aggregate-only commits; `includes_private` flag set when the latter
   is nonzero.
4. **Unrecognized collapse** (schema.md §10): all canonical-`null`
   provider groups merge into the single reserved `unrecognized` bucket;
   raw strings never cross this boundary. (`aggregate -v` prints raw
   unrecognized values locally so users can request registry additions.)
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
counts (commits scanned, AI-attributed commits, participation events,
human/unknown commits, per-provider commit/event/day counts keyed by
canonical slug or `None`, evidence totals in events, active-day date
sets). It is internal to the pipeline: only `privacy.py` may consume it,
and it never reaches renderers, exports, or stdout.

Period filtering is post-v0.1 (all-time only; schema.md §15).

## 8. Visualization data contract

`viz.py` defines `VizStats` (dataclasses, validated on construction):

```text
VizStats
  schema_version: str
  period: {from_date: None, to_date: None, label: "All time"}   # v0.1
  totals: {commits_scanned, ai_attributed_commits, ai_participation_events,
           human_declared_commits, unknown_commits, active_ai_days}
  providers: [ {provider, display_name, attributed_commits,
                participation_events, active_days} ]
      # ranked by attributed_commits desc, then slug asc (deterministic);
      # may include the reserved `unrecognized` bucket, ranked like any row
  provider_count: int        # distinct providers excluding `unrecognized`
  evidence: {verified, declared, imported, inferred, unknown}   # unit: events
  privacy: {public_commits, private_aggregate_commits, includes_private: bool}
  generated_on: str          # UTC date, YYYY-MM-DD, injected by the caller
```

This is the contract consumed by `render/` and `export.py` and serialized
(sorted keys, deterministic) into `profile.json`. It changes only with a
schema-version bump. `generated_on` is date-only by design (a full
timestamp would disclose timezone/working hours in a published artifact —
supersedes the proposal §24 example). No `manifest.json` in v0.1 (nothing
consumes it until the GitHub Action lands).

## 9. Static rendering

- Pure functions: `render_summary(stats: VizStats, theme: Theme) -> str`.
- Deterministic output: byte-identical SVG for identical inputs (snapshot
  tests); no clock reads inside render (only `generated_on` from the
  contract); no randomness; fixed decimal formatting.
- Provider table: top 6 rows; remaining providers collapse to one
  "+N more" line (counts included in totals regardless).
- Two assets in v0.1: `summary-light.svg`, `summary-dark.svg` (embedding via
  `<picture>` in the README — documented in mvp.md). Accessibility:
  `<title>`, `<desc>`, ≥11px labels, non-color distinctions, explicit metric
  labels and definitions footer.
- Text width handled with a conservative character-width table (no font
  dependencies); layout truncates provider names with an ellipsis rather
  than overflowing.

## 10. Error handling and diagnostics hygiene

- `errors.py`: `AiProfileError` → `ConfigError`, `GitError`,
  `StorageError`, `SchemaValidationError`, `RenderError`.
- CLI: catches `AiProfileError`, prints one clear actionable line (plus
  stderr detail with `--verbose`), exits 1; usage errors exit 2; success 0.
- Parse-level problems in commit messages are **warnings, not errors**
  (collected per scan, summarized at the end). A malformed trailer never
  aborts a scan and never invents data.
- **Pinned diagnostics rule (privacy):** default-verbosity warnings may
  reference the commit sha and the trailer *key* only — never trailer
  values, commit-message text, repository names, or paths. Trailer values
  appear only under `--verbose`, which the future CI/Action mode must not
  enable (ADR-011). `GitError` messages may include the failing command
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

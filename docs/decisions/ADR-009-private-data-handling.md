# ADR-009: Private data handling and the redaction boundary

Status: accepted (2026-07-14; revised same day after the Phase 0 privacy
review)

## Context

Aggregate stats from private repositories may be published, but names,
paths, org names, branches, messages, raw trailer values, and URLs must
never leak (proposal §3.5, §12, §27; §34 invariants 3 and 7). Redaction
must be structural, not best-effort.

## Decision

- Publication levels per repository: `full | repository_anonymous |
  aggregate_only | excluded`, with **exactly one home: `config.json`**
  (schema.md §9). The database stores no policy; events carry no policy;
  aggregation resolves levels from current config at query time, so a
  config edit takes effect without a rescan and stale copies cannot
  exist. A repository absent from config is treated as excluded
  (fail-closed); duplicate entries for one uid resolve to the most
  restrictive level.
- **Default for every newly scanned repo is `aggregate_only`** (v0.1
  cannot verify GitHub visibility; the user explicitly opts up with
  `scan --full`). `excluded` repos are skipped at scan time and
  re-excluded at aggregation (defense in depth — covers rows stored
  before a level flip).
- **The redaction boundary is the `VizStats` type**, built solely by
  `privacy.py` (architecture §3): counts, canonical slugs/display names,
  evidence totals, flags, a UTC date. Structurally absent: repository
  identity, emails, shas, paths, raw trailer strings, excluded-repo
  counts (existence metadata is what exclusion hides), sub-date
  timestamps. Unrecognized provider values collapse into the reserved
  `unrecognized` bucket before this boundary (schema.md §10) — raw
  commit-message text never crosses it.
- **Publication labels are policy-based, never visibility claims**
  (Gate 2 finding G2-04): the contract says `explicitly_publishable` /
  `anonymous_aggregate`, because `full` records a user decision, not
  verified GitHub visibility. "Public/private" wording is reserved until
  a collector verifies visibility and records how.
- Diagnostics hygiene is pinned in architecture §10 (default warnings:
  scan-local commit ordinal + trailer key only — **never a commit SHA at
  default verbosity** (Gate 2 finding G2-08, SHAs are stable
  cross-system correlators); values and SHAs only under `--verbose`;
  nothing from the warning/error path can reach `dist/`).
- The honest guarantee is **identity redaction, not anonymity**: exact
  aggregate counts published repeatedly allow differencing inferences
  about when private activity changed. `docs/PRIVACY.md` is the threat
  model of record (Gate 2 finding G2-09).
- The local DB may hold repo names/paths/author emails (identity
  filtering, future reconcile) — private, local, and disposable.
  **Deletion scope, stated honestly:** removing `AIPROFILE_HOME` deletes
  config and database; generated `dist/` assets and any copies the user
  published are separate user-placed files (post-v0.1 `purge` helper
  candidate). Users must not sync `AIPROFILE_HOME` into published
  dotfiles (it contains the salt and private paths) — documented in
  mvp.md §4 and README.
- A per-install random salt (created by `init`, stored in config, never
  published) backs `local:` repository uids (full 64-hex digest —
  schema.md §7). If `repository_anonymous` per-repo views ship later,
  **published anonymous IDs must use a separate dedicated secret** (e.g.
  HMAC key), not this salt: repo names are low-entropy, and a leaked
  config would otherwise retroactively de-anonymize every published ID
  with no rotation story.
- Mandatory integration tests: the dist/ leak test (repo name/path/uid/
  author email AND a distinctive unrecognized raw trailer value) and the
  policy-resolution test (flip-after-scan honored; absent-from-config →
  excluded) — mvp.md §7 tests 9–10.

## Consequences

- Privacy review of outputs reduces to one dataclass, one constructor
  (`privacy.py`), and two leak tests.
- `repository_anonymous` is RESERVED vocabulary: v0.1 config validation
  rejects it with a targeted error (G2-12); it returns with anonymous
  per-repository views — documented in schema.md §9.

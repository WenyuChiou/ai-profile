# ADR-014: Rewritten Git history

Status: accepted (2026-07-14; revised same day — the Phase 0 complexity
review showed the original last-seen/scan-id stamping mechanism was
untested intricacy that a simpler mechanism makes unnecessary)

## Context

Rebase/amend/squash change commit SHAs. A naive accumulating event store
keeps both the old and new SHA and silently double-counts (proposal §34
invariant 6). The first design tracked reachability with a `scans` table
plus `first_seen/last_seen_scan_id` stamps and a filter predicate in every
aggregation query — machinery whose one load-bearing behavior had no
required test, and which a full-enumeration scanner does not need.

## Decision

- Each `aiprofile scan` runs **one transaction per repository**: delete
  the repository's scan-derived rows (commits, events, provenance
  sources), reinsert from the fresh `git log HEAD` enumeration, update
  `repositories.last_scanned_at`. Commit or roll back atomically.
- Consequences by construction, with required tests (mvp.md §7): repeated
  scans are idempotent (test 6); rewritten/amended history counts once —
  old SHAs simply vanish on the next scan (test 15: amend → rescan →
  counts unchanged, old sha absent).
- Commits on non-HEAD branches are out of v0.1 scope (scanning `--all`
  would import work-in-progress branches and increase privacy surface —
  revisit with real demand).
- Superseded rows are **not** retained (the DB is a disposable local cache,
  rebuildable by re-scanning; nothing in v0.1 could display retained rows
  anyway). If audit retention becomes a requirement, it returns as an
  explicit feature with a viewer, not as silent rows.
- Forward constraint (recorded in schema.md §14): the post-v0.1 version
  that introduces `manual_declaration` events MUST change this replace
  step to preserve them (filtered delete), and the incremental-scan
  optimization (architecture §11) must preserve these exact observable
  semantics.

## Consequences

- No scan-state tables, no per-query reachability predicates, and the
  rewrite invariant is tested rather than asserted.
- Full re-enumeration per scan is the cost — acceptable at v0.1's
  single-repo scale and already the chosen collection strategy.

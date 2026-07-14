# ADR-008: Evidence precedence

Status: accepted (2026-07-14)

## Context

When several provenance sources describe one event, which wins? And what
does the event's headline evidence level mean?

## Decision

Precedence (high → low): `verified > declared > imported > inferred >
unknown`.

- An event's `evidence_level` = max over its provenance sources.
- Scalar attribute conflicts (model, mode, human_reviewed) resolve by a
  **canonical, ingestion-order-free rule** (Gate 2 finding G2-06 replaced
  the earlier first-write-wins-under-scan-order): higher evidence
  precedence wins; ties break by source-type priority
  (`git_trailer > git_trailer_coauthor > manual_declaration > none`),
  then lexicographic source locator, then lexicographic value.
- **Mechanics matter (gate round-2 P1):** the rule is computed as a single
  N-ary reduction over ALL leaf productions of one identity
  (`merge_event_group`), each scalar ranked against the leaf that carries
  it. An incremental pairwise fold is forbidden in accumulation paths — a
  weak-origin value can borrow a stronger sibling's rank through the
  merged pool, making the outcome fold-order dependent (reproduced with
  two reordered Co-authored-by lines). Source union keeps the higher
  evidence level on key collisions for the same reason. The same evidence
  set in any adapter/trailer order yields identical events (exhaustively
  permutation-tested over adversarial 4-leaf sets).
- The total order itself is **provisional** (Gate 2 §8): `imported` marks
  ingestion origin, not intrinsic quality — a versioned git-ai record is
  not necessarily weaker than a hand-typed trailer. Re-evaluating the
  ranking (or surfacing conflicts instead of ordering them) is a blocking
  precondition of the first importer (ROADMAP, v0.2).
- **All** sources are retained in `provenance_sources`, including
  superseded ones — stronger evidence takes precedence; weaker evidence
  stays auditable (proposal §29).
- v0.1 producers: `declared` (both trailer forms) and `unknown` (the
  no-evidence marker). `verified`/`imported`/`inferred` are vocabulary with
  no producer yet; renderers must always show inferred separately from
  verified when they do appear.

## Consequences

- Adding the git-ai importer later (`imported`) or signed hooks
  (`verified`) requires no schema change; the precedence ranking itself
  MUST be re-evaluated before that importer ships (see the provisional
  note above — gate M-06 removed the earlier no-re-ranking wording that
  contradicted it).

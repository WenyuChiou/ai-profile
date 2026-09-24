# ADR-034 — Explicit attribution reliability (v0.10.0)

Status: accepted for v0.10.0. Supersedes the reserved-only manual source in
ADR-008/schema §14; does not supersede explicit-evidence-only attribution.

## Context

Successful daily GitHub Actions runs can produce unchanged AI totals when new
reachable commits have no machine-readable evidence. Squash merging creates a
new final commit and can discard source-commit trailers. A Git hook cannot
retroactively establish historical participation, and commit content style is
not reliable evidence.

## Decision

1. Recognize `Assisted-By` and `Generated-By` only when the value explicitly
   identifies AI/LLM or exactly identifies a registered AI tool. A bare
   organization name, even a registered provider, is insufficient. This is
   a new `git_disclosure` source with closed locator values. Ambiguous prose
   remains unattributed. The declared evidence tier is unchanged. ACE becomes
   0.4.0; older 0.1–0.3 events remain readable.
2. `provenance mark` is opt-in per commit. The private mark binds repository
   root, HEAD, and staged tree. Optional `prepare-commit-msg`/`post-commit`
   hooks add trailers only for that exact state, consume only after verifying
   that the final committed message retains the confirmed trailers, and
   never overwrite an existing hook or custom `core.hooksPath`. A changed
   state fails closed and requires clearing/re-marking. Before editing the
   message, the hook checks that Git's final trailer serialization preserves
   any existing actor groups; an inseparable group aborts the commit for
   manual integration rather than reassigning another actor's evidence.
3. `provenance pr-check` compares explicit source-commit AI identities against
   a proposed squash message. It advises/blocks that proposed message only;
   it does not decide whether a person used AI or perform a merge.
4. `reconcile add` requires confirmation of one reachable SHA authored by a
   configured identity; `remove` may also clear an orphan after history
   rewriting. Its private JSON ledger is reapplied before each
   scan's atomic replacement. An entry applies only to the matching canonical
   origin or local root and SHA. Removal restores normal trailer-derived or
   Unknown classification on rescan. The ledger is never a public asset.
5. Hosted refresh accepts an optional private ledger secret, rejects malformed
   or >48 KB values, and requires all source identities to be on the existing
   public allowlist. Action summaries report snapshot and aggregate deltas
   separately. There is no automatic repository enrollment.

## Consequences

This improves evidence capture, not AI detection. Provider counts may overlap.
Squash checks require a proposed final message; post-merge doctor can only
report reachable history, not reconstruct discarded commits. The private
ledger must be backed up separately and explicitly synced as a secret when
cloud backfill is desired. GitHub scheduling remains the only daily updater.

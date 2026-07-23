# ADR-018: Publishable-only daily activity series (the calendar band)

Status: accepted (owner decision, 2026-07-22) · Round D2

## Context

The summary card publishes an activity-day COUNT (`active_ai_days`).
The Image 2.0 calendar band needs more: WHICH days had AI-attributed
activity, at what intensity, by which provider. Publishing dates is
strictly more information than publishing their count — for
aggregate-only repositories it would leak activity timing that the
existing contract deliberately withholds (PRIVACY.md's
snapshot-differencing honest-limit already warns that repeated exact
counts allow WHEN-inference; a date series would hand that inference
out directly).

## Decision

1. The daily series is built ONLY from repositories whose effective
   publication level is `full` ("explicitly publishable"). Repositories
   at `aggregate_only` (and the reserved anonymous level) contribute
   NOTHING to the series — their contract is completely unchanged. This
   is the fail-closed direction every prior decision in this project
   has taken (C-04, ADR-009, gate-3 fail-closed exclusion).
2. Scope rationale — stated with its assumption: `full` is a POLICY
   label, not a visibility claim (README, `--full` help). For a
   genuinely public repository marked `full`, per-date activity is
   already visible on the hosting platform, and the card adds no new
   channel. For a private or local-only repository that the owner
   marks `full` anyway (by mistake or by choice), the calendar DOES
   add a real disclosure channel — that residual risk is owned by the
   `full` decision itself, which is why the default is aggregate-only,
   the privacy preview shows exactly what will publish, and the
   calendar never reaches beyond repositories the owner explicitly
   elevated.
3. Semantics: per (date, provider) ATTRIBUTED COMMITS — the same
   commit-unit semantic as the provider rows; the standard
   presences-per-commit footnote covers provider overlap. The AI
   population follows schema.md §15 (`actor.type in {ai, mixed}`),
   identical to the provider rows (maintainer ruling during D2 — the
   calendar must never drift from the row counts).
4. Window: at most `DAILY_WINDOW_DAYS` (84 = 12 weeks), anchored at
   the NEWEST publishable date — never the clock. The bound is a
   VizStats validation contract, not a renderer preference: a
   validated instance cannot carry an unbounded activity history.
5. Boundary mechanics: the series enters `VizStats` as exact-typed
   frozen records (`DayCell`/`DayCount`) under the full gate-7..9
   battery — exact container/record/leaf types, canonical-date rules
   shared with `generated_on`, closed provider vocabulary, ascending
   unique dates, and two subset invariants (every daily slug must have
   a provider row; per-slug daily totals cannot exceed that row's
   attributed commits). Policy is applied at the single chokepoint
   (`privacy._build_daily`); the aggregate layer stays policy-free.
6. `profile.json` gains an additive `daily` list (empty when no
   publishable activity). Additive per ADR-012's compatibility rules.

## Consequences

- A user with only aggregate-only repositories sees no calendar band —
  the honest outcome of their own policy choice, not a bug.
- The subset invariants mean the calendar can never claim more
  activity than the provider rows admit.
- Renderer omission on empty series keeps pre-D2 cards byte-identical.
- Future finer policy (per-repo calendar opt-out separate from `full`)
  would extend config vocabulary, not this boundary.

# v0.10.0 Public Beta evaluation contract

Frozen before candidate dogfood on 2026-09-24. Source baseline:
`8c6f2a9ba9625b8602bb3965a4dc45af8065b15c`. This release changes
explicit attribution capture, not AI inference or the eight public outputs.

- Use only the exact Ubuntu candidate wheel authorized by
  `promotion-candidate.json`. Four README-only roles remain required:
  newcomer, privacy-sensitive user, overlapping-provider user, and Profile
  publisher. Each gets the two READMEs, exact wheel, and role objective—not
  source or private maintainer hints—and an isolated repository and home.
- Pass requires 4/4 roles, correct hand-derived counts, zero private-canary
  hits in all eight outputs, a deterministic repeated refresh, and no
  installation, configuration, privacy, or hosted-publication dead end.
- Add v0.10-specific probes: clear AI/LLM disclosure versus ambiguous company
  names; an explicit, single-commit mark with an unchanged and a changed
  staged tree; preservation of another actor and Human-Only trailer; squash
  message loss detection; a confirmed private ledger surviving rescans and
  never appearing in public output. Unconfirmed history remains Unknown.
- Full pytest, Ruff, bilingual README parity, sanctioned zero-drift snapshot
  regeneration, installed-wheel smoke, independent staged-diff review, and
  all eight GitHub jobs must pass before merge. The C1 reusable-workflow pin
  must survive as an ancestor of the merge commit.
- After publication, compare precise before/after public counts, run the
  Profile caller twice (changed asset commit and no-change), verify Pages and
  HTTP 200, and inspect the next scheduled GitHub run. Do not create a local
  daily schedule or backfill any old commit without individual confirmation.

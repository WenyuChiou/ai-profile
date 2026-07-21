# AGENTS.md — agent orientation for ai-profile

`aiprofile` is a local-first CLI that scans local Git repos for explicit
AI provenance (AI-* trailers, known co-author trailers) and renders
privacy-safe SVG/JSON profile summaries. It is NOT an AI code detector.
Read `README.md` and `CONTRIBUTING.md` first; where docs and code
disagree, docs win and the code is the bug.

## Quality gates (must stay green after every change)

- `python -m pytest tests -p no:cacheprovider` — full suite; state the
  count you observe (as of 2026-07-21: 340 passed, 1 skipped — the skip
  is a POSIX-only fixture on Windows; if your run differs, update this
  line in the same commit).
- `python -m ruff check src tests` — clean.
- Privacy invariants are test-enforced; anything weakening `VizStats`
  structural redaction needs its own ADR. Snapshot/sample regeneration
  only via the single sanctioned command
  `python tests/unit/test_render_summary.py` (byte-drift guarded).
- Contract changes need an ADR under `docs/decisions/` + schema bump.

## Collaboration contract (Fable ↔ Codex gate loop)

This repo is built through numbered independent "gate" review rounds:

- **Fable (Claude Code)** implements, resolves review findings
  red-first (regression proven failing pre-fix), records dispositions in
  `docs/reviews/gate-disposition.md` + `docs/progress.md`, and is the
  ONLY party that commits (`Resolve gate-N review: ...`).
- **Codex** acts as independent Principal-Software-Engineer reviewer:
  verification only, adversarial reproduction with runnable probes,
  never commits, never changes production/test/design code. The review
  overwrites `docs/reviews/gate-review.md` (repo convention; usually
  committed alongside the commit that resolves it — but a round may
  leave it deliberately uncommitted, as gate-9's did; check `git status`
  and the round's own commit message/brief before assuming which).

## Handoff protocol (replaces clipboard copy-paste between apps)

Round files live in `.ai/handoff/` (git-ignored via `.git/info/exclude`;
Codex's file tools read them regardless):

- `NNN_<slug>.to_codex.md` — a task/review brief authored by Fable.
- `NNN_<slug>.to_fable.md` — Codex's durable reply (same NNN; this file
  is never overwritten by later rounds, unlike gate-review.md).
- Exception: `000_gate8_review_snapshot.to_fable.md` is a one-off
  bootstrap snapshot authored by Fable (preserving the never-committed
  gate-8 review text), not a Codex reply.

To run a round from the Codex app, open it with cwd = this repo's root
and say exactly:

> Read .ai/handoff/NNN_<slug>.to_codex.md and execute all instructions;
> write your reply to .ai/handoff/NNN_<slug>.to_fable.md.

The brief itself carries all round-specific instructions (review range,
expected test counts, output contract) — the sentence never changes.

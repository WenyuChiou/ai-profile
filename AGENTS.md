# AGENTS.md — agent orientation for ai-profile

`aiprofile` is a local-first CLI that scans local Git repos for explicit
AI provenance (AI-* trailers, known co-author trailers) and renders
privacy-safe SVG/HTML/JSON profile summaries. It is NOT an AI code detector.
Read `README.md` and `CONTRIBUTING.md` first; where docs and code
disagree, docs win and the code is the bug.

## Quality gates (must stay green after every change)

- `python -m pytest tests -p no:cacheprovider` — full suite; state the
  count you observe (as of 2026-07-26: 549 passed, 4 skipped — three
  skips are POSIX-only permission fixtures on Windows and one requires
  a case-sensitive filesystem; if your run differs, update this
  line in the same commit).
- `python -m ruff check src tests scripts` — clean.
- Privacy invariants are test-enforced; anything weakening `VizStats`
  structural redaction needs its own ADR. Snapshot/sample regeneration
  only via the sanctioned per-family commands (byte-drift guarded):
  `python tests/unit/test_render_summary.py` (summary family) and
  `python tests/unit/test_heatmap_svg.py` (heatmap/badge family, D4).
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
- NNN is single-use: a second round over the same range or brief (a
  second opinion, a re-run) ALWAYS gets its own fresh NNN brief — never
  point a new round at an existing NNN, because its reply instruction
  would overwrite that round's supposedly-durable `.to_fable.md`
  (this happened live on 2026-07-21: an app round reusing brief 001
  silently clobbered the headless round's 001 reply; recovered from a
  session transcript, which will not always exist).
- While an external review of a committed range is in flight, do not
  draft next-round files in the same working tree: the reviewer's
  `git status` picks up the strays (observed live during gate-11 — a
  concurrently-drafted test file appeared mid-review; the reviewer
  disclosed rather than touched it, but the ambiguity is avoidable).
  Range-pinned checks are immune, tree-state checks are not.

To run a round from the Codex app, open it with cwd = this repo's root
and say exactly:

> Read .ai/handoff/NNN_<slug>.to_codex.md and execute all instructions;
> write your reply to .ai/handoff/NNN_<slug>.to_fable.md.

The brief itself carries all round-specific instructions (review range,
expected test counts, output contract) — the sentence never changes.

Preferred transport (proven on the gate-10 round, 2026-07-22): Fable
runs the same brief headlessly — no human in the transport at all —
via the codex-delegate wrapper (personal-environment tooling from the
maintainer's global skills install, optional; the Codex-app sentence
above is the portable path for anyone else):

```bash
bash ~/.claude/skills/codex-delegate/scripts/run_codex.sh \
  --brief-file .ai/handoff/NNN_<slug>.to_codex.md --repo <repo-root>
```

Machine-readable status lands at `<brief>.txt.result.json`
(`success` / `fallback` = Codex quota exhausted / `error`). On
`fallback`, wait for the quota reset or fall back to the Codex-app
sentence above — never substitute a same-vendor review for the
independent external round.

## Commit trailers (dogfood — this repo's own product)

Every commit here declares its AI participation with the tool's own
schema (README "Declaring AI participation"), so `aiprofile scan` on
this repo reports the true multi-tool history. One block per AI actor;
a repeated `AI-Provider:` key starts the next block (ADR-005). Example
for the standard round shape (Fable implements, Codex reviews):

```text
AI-Provider: Anthropic
AI-Model: Claude-Fable-5
AI-Tool: Claude-Code
AI-Role: implementation, documentation
AI-Mode: AI-Assisted
AI-Provider: OpenAI
AI-Model: GPT-5.5
AI-Tool: Codex-CLI
AI-Role: review
AI-Mode: AI-Assisted
```

ONE CONTIGUOUS BLOCK — never put a blank line between groups: git's
trailer extraction (`%(trailers:only)`) keeps only the last contiguous
paragraph, so a blank line silently drops every group above it
(verified empirically 2026-07-21: the blank-line form lost the entire
Anthropic group). The repeated `AI-Provider:` key alone is the group
separator.

AND a blank line BEFORE the block — the trailer paragraph must be
separated from the body prose, or git rejects the whole paragraph as
non-trailers (too many non-trailer lines in it). Found by dogfooding
2026-07-23: commits ea5f37d / d2c1147 / 66bc3e9 glued their trailer
block to the preceding body line and scan as `unknown` forever (pushed
history is never rewritten here — this note is the erratum). The two
rules together: blank line before the block, no blank line inside it.

Honesty rules: only list actors that actually touched the commit;
`AI-Reviewed-By: Human` only when a human actually read the diff
(omit or `None` otherwise); keep the `Co-Authored-By:` line too
(GitHub UI + the tool's registry fallback both read it).

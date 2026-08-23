# AGENTS.md — agent orientation for ai-profile

`aiprofile` is a local-first CLI that scans local Git repos for explicit
AI provenance (AI-* trailers, known co-author trailers) and renders
privacy-safe SVG/HTML/JSON profile summaries. It is NOT an AI code detector.
Read `README.md` and `CONTRIBUTING.md` first; where docs and code
disagree, docs win and the code is the bug.

## Quality gates (must stay green after every change)

- `python -m pytest tests -p no:cacheprovider` — full suite; state the
  platform and count you observe. Windows local (v0.7.2 candidate,
  2026-08-23): 960 passed, 30 skipped; WSL Ubuntu Python 3.12 local: 984
  passed, 6 skipped. Linux CI (v0.7.1 candidate, run
  31405185444): Python 3.11–3.14 each passed 978 tests with 6 skipped; the
  release-candidate build and three platform wheel-onboarding jobs also passed
  (**8/8** total). Update only the corresponding platform baseline, never
  overwrite one platform's count with another's expected skip profile.
- `python -m ruff check src tests scripts` — clean.
- Privacy invariants are test-enforced; anything weakening `VizStats`
  structural redaction needs its own ADR. Snapshot/sample regeneration
  only via the sanctioned per-family commands (byte-drift guarded):
  `python tests/unit/test_render_summary.py` (summary family) and
  `python tests/unit/test_heatmap_svg.py` (heatmap/badge family, D4).
- Contract changes need an ADR under `docs/decisions/` + schema bump.

## Dogfood and disposable-output cleanup

Dogfood, release-probe, and review-probe directories are disposable artifacts,
not project data. Every dogfood/release task MUST finish with a cleanup sweep of
the disposable roots declared by that task. On Windows, declare the exact
values of `$env:TEMP`, `$env:TMP` when distinct, and every task-created scratch
root; on POSIX, declare `/tmp` or its equivalent plus every scratch root.

- Determine the current release from **both** `pyproject.toml` (`[project].version`)
  and `src/aiprofile/__init__.py` (`__version__`). Normalize only an optional
  leading `v`; abort the sweep if either value is missing, unparsable, or does
  not match the other. Never infer the current version from a directory name.
- Discovery is candidate generation, not deletion authorization. Match semantic
  families, not just the literal word `dogfood`: include `ai-profile-*` /
  `aiprofile-*` versioned forms. Normalize only these version-token forms:
  `vMAJOR.MINOR.PATCH` or `MAJOR.MINOR.PATCH`, and compact three-digit
  `vXYZ` or `XYZ` where `XYZ` means `X.Y.Z` (`v046` = `0.4.6`, `046` =
  `0.4.6`). Reject ambiguous or missing tokens as UNKNOWN. Labels may include
  `dogfood`, `build`, `live`, `final`, `candidate`, `review`, `staging`,
  `publisher`, `profile`, `home`, `repo`, `venv`, `pypi`, or `CI artifact`.
  The 046–050 incident examples include `aiprofile-v046-*`,
  `aiprofile-046-*`, `aiprofile-staging-v049-*`,
  `aiprofile-profile-v050-*`, `aiprofile-dogfood-046-*`, and
  `aiprofile_dogfood_dist*`. A date is supporting evidence only; it is never
  the sole deletion selector.
- A path may be classified DELETE only when it is either (a) an explicitly
  enumerated absolute path in the task handoff, or (b) a direct child of a
  declared disposable root containing the task marker
  `.aiprofile-dogfood.json` with version, owner, creation time, and expiry.
  Unmarked matches are UNKNOWN and MUST NOT be deleted by a broad glob.
- Keep exceptions require an owner, reason, and expiry. Current-release
  evidence may be kept only while its release checklist is open; after expiry
  it becomes stale. Resolve `AIPROFILE_HOME`, source repositories, and worktree
  paths to canonical absolute paths (case-insensitive on Windows) before
  comparing them. If `AIPROFILE_HOME` cannot be resolved or
  `git worktree list --porcelain` cannot be read, stop. Never delete a current
  `AIPROFILE_HOME`, source repository, active worktree, published/current-
  release artifact, or a path listed by `git worktree list --porcelain`.
- Before deletion, resolve each absolute path and verify that it is a direct
  child of its declared root, is not the root itself or a reparse point/symlink,
  and is not a Git worktree (`git -C <path> rev-parse --is-inside-work-tree`
  must not succeed). Do not use recursive globs from the user profile or repo
  root.
- Delete one verified absolute path at a time with a literal-path operation;
  verify that path is gone before moving to the next item. If a path is locked,
  unexpected, unmarked, or changes between enumeration and deletion, stop and
  report it rather than widening the selector.
- After the sweep, rescan the exact declared roots with the same classifier.
  Report `DELETE candidates remaining = 0`, the KEEP paths with their expiry,
  all UNKNOWN paths, and every failure. Also verify `git status --short` and
  `git worktree list --porcelain` so cleanup did not touch the repository or an
  active worktree.

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

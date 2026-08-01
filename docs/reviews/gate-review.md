# Gate review — v0.4.8 recruiter-first collaboration record

Date: 2026-08-01

Review range: `374118a88840388a0a374d5cab695b6f18a49c2c..04c27504ed02c83ccdd0ef657558d65f6798eb80`

Reviewer posture: independent Principal Software Engineer; implementation
verification only. Production, schema, aggregation, and design code were not
changed by the reviewer. This report overwrites the prior gate-review artifact
per repository convention.

## Executive summary

The v0.4.8 implementation follows the approved architecture and MVP boundary.
It replaces the existing summary-card presentation without changing the ACE
schema, CLI, configuration format, `VizStats` privacy boundary, aggregation
units, or eight-output contract. The collaboration terrain uses unique daily
commit totals for height and AI share for hue; provider participation never
increases terrain height. Unknown remains distinct from human.

The initial candidate CI run correctly failed closed because the pinned wheel
digest came from a non-authoritative Docker builder. The remediation did not
weaken checksum enforcement: it re-froze the digest produced by the GitHub
`ubuntu-latest` Python 3.12.13 candidate builder and documented that every
cross-platform onboarding job consumes those retained bytes. The second run
passed the candidate build, Python 3.11–3.14 suites, and Ubuntu, Windows, and
macOS wheel onboarding.

Independent browser probes cleared the normal and 200%-zoom width matrix,
provider filtering, theme-state accessibility, keyboard navigation, tooltip
dismissal, and visible focus. Four README-only clean-room roles completed
against the exact CI-retained wheel. Hand-derived aggregation values matched,
and the privacy role found zero matches across 69 private canaries and all
eight public artifacts. No Critical, High, or Medium finding remains.

## Review basis

The review covered the complete pinned range, repository guidance, README and
Traditional Chinese mirror, architecture and MVP documents, privacy contract,
ROADMAP and progress records, ADR-020 and ADR-022, release workflow and
candidate manifest, changed renderers and `VizStats` boundary, all changed
tests, committed snapshots/sample assets, and the CI-retained wheel/sdist.

The range contains three commits:

1. `0b012ba` — freezes the v0.4.8 evaluation gates before implementation.
2. `e1ba6cb` — implements the recruiter-first card, dashboard/brand alignment,
   documentation, tests, and fail-closed snapshot provenance guard.
3. `04c2750` — re-pins the candidate to the authoritative GitHub-built wheel
   after the checksum gate rejected environment-specific local bytes.

## Findings

### Low — README does not explicitly place Human-Only records in the declared-evidence bucket

**Location:** `README.md:275`, `README.md:310`; mirrored concepts in
`README.zh-TW.md:267`, `README.zh-TW.md:300`.

**Description:** The README correctly explains `AI-Mode: Human-Only`, the
unknown/human separation, and the evidence-quality order. It does not say in
one sentence that an explicit Human-Only record contributes to the aggregate
`declared` evidence count. The multi-provider clean-room role initially
derived two declared AI actor records instead of the observed three declared
records (two AI actors plus one Human-Only declaration).

**Impact:** A user manually checking evidence totals may need one extra
interpretive step. Commit, provider, human, unknown, and actor-presence counts
remain correct; the CLI labels the denominator as “all records,” and no privacy
or attribution ambiguity results.

**Recommendation:** Clarify the evidence bucket in the next documentation
release. This is accepted as Low for v0.4.8 because the role completed without
an outside product hint and all public counts were unambiguous.

## Verification evidence

Commands and observed results:

- `python -m pytest tests -p no:cacheprovider`:
  `628 passed, 4 skipped in 32.01s` on Windows. The four skips match the
  documented platform/filesystem fixtures.
- `python -m ruff check src tests scripts`: `All checks passed!`.
- `python scripts/check_readme_parity.py`:
  `PASS: README English/Traditional Chinese structure and contract parity`.
- `git diff --check`: clean.
- `python tests/unit/test_render_summary.py` and
  `python tests/unit/test_heatmap_svg.py`, each run twice with `PYTHONPATH`
  unset: every run imported this worktree's `src/aiprofile/__init__.py`; first-
  and second-run drift were both zero.
- Mismatched-import behavioral regression: all four governed writer entry
  points refused before writing and retained-file digests remained unchanged.
- `python scripts/check_release_artifacts.py --artifact-only ...`:
  `PASS: artifact contract for ai-profile-cli 0.4.8`; wheel contains `LICENSE`
  and `THIRD_PARTY_NOTICES.md`.

Authoritative CI evidence for PR #16, run `30714875482`:

- Release candidate build: pass.
- Python 3.11, 3.12, 3.13, and 3.14: pass. Linux observed
  `631 passed, 1 skipped`, the expected inverse of three Windows-only skips.
- Wheel onboarding on Ubuntu, Windows, and macOS, Python 3.12: pass against
  the same retained candidate bundle.
- Wheel SHA-256:
  `d8d307d4155f58f157ee817cdd628ef4c257287083aad66cf30e02f679fe47b6`.
- sdist SHA-256:
  `6ee4971ed20300f96196326a1abf048b9bdd44d530092fd70207cae08cb0acd2`.

Independent browser evidence:

- Normal widths 320, 390, 768, 1280, and 1440px: no document/body horizontal
  overflow.
- 200% effective widths 145, 180, 369, 625, and 705px: no document/body
  horizontal overflow.
- Theme state cycled `auto → light → dark → auto`; visible text and accessible
  name remained synchronized with the next action.
- All AI, Claude, and OpenAI filters each exposed the correct pressed state and
  live-region status.
- Calendar ArrowLeft moved focus by one week, Escape dismissed the tooltip,
  and the active cell exposed a 3px solid focus outline.
- Light/dark summary assets show `AI Collaboration Record`, terrain before the
  provider ledger, no rail/text collision, and no clipping.

Independent privacy and dogfood evidence:

- Four of four README-only roles completed against the exact retained wheel.
- Newcomer: 2 commits → 1 unique AI commit, 1 actor presence, 1 unknown.
- Multi-provider: 3 commits → 1 unique AI commit, 2 actor presences,
  1 human, and 1 unknown; Claude and OpenAI each report 1/1/1.
- Privacy policy: 2 full plus 3 aggregate-only commits yielded 5 public total;
  four excluded commits had no effect. Only the two full-policy dates appeared.
- Agent sweep: 69 private markers across eight public artifacts, zero hits.
- Reviewer recomputation: 47 independently reconstructed markers × 8 artifacts
  = 376 comparisons, zero hits; aggregate-only dates had zero hits and the two
  full dates served as positive controls.
- Publisher retry: clean non-worktree root, exact eight files, local `main`
  publish commit containing only `README.md` and `dist/`, coherent Pages URL,
  and no configured remote.

## Verified areas without findings

- Renderer dependency direction remains `VizStats → renderer`; renderers do
  not scan Git, access SQLite/storage, call the network, infer attribution, or
  recompute aggregates.
- One commit with multiple AI actors remains one unique AI-attributed commit
  and multiple actor presences. Provider totals are explicitly non-exclusive.
- Terrain height is derived from `DayCell.total_commits`, not provider sums;
  its hue uses `ai_commits / total_commits` fixed bins.
- Aggregate-only repositories contribute permitted totals but not daily dates;
  excluded repositories contribute neither totals nor dates.
- Unknown is never converted to human; zero-attributed-AI days use neutral
  wording and still show whole-rhythm commit volume.
- SVG output is deterministic and static; no external font, script, tracker,
  animation, gradient, or runtime dependency was added.
- README EN/zh-TW structure, claims, links, and privacy promises remain paired.
- No duplicated Git AI, GitHub API, generic GitHub statistics, or contribution
  graph subsystem was introduced.

## Severity summary

- Critical: 0
- High: 0
- Medium: 0
- Low: 1

## Final recommendation

READY FOR NEXT GATE

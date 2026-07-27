# v0.4.5 Public Beta promotion readiness review

Date: 2026-07-26
Release source: `b1e8d75f667e0808d81ac4651207933d25fbace8`
Dogfood baseline: `05c55e7ee4f743e5e4844eb67c2e8182f1a25e0e`
Profile source: `41a1ed92f2be54dc1a9beb09b4c1fdf16a902a95`

Published artifacts:

- wheel: `ai_profile_cli-0.4.5-py3-none-any.whl`
- wheel SHA-256:
  `c03cbf694737bcf53ee44e88b0ddd4feb6ef4d68226a3ff372b03bb5051cff8b`
- sdist: `ai_profile_cli-0.4.5.tar.gz`
- sdist SHA-256:
  `ed23dcedaca9f473dca3456c920ab0067bed5fe0e0a3e401a6d4b2ab60c184d5`

## Reviewer posture

This is a post-publication promotion verification, not a redesign. It reviews
the v0.4.5 visual release, package, README onboarding, privacy boundary,
published artifacts, and live maintainer Profile. ACE schema, aggregation
semantics, provider vocabulary, privacy levels, and CLI behavior remain
unchanged.

## Executive summary

v0.4.5 satisfies the Public Beta promotion gate:

- PyPI and GitHub Release serve the exact retained wheel and sdist;
- the live wheel clean-installs and passes the release smoke;
- the publish workflow built once, tested the same wheel on Ubuntu, Windows,
  and macOS, verified PyPI digests, and byte-checked release assets;
- four README-only roles completed against the same native-Linux wheel with
  zero external product hints;
- privacy, commit/presence separation, unknown/human separation, provider
  filters, and the eight-output contract passed independently;
- the soft editorial visual system uses pale blue and pale yellow data
  surfaces, distinctive local typography, clearer hierarchy, and
  keyboard-safe provider exploration without generic AI styling;
- the maintainer Profile was regenerated from live PyPI, passed 53,288
  private-canary comparisons, merged through Profile PR #9, and deployed;
- all eight live Pages assets return HTTP 200 and are byte-identical to the
  canonical Profile Git blobs;
- there are no unresolved Critical, High, or Medium findings.

The approved positioning remains **Public Beta** under `0.x`; this report does
not claim Stable or GA status.

## Verification evidence

### Product quality gates

```text
python -m pytest tests -p no:cacheprovider
551 passed, 4 skipped

python -m ruff check src tests scripts
All checks passed!

python scripts/check_readme_parity.py
PASS: README English/Traditional Chinese structure and contract parity

python tests/unit/test_render_summary.py
python tests/unit/test_heatmap_svg.py
git diff --exit-code -- tests/snapshots docs/assets
PASS: sanctioned regeneration completed with zero drift
```

The four skips are declared platform or fixture cases. No promotion
requirement was silently omitted.

### Published artifact identity

GitHub Actions publish run
[`30233592360`](https://github.com/WenyuChiou/ai-profile/actions/runs/30233592360)
completed successfully:

```text
Build verified release bundle: PASS
Ubuntu Python 3.12 onboarding: PASS
Windows Python 3.12 onboarding: PASS
macOS Python 3.12 onboarding: PASS
PyPI trusted publishing and digest readback: PASS
GitHub Release asset verification: PASS
```

Independent public-source verification downloaded both PyPI packages and the
GitHub Release `SHA256SUMS`:

```text
wheel SHA-256 = c03cbf69...f8b
sdist SHA-256 = ed23dced...d5
artifact contract = PASS
LICENSE and THIRD_PARTY_NOTICES.md = present
clean PyPI install version = aiprofile 0.4.5
release smoke = PASS
```

The GitHub Release contains exactly the wheel, sdist, and `SHA256SUMS`.

### README-only dogfood and aggregation semantics

Final raw evidence is retained under `.artifact/v045-dogfood-final/` and
summarized in `docs/reviews/promotion-dogfood.md`.

```text
roles: 4/4 PASS
candidate digest matches: 4/4
README-external hints: 0
installation/configuration dead ends: 0
outputs: 8/8 for every role
privacy: 34 canaries * 8 outputs * 3 encodings = 816 checks, hits 0
dashboard filter mismatches: 0
```

The multi-provider oracle and observed output matched:

```text
commits scanned = 3
unique AI-attributed commits = 1
AI actor presences = 2
human-declared commits = 1
unknown commits = 1
evidence records = 4 (declared 3, unknown 1)
```

One commit with OpenAI and Anthropic participation remains one unique commit
and two actor presences. Unknown remains separate from human.

### Visual, responsive, and accessibility verification

The v0.4.5 design direction is soft editorial rather than synthetic or
template-like:

- pale blue identifies AI participation and pale yellow identifies evidence
  without turning large surfaces into saturated color blocks;
- Bahnschrift, DIN Alternate, Franklin Gothic, Candara, Corbel, and compatible
  local fallbacks provide a distinctive, download-free type system;
- tabular numerals, restrained rules, aligned bars, and more generous spacing
  preserve analytical precision;
- normal labels retain text color; accent is reserved for marks, borders,
  bars, and large hero values;
- All AI, Claude, and OpenAI controls support visual, pointer, and keyboard
  exploration while keeping every aggregation unit explicit.

The full browser matrix passed:

```text
widths: 320 / 390 / 768 / 1440
themes: light / dark / system
viewport/theme states: 12
provider states: 36
maximum document overflow: 0
minimum meaningful-mark contrast: 5.543:1
minimum normal metadata contrast: 5.620:1
200% rendering: document overflow 0; calendar scrolls locally
keyboard / focus / hover / touch / reduced motion: PASS
console errors / external requests: 0 / 0
```

The 390-pixel calendar starts at the newest activity. Its sole roving tab stop
is the newest date, and focus position survives provider and theme rerenders.

### Real GitHub Profile and privacy

The Profile was generated in a clean environment installed from live PyPI
v0.4.5, then merged through
[Profile PR #9](https://github.com/WenyuChiou/WenyuChiou/pull/9).

```text
repositories scanned: 11
commits scanned: 1701
unique AI-attributed commits: 1136
AI actor presences: 1155
human-declared commits: 0
unknown commits: 565
active AI days: 89
providers: 2
evidence records: 1720

1701 = 1136 AI + 0 human + 565 unknown
1155 = 1098 Claude + 57 OpenAI presences
1720 = 1155 declared presences + 565 unknown records
```

The retained sweep derived 6,661 unique canaries from private identities,
paths, repository names, UIDs, remotes, owner names, emails, full and short
SHAs, subjects, messages, and salt:

```text
6661 unique canaries * 8 public outputs = 53,288 comparisons
privacy hits = 0
deterministic second-render differences = 0/8
```

Pages serves all eight outputs for Profile source
`41a1ed92f2be54dc1a9beb09b4c1fdf16a902a95`; every live asset returned HTTP
200 and matched its canonical Git blob.

### README and OSS readiness

The English README remains canonical and Traditional Chinese preserves the
same headings, CTAs, commands, output contract, privacy claims, and limits.
The first screen leads with the evidence-backed value proposition, live demo,
quickstart, trust signals, and real Profile example. It explains that large
unknown totals are honest rather than a failed scan.

The package contains both notices; the repository exposes contribution,
security, release, issue, and pull-request guidance; protected checks cover
Python 3.11–3.14 and three operating-system onboarding paths. The current
README, package, release, support, Profile, and dashboard links return HTTP
200.

## Independent review synthesis

| Lens | Verdict | Critical | High | Medium | Low |
|---|---|---:|---:|---:|---:|
| Architecture and maintainability | APPROVE | 0 | 0 | 0 | 0 |
| Security and privacy | APPROVE | 0 | 0 | 0 | 0 |
| Packaging and release | APPROVE | 0 | 0 | 0 | 0 |
| README-only onboarding | APPROVE | 0 | 0 | 0 | 0 |
| Visual and accessibility | APPROVE | 0 | 0 | 0 | 0 |
| Completion integrity | APPROVE | 0 | 0 | 0 | 0 |

## Findings and dispositions

### High — Keyboard entry initially selected the oldest calendar date

- **Impact:** Narrow-screen keyboard users could land on historical activity
  and lose the dashboard's intended newest-first exploration context.
- **Evidence:** An independent adversarial browser review reproduced the
  initial focus error before release authorization.
- **Recommendation:** Make the newest date the initial roving tab stop and
  preserve the bounded focus index across provider and theme rerenders.
- **Disposition:** Fixed before publication. Executed Chromium regression
  checks pass at 390 pixels, including rerenders and the newest scroll edge.

### Low — A Windows dogfood harness used PowerShell's protected HOME name

- **Impact:** One isolated setup attempt briefly created two new files in the
  user-home root before any scan or render.
- **Evidence:** The role's raw command ledger recorded the resolved path and
  the two file creations.
- **Recommendation:** Assert every mutable harness path before execution and
  keep native stderr separate from exit status.
- **Disposition:** Resolved. Both files were removed and independently
  confirmed absent; no existing or tracked file was affected. The final role
  restarted with a literal scoped `AIPROFILE_HOME` and passed.

### Low — Isolated dogfood homes trigger a conservative warning

- **Impact:** Evaluators see a warning because private test homes sit beneath
  an ignored outer worktree.
- **Recommendation:** Keep the warning; real users should store private state
  outside repositories intended for publication.
- **Disposition:** Accepted as accurate, useful, and non-blocking.

### Low — GitHub Actions reports Node 20 action deprecation annotations

- **Impact:** Pinned actions currently succeed under GitHub's Node 24 override
  but should be refreshed before enforcement changes.
- **Recommendation:** Upgrade pinned action revisions in a maintenance PR and
  rerun release-recovery tests.
- **Disposition:** Accepted as non-blocking maintenance debt; every required
  workflow and publication step passed.

## Verified areas without findings

- Renderers consume sealed validated `VizStats`; they do not scan Git, access
  SQLite, infer attribution, or recalculate statistics.
- Unique commits, actor presences, provider commits, active days, and evidence
  records remain distinct.
- Unknown remains separate from human; no source-style inference exists.
- Public outputs contain no repository, organization, path, prompt, message,
  email, URL, salt, UID, or SHA canary.
- Static SVG Profile assets and the self-contained filterable dashboard fit
  GitHub README and Pages constraints.
- v0.4.5 adds no schema change, remote font, dependency, configuration CLI, or
  feature outside the frozen Public Beta boundary.

## Severity summary

| Severity | Fixed or resolved | Accepted | Pending |
|---|---:|---:|---:|
| Critical | 0 | 0 | 0 |
| High | 1 | 0 | 0 |
| Medium | 0 | 0 | 0 |
| Low | 1 | 2 | 0 |

There are no unresolved Critical, High, or Medium findings. The accepted Low
items are documented operational or maintenance notes and are not promotion
blockers.

## Final verdict

GO — PUBLIC BETA

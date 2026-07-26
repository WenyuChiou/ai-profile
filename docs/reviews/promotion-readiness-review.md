# v0.4.4 Public Beta promotion readiness review

Date: 2026-07-26
Release source:
`03cfdf03b4f470761a6a0c6962b35d56452bac08`
Dogfood baseline:
`363fc615e3c4133551f99a881046b26d45b027ac`
Profile source:
`c0a599dc8e1f501fe9724cd3416fa3d623dbe9cb`

Published artifacts:

- wheel: `ai_profile_cli-0.4.4-py3-none-any.whl`
- wheel SHA-256:
  `668cf226cd9f292681427ccc2dbc3305d6e886e9a4aa03650f2c160f7074ca3d`
- sdist: `ai_profile_cli-0.4.4.tar.gz`
- sdist SHA-256:
  `94f2decb07efe2d2c6179bf673b09216c0d9746326d33622e6fceb10ead823b0`

## Reviewer posture

This is a post-publication promotion verification, not a redesign. It reviews
the v0.4.4 renderer, package, README onboarding, privacy boundary, published
artifacts, and live maintainer Profile. ACE schema, aggregation semantics,
provider vocabulary, privacy levels, and CLI behavior remain unchanged.

## Executive summary

v0.4.4 satisfies the Public Beta promotion gate:

- PyPI and GitHub Release serve the exact retained wheel and sdist;
- the live PyPI wheel clean-installs and passes the complete release smoke;
- the tag workflow built once, smoked the same wheel on Ubuntu, Windows, and
  macOS, verified PyPI digests, and byte-checked GitHub Release assets;
- four README-only roles completed against the native-Linux wheel with zero
  external product hints;
- privacy, commit/presence separation, unknown/human separation, dashboard
  filters, and the eight-output contract passed independently;
- the visual system now uses a technical-editorial evidence-ledger direction
  rather than generic AI gradients, oversized pills, or remote web fonts;
- the maintainer Profile was regenerated from live PyPI, passed 52,808 private
  canary comparisons, merged through PR #8, and deployed through Pages;
- all eight live Pages assets are byte-identical to Profile `main`;
- 30 canonical README, package, release, support, and demo URLs return 200;
- there are no unresolved Critical or High findings.

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

The four skips are declared platform/fixture cases. No promotion requirement
was silently omitted.

### Published artifact identity

GitHub Actions publish run
[`30210402462`](https://github.com/WenyuChiou/ai-profile/actions/runs/30210402462)
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
wheel SHA-256 = 668cf226...ca3d
sdist SHA-256 = 94f2decb...23b0
artifact contract = PASS
LICENSE and THIRD_PARTY_NOTICES.md = present
clean PyPI install version = aiprofile 0.4.4
release smoke = PASS
```

The GitHub Release contains exactly the wheel, sdist, and `SHA256SUMS`.

### README-only dogfood and aggregation semantics

Final raw evidence is retained under `.artifact/v044-dogfood-r2/` and
summarized in `docs/reviews/promotion-dogfood.md`.

```text
roles: 4/4 PASS
candidate digest matches: 4/4
README-external hints: 0
installation/configuration dead ends: 0
outputs: 8/8 for every role
privacy: 38 patterns * 9 public outputs = 342 pattern/file checks, hits 0
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

The v0.4.4 direction is a technical editorial record:

- condensed local display faces such as Bahnschrift, DIN Alternate, and
  Franklin Gothic provide character without downloading fonts;
- Trebuchet, Corbel, Avenir, Ubuntu, and DejaVu form a readable cross-platform
  body stack;
- tabular numerals, structural rules, a restrained GitHub Primer palette, and
  an evidence grid create hierarchy without decorative AI styling;
- accent color remains concentrated in hero values, marks, borders, and data
  bars instead of normal labels.

The full browser matrix passed:

```text
widths: 320 / 390 / 768 / 1440
themes: light / dark / system
viewport/theme states: 12
provider states: 36
maximum document overflow: 0
minimum meaningful-mark contrast: 5.011:1
minimum normal metadata contrast: 4.704:1
accessible date cells per state: 295
200% rendering: document overflow 0; calendar scrolls locally
keyboard / focus / hover / touch / reduced motion: PASS
console errors / external requests: 0 / 0
```

The complete matrix ran against the final maintainer dashboard generated by
the live PyPI v0.4.4 wheel. The exercised Windows checkout file normalizes to
the canonical Profile Git blob, which was byte-identical to the deployed
Pages asset. Evidence is retained at
`.artifact/v044-profile/browser-final/browser-gate.json`, with screenshots at
the narrow, wide, and 200% rendering gates.

### Real GitHub Profile and privacy

The Profile was generated in a clean environment installed from live PyPI
v0.4.4, then merged through
[Profile PR #8](https://github.com/WenyuChiou/WenyuChiou/pull/8).

```text
repositories scanned: 11
commits scanned: 1686
unique AI-attributed commits: 1130
AI actor presences: 1149
human-declared commits: 0
unknown commits: 556
active AI days: 89
providers: 2
evidence records: 1705

1686 = 1130 AI + 0 human + 556 unknown
1149 = 1098 Anthropic + 51 OpenAI presences
1705 = 1149 declared presences + 556 unknown records
```

The retained sweep derived 6,601 unique canaries from the private salt,
identities, paths, repository names and UIDs, remotes and owner names, author
emails, every database full/short SHA, and every exact commit subject/message:

```text
6601 unique canaries * 8 public outputs = 52,808 comparisons
privacy hits = 0
deterministic second-render differences = 0/8
```

Pages run
[`30210910412`](https://github.com/WenyuChiou/WenyuChiou/actions/runs/30210910412)
completed successfully. All eight live assets returned HTTP 200 and were
byte-identical to Profile `main`.

### README, OSS readiness, and public links

The English README remains canonical and Traditional Chinese preserves the
same headings, CTAs, commands, output contract, privacy claims, and limits.
The first screen leads with the evidence-backed value proposition, live demo,
quickstart, trust signals, and real Profile example. It states that large
unknown totals are honest rather than a failed scan.

The package contains notices; the repository exposes contribution, security,
release, issue, and pull-request guidance; `main` requires the release and
onboarding checks. Thirty non-placeholder README and release URLs returned
HTTP 200. Evidence is retained in
`docs/reviews/promotion-public-link-evidence.json`.

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

### High — Initial candidate did not represent native-Linux release bytes

- **Impact:** Dogfood against a different wheel cannot authorize the package
  that CI publishes.
- **Evidence:** WSL over the Windows checkout built `ff7ad454...7a99`; the
  first PR release job's native Linux checkout built `668cf226...ca3d`.
- **Recommendation:** Export Git blobs to a native Linux filesystem, freeze
  the resulting digest, and invalidate every prior role result.
- **Disposition:** Fixed. Native Linux reproduced CI's digest, all four roles
  reran against it, PR CI passed, and public PyPI/GitHub bytes match it.

### Low — Anthropic trailers display under the Claude product label

- **Impact:** A new user may need one moment to understand provider alias
  canonicalization.
- **Recommendation:** Clarify provider display aliases in a later
  documentation-only release.
- **Disposition:** Accepted for v0.4.4. Provider identity and all metric units
  remain correct in `profile.json`.

### Low — GitHub Actions reports Node 20 action deprecations

- **Impact:** The pinned upload/download actions currently run successfully
  under GitHub's Node 24 override but should be refreshed before enforcement
  changes.
- **Recommendation:** Upgrade the pinned action revisions in a future
  maintenance PR and rerun release recovery tests.
- **Disposition:** Accepted as non-blocking maintenance debt; every required
  workflow and publication step passed.

## Verified areas without findings

- Renderers consume sealed validated aggregate data; they do not scan Git,
  access SQLite, infer attribution, or recalculate statistics.
- Unique commits, actor presences, provider commits, active days, and evidence
  records remain distinct.
- Unknown remains separate from human; no source-style inference exists.
- Public outputs contain no repository, organization, path, prompt, message,
  email, URL, salt, UID, or SHA canary.
- Static SVG Profile assets and the self-contained filterable dashboard are
  realistic for GitHub README and Pages constraints.
- v0.4.4 adds no configuration CLI, schema change, remote font, dependency, or
  other feature outside the frozen Public Beta scope.

## Severity summary

| Severity | Fixed | Accepted | Pending |
|---|---:|---:|---:|
| Critical | 0 | 0 | 0 |
| High | 1 | 0 | 0 |
| Medium | 0 | 0 | 0 |
| Low | 0 | 2 | 0 |

There are no unresolved Critical or High findings. The two accepted Low items
are documented maintenance/onboarding friction and are not promotion blockers.

## Final verdict

GO — PUBLIC BETA

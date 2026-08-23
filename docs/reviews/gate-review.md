# ai-profile v0.8.0 Signal Console gate review

Date: 2026-08-23

Review range: `v0.7.2..8920227ecd1f815d6e246940bff6ffd71a247463`

Reviewer posture: independent Codex Principal Software Engineer; verification only

## Executive summary

The v0.8.0 Signal Console candidate is **READY**. The visual redesign is
coherent across dashboard, summary, heatmap, and badge; the 390px first
viewport contains the core metrics and commit map; the 195px extreme-narrow
case has no unexpected horizontal overflow. Light, dark, system, keyboard,
tooltip, provider-filter, disclosure, reduced-motion, zero-data, README-width,
and 1x/2x SVG evidence are clear and free of clipping.

The compatibility boundary is preserved: ACE remains `0.3.0`; `VizStats`,
`profile.json`, CLI behavior, eight output names, privacy semantics, provider
overlap semantics, deterministic bytes, self-contained CSP, and zero-network
rendering are unchanged. `generated_on` is presented as a snapshot rather than
live data. No framework, remote font, API, tracker, or renderer data source was
added.

## Verification evidence

| Area | Result |
|---|---|
| Final commit | `8920227ecd1f815d6e246940bff6ffd71a247463`; clean worktree; `git diff --check` clean |
| GitHub PR CI | run `32663289016`: **8/8 passed** (Python 3.11-3.14, release-candidate build, Ubuntu/macOS/Windows wheel onboarding) |
| Local full suite | Windows Python 3.14: **977 passed, 30 skipped**; clean Ubuntu Python 3.12: **1001 passed, 6 skipped** |
| Lint and docs | Ruff clean; bilingual README parity passed; sanctioned snapshot/sample regeneration has zero residual drift |
| Browser matrix | 1440x900, 1024x768, 768x1024, 390x844, 320x568, 195x600; light/dark/system; no overflow or network requests; minimum rendered font 13px |
| Static images | Summary/heatmap width 830 and badge height 24 inspected at README width and 1x/2x; no clipping, blur, overlap, or undersized copy |
| Interaction | Provider filtering, theme cycle, tooltip hover/focus/Escape, roving calendar keyboard navigation, disclosure, and reduced motion passed |
| Anti-pattern scan | `npx impeccable detect --json` returned `[]`; the v0.7.2 baseline returned six findings |
| Package identity | Clean-clone deterministic wheel SHA-256 `9cc06f2052a642bd198fa00d728c75b72fce061dad24c51b72feddf84b07c89e` |

## Findings

No Critical, High, Medium, or Low findings were reproduced on the final
candidate. The extreme 195px title wraps across syllables, but remains readable
and unclipped; this is acceptable degradation outside the primary mobile
acceptance width and is not a release blocker.

## Final recommendation

**READY — approve PR #35 for merge after this review record is committed and
the resulting CI run remains green.** Post-merge release, Profile caller pin,
cloud refresh, exact-eight generated commit, Pages HTTP 200, and public
light/dark/mobile checks remain deployment gates rather than candidate defects.

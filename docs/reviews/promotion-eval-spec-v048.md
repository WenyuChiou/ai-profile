# v0.4.8 Public Beta HR-first visual-refresh evaluation specification

Date frozen: 2026-08-01
Baseline: `374118a88840388a0a374d5cab695b6f18a49c2c` (pre-v0.4.8 `main`,
the live v0.4.7 release state)
Target: `ai-profile-cli` 0.4.8 Public Beta

This specification is fixed before candidate evaluation. Results may not
weaken these gates. v0.4.8 is a renderer/documentation refresh (ADR-022):
the ACE schema, aggregation semantics, privacy boundary and modes, CLI
behavior, and the exact eight-output bundle must remain unchanged from
v0.4.7. Changed surfaces are the summary card (`AI Collaboration
Record`), the shared day-cell bin helper (`render/_bins.py`), the
dashboard H1, README structure, and the banner/social assets.

## Candidate identity

- Version: `0.4.8`
- Wheel: `ai_profile_cli-0.4.8-py3-none-any.whl`
- Frozen `SOURCE_DATE_EPOCH`: `1785369600`
- Canonical clean-Linux wheel SHA-256:
  `04e90f2599bda2ce24bbd254f48bb2034fcaba140a17a40912594edc45257bd0`
  (isolated Docker `python:3.12` build of the candidate tree; pinned in
  `docs/reviews/promotion-candidate.json`, the staging workflow, and
  `tests/unit/test_staging_preview.py` before any promotion evidence is
  accepted; a re-frozen digest requires rebuilding and re-running every
  gate below that consumed it).
- The staging dashboard SHA-256 must remain
  `c8680c2812343077775c2b5c0fddae9dce32c1517bbaa4c920e056b347fdbd4f`.

## Required gates

1. **Exact semantics.** The redesigned card must publish only honest
   claims: terrain height = `DayCell.total_commits` through the fixed
   1 / 2-4 / 5-7 / 8+ bins; terrain hue = the day's AI share through the
   heatmap's fixed share bins; provider counts never influence terrain
   geometry; hue bin 0 states only zero attributed AI (never a
   human-authorship claim — unattributed history sits in that bin);
   provider totals are explicitly non-exclusive; an unpublished daily
   series states exactly `Daily activity is not published for this
   profile`; the zero state is unchanged. Each of these is pinned by a
   regression test that fails when the semantics drift.
2. **Test and lint gates.** Full pytest, Ruff, sanctioned snapshot
   regeneration for the summary family (second run byte-identical),
   README EN/zh-TW parity, and deterministic release smoke must pass on
   the candidate tree. The heatmap/badge family must be byte-unchanged
   from the baseline (the `_bins` extraction is a pure refactor).
3. **Exact artifacts.** A clean-Linux build with the frozen
   `SOURCE_DATE_EPOCH` must reproduce the pinned wheel SHA-256 exactly.
   `twine check` and the release artifact contract must pass for the
   exact retained wheel and sdist (both notices present, no generated
   cache or private members, canonical paths only).
4. **Cross-platform smoke.** Ubuntu, Windows, and macOS must install the
   retained candidate wheel in a clean environment and complete
   onboarding smoke against those exact bytes (never a platform rebuild).
5. **README-only dogfood.** The exact retained candidate must pass four
   README-only roles: newcomer, privacy, multi-provider semantics, and
   Profile publisher. Required result: 4/4 complete, zero external
   hints, zero privacy-canary hits, and exact hand-derived aggregate
   agreement with the rendered card, heatmap, badge, dashboard, and
   `profile.json`.
6. **Zero privacy leaks.** The end-to-end canary sweep over every
   generated output must report zero hits (repository names/paths/uids,
   author emails, SHAs, raw trailer values, unrecognized raw provider
   strings). Aggregate-only repositories must surface no dates anywhere,
   including the new terrain.
7. **Staging and browser matrix.** The exact staging dashboard must be
   served at
   `https://wenyuchiou.github.io/ai-profile/v0.4.8/dashboard.html` and
   match the pinned wheel and dashboard digests. The browser matrix must
   then pass ALL of the following, explicitly:
   - viewport widths 320, 390, 768, 1280, and 1440 CSS pixels;
   - 200% browser zoom;
   - light, dark, and system color themes;
   - the All AI, Claude, and OpenAI provider filters;
   - Tab, Arrow, Enter, and Escape keyboard operation with a visible
     focus indicator at every stop;
   - reduced-motion preference honored;
   - touch-target adequacy on coarse pointers;
   - tooltip containment within the viewport;
   - zero horizontal overflow at every width/zoom combination above;
   - WCAG contrast of at least 4.5:1 for normal text and 3:1 for large
     text and meaningful graphical marks;
   - surface checks on the GitHub README render, the raw SVG assets,
     and the Pages dashboard.
8. **Independent review.** Independent design/semantics,
   security/privacy, packaging/onboarding, and completion-integrity
   review must report no unresolved Critical or High finding. Any
   accepted Medium must name an owner and follow-up.

## Release and live verification

The PR must merge through protected `main` with required checks. The
`v0.4.8` tag must point to that merge commit. The publish workflow must
upload exactly the retained bytes to PyPI and the GitHub Release. Live
verification must confirm:

- exact public wheel and sdist SHA-256 values;
- both notices in both artifacts;
- zero forbidden cache/private members in the public sdist;
- clean PyPI installation, version, quickstart, privacy canary,
  deterministic render, and the expected eight outputs;
- green GitHub Actions and valid public links, including the
  restructured README image set.

Two link-evidence files exist and must not be conflated:

- `docs/reviews/promotion-public-link-candidate-v048.json` — the
  PRE-RELEASE candidate evidence: a complete fresh verification of the
  candidate README URL set, Markdown counts, Profile HEAD, and Pages
  byte-identity, performed before any v0.4.8 release exists; its
  `release_urls` honestly point to the live v0.4.7 release. The candidate
  README contract test reads this file.
- `docs/reviews/promotion-public-link-evidence.json` — the RETAINED
  post-release public evidence. It stays byte-identical (digest-pinned in
  the candidate contract test) until the post-release live verification
  above completes and updates it; nothing may modify it ahead of that
  verification.

Any artifact mismatch, privacy leak, cross-platform failure, horizontal
overflow, README-only dead end, publication mismatch, or unresolved
Critical or High review finding forces `NO-GO`.

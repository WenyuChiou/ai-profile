# Evidence Ledger Visual Refinement Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine the released v0.4.8 profile card and dashboard into a calm, editorial instrument panel that makes explicit AI provenance legible in five seconds, without changing ACE, aggregation semantics, privacy policy, CLI behavior, or the eight-file output contract.

**Architecture:** Keep `VizStats` as the only renderer input. Keep SVG/HTML rendering pure, deterministic, local-first, and isolated from Git, storage, schema, and network code. Treat each visual section (hero, terrain, provider ledger, evidence rail, dashboard panels) as an independently testable render unit. Use existing `Theme` tokens and local font stacks; add a new token only when a semantic color cannot be expressed by an existing token. Do not add a theme engine, runtime CSS loader, or user-configurable style format in this release.

**Tech Stack:** Python 3.11–3.14, stdlib SVG string renderers, self-contained HTML/CSS/JS, pytest, Ruff, sanctioned snapshot generators, existing browser/release smoke scripts.

---

## Pinned constraints and research decisions

- Current baseline is the released v0.4.8 contract (`628 passed, 4 skipped`, Ruff clean); any count change must be explained and reflected in the repository's quality guidance.
- Preserve the 830px summary width, dynamic deterministic height, light/dark pair, SVG allowlist, no external font/network/script references, `VizStats` structural redaction, and all eight output filenames.
- Unknown remains separate from Human. A provider presence never becomes a second unique commit. Terrain height remains `DayCell.total_commits`; terrain hue remains AI share; provider counts never feed terrain geometry.
- Keep IBM Plex Sans Condensed / IBM Plex Sans / IBM Plex Mono local fallback stacks already pinned by tests. Do not fetch or vendor a paid font.
- Adopt the research-derived “evidence ledger” grammar: explicit facts first, semantic status marks, strong metadata/source boundaries, progressive detail, and reduced-motion/fallback paths. Do not copy Liquid Glass, aurora backgrounds, terminal density, remote installers, or provider colors as evidence.
- Direct design references reviewed on 2026-08-04: [Nanako0129 profile](https://raw.githubusercontent.com/Nanako0129/Nanako0129/main/README.md), [TokenBar](https://raw.githubusercontent.com/Nanako0129/TokenBar/main/README.md), [coralline](https://raw.githubusercontent.com/Nanako0129/coralline/main/README.md), [pilotfish design rationale](https://raw.githubusercontent.com/Nanako0129/pilotfish/main/docs/design.md), and [remora-cc](https://raw.githubusercontent.com/Nanako0129/remora-cc/main/README.md). The reusable insight is information hierarchy and auditability, not the source projects’ decorative language.

## Task 1: Freeze the visual contract before editing

**Files:** `docs/decisions/ADR-023.md`, `docs/architecture.md`, `docs/mvp.md`, `docs/ROADMAP.md`, `docs/progress.md`

1. Record that this is a post-v0.4.8 visual refinement only; explicitly state that ACE, schema, aggregation, privacy boundary, CLI, and output names are unchanged.
2. Pin the evidence-ledger primitives: 4px spacing, section marker/label pair, aligned number columns, neutral track plus small provider mark, terrain legend, explicit privacy cue, and local font stacks.
3. Record the non-goals: no new dashboard filters, no role aggregation, no network font, no 3D/animation requirement, no generic GitHub-statistics implementation, no change to historical attribution.
4. Keep documentation claims no stronger than the code and preserve the existing v0.4.8 release record.

## Task 2: Add red-first renderer regression coverage

**Files:** `tests/unit/test_render_summary.py`, `tests/unit/test_recruiter_card.py`, `tests/unit/test_dashboard_html.py`

1. Add focused assertions for separate provider count and percentage alignment, section-label markers, and neutral provider tracks with brand color restricted to the small fill/mark.
2. Add geometry checks that all newly introduced coordinates remain integers or two-decimal values and that no SVG element outside the allowlist appears.
3. Add a double-render byte-equality check for each theme and the existing zero, aggregate-only, sparse, populated, and long-number fixtures.
4. Run only the targeted tests and capture the expected red failures before implementation.

## Task 3: Implement the pluggable visual primitives

**Files:** `src/aiprofile/render/summary_svg.py`, `src/aiprofile/render/themes.py`, `src/aiprofile/render/dashboard_html.py`

1. Keep the current private section boundaries and introduce only small pure helpers where the new visual primitives are repeated (section marker, aligned metric pair, provider meter, evidence label).
2. Give provider rows a stable three-column ledger: identity lockup, neutral track with a thin provider-colored fill, and a right-aligned count/percentage pair. Preserve the exact metric strings and denominator text required by tests.
3. Use the existing accent only for the hero value, share fill, small provider fills/marks, and header mark. Keep labels, values, and privacy copy in semantic text/muted tokens.
4. Refine the terrain without changing its encoding: preserve volume/share bins, reduce visual noise, keep the static isometric prism, and make the legend explain both encodings without relying on color alone.
5. Align dashboard tokens and controls with the same editorial ledger grammar. Preserve all current provider filters, theme toggle, keyboard behavior, CSP, reduced-motion rule, and no-storage/no-network guarantees.

## Task 4: Regenerate sanctioned artifacts only

**Files:** `tests/snapshots/*.svg`, `docs/assets/*.svg`

1. Run `python tests/unit/test_render_summary.py` for the summary family.
2. Run `python tests/unit/test_heatmap_svg.py` only if shared theme/bin changes affect that family.
3. Run each sanctioned generator a second time and assert zero byte drift in snapshots and assets.
4. Do not hand-edit generated SVGs.

## Task 5: Verify implementation and privacy

1. Run targeted renderer/dashboard tests.
2. Run `python -m pytest tests -p no:cacheprovider` and record the observed count.
3. Run `python -m ruff check src tests scripts`.
4. Run `python scripts/check_readme_parity.py`.
5. Run the existing release smoke against a freshly built wheel/sdist if version or package files changed; otherwise run the exact current v0.4.8 artifact contract without republishing.
6. Sweep snapshots, docs assets, generated `dist/`, dashboard HTML, and JSON for repository names/paths, organizations, emails, SHAs, prompts, messages, and external font/network references.
7. Re-check light/dark contrast, 320/390/768/1280/1440 widths, 200% zoom, keyboard focus, reduced motion, and no horizontal overflow using the existing browser QA route.

## Task 6: Independent review and release decision

1. Review the complete diff with the code-review gate because this is a multi-file renderer/documentation change.
2. Confirm no schema/CLI/aggregation/privacy behavior changed and no duplicate generic GitHub-statistics functionality was introduced.
3. Write `docs/reviews/v0.4.9-visual-readiness.md` with findings, exact commands, screenshots/evidence, and one verdict: `GO — PUBLIC BETA`, `GO WITH CONDITIONS`, or `NO-GO`.
4. Do not tag or publish a new version until artifact, privacy, cross-platform, browser, and README gates are green. If visual changes remain snapshot-only and no release is authorized, leave the branch unmerged and hand off the verified diff.

## Expected completion evidence

- Git status contains only the explicitly allowed source/tests/generated/docs files plus the plan/review files.
- Full test suite and Ruff are green with observed counts recorded.
- Sanctioned regeneration is byte-stable.
- Public assets remain privacy-safe and deterministic.
- A new contributor can understand the visual grammar and why each mark exists from the ADR and README, without learning internal schema details.

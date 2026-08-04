# Structural Current design system and visual refinement

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the static summary and self-contained dashboard feel like one
distinctive, calm evidence instrument while preserving every data, privacy,
determinism, CLI, and eight-output contract.

**Architecture:** Renderers continue to accept only validated `VizStats`. The
typed `Theme` remains the runtime boundary for SVG; the dashboard keeps its
self-contained CSS/JS. `DESIGN.md` documents the shared roles and extension
points but is not runtime configuration. No schema, aggregation, storage, or
network dependency is introduced.

**Tech Stack:** Python stdlib renderers, static SVG/HTML, pytest, Ruff,
sanctioned snapshot generators, existing artifact/privacy/browser smoke.

---

## Acceptance invariants

- `python -m pytest tests -p no:cacheprovider` remains green (baseline:
  `628 passed, 4 skipped`).
- `python -m ruff check src tests scripts` is clean.
- Summary snapshots and committed samples change only through
  `python tests/unit/test_render_summary.py`; a second run is zero-diff.
- The eight public outputs, `VizStats` fields, provider/commit/evidence units,
  unknown-versus-human distinction, and privacy canary sweep are unchanged.
- SVG tags/attributes, width 830, dynamic height, local font stacks, and
  light/dark contrast remain within existing tests.
- Dashboard remains self-contained, keyboard-operable, reduced-motion safe,
  and network/CSP closed.

## Tasks

### 1. Make the visual contract explicit

- Add `DESIGN.md`, the reverse-engineering review, and ADR-024.
- Update architecture/roadmap/progress/changelog only with claims that match
  the actual renderer behavior.
- Keep this documentation separate from schema and runtime configuration.

### 2. Strengthen the static terrain without changing its encoding

- Add a faint, theme-border calibration spine/grid along tile seams after the
  existing prisms, with shared seam chains emitted only once.
- Keep prism height = unique daily total-commit bin and top-face hue = AI-share
  bin; provider counts must not affect geometry.
- Keep the current legend and accessible description; do not introduce motion,
  gradients, arbitrary icons, or a third signal color.
- Add focused assertions to existing terrain tests for the spine and unchanged
  height/provider-independence semantics.

### 3. Refine the evidence ledger grammar

- Give the provider table and evidence rail a shared quiet index marker and
  stronger column alignment, without changing any pinned content string.
- Keep count and percentage in separate right-aligned columns and state the
  non-exclusive denominator beside the ledger.
- Keep provider color limited to glyphs and bars; labels/values use text roles.

### 4. Align dashboard roles and fallback states

- Replace duplicated role literals only where a visual regression demonstrates
  drift; do not build a generic token framework.
- Keep the selected-provider label in normal text color, and preserve border,
  icon, text, and state cues for selection.
- Add/retain explicit daily unpublished, zero, aggregate-only, unknown, and
  provider-overlap copy. No new data field or filter is allowed.

### 5. Verify and package

- Run targeted renderer/dashboard tests, sanctioned snapshot regeneration,
  full pytest, Ruff, README parity, artifact contract, fresh-wheel smoke,
  privacy canary sweep, SVG security/geometry sweep, and double-render checks.
- Inspect light/dark summary images at README scale plus 320/390/768/1280/1440
  dashboard widths, 200% zoom, keyboard/focus, reduced motion, and no overflow.
- Prepare a readiness report with reproducible evidence. Do not call the work
  a public release until a versioned candidate, clean-wheel smoke, CI, and
  Profile update are all verified.

## Explicit non-goals

No ACE/schema or aggregation changes; no provider/role inference; no generic
GitHub statistics; no Git Notes/Git AI reimplementation; no new config CLI; no
remote assets; no paid fonts; no hosted dashboard; no ninth output; no 3D
animation or liquid-glass decoration.

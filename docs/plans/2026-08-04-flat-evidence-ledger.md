# Flat Evidence Ledger visual pivot

## Intent

Replace the previous isometric/prism terrain with a calm, flat 2D evidence
timeline. The visual should communicate the same validated facts in a faster,
more professional scan: volume is a short bar height, AI share is a discrete
color ramp, and provider breadth remains a labelled ledger.

## Invariants

- Keep `render_summary(stats, theme) -> str`, the 830px width, deterministic
  height ordering, light/dark themes, eight output files, CLI, `VizStats`, ACE
  schema, aggregation units, and privacy boundary.
- Keep daily volume bins (`0 / 1 / 2-4 / 5-7 / 8+`) and AI-share bins. Provider
  rows never affect daily geometry; unknown never becomes Human.
- Keep the unpublished-daily notice and aggregate-only wording. Never draw a
  fabricated daily grid when `stats.daily` is empty.
- Use only the existing SVG allowlist, integer coordinates, local fallback
  fonts, and no external assets, animation, gradients, or network requests.

## Direction

- Header and hero remain unchanged so the card's identity and numbers stay
  familiar.
- Replace the perspective terrain with a 12-column by 7-row flat calendar
  matrix. Each cell has a neutral track; a small bottom-anchored bar encodes
  the volume bin and its fill uses the AI-share ramp.
- Month labels align to column centers. A compact text legend explains
  `bar height = total commits` and `fill = AI share`; no prism/diamond symbols.
- Keep generous 4px spacing, normal text color for labels, and accent only on
  data marks and the hero value.

## Verification

- Rewrite geometry tests to assert flat rectangles, unique daily cells, volume
  bin heights, share colors, provider independence, and no `polygon` output.
- Regenerate summary snapshots/assets only through
  `python tests/unit/test_render_summary.py`.
- Run targeted tests, full pytest, Ruff, README parity, artifact contract,
  exact-wheel smoke, privacy canary, and Playwright viewport/focus/theme checks.
- Keep the previous `codex/v050-structural-current` commit available as a
  rollback reference until this branch passes independent review.

## Non-goals

No ACE/schema change, new output, new CLI, role aggregation, provider registry,
network dependency, or interactive behavior in the static SVG.

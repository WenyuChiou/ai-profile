# ADR-033: Voxel Collaboration World — Collaboration Mine

Date: 2026-09-06
Status: Mine preview accepted; chart-first dashboard locally verified; release pending

## Context

ADR-032's fixed volume bins and AI-share quarters obscured differences between
8, 20, 38 and 55 commits. The user requested an original voxel-game mine,
all dates in the selected range, integrated workstations/evidence and moving
characters. Later amendments explicitly replace the finite README animation
with continuous motion, strengthen 3D geometry and prohibit overlapping dates.

## Decision

The user accepted the deeper-3D mine preview on 2026-09-06, then requested a
chart-first dashboard. Provider glyphs are the primary recognition cue, with
short visible names and accessible labels; they do not assert a specific tool.
Custom dates, the full table and technical definitions use native disclosures.
Exact counts, shared denominators, scope and overlap warnings remain visible.
The approved terrain, date bands and continuous actor animation are unchanged.

### Truthful geometry

- Summary remains 830px wide, with three consecutive 28-day terraces ending on
  the latest publishable daily date. Date ranges are not called calendar weeks.
- Dashboard offers 28/84/365 days, all publishable dates and custom bounds.
  Every selected date is rendered, including zero positions. No carousel.
- Daily AI-attributed and Other-record pillars share a zero and linear scale.
  Other is total minus AI, never a Human or Unknown label.
- Front height alone measures quantity. The ceiling is the next leading-decimal
  integer step: 38→40, 55→60, 101→200. Provider selection cannot change it.
- All dashboard rows, including partial final rows, have identical projection
  width. Responsive rows contain 28, 14 or 7 positions; zoom changes layout,
  not selected dates or data.
- Provider trough fronts use attributed commits divided by all-period unique
  AI-attributed commits, without minimum width or integer-pixel rounding.
  Providers may overlap; neither ore decorations nor provider totals are
  summed into the daily AI/Other split.
- Evidence remains all-period, with neutral Unknown, explicit category counts
  and denominator. Publication scope is separate, not a daily evidence grade.

### Original orthographic world

The grass top has a fixed 18px right / 12px up depth vector; 14px soil and
22px masonry create a thick cutaway face. Pixel seams and ore are decoration,
not a unit-per-block encoding. Pillar fronts stay vertical and parallel;
their shallow top/side faces do not add quantity.

Original cuboid miner and mossy explorer geometry is shared in
render/voxel_art.py. No game assets are imported. Blender is not a runtime
dependency: the result is native SVG, not embedded raster frames or video.

Horizontal dates occupy a dedicated band beneath the terrain. Summary dates
are 14px in the 830px source. Month/year ranges occupy a separate header.
Actors use the service shaft at the outside edge; below 240px dashboard
container width, the shaft moves under the date band to preserve date spacing.

### Continuous motion and accessible fallback

- Summary and dashboard use seamless 18-second character loops. The user's
  explicit amendment supersedes the once-only, at-most-five-second README rule.
- Only actor transform/opacity changes. UI feedback is at most 120ms.
  Dates, labels, pillars and headline numbers never animate.
- Dashboard has pause/play and hidden-page pause. README is an image, so no
  embedded JavaScript pause button is promised.
- Reduced motion and print stop all actors. Data is complete from the first
  frame. No activity means idle characters, not mining.
- Maximum two characters per scene. Routes must avoid data fronts and date
  hit areas; mining does not remove or create commit columns.

### Layout and security

DOM reading order is snapshot/core metrics, controls, landscape, selected-day
details, workstations/evidence, daily table and definitions. Desktop details
sit beside the landscape; mobile details follow it. Dates use one roving
tab stop. Native buttons support keyboard activation and visible focus.

SVG allows only svg/title/desc/rect/line/text/tspan/path/g/style. The added
g/style support closed renderer-owned keyframes and media rules, not arbitrary
CSS. No script, event attribute, external reference, URL/import CSS, SMIL or
foreignObject. Negative tests retain these prohibitions.

Dashboard remains one self-contained document with default-src 'none',
embedded script/style only, img-src data:, and font/connect/object/base/form
sources disabled. No API, tracking or additional renderer data source.

## Acceptance and consequences

VizStats, ACE 0.3.0, CLI and eight public output names remain unchanged.
Golden assets regenerate only via the two sanctioned family commands.

Acceptance includes linear/extreme/zero tests; date-label and actor/data
bounding-box checks throughout multiple animation cycles; 1440/1024/768/390/
320/195px browser checks; 830/664px SVG at true 1x/2x; reduced-motion/print;
full pytest, Ruff, README parity and actual Impeccable results.

This design decision does not certify preview approval, GitHub CI success or
publication. Those remain separate gates. Daily updates remain GitHub-hosted;
no local schedule is created.

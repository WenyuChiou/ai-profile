# ADR-026: Editorial Signal visual skin

Date: 2026-08-04  
Status: proposed on `codex/editorial-signal-skin`  
Supersedes: none

## Context

The v0.4.9 flat Evidence Ledger removed the earlier perspective/3D terrain and
made the card semantically legible. A visual research round compared the
current card with Nanako0129's terminal-ledger composition, Primer/Carbon/Radix
token systems, and common GitHub profile generators. The useful common ground
is hierarchy, alignment, direct labels, and semantic tokens—not decoration.

## Decision

Keep the existing flat card and add a small Editorial Signal skin:

- section headings use a two-part editorial marker (short rule + datum bar);
- the twelve-week matrix gets sparse quarter-window alignment rails;
- the rails are structural only and carry no quantitative value;
- existing blue signal, warm evidence cue, provider glyphs, type stacks, and
  flat bar encodings remain in place;
- dashboard and README continue to use the same visual vocabulary.

The skin is implemented by private render-layer helpers that reuse the existing
semantic theme tokens; fixed marker/rail geometry remains named private
constants. No new data path, public configuration option, runtime dependency,
font request, animation, or output file is introduced.

## Consequences

The card gains a distinctive editorial/instrument-panel rhythm at README width
without returning to perspective, glass, gradients, or AI-score decoration.
Because the rails are generated from fixed constants and existing theme
tokens, the output remains deterministic and can be removed without changing
ACE or aggregation semantics.

The review gates must continue to assert that rails are not an extra data
channel, that labels remain readable without color, and that all affected
snapshots/assets are regenerated only by the sanctioned script.

The low-opacity rails and short rules are non-semantic alignment guides. They
must not be interpreted as quantitative marks. If a future skin assigns them
meaning, it must promote them to a semantic token and satisfy the graphical
contrast requirement with dedicated tests.

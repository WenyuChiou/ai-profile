# v0.4.3 Public Beta remediation evaluation specification

Status: draft — not frozen  
Target: `ai-profile-cli` 0.4.3 Public Beta

The immutable baseline is
`docs/reviews/promotion-eval-spec.md@02068ba5cf7a1ce6a194b18f70f6245603081916`.
That file must remain byte-identical. v0.4.3 may not exempt, weaken, or
reinterpret any gate in that baseline.

## Scope

v0.4.3 is an immutable patch successor to the published v0.4.2. It may
change only:

- the dashboard root-width behavior needed to remove horizontal page
  overflow at the 320 CSS-pixel gate with classic scrollbars;
- dashboard calendar keyboard/touch inspection, accessibility-tree
  semantics, meaningful-mark contrast, and generated-metadata contrast
  needed to satisfy the already-approved accessibility gates;
- the maintainer Profile's responsive choice between existing generated
  asset families so fixed-width summary details are not illegibly scaled on
  a 320-pixel README viewport;
- regression coverage, version metadata, release evidence, and generated
  samples required by that change.

It must not change the ACE schema, aggregation semantics, privacy boundary,
CLI, provider vocabulary, or SVG renderer contract.

## Frozen promotion gates

The v0.4.2 evaluation specification remains the baseline. v0.4.3 must satisfy
every gate in that document plus these remediation-specific requirements:

1. Headed Chromium with non-overlay scrollbars has zero document-level
   horizontal overflow at 320, 390, 768, and 1440 CSS pixels in light and
   dark modes.
2. At 200% zoom, the document has zero horizontal overflow and the calendar
   remains locally scrollable rather than widening the page.
3. All AI, Claude, and OpenAI filters remain keyboard operable; selected
   state remains visible through text/shape/border as well as color.
4. Every rendered calendar date is visible in the accessibility snapshot,
   rather than being hidden behind a single `role="img"` summary. The
   calendar uses one Tab entry plus roving `tabindex` and arrow-key
   navigation; it must not add up to 365 dates to the linear Tab sequence.
   Focus, Enter/Space, tap, and hover expose the same date, total-commit
   count, selected-provider count, and share. Escape or repeating the
   activating operation closes the detail without losing focus.
5. Normal text clears 4.5:1 in both themes. Every non-empty calendar mark
   clears 3:1 against the adjacent empty-cell state in both themes and for
   every provider filter. Validation uses browser-composited fill/border
   colors, not raw accent tokens, and covers each provider's lowest non-zero
   activity plus meaningful legend marks. The 12-pixel `.generated`
   metadata clears 4.5:1 against its actual light/dark background.
6. The dashboard remains self-contained, network closed, deterministic, and
   free of private paths, repository identities, organization names, commit
   identifiers, messages, prompts, and email addresses.
7. The exact candidate wheel is rebuilt with a frozen `SOURCE_DATE_EPOCH`,
   recorded by SHA-256, and used by all four isolated dogfood roles.
8. All four roles complete with zero README-external hints; privacy canaries
   have zero hits; independently derived aggregation values match exactly.
9. Ubuntu, Windows, and macOS consume and pass onboarding against the same
   retained universal wheel.
10. PyPI and GitHub Release serve the exact retained wheel and sdist bytes,
   with both `LICENSE` and `THIRD_PARTY_NOTICES.md` present.
11. The maintainer Profile is regenerated only from the released PyPI wheel.
    At a 320-pixel README viewport it uses a legible compact generated asset
    instead of scaling the 830-pixel summary's 11-pixel text below readable
    size. A real GitHub-rendered README at 320 and 390 pixels, in both light
    and dark modes, must select the compact asset; its smallest rendered text
    is at least 11 CSS pixels. At 768 and 1440 pixels the full summary remains
    selected. Compact and full assets link to the same dashboard, have
    equivalent alt purpose, and cause no page-level horizontal overflow.
    The check must confirm GitHub's sanitizer preserves the required
    `<picture>`/`<source media>` behavior. The Profile passes the same privacy
    gates and deploys through its normal pull-request path.

## Fixed failure policy

- Any artifact, privacy, cross-platform, dogfood, 320-pixel overflow, or
  Profile/Pages failure forces `NO-GO`.
- Gates 1–5 and 11 are known remediation blockers. Failure of any one forces
  `NO-GO`; none may be accepted as residual Medium risk.
- Critical and High findings must be zero.
- Medium findings must be fixed or explicitly accepted with evidence in the
  final readiness report.
- The final verdict is exactly one of `GO — PUBLIC BETA`,
  `GO WITH CONDITIONS`, or `NO-GO`.
- Published v0.4.2 artifacts and its tag are never deleted, replaced, or
  rewritten.

## Freeze procedure

This specification must be committed before v0.4.3 implementation, dogfood,
or promotion evidence begins. A subsequent metadata-only freeze commit
changes `Status` to `frozen` and records the draft commit SHA; the v0.4.3
candidate manifest records the freeze commit SHA as its evaluation baseline.
After that commit, this file must remain byte-identical. Any later change
invalidates existing evidence and requires every affected gate to be rerun.

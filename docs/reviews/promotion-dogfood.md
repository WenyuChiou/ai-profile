# v0.4.6 R2 promotion dogfood evidence

Date: 2026-07-29
Candidate wheel: `ai_profile_cli-0.4.6-py3-none-any.whl`
SHA-256: `26227c0435d2d6a80ff8a46ad878270509b2cadeeb6d0dd78555019884239d8a`

## Posture and acceptance rule

This is the pre-registered R2, README-only evaluation required by
[promotion-eval-spec-v046.md](promotion-eval-spec-v046.md). Earlier R1
reports do not count toward this result. Each role had to use the exact wheel,
a fresh temporary repository, venv, and `AIPROFILE_HOME`; no source, tests, or
non-README guidance; and report commands, exit status, stderr, duration, and
friction. The R2 gate passes only if all four roles complete with no external
hint, every privacy canary has zero public-output hits, and hand-derived
aggregation values agree with the generated artifacts.

Negative-access assertions are role attestations, not an enforceable sandbox.
The raw command ledgers are retained under `.ai/dogfood-049-*.md` and are
intentionally not versioned because they contain local temporary paths.

## Role matrix

| Role | Exact wheel | Isolated run | Result | Counts toward R2 |
| --- | --- | --- | --- | --- |
| Newcomer | Match | Final `C:\Temp` rerun outside a Git worktree | `init → scan → aggregate → render` passed; eight outputs | Yes |
| Multi-provider | Match | Fresh explicit `C:\aiprofile-dogfood-*` home | Hand-derived values and eight outputs matched | Yes |
| Profile publisher | Match | Fresh explicit `C:\aiprofile-dogfood-*` home | SVGs, card markup, Pages/404 guidance, and eight outputs passed | Yes |
| Privacy user | Match | Fresh temporary repository, venv, and explicit home | `aggregate_only`, `full`, and `excluded` generated 24 public artifacts with zero exact canary matches | Yes |

## Verified role evidence

- **Newcomer:** installed the verified wheel in a fresh venv, confirmed
  `aiprofile 0.4.6`, and completed the README Quickstart with an explicit
  trailer commit. Scan reported one record; aggregate reported one attributed
  commit, one presence, OpenAI one, declared one, unknown zero; render wrote
  exactly `badge-{light,dark}.svg`, `heatmap-{light,dark}.svg`,
  `summary-{light,dark}.svg`, `dashboard.html`, and `profile.json`.
- **Multi-provider:** three synthetic commits produced three scanned commits,
  one unique AI-attributed commit, two actor presences/providers, one
  human-declared commit, one unknown commit, and four evidence records
  (declared three, unknown one). The provider display labels Claude and
  OpenAI retained one attributed commit/presence/day each. This preserves the
  required `one commit ≠ multiple presences` and `unknown ≠ human` semantics.
- **Publisher:** a README-only workflow generated the same eight files; it
  verified light/dark badge, heatmap, and summary SVG variants, the
  clickable-card markup, and the documented GitHub Pages `main` + `/ (root)`
  procedure, including the expected initial-404 recovery path. No remote
  publication was attempted.
- **Privacy:** the original R2 role used separate public-output directories
  for `aggregate_only`, `full`, and `excluded`; all three paths completed and
  all 24 artifacts had zero exact matches for its harmless repository, path,
  organization, commit-message, and email canaries. Its explicit temporary
  home happened to be beneath a parent Git worktree, so the product issued its
  documented advisory warning; the frozen R2 requirement does not prohibit
  that layout and the role did not treat it as a configuration dead end.

## Findings and disposition

| Severity | Description and evidence | Impact | Recommendation | Disposition |
| --- | --- | --- | --- | --- |
| Low | A later, discarded retry used PowerShell's reserved `$home` variable and created `C:\Users\wenyu\config.json`. The local command policy rejected its removal. Metadata observed after the stopped run: one identity, one repository, 64-character salt, 507 bytes. | This is local dogfood-containment residue, not a public-output leak and not part of the passing privacy role; it must not be left unexplained. | Manually inspect and remove `C:\Users\wenyu\config.json` if it is not an intentional user configuration before any normal use of that home. | Open — local cleanup required. |

## R2 result

**PASS — all four required R2 roles completed.** This is usability and privacy
evidence for the frozen wheel, not authorization to tag, publish, update the
Profile, or merge the PR. The separate discarded retry left the Low local
cleanup item above. See [promotion-readiness-review.md](promotion-readiness-review.md)
for the overall release verdict.

# v0.4.2 Public Beta promotion evaluation specification

Status: frozen before candidate dogfood  
Frozen on: 2026-07-26  
Target: `ai-profile-cli` 0.4.2 Public Beta

This file is the immutable evaluation baseline once committed. Its commit
hash must be recorded in both promotion reports. Any later change invalidates
all dogfood and review evidence collected against the earlier hash; the
affected gates must be rerun. Pass thresholds may not be weakened within the
v0.4.2 promotion round.

## Decision boundary

The release may be promoted only as a Public Beta. It must not be described
as Stable or generally available. The final verdict is exactly one of:

- `GO — PUBLIC BETA`
- `GO WITH CONDITIONS`
- `NO-GO`

Any release-artifact, privacy, cross-platform, installation, configuration,
or GitHub Pages blocker forces `NO-GO`.

## Frozen product boundary

This round may improve packaging, release automation, documentation,
onboarding, repository governance, and presentation. It must not change the
ACE schema, aggregation semantics, existing CLI commands, or attribution
rules. It must not add `doctor`, identity-management commands, repository
policy commands, or a Stable classifier.

If README-only configuration cannot be completed reliably by all relevant
dogfood roles, promotion stops. Configuration CLI work must be planned
separately for v0.5.0.

## Candidate artifact gates

The same wheel and sdist bytes that pass these checks must be uploaded:

1. Full pytest and Ruff checks pass with their observed counts recorded.
   Existing tests may not be deleted or weakened; remediation tests must be
   additive or a clearly stronger replacement, and the release review checks
   the diff for removed assertions.
2. Both sanctioned snapshot regeneration commands produce no diff.
3. The wheel and sdist both contain `LICENSE` and
   `THIRD_PARTY_NOTICES.md`.
4. Tag, project metadata, installed runtime, wheel metadata, and sdist
   metadata report the same version.
5. Twine validation passes.
6. A clean environment installs the candidate wheel, not the source tree,
   and completes the documented quickstart.
7. The smoke run produces the documented eight files, a CSP-bearing
   dashboard, byte-identical repeated output, and zero privacy-canary hits.
8. Candidate-wheel onboarding passes on Ubuntu, Windows, and macOS with
   Python 3.12.
9. SHA-256 digests are recorded before upload. PyPI-downloaded wheel and
   sdist bytes must match those exact digests after publication.

## Dogfood protocol

Each role receives only a copy of the canonical README and the candidate
wheel. It must use an isolated temporary repository, virtual environment,
and `AIPROFILE_HOME`. Source code and orchestrator hints are prohibited.
Each role reports natural-language commands, exit codes, stderr, elapsed
time, friction, and artifact or screenshot paths.

### Role 1 — New user

Install the wheel, confirm its version, then complete `init`, `scan`,
`aggregate`, and `render` using only the README.

### Role 2 — Privacy-sensitive user

Configure and distinguish `aggregate_only`, `full`, and `excluded`
repositories. Place private-name, organization, path, prompt, commit-message,
email, URL, and SHA canaries in the fixture and perform a byte-level sweep of
every public output.

### Role 3 — Multiple-provider user

Create a fixture where one commit has two explicit AI actor presences and
where unknown and human remain distinct. Hand-derive unique commits, actor
presences, provider commits, active days, and evidence records, then compare
them with the generated aggregate and dashboard filters.

### Role 4 — Profile publisher

Create GitHub Profile README embeds, the clickable summary-card HTML,
light/dark SVG references, the dashboard link, and the documented GitHub
Pages main/root configuration. Record any deployment dead end.

## Dogfood pass criteria

- Roles completed without non-README human/orchestrator hints: 4/4.
- Installation failures: 0.
- Configuration dead ends or privacy misunderstandings: 0.
- Privacy canary matches across all public artifacts: 0.
- Hand-derived commit/provider/evidence totals: exact match.
- GitHub Pages publishing dead ends: 0.

## Independent review gates

Independent reviewers cover architecture/maintainability,
security/privacy, packaging/release, onboarding, visual/accessibility, and
README claim accuracy. A completion-integrity reviewer then checks raw logs
and canonical artifacts instead of trusting summaries.

A separate no-tool synthesizer receives only the four natural-language
dogfood reports and produces a comparison matrix. It does not inspect source
or artifacts. The root reviewer then independently recomputes the matrix's
claims from raw logs and canonical outputs; the synthesizer cannot issue the
promotion verdict.

The promotion review must contain a disposition for every finding. There may
be no unresolved Critical or High findings. Every Medium finding must be
fixed or explicitly accepted with owner, rationale, and follow-up.

## Presentation and documentation gates

- English is canonical; Traditional Chinese preserves heading, CTA, code
  block, link, feature, and privacy-claim parity.
- GitHub Markdown rendering is structurally valid and every public link
  returns HTTP 200.
- The dashboard is checked at 320, 390, 768, and 1440 CSS pixels, at 200%
  zoom, in light/dark/system modes, with keyboard and visible focus,
  reduced-motion behavior, and no horizontal overflow.
- Normal text meets WCAG 4.5:1. Large text and meaningful marks meet 3:1.
  Selection is not conveyed by color alone.

## Required evidence

Raw dogfood evidence is stored outside Git under `.artifact/promotion/`.
The checked-in summaries are:

- `docs/reviews/promotion-dogfood.md`
- `docs/reviews/promotion-readiness-review.md`

The root reviewer independently re-runs the gates and re-derives at least one
reported metric from canonical output before issuing a verdict.

## Publication and post-publication gates

1. Publish only the pre-verified, digest-recorded wheel and sdist bytes.
2. Publish a GitHub Release for the same tag and attach the same artifacts.
3. Verify the PyPI notice files, install command, runtime version, GitHub
   Release, project homepage, demo URL, README links, and all public assets.
4. Preserve v0.4.1 and earlier releases; disclose the wheel-notice correction
   in the changelog and v0.4.2 release notes.
5. Update the real `WenyuChiou/WenyuChiou` Profile `dist/` and README only
   after the candidate gates pass. Wait for its CI and Pages deployment, then
   verify the live dashboard and Profile assets.
6. Set the `ai-profile` GitHub homepage to the live dashboard.
7. Protect `main` with pull requests and required test/wheel-onboarding
   checks after the release branch is merged and check names are confirmed.

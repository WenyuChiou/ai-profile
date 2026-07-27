# v0.4.6 candidate dogfood evidence

Date: 2026-07-27
Candidate wheel: ai_profile_cli-0.4.6-py3-none-any.whl
SHA-256: 26227c0435d2d6a80ff8a46ad878270509b2cadeeb6d0dd78555019884239d8a

## Scope and posture

This is sealed-candidate, README-only usability evidence. Four isolated roles
received the same wheel and the canonical README. Each role was instructed not
to read source, tests, or non-README documentation, and to report commands,
exit status, stderr, time, friction, and outcome. The root reviewer reconciled
the reports and independently rechecked the candidate artifact contract and
clean-wheel smoke. Negative-access claims are necessarily role attestations;
they are not mechanically observable from a report alone.

## Gate result

| Role | Candidate digest | Outcome | Reconciled result |
| --- | --- | --- | --- |
| New user | Match | init → scan → aggregate → render completed; eight named files | PASS |
| Privacy-sensitive user | Match | aggregate_only, full, and excluded rendered to separate directories; eight files per mode; zero byte-level hits for five harmless canaries | PASS |
| Multiple-provider user | Match | One unique AI commit, two actor presences; Claude/Anthropic 1, OpenAI 1, Human-Only 1, unknown 1 | PASS |
| Profile publisher | Match | Eight files, clickable-card markup, Pages main/root and first-deploy 404 guidance understood | PASS |

All roles confirmed C:\.git was absent before creating their C-rooted
sandbox. No role reported an installation failure, configuration dead end,
privacy leak, aggregation mismatch, or Pages-preparation dead end.

## Reconciled checks

- **Onboarding:** a clean virtual environment installed the exact wheel and
  reported runtime version 0.4.6; the documented flow generated exactly
  badge-light.svg, badge-dark.svg, heatmap-light.svg, heatmap-dark.svg,
  summary-light.svg, summary-dark.svg, dashboard.html, and profile.json.
- **Privacy:** the three public-output directories were distinct. Across each
  mode's eight public files, the repository/path/message/name/email canaries
  had zero raw byte matches. The reported publication previews were
  aggregate-only 0 explicitly publishable / 1 aggregate-only, full 1 / 0,
  and excluded 0 / 0.
- **Aggregation:** one commit with two explicit actor blocks remained one
  unique AI-attributed commit and two presences. Human-Only and absent
  evidence remained distinct. Anthropic displays as Claude in the UI as a
  label-only mapping; it does not change the provider count.
- **Publishing:** the documented card markup had all five expected references;
  the profile role could derive the expected Pages URL and recovery steps from
  the README without a publication attempt.

## Findings and dispositions

| Severity | Description and evidence | Impact | Recommendation | Disposition |
| --- | --- | --- | --- | --- |
| Low | README-only/non-source compliance is an execution attestation in the four role reports rather than a runtime-enforceable control. | It limits the strength of the usability-evidence provenance, not the observed product outcomes. | Keep future role briefs scope-limited and retain raw command ledgers; do not represent the assertion as mechanically enforced. | Accepted for this evidence model. |
| Low | Two roles saw the documented warning when AIPROFILE_HOME was placed inside their temporary Git worktree; neither flow failed. | A user who chooses that layout receives avoidable noise. | Keep the README's outside-worktree guidance visible; treat a future repeated confusion report as an onboarding issue. | Accepted; no dead end reproduced. |

## Result

The four-role dogfood gate is **PASS**. It is evidence for the frozen wheel,
not authorization to tag, publish, or update the maintainer Profile. The
remaining release decision is in
[promotion-readiness-review.md](promotion-readiness-review.md).

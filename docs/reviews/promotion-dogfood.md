# v0.4.8 Public Beta promotion dogfood evidence

Date: 2026-08-01

Candidate wheel: `ai_profile_cli-0.4.8-py3-none-any.whl`

SHA-256:
`d8d307d4155f58f157ee817cdd628ef4c257287083aad66cf30e02f679fe47b6`

## Posture and acceptance rule

This is the README-only evaluation pre-registered in
`promotion-eval-spec-v048.md`. Four independent user roles received only the
English and Traditional Chinese READMEs, the exact CI-retained wheel, wheel
metadata, and a role objective. They could not inspect source or tests and did
not receive product instructions from the orchestrator.

Each role used an isolated temporary repository, venv, and `AIPROFILE_HOME`.
Raw ledgers remain unversioned because they contain local paths and synthetic
private canaries. The coordinating reviewer independently parsed the retained
`profile.json` and artifact sets rather than accepting role summaries.

Pass required:

- all four roles complete with zero outside-README product hints;
- exact candidate identity in every role;
- no installation, configuration, privacy-policy, or Pages dead end;
- zero private-canary matches in generated public artifacts;
- exact agreement with hand-derived commit, provider, evidence, and day units;
- exactly eight deterministic outputs.

## Result matrix

| Role | Result | Key evidence |
| --- | --- | --- |
| Newcomer | PASS | Install, version, `init`, `scan`, `aggregate`, and `render`; 2 commits became 1 unique AI commit, 1 presence, and 1 unknown; exact eight files |
| Privacy user | PASS | `full`, `aggregate_only`, and `excluded`; 69 role canaries and 376 independent byte comparisons produced zero public hits |
| Multi-provider user | PASS | One commit remained one unique AI commit while Claude and OpenAI produced two actor presences; unknown and human stayed separate |
| Profile publisher | PASS | Root README plus eight `dist/` outputs, clickable summary, light/dark assets, Pages main/root instructions, deterministic local publish commit |

All four roles installed the exact retained candidate wheel. No role needed a
product hint outside the READMEs.

## Verified role evidence

### Newcomer

The newcomer completed the documented sequence in a clean environment and
confirmed `aiprofile 0.4.8`. The two-commit fixture produced:

```text
commits scanned             2
unique AI-attributed        1
AI actor presences          1
human-declared              0
unknown                     1
active AI days              1
```

The rendered directory contained exactly the documented eight non-empty
files. The role initially chose a temporary directory inside an enclosing Git
worktree; the CLI emitted the documented privacy warning, and the user moved
`AIPROFILE_HOME` to a non-worktree location without outside assistance.

### Privacy user

The role created three policy classes:

| Policy | Commits | Public effect |
| --- | ---: | --- |
| `full` | 2 | Totals and two identity-redacted daily dates published |
| `aggregate_only` | 3 | Totals published; all three dates withheld |
| `excluded` | 4 | No totals, dates, providers, or evidence published |

Observed public totals were 5 scanned commits, 4 unique AI-attributed
commits, 4 actor presences, 1 unknown, and 4 active AI days. Only the two
`full` dates appeared in daily data; the aggregate-only and excluded dates did
not appear.

The role tested 69 synthetic private markers across all eight artifacts and
reported zero hits. The coordinating reviewer rebuilt 47 markers from the
fixture repositories, identities, paths, e-mails, SHAs, and trailer values,
then performed 47 x 8 = 376 byte comparisons with zero hits. The two permitted
full-mode dates were retained as positive controls.

### Multi-provider user

The three-commit oracle was:

| Commit kind | Unique AI commits | AI presences | Human | Unknown | Evidence records |
| --- | ---: | ---: | ---: | ---: | ---: |
| No explicit declaration | 0 | 0 | 0 | 1 | 1 |
| `Human-Only` | 0 | 0 | 1 | 0 | 1 |
| Anthropic plus OpenAI | 1 | 2 | 0 | 0 | 2 |

Observed values matched exactly:

```text
commits scanned             3
unique AI-attributed        1
AI actor presences          2
Claude attributed commits  1
OpenAI attributed commits  1
human-declared              1
unknown                     1
evidence records            4
active AI days              1
```

The dashboard's All AI, Claude, and OpenAI filters matched the embedded data.
The daily row stayed at one unique AI commit even though both providers had
one attributed commit. Unknown was never rewritten as human.

### Profile publisher

The first fixture was discarded because its root was inside an enclosing Git
worktree and the role ended before producing a valid publish commit. The retry
started in a verified non-worktree root and completed unassisted.

It produced exactly eight artifacts, embedded the compact badge and clickable
summary in a root Profile README, and derived the documented Pages URL from a
synthetic account/repository name. Its local `main` publish commit contained
only `README.md` and the eight `dist/` files, and the worktree was clean. The
role verified light/dark SVG references, root-case paths, dashboard CSP, and
the Pages `main` plus `/ (root)` settings. No remote was configured or mutated.

## Root-agent recomputation

The coordinating reviewer independently verified:

- all four retained `profile.json` files and every eight-file output set;
- the candidate version and wheel digest recorded by each role;
- the commit/provider/presence/human/unknown/day values above;
- full-mode dates as positive controls and aggregate-only dates as absent;
- the publisher commit's exact file membership and clean repository state;
- zero privacy-canary hits in the public artifacts.

## Findings and disposition

| Severity | Description | Impact | Recommendation | Disposition |
| --- | --- | --- | --- | --- |
| Low | The README explains `Human-Only` and the evidence order but does not explicitly say that a Human-Only declaration contributes to the aggregate `declared` evidence bucket. | A manual evidence-total check can require one extra interpretive step; the CLI output and all attribution units remain correct. | Add one glossary sentence in v0.4.9. | Accepted for v0.4.8 Public Beta; no correctness, privacy, or onboarding dead end. |

## Final result

**PASS - 4/4 required roles completed.** There were zero outside-README
product hints, zero installation/configuration/Pages dead ends, zero public
canary hits, exact aggregation agreement, and deterministic eight-file
renders. This evidence is valid only for the pinned v0.4.8 wheel above.

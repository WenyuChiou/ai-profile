# v0.4.7 Public Beta promotion dogfood evidence

Date: 2026-07-30

Candidate wheel: `ai_profile_cli-0.4.7-py3-none-any.whl`

SHA-256:
`75b896c7a1bfa462d1caa6df7025bca79650e8ad48a006272e76eb9bfb5667d8`

## Posture and acceptance rule

This is the README-only evaluation pre-registered in
[promotion-eval-spec-v047.md](promotion-eval-spec-v047.md). Each role
received only the English and Traditional Chinese READMEs, the exact
CI-retained wheel, wheel metadata, and its user objective. Source, tests,
project scripts, prior dogfood, and orchestrator product hints were
prohibited.

Each role used a separate venv, synthetic repository, and
`AIPROFILE_HOME` below `.ai/dogfood-v047/`. Raw command ledgers remain
unversioned because they contain local paths and synthetic private canaries.

Pass required:

- all four roles complete without an outside-README product hint;
- exact candidate identity in every role;
- no install, configuration, or Pages dead end;
- zero private-canary matches in generated public artifacts;
- exact agreement with hand-derived aggregation values;
- deterministic eight-file output.

## Result matrix

| Role | Result | Key evidence |
| --- | --- | --- |
| Newcomer | PASS | Install, version, `init`, `scan`, `aggregate`, and `render`; 8/8 deterministic outputs; 224 privacy comparisons, zero hits |
| Privacy user | PASS | `aggregate_only`, `full`, and `excluded`; 46/46 commands; 558 primary comparisons plus 27 exclusion comparisons, zero hits |
| Multi-provider user | PASS | One unique AI commit, two actor presences, human and unknown distinct; All AI/Claude/OpenAI filters exact |
| Profile publisher | PASS | Eight outputs, light/dark and mobile embeds, Pages main/root layout, deterministic rerender, 16 canaries with zero hits |

All four roles used the pinned wheel digest. No role required an
outside-README product instruction.

## Root-agent recomputation

The coordinating reviewer read all four raw reports and independently
checked their command ledgers and generated artifacts:

- every successful product command used the exact 0.4.7 wheel;
- each role's final `AIPROFILE_HOME` was task-local;
- the accidental harness-created `%USERPROFILE%\config.json` was removed,
  and a final filesystem check confirmed it absent;
- each complete render contained exactly the documented eight nonempty
  files;
- all reported aggregate values matched the retained `profile.json` data;
- no public output contained a repository name, path, organization, email,
  prompt, commit message, branch, salt, repository UID, or commit SHA
  canary;
- deterministic rerenders were byte-identical.

## Verified role evidence

### Newcomer

The role installed the exact wheel in a fresh Python 3.14 venv and confirmed
`aiprofile 0.4.7`. A three-commit repository produced:

```text
commits scanned             3
unique AI-attributed        1
AI actor presences          1
human-declared              1
unknown                     1
active AI days              1
```

The first and second renders were identical for all eight files. Twenty-eight
canaries across eight outputs produced `224` byte comparisons and zero hits.

### Privacy user

Three repositories exercised all publication modes:

| Mode | Behavior verified |
| --- | --- |
| `aggregate_only` | Totals retained; private activity date absent |
| `full` | Totals retained; identity-redacted daily date present |
| `excluded` | Four commits and the provider removed from every data-bearing aggregate |

Before exclusion, totals were 9 scanned / 7 AI-attributed / 7 presences.
After exclusion, totals were 5 / 3 / 3. The exact four-commit delta,
provider removal, and date behavior matched the hand-derived oracle.

Thirty-one probes across sixteen rendered assets and two aggregate previews
produced `558` byte comparisons and zero matches. A separate final exclusion
sweep produced another `27` comparisons and zero matches.

### Multi-provider user

The frozen three-commit oracle was:

| Commit kind | Unique AI commits | AI presences | Human | Unknown | Evidence records |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unknown | 0 | 0 | 0 | 1 | 1 |
| `Human-Only` | 0 | 0 | 1 | 0 | 1 |
| Anthropic + OpenAI | 1 | 2 | 0 | 0 | 2 |

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

The dashboard's All AI, Claude, and OpenAI states matched the embedded
validated data and restored correctly. The daily row remained one unique AI
commit even though both providers received one attributed commit.
Twenty-four private canaries were absent from all eight outputs.

### Profile publisher

The role generated all eight outputs, validated the six SVGs and JSON, and
created a Profile-shaped `main` repository with root `README.md` and
`dist/dashboard.html`. It verified:

- the documented clickable summary-card target;
- badge fallback references for narrow screens;
- light/dark summary, badge, and heatmap references;
- exact-case local paths;
- Pages `main` + `/ (root)` mapping;
- self-contained dashboard CSP and no remote scripts, styles, or network
  APIs.

All eight rerendered files were byte-identical. Sixteen privacy canaries had
zero hits. The exact wheel and staging dashboard hashes matched the
candidate staging manifest. Public upload remained a dry run until protected
`main` merge.

## Findings and disposition

| Severity | Description | Impact | Recommendation | Disposition |
| --- | --- | --- | --- | --- |
| Low | The READMEs do not explicitly define evidence-record and active-AI-day counting semantics. | A README-only user may initially derive evidence or active-day totals differently, although CLI labels and stored data are internally consistent. | Add a concise metric glossary in a later documentation release. | Accepted for Public Beta; no correctness or privacy defect. |
| Low | Singular synthetic data produces `1 commits contain...` and `appears in 1 unique commits` in dashboard explanatory copy. | Cosmetic grammar issue for very small histories; values and units remain unambiguous. | Add count-aware copy with renderer tests in a later patch. | Accepted to preserve the artifact-only v0.4.7 boundary. |
| Low | A deliberately repo-contained `AIPROFILE_HOME` emits a privacy warning. | Expected stderr in isolated automation, not a command failure. | Keep the warning; users should normally place the home outside a Git worktree. | Accepted; the warning enforces the documented privacy posture. |

## Final result

**PASS — 4/4 required roles completed.** There were zero outside-README
product hints, zero install/configuration/Pages dead ends, zero public-output
canary hits, exact aggregation agreement, and deterministic eight-file
renders. This evidence is valid only for the pinned v0.4.7 wheel.

# v0.4.6 R5 promotion dogfood evidence

Date: 2026-07-30

Candidate wheel: `ai_profile_cli-0.4.6-py3-none-any.whl`

SHA-256: `84aa13766c70ad082fe70e4e860f2b15f77472826abbc579531376d5cdc4bcdb`

## Posture and acceptance rule

This is the fresh R5 README-only evaluation pre-registered in
[promotion-eval-spec-v046-r5.md](promotion-eval-spec-v046-r5.md). R4 failed
because overlapping provider counts were presented with an ambiguous
accessible label. No R4 role or artifact counts toward R5.

Each R5 role received only `README.md`, the exact CI-retained wheel, and its
role objective. Each used a fresh repository, venv, and explicit
task-specific `AIPROFILE_HOME` under `C:\Windows\Temp`; source, tests, other
project docs, prior dogfood, and orchestrator product hints were prohibited.
Raw command ledgers are retained in `.ai/dogfood-051-*.md` and are
intentionally unversioned because they contain local temporary paths.

Pass required all four roles, zero outside-README product hints, zero
installation or configuration dead ends, zero public-asset canary hits, exact
hand-derived aggregate agreement, and honest overlap-qualified accessible
wording.

## Role matrix

| Role | Exact wheel | Isolation | Result | Counts toward R5 |
| --- | --- | --- | --- | --- |
| Newcomer | Match | Fresh repo, venv, and explicit home | Install, version, `init`, `scan`, `aggregate`, `render`; eight outputs | Yes |
| Privacy user | Match | Three fresh repos and homes | `aggregate_only`, `full`, and `excluded`; 24 outputs; zero canary hits | Yes |
| Multi-provider user | Match | Fresh three-commit repo | One unique AI commit, two actor presences, human and unknown distinct | Yes |
| Profile publisher | Match | Fresh Profile-shaped repo | Eight deterministic outputs, theme pairs, clickable card, Pages dry run | Yes |

## Root-agent recomputation

The coordinating reviewer independently read every raw ledger and recomputed
the acceptance values rather than relying only on agent verdicts:

- all four observed wheel hashes equal the pinned R5 digest;
- every successful product invocation used a sandbox-local
  `AIPROFILE_HOME`;
- `C:\Users\wenyu\config.json` was absent before and after R5;
- each role generated exactly the documented eight nonempty outputs;
- no role needed an outside-README product hint;
- no role reported a product blocker.

## Verified role evidence

### Newcomer

The user installed the exact wheel in a fresh Python 3.14 venv, confirmed
`aiprofile 0.4.6`, and completed the README quickstart. Two commits produced
two scanned commits, one unique AI-attributed commit, one actor presence, and
one honest unknown commit. The output directory contained exactly:

```text
badge-dark.svg
badge-light.svg
dashboard.html
heatmap-dark.svg
heatmap-light.svg
profile.json
summary-dark.svg
summary-light.svg
```

All product commands exited 0 with empty stderr.

### Privacy user

The privacy role exercised three independent configurations:

| Mode | Published totals | Daily data | Output count |
| --- | --- | --- | ---: |
| `aggregate_only` | Anonymous aggregate retained | Empty | 8 |
| `full` | Explicitly publishable aggregate retained | One identity-redacted daily row | 8 |
| `excluded` | All totals zero | Empty | 8 |

Twenty-one distinct canaries covered repository name, path, organization,
commit message, email, prompt, and URL across all three modes. The role
performed exact UTF-8 byte-subsequence searches over every output:

```text
24 artifacts × 21 canaries = 504 comparisons
canary hits = 0
```

The public JSON and assets contained only the intended aggregate schema.
Local CLI status output displayed sandbox paths, the synthetic identity, and
the synthetic repository display name; none entered public artifacts.

### Multi-provider user

The hand-derived three-commit fixture was:

| Commit kind | Unique commits | AI presences | Human | Unknown | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unknown | 1 | 0 | 0 | 1 | 1 |
| `Human-Only` | 1 | 0 | 1 | 0 | 1 |
| Anthropic + OpenAI | 1 | 2 | 0 | 0 | 2 |

Generated values matched exactly:

```text
commits scanned             3
unique AI-attributed        1
AI actor presences          2
human-declared              1
unknown                     1
providers                   2
evidence records            4
```

The daily row preserved `ai_commits = 1` while the Anthropic and OpenAI
provider rows each reported one attributed commit. `profile.json` and the
dashboard's embedded data remained semantically identical. Both summary SVGs
used:

```text
peak day summed provider-attributed count 2; provider counts may overlap
```

The number two was never presented as a unique-commit count.

### Profile publisher

The publisher generated exactly eight outputs and then rendered again into
the same directory. All eight SHA-256 values were unchanged. All six SVGs
were valid XML, the light/dark pairs were distinct, `profile.json` parsed,
and the dashboard was self-contained.

The README's clickable-card HTML was copied verbatim with only `USERNAME`
replaced. A synthetic `main` branch contained root `README.md` and
`dist/dashboard.html`; a local root server returned HTTP 200 for
`/dist/dashboard.html`. The documented Pages source (`main`, `/ (root)`),
case-sensitive URL, deployment-wait step, and 404 recovery checklist were
actionable without publication or external hints.

## Friction and disposition

| Severity | Evidence | Impact | Recommendation | Disposition |
| --- | --- | --- | --- | --- |
| Low | Windows PowerShell 5.1 displayed some UTF-8 punctuation as mojibake in three raw ledgers. GitHub's Markdown API rendered both canonical READMEs successfully. | Cosmetic terminal-reading friction only; commands and GitHub onboarding remained readable. | Keep UTF-8 canonical files and favor current PowerShell/terminal hosts in support guidance. | Accepted for Public Beta; no product-byte change. |
| Low | The summary SVG accessible sentence does not singularize count nouns (`1 ... commits`, `1 ... days`). | Minor screen-reader copy polish; units and values remain unambiguous. | Add count-aware grammar in a later renderer release with snapshot coverage. | Accepted for Public Beta; tracked as post-beta polish. |
| Low | `human_declared_commits` is distinct in JSON/dashboard data but lacks its own visible dashboard tile. | Users relying only on the dashboard cannot directly read that secondary total, although unknown is never classified as human. | Consider a human-declared secondary metric in a future visualization iteration. | Accepted; not an aggregation or privacy defect. |
| Low | Normal local `init`, `scan`, and `render` status lines can contain local paths, configured identity, repository display name, or output path. | Safe for the local-first workflow and absent from public assets, but users should not paste raw terminal logs publicly without review. | Clarify the distinction between sanitized parse diagnostics and normal local operational output in a future privacy-doc update. | Accepted for Public Beta; public-output guarantee verified independently. |

## R5 result

**PASS — 4/4 required R5 roles completed.** There were zero outside-README
product hints, zero installation/configuration/Pages dead ends, zero privacy
canary hits, exact aggregation agreement, and honest overlap-qualified
accessible wording. This evidence is valid only for the pinned R5 wheel.

# Landscape and non-duplication audit

Status: Phase 0 deliverable, 2026-07-14.

Method: four parallel web-research lanes (existing attribution tools; exact
tool attribution strings; profile-stats/SVG generators; git-native
mechanisms), followed by an adversarial verification pass over every
claim destined for the normalization registry, using primary sources only
(official docs, tool source code, GitHub API bot-account lookups, GitHub
commit-search counts). The verifier refuted 8 research claims before they
could reach code; only confirmed strings seed `registry.py` (ADR-013).
Commit counts below are GitHub search-index approximations as of
2026-07-14 and will drift.

## 1. Existing AI attribution tools

| project | what it solves | level | provenance format | license / status |
|---|---|---|---|---|
| **git-ai** (git-ai-project/git-ai, usegitai.com) | line-level AI attribution: hooks, checkpoints, `git ai blame/stats`; versioned "Git AI Authorship Standard" (schema `authorship/3.0.0`); documented rebase/merge/amend semantics | repository (cross-repo only in paid "Teams") | JSON in `refs/notes/ai` (+ `refs/notes/ai-stash`) | Apache-2.0; ~2.3k stars; very active (pushed 2026-07-14) |
| **Agent Blame** (mesa-dot-dev/agentblame) | AI blame layer per repo/PR (browser extension) | repository / PR | `refs/notes/agentblame` | Apache-2.0; 97 stars; last push 2026-05 |
| **whogitit** (dotsetlabs) / **blameprompt** (Ekaanth) | niche line/commit AI tracking | repository | git notes (schemas unverified) | MIT; single-digit stars |
| **BlamePrompt** hosted (blameprompt.com) | closest conceptual analog: profile-level AI score/badges/leaderboard | profile | `refs/notes/blameprompt` synced to a **hosted backend + login** | hosted; not local-first |
| **Agent Trace** (Cursor RFC) | storage-agnostic JSON trace-record spec (human/ai/mixed/unknown) | n/a (spec) | draft RFC, no shipping ingestable format yet | license unknown |

Ruled out as irrelevant after checking: GitButler and JetBrains AI
(generate commit *messages*, store no attribution), Graphite Diamond (AI
review), ai4curation/ai-blame (name collision — scientific data curation).

**Consequences for this project** (already reflected in the ADRs):

- Line-level attribution is a solved, actively-maintained problem
  (git-ai). We must not reimplement it (proposal §2: "must not duplicate
  Git AI's line-level attribution engine"); the future importer maps
  git-ai notes → ACE `imported` events (ADR-008 tier exists for exactly
  this).
- The only free, local-first, cross-repository, explicit-provenance
  profile aggregation with README-embeddable assets is **unclaimed
  territory**. BlamePrompt reaches profile level but is hosted,
  login-gated, and gamified; git-ai reaches cross-repo only in a paid team
  product.
- `refs/notes/ai` (git-ai), `refs/notes/agentblame`, `refs/notes/blameprompt`
  are taken; our reserved `refs/notes/ai-collaboration` (ADR-006) collides
  with nothing. git-appraise's `refs/notes/devtools/*` namespace design is
  the strongest production precedent for notes-based metadata.

## 2. AI tool commit-attribution conventions (registry ground truth)

Three git fields carry attribution in the wild — commit-message trailers,
the author field, and the committer field. A trailer-only parser misses
the author-field cases (see §2.3).

### 2.1 Verified identities → v0.1 registry seeds

Every row below survived adversarial verification against primary sources
(tool source code, official docs, GitHub bot-account API, real commits).
Matching is **email-anchored and case-insensitive** (display names drift
across versions; `Co-Authored-By:` vs `Co-authored-by:` casing varies).

| co-author email (exact) | display name(s) observed | → provider / tool | evidence |
|---|---|---|---|
| `noreply@anthropic.com` | "Claude", "Claude <model> <ver>" (interpolated) | anthropic / claude-code | source conditional quoted in anthropics/claude-code#66602; ~2.56M commits |
| `noreply@openai.com` | "Codex" | openai / codex-cli | literal `DEFAULT_ATTRIBUTION_VALUE` in openai/codex#11617 (feature default-OFF) |
| `cursoragent@cursor.com` | "Cursor" (~2.68M), "Cursor Agent" (~848K) | cursor / cursor | Cursor staff forum reply; commit search |
| `copilot@github.com` | "Copilot" | github / copilot | vscode git extension `package.json` (`git.addAICoAuthor`, default off); ~350K commits |
| `223556219+Copilot@users.noreply.github.com` | "Copilot" | github / copilot | fixed global bot account (GitHub API); ~2.37M commits; also auto-added by copilot-sdk |
| `198982749+Copilot@users.noreply.github.com` | "Copilot" | github / copilot | fixed global bot account (GitHub API); ~362K commits |
| `aider@aider.chat` | `aider (<provider/model>)` | aider / aider | ~108K commits (fills the docs gap; NOT the `noreply@aider.dev` from issue #3788) |
| `roomote@roocode.com` | "Roo Code" | roo-code / roo-code | ~21.7K commits (Roo Code Cloud "Roomote") |
| `openhands@all-hands.dev` | "openhands" | openhands / openhands | ~130K commits |
| `158243242+devin-ai-integration[bot]@users.noreply.github.com` | "devin-ai-integration[bot]" | cognition / devin | bot ID via GitHub API; ~61.7K commits — note the **required** `158243242+` prefix |
| `161369871+google-labs-jules[bot]@users.noreply.github.com` | "google-labs-jules[bot]" | google / jules | bot ID via GitHub API; ~183K commits |
| `176961590+gemini-code-assist[bot]@users.noreply.github.com` | "gemini-code-assist[bot]" | google / gemini-code-assist | bot ID via GitHub API |
| `gemini-cli@google.com` | "Gemini CLI" | google / gemini-cli | de facto observed form (within ~242K "Gemini" trailer commits); no official convention (google-gemini/gemini-cli discussion #11447 unanswered) |
| `cascade@windsurf.ai`, `cascade@windsurf.com` | "Windsurf Cascade", "Cascade" | windsurf / windsurf | low volume (~960); automation-origin unconfirmed but explicit declaration either way |
| `amazon-q@amazon.com` | "Amazon Q" | amazon / amazon-q | ~2.6K commits; automation-origin unconfirmed |

Conditional entry: `noreply@google.com` with display name starting
"Gemini" → provider google, tool null (the bare email cannot identify a
specific tool; name-prefix guard required — it is a generic Google
address, so email-only matching would over-claim). ADR-013 supports this
as a per-entry display-name-prefix condition on top of exact email
matching.

**Excluded from the registry, deliberately:** `gitbutler@gitbutler.com`
(GitButler's own committer identity on workspace/integration commits —
matching it as AI would mis-attribute non-AI automation); "Cline"
(no consistent tool-branded identity exists; the ~7K "Co-authored-by:
Cline" hits are inconsistent human-typed strings).

Tools with **no shipped attribution signal** (confirmed absences):
Copilot CLI (open feature request github/copilot-cli#1455 — though the
Copilot *SDK* auto-appends the 223556219 trailer), Cline, Amazon Q as
IDE-default. These validate the design stance: where no explicit signal
exists, commits stay `unknown` — never inferred.

External corroboration of the whole approach: Liu et al., "Debt Behind
the AI Boom" (arXiv:2603.28592) mined 302.6K AI-authored commits using
exactly these four signal classes (actor logins, author emails, author
names, co-author trailers) across 29 tools — explicit git metadata, no
style inference.

### 2.2 Declared-trailer conventions (parse targets)

No ratified cross-industry standard trailer exists. Confirmed policies:
Linux kernel and Fedora use `Assisted-by:` (kernel: AI must not add
`Signed-off-by:`); OpenInfra uses `Assisted-By:`/`Generated-By:` two-tier;
Apache recommends `Generated-by:`. Proposals without consensus:
`Coding-Agent:` + `Model:`, `AI-assistant:`, percentage-tiered schemes.

v0.1 parses our own explicit `AI-*` convention (ADR-005) plus the §2.1
co-author registry. `Assisted-by:`/`Generated-by:` parsing is a natural
post-v0.1 addition (same `declared` evidence tier, same event shape).
One warning from the field: at least one scheme reuses `Co-authored-by:`
itself for AI tiers, and GitHub/GitLab define it as human co-authorship —
which is why our registry matches **exact known-AI emails only** and
never treats co-author trailers as AI per se.

### 2.3 Known v0.1 blind spot (documented limitation)

GitHub Copilot cloud agent authors commits itself (human as co-author,
GitHub docs confirmed); Devin and Jules have bot-as-author modes (Jules'
default). ADR-015 counts commits by **the user's author email**, so
bot-*authored* commits are skipped in v0.1 even though the user drove
them. This is recorded in mvp.md §9; the post-v0.1 fix is co-author-based
identity inclusion (count commits where the *user* appears as co-author),
which needs the GitHub-noreply email mapping and more care — deferred.

## 3. GitHub profile statistics and README SVG generators

| project | displays | level | rendering | license |
|---|---|---|---|---|
| anuraghazra/github-readme-stats | commits/PRs/stars/languages cards | profile | hosted serverless (Vercel), themes | MIT |
| lowlighter/metrics | plugin-based mega-card | profile | Action / hosted; shared renderer entrypoint | MIT |
| DenverCoder1/github-readme-streak-stats | streaks | profile | hosted serverless (PHP) | MIT |
| star-history | star growth charts | repository | hosted + npm | MIT |
| Platane/snk | contribution snake | profile | Action/CLI, no server | **no LICENSE found** — treat all-rights-reserved |
| github-profile-trophy | trophy gamification | profile | hosted serverless | MIT |
| jstrieb/github-stats | stats, JSON+SVG dual output | profile | **Action-only, no server** — closest architectural analog | **GPLv3 — reference-only, no code reuse** |
| waka-readme | WakaTime coding-time | profile | Action | MIT |

None of these touch AI attribution. The only AI-stats prior art found:
two **repo-level** AI-commit-percentage badges (ai-ecoverse/
vibe-coded-badge-action; "Hand Crafted Badge") — both **heuristic**
(message pattern-matching / blame heuristics), both single-repo, both
shields.io badges. The profile-level, cross-repo, explicit-provenance
gap is confirmed open.

Reusable patterns adopted (ADR-010, mvp.md): small closed theme-token
vocabulary (title/text/bg/border roles); pure-function
`(data, theme) → SVG` renderer decoupled from front-ends; JSON alongside
SVG as first-class output (jstrieb precedent); `<picture>` +
`prefers-color-scheme` embedding (snk precedent) — with
`#gh-dark-mode-only` URL anchors as a fallback technique.

Not reproduced: generic commit/star/PR/language/streak stats, trophies,
time tracking — GitHub already has native and third-party coverage; our
cards show only AI-collaboration metrics.

## 4. Git-native mechanisms (implementation ground truth)

- **Trailers:** `%(trailers:only,unfold)` requires git ≥ 2.17;
  `key=`/`valueonly` filtering requires ≥ 2.22 (pinned by diffing 2.21 vs
  2.22 docs). ADR-005 therefore parses trailer lines in Python from the
  portable ≥2.17 form (validated locally on git 2.47.1). Trailer-block
  detection uses git's 25%-trailer heuristic — mixed prose blocks are a
  real edge case; fixtures cover it.
- **Co-authored-by:** GitHub credits co-authors when the email matches an
  account email (noreply addresses recommended); GitLab supports the same
  trailer. Human co-authorship semantics — see §2.2 warning.
- **Git Notes:** NOT fetched/pushed by default (adoption barrier for any
  notes-based interop — needs explicit refspec); GitHub displayed notes
  2010–2014, then removed the UI entirely; notes are invisible on GitHub
  today. Production namespace precedent: git-appraise `refs/notes/devtools/*`.
  This confirms trailers-first for v0.1 portability and notes as the
  richer, later channel (ADR-006).

## 5. Licensing and interoperability considerations

- Our reuse targets are data formats, not code, in v0.1: parsing *our own*
  trailer convention plus public co-author strings has no licensing
  surface. The future git-ai importer reads an Apache-2.0 tool's notes
  format — schema reimplementation for interop is fine; if code is ever
  vendored, Apache-2.0 is compatible with MIT distribution
  (attribution + NOTICE obligations).
- jstrieb/github-stats (GPLv3) and Platane/snk (no license) are
  architectural references only; no code may be copied from either.
- The Git AI Authorship Standard is versioned (`authorship/3.0.0`); the
  importer must pin the versions it understands and mark others
  unsupported loudly (consistent with ADR-012's posture).

## 6. Non-duplication matrix

| existing project | already solves | level | provenance format | reusable component | we must NOT reproduce | remaining gap we address |
|---|---|---|---|---|---|---|
| git-ai | line-level AI attribution, hooks, blame/stats, rewrite semantics | repo (paid: org) | `refs/notes/ai` JSON, versioned standard | future import source (`imported` tier) | line-level attribution engine, checkpoint hooks | free local cross-repo profile aggregation + README assets |
| Agent Blame | AI blame on PRs | repo/PR | `refs/notes/agentblame` | potential future import source | PR blame UI | profile-level aggregation |
| BlamePrompt (hosted) | profile AI score/badges | profile | notes + hosted backend | concept validation only | hosted backend, login, gamification | local-first, no-signup, no-upload, honest metrics |
| Agent Trace RFC | trace-record spec | spec | draft JSON spec | vocabulary cross-check (human/ai/mixed/unknown matches ACE) | n/a (not shipping) | a shipping local pipeline |
| github-readme-stats / metrics / streak-stats / trophy | generic profile stats cards | profile | GitHub API | theme tokens, card layout conventions | generic commit/language/streak stats | AI-collaboration dimension |
| jstrieb/github-stats | Action-only JSON+SVG stats | profile | GitHub API | architecture pattern (GPLv3 — pattern only) | generic stats | AI provenance |
| Platane/snk | contribution snake | profile | GitHub API | `<picture>` embedding pattern | novelty calendar art | n/a |
| star-history | star charts | repo | GitHub API | none | star analytics | n/a |
| vibe-coded-badge-action / Hand Crafted Badge | repo-level AI % badge | repo | **heuristic** message matching | none (heuristics are what we refuse to do) | heuristic AI detection | explicit-evidence-only, profile-level |
| aider/claude-code/cursor/copilot/… conventions | emitting attribution | n/a | trailers / author fields | **input formats** (§2.1 registry) | emitting tools' own attribution | consuming + aggregating them |

## 7. Unverified-claims ledger (honesty record)

Excluded from the registry and from any code path until verified; kept
here so future work starts from the known frontier: Aider's
`--attribute-co-authored-by` literal (docs confirm the flag; the observed
`aider (<provider/model>) <aider@aider.chat>` form is what we registered);
Jules' sole-author literal author string; whether Codex's
`commit_attribution` has graduated from default-off; Windsurf/Amazon Q/
GitButler automation-origin; whogitit/blameprompt exact schemas; the
allthingsopen.org `Assisted-by` tiered scheme (source 403'd — secondhand);
OpenTelemetry/Rocky Linux policies (same source); GitHub noreply email
format on an official page; git 1.8.5/2.32 trailer-tooling intro versions;
the arXiv:2603.28592 replication package's full 29-tool rule list (good
future registry source: github.com/yueyueL/tech-debt-ai-coding);
Platane/snk license (negative result, could be stale).

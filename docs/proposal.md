# AI Profile: Profile-Level AI Collaboration Analytics for GitHub

## 1. Project objective

Build a lightweight, local-first open-source tool that records, aggregates, and visualizes how different AI coding tools contribute across a developer’s entire GitHub profile.

The project operates at the GitHub account level rather than the individual repository level.

The intended workflow is:

1. A developer installs or enables the tool.
2. The tool collects AI contribution metadata from authorized repositories and local development records.
3. Contributions are normalized into a common schema.
4. Profile-level statistics are generated across all repositories.
5. Static SVG assets and JSON summaries are produced.
6. The user embeds the generated assets in a GitHub Profile README.
7. Public and private contribution data are handled separately through explicit privacy rules.

The project should feel similar to GitHub contribution graphs, Star History, and GitHub Readme Stats, but focus specifically on human–AI collaboration history.

---

## 2. Product positioning

This project is not primarily:

- an AI code detector;
- a replacement for Git blame;
- a line-level attribution engine;
- a token usage tracker;
- a repository-only analytics dashboard;
- an AI coding assistant;
- a large SaaS platform.

This project is:

> A profile-level aggregation and visualization layer for AI-assisted software development.

Its unique contribution is:

> Cross-repository, profile-level aggregation and public presentation of verifiable human–AI development collaboration history.

The system should reuse existing provenance sources when available, including Git trailers, Git Notes, Git AI metadata, local AI session logs, and manual declarations.

It must not duplicate Git AI’s line-level attribution engine.

---

## 3. Core design principles

### 3.1 Local-first

Raw prompts, code, transcripts, file contents, and private repository names remain on the user’s machine unless remote synchronization is explicitly enabled.

The default workflow requires no hosted database.

### 3.2 Attribution, not detection

Do not infer AI authorship from code style or source-code patterns.

Only record AI participation when supported by explicit provenance evidence.

### 3.3 Profile-level aggregation

The system aggregates activity across:

- all public repositories;
- authorized private repositories;
- repositories owned by the user;
- repositories to which the user contributed;
- optionally, authorized organization repositories.

### 3.4 Adapter-based interoperability

The project must support multiple tools and evidence formats through adapters.

Potential sources include:

- Git trailers;
- Git Notes;
- Git AI metadata;
- Claude Code;
- Codex CLI;
- Gemini CLI;
- GitHub Copilot;
- Cursor;
- Cline;
- Roo Code;
- Aider;
- OpenHands;
- manual declarations;
- future AI development tools.

### 3.5 Privacy by design

Private contribution counts may be included in aggregate statistics without exposing:

- repository names;
- organization names;
- commit messages;
- branch names;
- file paths;
- prompts;
- diffs;
- session content.

### 3.6 Honest uncertainty

Historical records without sufficient evidence must be labeled `unknown`.

Do not automatically classify unknown records as human.

---

## 4. Historical attribution limits

Existing commits can only be reconstructed when historical evidence exists.

Reliable or partially reliable evidence may include:

- AI-specific Git trailers;
- `Co-authored-by` entries;
- Git Notes;
- Git AI attribution data;
- local AI session records;
- bot accounts;
- pull-request descriptions;
- known AI-generated branches;
- explicit manual declarations.

When no evidence exists, the record should be:

```yaml
actor:
  type: unknown

provenance:
  evidence_level: unknown
```

Do not use an LLM classifier to guess which provider generated a historical commit.

---

## 5. High-level architecture

```text
AI tools and Git repositories
            │
            ▼
     Provenance collectors
            │
            ▼
      Source adapters
            │
            ▼
      Normalization layer
            │
            ▼
     Local event database
            │
            ▼
    Profile aggregation engine
            │
            ▼
  Visualization data contract
            │
            ├── JSON export
            ├── Static SVG cards
            ├── Contribution calendars
            └── Optional web dashboard
```

Recommended source modules:

```text
src/
  collectors/
  adapters/
  schema/
  storage/
  aggregate/
  privacy/
  visualization/
  render/
```

### Module responsibilities

#### `collectors/`

Discover repositories and retrieve Git and AI-tool evidence.

#### `adapters/`

Convert provider-specific records into the common schema.

#### `schema/`

Define canonical event models, validators, controlled vocabularies, and schema migrations.

#### `storage/`

Persist normalized events and scan state in SQLite.

#### `aggregate/`

Generate daily, monthly, provider-level, model-level, tool-level, and profile-level summaries.

#### `privacy/`

Apply repository and event publication rules.

#### `visualization/`

Define renderer-neutral profile statistics and visual data contracts.

#### `render/`

Generate SVG cards, calendars, timelines, and JSON assets.

---

## 6. Canonical schema

Create a versioned schema named **AI Collaboration Event**, abbreviated as **ACE**.

A single ACE event represents an attributable human or AI participation event associated with a software-development artifact.

Example:

```yaml
schema_version: "0.1.0"

event_id: "ace_01JXYZ..."
recorded_at: "2026-07-14T08:30:00-04:00"

actor:
  type: "ai"
  provider: "anthropic"
  model: "claude-sonnet"
  tool: "claude-code"
  agent_name: null

human:
  github_login: "WenyuChiou"
  role: "owner"
  reviewed: true

activity:
  type: "commit"
  role:
    - "implementation"
    - "documentation"
  contribution_mode: "ai_assisted"
  timestamp: "2026-07-14T08:22:12-04:00"

git:
  repository_id: "github:123456789"
  repository_visibility: "private"
  repository_name_hash: "sha256:..."
  commit_sha: "abc123..."
  branch: null
  parent_event_ids: []

metrics:
  commits: 1
  files_changed: 4
  additions: 86
  deletions: 21
  ai_lines_added: null
  retained_ai_lines: null

provenance:
  source_type: "git_trailer"
  source_tool: "claude-code"
  source_reference: null
  evidence_level: "declared"
  confidence: 1.0

privacy:
  publication_level: "aggregate_only"
  expose_repository: false
  expose_model: true
  expose_commit: false
  expose_metrics: true

integrity:
  content_hash: "sha256:..."
  signature: null
```

---

## 7. Controlled vocabularies

### 7.1 Actor types

```text
human
ai
mixed
unknown
```

Use `mixed` when meaningful human and AI work exist in the same commit but cannot be separated reliably.

### 7.2 Contribution modes

```text
ai_generated
ai_assisted
ai_reviewed
human_reviewed_ai
human_only
unknown
```

### 7.3 Activity types

Initial MVP:

```text
commit
pull_request
review
issue
documentation
test
refactor
other
```

Only `commit` is required for v0.1.

### 7.4 Evidence levels

```text
verified
declared
imported
inferred
unknown
```

Definitions:

- `verified`: emitted directly by an integrated tool or signed hook;
- `declared`: supplied through a trailer or explicit user command;
- `imported`: converted from a trusted external attribution system;
- `inferred`: reconstructed from weaker historical evidence;
- `unknown`: no reliable evidence exists.

Inferred records must be shown separately from verified records.

---

## 8. Git-native metadata

Use Git trailers as the simplest portable attribution format.

Example:

```text
feat: add profile-level contribution aggregation

AI-Provider: Anthropic
AI-Model: Claude-Sonnet
AI-Tool: Claude-Code
AI-Role: Implementation
AI-Mode: AI-Assisted
AI-Reviewed-By: Human
AI-Schema: ACE/0.1
```

Git trailers can be parsed using:

```bash
git interpret-trailers
```

For richer metadata, support Git Notes under:

```text
refs/notes/ai-collaboration
```

Recommended storage rules:

- Git trailers: small, visible, portable declarations;
- Git Notes: richer structured metadata;
- local logs: sensitive session evidence;
- public profile assets: aggregate statistics only.

---

## 9. Event capture workflow

Suggested CLI name:

```bash
aiprofile
```

Initial commands:

```bash
aiprofile init
aiprofile install-hooks
aiprofile scan
aiprofile import
aiprofile reconcile
aiprofile aggregate
aiprofile render
aiprofile privacy-preview
aiprofile doctor
```

Recommended future-commit flow:

```text
AI tool edits files
       │
       ▼
Adapter records session evidence
       │
       ▼
User creates commit
       │
       ▼
prepare-commit-msg or post-commit hook
       │
       ▼
ACE metadata attached
       │
       ▼
Local event database updated
```

The project must not claim AI participation merely because an AI extension is installed.

An adapter must observe an actual edit, generation, review, or explicit declaration.

---

## 10. Historical import strategy

### Tier A: Strong evidence

Automatically import:

- Git AI Notes;
- standardized AI Git Notes;
- recognized AI trailers;
- signed adapter records;
- provider session logs mapped to a commit;
- AI-specific bot authors.

Classification:

```text
verified
declared
imported
```

### Tier B: Moderate evidence

Examples:

- `Co-authored-by: Claude`;
- explicit `[Claude]`, `[Codex]`, or similar prefixes;
- PR descriptions naming an AI tool;
- known AI-generated branches;
- tool-generated commit metadata.

Classification:

```text
declared
inferred
```

### Tier C: No evidence

Use:

```text
unknown
```

### Manual reconciliation

Provide:

```bash
aiprofile reconcile --since 2025-01-01
```

Allow users to classify uncertain commits as:

```text
Claude
Codex
ChatGPT
Gemini
Human
Mixed
Unknown
```

Manual assignments must retain:

```yaml
source_type: manual_declaration
evidence_level: declared
```

---

## 11. Public and private repository modes

### Mode 1: Public-only

Scan public GitHub repositories.

Use anonymous access or a minimal GitHub token.

Limitations:

- no private repositories;
- lower rate limits;
- incomplete organization access.

### Mode 2: Local private mode

Scan repositories already cloned on the user’s computer.

No private repository metadata is uploaded.

Only aggregate values may be published.

Example:

```json
{
  "date": "2026-07-14",
  "provider": "anthropic",
  "private_commits": 4
}
```

This should be the default private-repository workflow.

### Mode 3: GitHub App mode

Optional later-phase integration.

The GitHub App may be installed on selected repositories or all authorized repositories.

Request only minimal permissions:

```text
Repository contents: Read-only
Metadata: Read-only
```

Use installation tokens instead of broad classic personal access tokens.

---

## 12. Privacy publication levels

Each repository or event supports:

```text
full
repository_anonymous
aggregate_only
excluded
```

### `full`

May expose:

- repository name;
- provider;
- model;
- date;
- commit link;
- selected metrics.

### `repository_anonymous`

May expose:

- provider;
- model;
- date;
- metrics;
- anonymous repository ID.

Must not expose repository name or URL.

### `aggregate_only`

May expose only date- or provider-level totals.

### `excluded`

Must not appear in public output.

Recommended defaults:

```text
public repository  → full
private repository → aggregate_only
```

---

## 13. Local storage

Use SQLite for v0.1.

Suggested tables:

```text
repositories
commits
collaboration_events
actors
provenance_sources
daily_aggregates
sync_state
privacy_rules
schema_migrations
```

Do not store full prompts or transcripts by default.

References to external logs may be stored only when explicitly enabled.

---

## 14. Cross-repository discovery

### Local discovery

Allow configured search paths:

```text
~/projects
~/github
~/work
```

Command example:

```bash
aiprofile add-path ~/work
```

### GitHub discovery

Use the GitHub API to discover authorized repositories.

For each repository:

1. store the stable GitHub repository ID;
2. retrieve commits incrementally;
3. inspect trailers;
4. retrieve supported Git Notes;
5. map commits to the configured GitHub identity;
6. import adapter-specific attribution;
7. apply privacy rules;
8. update aggregate statistics.

Avoid complete rescans on every run.

---

## 15. Aggregation rules

### 15.1 Unique attributed commits

Number of unique commits with supported AI provenance.

### 15.2 Participation events

A single commit may contain several AI participation events.

Example:

```text
Claude implements.
Codex reviews.
Human edits and commits.
```

Count as:

```text
1 unique commit
2 AI participation events
1 human review event
```

### 15.3 Active days

Count dates on which at least one qualifying collaboration event occurred.

### 15.4 Provider-attributed commits

A commit may be attributed to more than one provider in participation views.

Do not add provider totals together and call the result unique commits.

### 15.5 Lines of code

Render LOC statistics only when reliable line-level attribution exists.

Do not estimate AI LOC from whole-commit additions.

### 15.6 Unknown is separate from human

Never fold unknown commits into human activity.

---

## 16. Visualization goals

Build a polished but lightweight visualization layer that transforms verified profile-level statistics into clear, attractive, and shareable GitHub assets.

Visualization must remain secondary to attribution correctness.

The renderer must not query repositories directly or independently recalculate attribution.

```text
ACE events
   ↓
Validated aggregates
   ↓
Visualization data contract
   ↓
SVG / JSON / optional dashboard
```

---

## 17. Visualization data contract

Example:

```json
{
  "period": {
    "from": "2026-01-01",
    "to": "2026-12-31"
  },
  "summary": {
    "unique_commits": 486,
    "ai_attributed_commits": 312,
    "participation_events": 391,
    "active_days": 142
  },
  "providers": [
    {
      "provider": "anthropic",
      "display_name": "Claude",
      "attributed_commits": 182,
      "participation_events": 211,
      "active_days": 94
    }
  ]
}
```

All renderers should use the same normalized profile statistics.

---

## 18. Primary visualizations

### 18.1 AI Collaboration Summary Card

Required metrics:

- unique commits;
- AI-attributed commits;
- AI participation events;
- active collaboration days;
- number of AI providers;
- public activity;
- private aggregate-only activity;
- unknown commits.

Example:

```text
AI Collaboration · 2026

312 AI-attributed commits
391 AI participation events
142 active days

Claude        182
Codex          71
Gemini         34
ChatGPT        25

Private activity included anonymously
```

The metric definition must always be explicit.

### 18.2 Provider Contribution Calendar

GitHub-style daily heatmap.

Views:

```text
all
claude
codex
chatgpt
gemini
human
mixed
unknown
```

Generate separate static assets:

```text
calendar-all.svg
calendar-claude.svg
calendar-codex.svg
calendar-chatgpt.svg
calendar-gemini.svg
calendar-human.svg
calendar-unknown.svg
```

Default heatmap intensity:

```text
unique attributed commits per day
```

Optional configurable metrics:

```text
participation events
active sessions
retained AI lines
```

Do not combine different metrics in one heatmap.

### 18.3 Provider Breakdown

Use horizontal ranked bars by default.

Support grouping by:

```text
provider
model
tool
contribution mode
activity role
evidence level
```

Example:

```text
Claude        182  58.3%
Codex          71  22.8%
Gemini         34  10.9%
ChatGPT        25   8.0%
```

### 18.4 Monthly Collaboration Timeline

Show changes in provider usage over time.

Requirements:

- complete monthly buckets;
- months with no activity shown as zero;
- provider filters;
- count and percentage modes;
- current-year and custom-range views.

### 18.5 Attribution Quality Card

Show:

```text
verified
declared
imported
inferred
unknown
```

Example:

```text
Attribution quality

Verified       174
Declared        96
Imported        42
Inferred        18
Unknown        106
```

### 18.6 Public and Private Activity Card

Example:

```text
Contribution sources

Public repositories               228
Private repositories, anonymized   84
Excluded repositories               6
```

### 18.7 Collaboration History

Show deterministic milestones rather than every commit.

Examples:

```text
2025-08
First verified Claude contribution

2025-11
Codex added as a collaboration tool

2026-02
100th AI-attributed commit

2026-05
First multi-AI commit

2026-07
Private aggregation enabled
```

Possible event types:

```text
first_provider_use
first_verified_event
provider_added
provider_became_primary
milestone_commit_count
first_multi_ai_commit
private_aggregation_enabled
schema_version_changed
```

Do not use an LLM to invent milestone events.

---

## 19. README layout

Recommended layout:

```text
┌──────────────────────────────────────────────┐
│ AI Collaboration Summary                    │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ AI Contribution Calendar                    │
└──────────────────────────────────────────────┘

┌──────────────────────┐ ┌─────────────────────┐
│ Provider Breakdown   │ │ Attribution Quality │
└──────────────────────┘ └─────────────────────┘

┌──────────────────────────────────────────────┐
│ Collaboration History                       │
└──────────────────────────────────────────────┘
```

Card sizes:

```text
compact
standard
wide
```

Recommended standard width:

```text
800–850 px
```

---

## 20. Static README and interactive dashboard

GitHub README does not allow arbitrary JavaScript.

Therefore:

### Static README

Support:

- summary card;
- contribution heatmap;
- provider breakdown;
- evidence card;
- short history timeline;
- light and dark themes;
- links to an external dashboard.

### Optional dashboard

May support:

- provider switching;
- model filtering;
- tool filtering;
- evidence-level filtering;
- date-range selection;
- public/private filtering;
- repository drill-down for authorized users;
- JSON and SVG downloads.

The dashboard should be optional and delayed until after the core local workflow is stable.

---

## 21. Theme system

Built-in themes:

```text
github-light
github-dark
github-auto
minimal-light
minimal-dark
```

Example configuration:

```yaml
theme:
  mode: auto
  density: comfortable
  radius: 8
  font_family: system
  show_icons: true
  show_footer: true
```

Provider identity must not rely on color alone.

Use text labels or icons in addition to color.

---

## 22. Visual design principles

The visual style should be:

- clean;
- restrained;
- professional;
- GitHub-native;
- compact;
- information-dense without being crowded;
- readable in light and dark modes.

Avoid:

- excessive gradients;
- gaming-dashboard aesthetics;
- animated GIFs;
- large provider logos;
- rainbow palettes;
- charts without metric labels;
- visual treatments that hide uncertainty.

The desired visual quality should resemble:

```text
GitHub Insights
Star History
GitHub Readme Stats
```

---

## 23. Accessibility

All SVG outputs must include:

- `<title>`;
- `<desc>`;
- readable font sizes;
- sufficient contrast;
- non-color distinctions;
- text equivalents for key values.

Suggested minimum sizes:

```text
primary metric: 18–28 px
card title: 14–18 px
body labels: 11–14 px
```

---

## 24. Visualization output

Expected generated assets:

```text
dist/
  summary.svg
  calendar-all.svg
  calendar-claude.svg
  calendar-codex.svg
  provider-breakdown.svg
  attribution-quality.svg
  privacy.svg
  history.svg
  profile.json
  manifest.json
```

Example manifest:

```json
{
  "generated_at": "2026-07-14T10:00:00-04:00",
  "schema_version": "0.1.0",
  "assets": {
    "summary": "summary.svg",
    "calendar_all": "calendar-all.svg",
    "provider_breakdown": "provider-breakdown.svg"
  }
}
```

---

## 25. Visualization configuration

Example:

```yaml
visualization:
  period: current_year
  metric: unique_attributed_commits
  theme: github-auto
  layout: standard

  cards:
    summary: true
    calendar: true
    provider_breakdown: true
    monthly_timeline: true
    evidence: true
    privacy: true
    history: true

  providers:
    include:
      - anthropic
      - openai
      - google
    include_unknown: true
    include_human: true

  private_activity:
    display: aggregate_only

  history:
    maximum_events: 6
```

---

## 26. Visualization integrity rules

1. A unique commit is counted once in overall totals.
2. One commit may have multiple participation events.
3. Private aggregate-only data must not reveal repository identities.
4. Unknown data must not be folded into human activity.
5. Inferred evidence must not look equivalent to verified evidence.
6. Percentages must clearly state their denominator.
7. Missing dates and months must be shown as zero.
8. LOC must only be rendered with reliable attribution.
9. Manual historical assignments must be marked as declared.
10. Each card should show its generation date and metric definition when space permits.

---

## 27. Security requirements

The project must:

- never commit tokens into generated assets;
- redact local paths from public output;
- avoid storing prompt text by default;
- use stable repository IDs rather than private names;
- use salted hashes when anonymous repository IDs are required;
- support complete local data deletion;
- support per-repository exclusion;
- preview publishable data before rendering;
- avoid uploading private Git Notes without consent.

Provide:

```bash
aiprofile privacy-preview
```

This command must show exactly what public assets will contain.

---

## 28. Adapter interface

Example Python interface:

```python
from typing import Iterable, Protocol

class AttributionAdapter(Protocol):
    name: str

    def detect(self, repository_path: str) -> bool:
        ...

    def collect(
        self,
        repository_path: str,
        since_commit: str | None = None,
    ) -> Iterable["CollaborationEvent"]:
        ...
```

Initial adapters:

```text
GitTrailerAdapter
GitNotesAdapter
GitAIAdapter
ManualDeclarationAdapter
UnknownCommitAdapter
```

Provider-specific adapters should be added only after validating the source format and licensing constraints.

---

## 29. Deduplication

The same contribution may appear in several sources.

Example:

- Git trailer;
- Git AI Note;
- local Claude session log.

Use a deterministic identity based on:

```text
repository ID
commit SHA
provider
model
tool
activity role
```

Retain all provenance sources:

```yaml
provenance_sources:
  - git_ai_note
  - git_trailer
  - local_session_log
```

Stronger evidence should take precedence, but weaker evidence should remain auditable.

---

## 30. GitHub Action

Provide a reusable workflow.

Example:

```yaml
name: Update AI Profile

on:
  schedule:
    - cron: "17 1 * * *"
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: project-name/aiprofile-action@v1
        with:
          github-token: ${{ secrets.AIPROFILE_TOKEN }}
          include-private: true
          private-visibility: aggregate_only

      - name: Commit generated assets
        run: |
          git add assets/
          git commit -m "chore: update AI collaboration profile" || exit 0
          git push
```

For public-only workflows, prefer `GITHUB_TOKEN` when sufficient.

For account-wide private scanning, support:

- GitHub App authorization;
- fine-grained personal access tokens;
- local-only aggregation.

Never request write access to source repositories solely for analytics.

---

## 31. MVP scope

Version 0.1 should implement only:

1. local CLI initialization;
2. local repository discovery;
3. Git trailer parsing;
4. Git Notes parsing;
5. Git AI import;
6. manual attribution;
7. SQLite event storage;
8. public/private privacy rules;
9. profile-level aggregation;
10. static SVG summary card;
11. static provider contribution calendars;
12. provider breakdown SVG;
13. attribution-quality SVG;
14. privacy summary SVG;
15. deterministic history timeline;
16. JSON export;
17. GitHub Action for profile README updates;
18. documentation and example profile;
19. unit and snapshot tests.

Do not include in v0.1:

- AI source-code detection;
- full transcript hosting;
- billing;
- enterprise administration;
- semantic commit classification;
- full SaaS authentication;
- custom IDE extensions;
- line-level attribution reimplementation;
- large interactive dashboard;
- AI-generated recommendations.

---

## 32. Suggested repository structure

```text
ai-profile/
├── README.md
├── LICENSE
├── pyproject.toml
├── action.yml
├── docs/
│   ├── proposal.md
│   ├── landscape.md
│   ├── architecture.md
│   ├── schema.md
│   ├── mvp.md
│   └── decisions/
├── src/
│   └── aiprofile/
│       ├── cli.py
│       ├── config.py
│       ├── db.py
│       ├── schema/
│       │   ├── event.py
│       │   └── ace.schema.json
│       ├── collectors/
│       │   ├── local_git.py
│       │   └── github.py
│       ├── adapters/
│       │   ├── trailers.py
│       │   ├── git_notes.py
│       │   ├── git_ai.py
│       │   └── manual.py
│       ├── storage/
│       │   ├── database.py
│       │   └── migrations.py
│       ├── aggregate/
│       │   ├── daily.py
│       │   ├── monthly.py
│       │   └── profile.py
│       ├── privacy/
│       │   ├── policy.py
│       │   └── redact.py
│       ├── visualization/
│       │   ├── models.py
│       │   ├── themes.py
│       │   └── accessibility.py
│       └── render/
│           ├── summary_svg.py
│           ├── calendar_svg.py
│           ├── breakdown_svg.py
│           ├── evidence_svg.py
│           ├── privacy_svg.py
│           └── history_svg.py
├── tests/
├── examples/
└── .github/
    └── workflows/
```

---

## 33. Implementation phases

### Phase 0: Landscape and non-duplication audit

Before coding:

1. inspect Git AI’s schema, Git Notes refs, commands, and license;
2. inspect Agent Blame and similar attribution projects;
3. inspect GitHub profile statistics generators;
4. inspect contribution heatmap and SVG-generation projects;
5. document reusable components;
6. produce a non-duplication matrix.

Required output:

```text
docs/landscape.md
```

### Phase 1: Schema and first vertical slice

Implement:

- ACE schema;
- Git trailer parser;
- one local repository scanner;
- SQLite storage;
- profile provider counts;
- one SVG summary card;
- fixture repositories;
- unit tests.

### Phase 2: Notes, privacy, and aggregation

Implement:

- Git Notes parser;
- Git AI importer;
- daily and monthly aggregation;
- unknown handling;
- public/private privacy rules;
- deduplication;
- privacy preview.

### Phase 3: Visualization

Implement:

- summary card;
- all-provider calendar;
- provider-specific calendars;
- provider breakdown;
- attribution-quality card;
- private/public card;
- deterministic history timeline;
- light and dark themes;
- snapshot tests.

### Phase 4: Cross-repository GitHub integration

Implement:

- GitHub API discovery;
- public-only mode;
- fine-grained token mode;
- incremental scanning;
- reusable GitHub Action.

### Phase 5: Provider adapters

Suggested order:

1. Git AI;
2. Claude Code;
3. Codex CLI;
4. Gemini CLI;
5. GitHub Copilot;
6. additional tools.

---

## 34. Testing strategy

Create fixture repositories for:

- human-only commits;
- Git trailer attribution;
- Git Notes attribution;
- Git AI attribution;
- mixed Claude and Codex participation;
- squash merges;
- rebases;
- cherry-picks;
- amended commits;
- private aggregate-only repositories;
- excluded repositories;
- duplicate evidence;
- unknown historical commits.

Key invariants:

1. One Git commit remains one unique commit.
2. Multiple participation events may belong to one commit.
3. Private repository names never appear in aggregate-only output.
4. Unknown commits are never classified as human automatically.
5. Duplicate evidence does not inflate counts.
6. Rewritten history does not silently duplicate records.
7. Public rendering contains no token, path, prompt, or private URL.
8. SVG output is deterministic.
9. Missing dates are represented as zero.
10. Evidence levels remain visible in the statistics.

Visualization fixtures:

```text
new_user
public_only
private_aggregate
claude_dominant
multi_provider
unknown_history
high_activity
no_activity
```

---

## 35. Definition of done for v0.1

A user can run:

```bash
aiprofile init
aiprofile scan ~/github
aiprofile import --adapter git-ai
aiprofile aggregate
aiprofile privacy-preview
aiprofile render
```

The tool generates:

```text
dist/
  summary.svg
  calendar-all.svg
  calendar-claude.svg
  calendar-codex.svg
  provider-breakdown.svg
  attribution-quality.svg
  privacy.svg
  history.svg
  profile.json
  manifest.json
```

The user can place these assets in a GitHub profile repository and display account-wide AI collaboration history.

The system must clearly distinguish:

- verified AI-attributed contributions;
- declared AI contributions;
- imported attribution;
- inferred historical contributions;
- human-only activity;
- unknown activity;
- public repository activity;
- private aggregate-only activity.

---

## 36. Engineering decisions required before full implementation

Document:

1. Python package and CLI framework.
2. SQLite migration strategy.
3. ACE JSON Schema.
4. Git Notes namespace.
5. Git trailer naming conventions.
6. Git AI interoperability method.
7. GitHub API pagination and caching.
8. rewritten-history handling.
9. GitHub identity matching.
10. private repository redaction.
11. SVG rendering strategy.
12. authentication modes.
13. evidence precedence.
14. provider and model normalization registry.
15. schema migration and backward compatibility.

Do not begin broad feature development until these decisions are internally consistent.

---

# Instructions for Claude Code or another implementation agent

Read this proposal completely before making changes.

Treat this as a lightweight, local-first, open-source project for profile-level AI collaboration analytics across multiple GitHub repositories.

Do not implement the complete platform immediately.

## First task: Phase 0 documentation

Create:

1. `docs/landscape.md`
   - Review existing AI code-attribution repositories, Git Notes tools, Git AI, GitHub profile statistics projects, contribution heatmaps, and README SVG generators.
   - Identify what can be reused or integrated.
   - Explicitly document how this project avoids duplicating existing tools.
   - Include a non-duplication matrix.

2. `docs/architecture.md`
   - Define the v0.1 architecture.
   - Separate collection, normalization, storage, aggregation, privacy, visualization, and rendering.
   - Explain public and private repository handling.

3. `docs/schema.md`
   - Finalize ACE v0.1.
   - Define required fields, evidence levels, privacy levels, controlled vocabularies, and deduplication rules.

4. `docs/mvp.md`
   - Define the exact v0.1 scope.
   - Include CLI commands, expected outputs, tests, and definition of done.

5. `docs/decisions/`
   - Add architecture decision records for:
     - runtime and packaging;
     - database;
     - Git metadata format;
     - privacy model;
     - SVG rendering;
     - GitHub authentication;
     - schema versioning.

After writing these documents, inspect them for contradictions, unnecessary complexity, privacy risks, and duplicated functionality.

Do not begin implementation until the architecture and MVP scope are consistent.

## Second task: First vertical slice

After the documents are approved, implement only:

1. scanning one local Git repository;
2. reading explicit AI attribution from Git commit trailers;
3. normalizing records into ACE;
4. storing events in SQLite;
5. aggregating profile-level provider counts;
6. generating one polished static SVG summary card;
7. running unit tests with fixture repositories.

Do not add:

- GitHub App integration;
- hosted dashboards;
- provider-specific session-log adapters;
- line-level code attribution;
- semantic classification;
- unnecessary framework complexity.

Prioritize:

- attribution correctness;
- privacy-safe defaults;
- deterministic rendering;
- small dependency footprint;
- clear documentation;
- test coverage.

At the end, report:

- resulting directory structure;
- setup and usage commands;
- tests executed;
- known limitations;
- the next smallest vertical slice.

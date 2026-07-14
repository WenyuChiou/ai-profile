# ACE v0.1 — AI Collaboration Event Schema

Status: **finalized for v0.1** (2026-07-14; revised same day after the
Phase 0 three-lens adversarial review — see progress.md for the finding
ledger).
Schema version string: `"0.1.0"`.

An ACE event records one attributable participation (by an AI tool, a human,
or an unknown actor) in one software-development artifact. For v0.1 the only
artifact type is a Git commit.

This document is the single source of truth for the event model. Code
(`src/aiprofile/schema/`) implements this document; where they disagree, this
document wins and the code is a bug.

Design stance for v0.1: fields exist because the vertical slice consumes
them, with one named exception — `roles`, `contribution_mode`, and
`human_reviewed` are captured (parsed, validated, stored) because the
slice's parse contract requires mapping role, mode, and review status even
though no v0.1 card renders them yet; deferring their *capture* would be
lossless (full re-scan) but re-adding the fields later costs a migration
while keeping them costs two columns. Fields from the proposal that
nothing consumes at all (metrics, integrity/signature, human identity
block, branch, parent events, confidence score, repository visibility,
per-event privacy block) are **deferred, not included** — see §12.

---

## 1. Event structure

```yaml
schema_version: "0.1.0"          # required, const for this schema revision
event_id: "ace_3f9c2a71b4e8d05a6c1f2b93"   # required, deterministic (§8)

actor:                            # required
  type: "ai"                      # required: human | ai | mixed | unknown
  provider: "anthropic"           # optional: canonical slug (§10) or null
  provider_raw: "Anthropic"       # optional: verbatim source string
  model: "claude-sonnet"          # optional: lowercased/trimmed raw (§10)
  model_raw: "Claude-Sonnet"      # optional: verbatim source string
  tool: "claude-code"             # optional: canonical slug or null
  tool_raw: "Claude-Code"         # optional: verbatim source string

activity:                         # required
  type: "commit"                  # required: v0.1 vocabulary = {commit}
  roles: ["implementation"]       # optional: sorted, deduplicated (§4)
  contribution_mode: "ai_assisted"  # optional: §5, null = unstated
  human_reviewed: true            # optional tri-state: true | false | null
  timestamp: "2026-07-14T08:22:12-04:00"  # required: commit author date, ISO 8601

source:                           # required — artifact identity
  repository_uid: "remote:github.com/wenyuchiou/ai-profile"  # required (§7)
  commit_sha: "0123456789abcdef0123456789abcdef01234567"     # required, 40 hex

provenance:                       # required
  evidence_level: "declared"      # required: §6 (max over sources)
  sources:                        # required, at least one entry
    - source_type: "git_trailer"  # §6.2
      source_reference: null      # optional free-form locator
      evidence_level: "declared"

recorded_at: "2026-07-14T12:00:00+00:00"  # optional, audit only; never part
                                          # of identity or aggregation
```

There is **no per-event privacy block**: publication levels are
repository-level policy resolved from configuration at aggregation time
(§9). This is a documented deviation from the proposal's example event
(proposal §6); per-event overrides can be added post-v0.1 if a use case
appears.

Validation rules:

- Unknown enum values are **rejected** (`SchemaValidationError`), never
  coerced.
- Required fields missing → rejected.
- `commit_sha` must be 40 lowercase hex characters.
- `roles` is stored sorted and deduplicated; validation rejects unknown role
  values (the *parser* drops unknown tokens with a warning before the event
  is built — the schema layer itself never silently drops).
- `actor.type = ai` requires at least one of `provider`, `provider_raw`,
  `tool`, `tool_raw`.
- `actor.type = human` and `actor.type = unknown` require
  `provider/model/tool` (canonical and raw) to be null. `unknown`
  additionally requires `evidence_level = unknown`; `human` in v0.1 is
  produced only by an explicit declaration (§2) and therefore carries
  `evidence_level = declared`.
- `event_id` derivation is deterministic (§8). A minimal canonical dict/
  JSON form (`to_dict()` + sorted-keys dump) exists for tests and future
  raw-event export; it is deterministic byte-for-byte for equal events.
  No v0.1 CLI command emits it (the public JSON artifact is the viz
  contract, not raw events).

## 2. Actor types

```text
human | ai | mixed | unknown
```

- `human` — explicit human-only declaration exists. v0.1 producer: a
  trailer group declaring `AI-Mode: Human-Only` with no AI provider/tool
  in the group (ADR-005 carves this exception into the grouping rule).
  Never assigned by default.
- `ai` — explicit AI provenance exists for this participation.
- `mixed` — meaningful human and AI work in one artifact that cannot be
  reliably separated. **No v0.1 producer** (reserved for manual
  reconciliation, post-v0.1); validated as legal input so stored data
  written by future versions remains readable.
- `unknown` — no reliable evidence. Never folded into `human`.

## 3. Activity types

v0.1 vocabulary: `commit` only. The enum exists so later versions can add
`pull_request`, `review`, etc. without a schema redesign; v0.1 validation
rejects anything but `commit`.

## 4. Activity roles

```text
implementation | review | documentation | testing | other
```

Multiple roles per participation are legal (`roles: [documentation,
implementation]`). Roles are an **attribute** of a participation, not part
of its identity (§8): a later source adding a role merges by union instead
of minting a second event. No v0.1 card renders roles; they are captured
under the stance exception named in the header.

## 5. Contribution modes

```text
ai_generated | ai_assisted | ai_reviewed | human_reviewed_ai | human_only | unknown
```

`contribution_mode: null` means *unstated* — the evidence declared AI
participation without declaring a mode. The parser never invents a mode.
`unknown` (the explicit value) is reserved for records whose source
positively asserts "mode unknown"; v0.1's parser emits `null`, not
`unknown`, for missing modes.

Mode → actor-type mapping used by the trailer adapter:

| declared mode | actor.type |
|---|---|
| ai_generated, ai_assisted, ai_reviewed, human_reviewed_ai | ai |
| human_only (group has no AI provider/tool) | human |
| human_only (group ALSO names an AI provider/tool) | contradiction → group discarded with a warning (ADR-005) |
| (missing / unparseable) | ai (the AI-* trailer group itself declares AI participation); mode stays null |

## 6. Provenance

### 6.1 Evidence levels (precedence order, high → low)

```text
verified > declared > imported > inferred > unknown
```

- `verified` — emitted directly by an integrated tool or signed hook.
  **No v0.1 producer.**
- `declared` — supplied through a trailer or explicit user command. v0.1:
  all trailer-derived events (including human-only declarations).
- `imported` — converted from a trusted external attribution system
  (e.g. git-ai notes). **No v0.1 producer.**
- `inferred` — reconstructed from weaker historical evidence. **No v0.1
  producer** (and never produced by style analysis — prohibited).
- `unknown` — no reliable evidence.

An event's `evidence_level` is the **maximum** over its provenance sources.
All sources are retained for audit even when superseded (§8.3).

### 6.2 Provenance source types

v0.1 vocabulary:

```text
git_trailer            # AI-* trailer group in the commit message
git_trailer_coauthor   # Co-authored-by trailer matching a known AI identity
manual_declaration     # reserved: `aiprofile reconcile` (post-v0.1)
none                   # the no-evidence marker used by unknown events
```

`source_reference` is an optional free-form locator (e.g. the matched
trailer key, a note ref). It must never contain prompts, file paths, or
message bodies.

## 7. Repository identity

`repository_uid` is stable across machine paths and never published:

- If the repository has an `origin` remote:
  `remote:<normalized-url>` where normalization lowercases host and path,
  strips protocol, credentials, trailing `/`, and `.git`
  (e.g. `remote:github.com/owner/repo`).
- Otherwise: `local:<full 64-hex sha256(salt || absolute-path)>` using the
  per-install salt created by `aiprofile init`. (Full digest, not
  truncated: the uid is local-only, and truncation would buy nothing while
  creating a collision-merges-two-repos failure mode.)

Two clones of one remote share a uid by design; configuration may then
hold two entries for one uid, and the **most restrictive publication
level wins** (§9).

The uid exists **only** inside the local database and local configuration.
Public aggregate outputs never contain repository uids, names, paths, or
hashes of them (§9).

## 8. Deterministic event identity and deduplication

### 8.1 Identity fields

A participation's identity is:

```text
repository_uid
commit_sha
actor.type
actor.provider   (canonical if known, else lowercase provider_raw, else "")
actor.tool       (canonical if known, else lowercase tool_raw, else "")
activity.type
```

```text
identity_string = "ace-identity-v1" + "\n" + <fields joined by "\n">
event_id        = "ace_" + sha256(identity_string)[:24 hex]
```

### 8.2 Deliberate deviation from the proposal

The proposal (§29) includes `model` and `activity role` in the dedup
identity. ACE v0.1 **excludes both**, for count integrity:

- Two sources describing the same participation with different model
  precision (`claude-sonnet` vs unstated) must merge into one event, not
  inflate participation counts. Model is an attribute resolved by evidence
  precedence; both raw values stay auditable in provenance sources.
- The same argument for roles: "Claude implemented" and "Claude implemented
  + documented" from two sources are one participation with the role union,
  not two events.

The semantics of a participation event are therefore: **one actor tuple
(type, provider, tool) participated in one commit**. "Claude implements,
Codex reviews" is still 2 events (different providers). One unknown event
per no-evidence commit is still exactly one event (empty provider/tool).

### 8.3 Merge rules (same event_id produced more than once)

These rules apply when one scan derives the same identity from several
places (e.g. two trailer groups with the same provider+tool, or a trailer
group plus a matching co-author line), and to future multi-source imports
(notes, git-ai, manual declarations):

- provenance sources: set-union (dedup by `(source_type,
  source_reference)`).
- `evidence_level`: max over sources.
- `roles`: sorted union.
- `model` / `model_raw`, `contribution_mode`, `human_reviewed`: the value
  from the highest-precedence source wins; on equal precedence, an existing
  non-null value is kept (first-write-wins — deterministic because scans
  process commits and trailer groups in stable order).
- Across scans, idempotence comes from the scan mechanism itself
  (ADR-014): each scan atomically replaces the repository's scan-derived
  rows, so re-scanning an unchanged repository yields identical state and
  identical counts.

## 9. Privacy publication levels

```text
full | repository_anonymous | aggregate_only | excluded
```

Semantics as in the proposal §12. v0.1 specifics:

- Publication level is **repository-level policy with exactly one home:
  the config file** (`config.json`). It is not stored in the database,
  not stored on events, and never read from anywhere else at aggregation
  time — so editing the config takes effect on the next
  `aggregate`/`render` with no rescan, and stale copies cannot exist
  (there are no copies).
- Each configured repository entry records `{path, repository_uid,
  publication_level}` (the uid is written at scan time so aggregation
  never needs to touch git). Events join to policy via `repository_uid`.
- **Default for every newly scanned repository: `aggregate_only`.**
  Raising to `full` is an explicit user action (`scan --full`, persisted
  in config). A repeat `scan` without `--full` never downgrades an
  existing entry.
- A repository whose uid has **no config entry** is treated as `excluded`
  at aggregation time (fail-closed).
- If several config entries share one uid (two clones), the **most
  restrictive** level wins: `excluded > aggregate_only >
  repository_anonymous > full`.
- `excluded` repositories are skipped entirely at scan time AND excluded
  again at aggregation (defense in depth, and it covers rows stored
  before the user flipped the level).
- v0.1 public outputs are aggregate-level only, so `full` vs
  `repository_anonymous` vs `aggregate_only` currently affect only the
  public/private split (§15): `full` counts as public activity, the other
  two count as private aggregate-only activity. Per-repository rendering
  (where `repository_anonymous` differs from `aggregate_only`) is
  post-v0.1.

## 10. Provider / model / tool normalization

**Providers and tools** normalize through the registry
(`src/aiprofile/registry.py`; ADR-013). Raw source strings are always
preserved in `*_raw`. An unrecognized raw value yields canonical `null`.
Nothing is ever guessed into a canonical slug.

**Models do not use the registry** (ADR-013): canonical `model` =
`lowercase(trim(model_raw))`; there is no model alias table in v0.1.

**Public-output rule for unrecognized values (privacy-critical):** raw
strings are commit-message text and may contain anything, including
private project names. In any public artifact (`profile.json`, SVGs),
all canonical-`null` participations aggregate under the single reserved
provider slug `unrecognized` (display name "Unrecognized"). Raw strings
are visible only in local terminal output (`aggregate -v`). The reserved
slug may not be used as a registry alias.

Canonical provider slugs seeded in v0.1 (from landscape.md §2.1, verified
strings only): `anthropic`, `openai`, `google`, `github`, `amazon`,
`cursor`, `aider`, `roo-code`, `openhands`, `windsurf`, `cognition`.
Canonical tool slugs: `claude-code`, `codex-cli`, `copilot`, `cursor`,
`aider`, `roo-code`, `openhands`, `devin`, `jules`, `gemini-cli`,
`gemini-code-assist`, `windsurf`, `amazon-q`. (Exact recognized
spellings and co-author identities live in the registry, seeded only from
landscape-verified claims. `cline` is deliberately absent — landscape.md
§2.1.)

## 11. Unknown handling

Every commit inside a scan (authored by a configured identity, ADR-015)
that yields **zero** participation events receives exactly one synthetic
event:

```yaml
actor: { type: unknown }
provenance:
  evidence_level: unknown
  sources: [{ source_type: none, evidence_level: unknown }]
```

Consequences:

- unknown commits are countable and visibly separate from human;
- "no evidence" is representable, auditable, and re-classifiable later
  (manual reconciliation upgrades the same commit by adding new events);
- aggregation never needs to infer the unknown count by subtraction.

## 12. Deferred fields (explicitly not in v0.1)

| proposal field | why deferred |
|---|---|
| `privacy.*` per-event block | publication level is repo-level config (§9); per-event overrides have no v0.1 use case |
| `human.github_login/role/reviewed` | identity matching is config-email based in v0.1 (ADR-015); `activity.human_reviewed` kept as the only review bit |
| `metrics.*` (LOC, files) | nothing in v0.1 renders LOC; AI-LOC estimation from commit stats is prohibited anyway |
| `integrity.content_hash/signature` | no verified-level producer exists yet |
| `git.branch`, `git.parent_event_ids` | privacy risk / no consumer |
| `provenance.confidence` | evidence_level enum is the v0.1 granularity |
| `git.repository_visibility` | local scanning cannot verify it; publication level is the operative policy |
| `actor.agent_name` | no consumer |

Adding any of these later is a minor-version schema change (§13).

## 13. Schema versioning

- Events store the `schema_version` they were written with.
- Pre-1.0: additive optional fields bump **minor**; any breaking change
  bumps **minor** with a migration; v0.1 code refuses to aggregate events
  whose `major.minor` exceeds what it supports and says so explicitly.
- The database migration sequence (integers, ADR-004) is independent of the
  ACE version.

## 14. Manual reconciliation (forward contract only)

`aiprofile reconcile` is post-v0.1. Its contract is fixed now so the schema
does not shift later: manual assignments produce events with
`source_type: manual_declaration`, `evidence_level: declared`, and the
standard identity rules (§8) — reconciling a commit already holding an
unknown event *adds* the declared event; the unknown event is removed only
when the reconciliation explicitly resolves the whole commit. Because
v0.1's scan mechanism replaces scan-derived rows per scan (ADR-014), the
version that introduces manual events MUST also change the scan to
preserve `manual_declaration` events across rescans — recorded here so it
cannot be forgotten.

## 15. Aggregation semantics bound to this schema

Definitions used by every consumer (aggregator, privacy layer, renderer,
exports). Units are stated explicitly; a metric without its unit named is
a spec bug.

- **Unique commit** — one row per `(repository_uid, commit_sha)`; never
  double-counted regardless of how many events it holds.
- **Commits scanned** (unit: commits) — unique commits by the configured
  identities in non-excluded repositories.
- **AI-attributed commit** (unit: commits) — a unique commit with ≥1 event
  of `actor.type ∈ {ai, mixed}`.
- **AI participation event** (unit: events) — one ACE event with
  `actor.type ∈ {ai, mixed}`. Several may share one commit.
- **Human-declared commit** (unit: commits) — no AI events and ≥1 `human`
  event.
- **Unknown commit** (unit: commits) — only `unknown` events.
- **Provider-attributed commits** (unit: commits, per provider) — distinct
  commits with ≥1 event of that provider; the per-provider column may sum
  to more than the AI-attributed total and must never be presented as
  unique commits. Canonical-`null` events group under the reserved
  `unrecognized` slug in public outputs (§10).
- **Provider participation events / active days** (units: events / days,
  per provider) — same grouping.
- **Active AI day** (unit: days) — a calendar date (taken from the commit
  author date's own UTC offset, i.e. the author's local day) with ≥1 AI
  participation event.
- **Evidence totals** (unit: **events**) — count of events per evidence
  level; rendered labels must say "events".
- **Public commits** (unit: commits) — commits scanned in repositories
  whose resolved publication level is `full`. **Private aggregate-only
  commits** (unit: commits) — commits scanned in `aggregate_only` or
  `repository_anonymous` repositories. The two sum to commits scanned
  (excluded repositories are absent from every metric).
- **AI providers count** (unit: providers) — number of distinct canonical
  provider slugs with ≥1 AI participation event, **excluding** the
  reserved `unrecognized` bucket.
- The v0.1 reporting period is all-time; `VizStats.period` carries null
  bounds and the label `"All time"` (range filtering is post-v0.1; when it
  lands, boundaries compare against the author-local date, matching
  active-day semantics).

# ACE v0.3 — AI Collaboration Event Schema and public aggregate contract

Status: **current for the v0.7.2 Public Beta candidate** (2026-08-23; unchanged
from the released v0.6.1 schema; the v0.1 event
field semantics remain the historical input contract, while ADR-027 adds the
public model-family aggregate).
Schema version string: `"0.3.0"`.

An ACE event records one attributable participation (by an AI tool, a human,
or an unknown actor) in one software-development artifact. The only supported
artifact type remains a Git commit. Sections that explicitly say **v0.1**
describe the frozen event-field and input semantics; the v0.3 additive public
aggregate is specified in section 15 and ADR-027.

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
      source_reference: null      # enum-constrained locator (see 6.2)
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
- `activity.timestamp` and `recorded_at` must be OFFSET-AWARE ISO 8601
  timestamps (date-only and naive forms are rejected — author-local day
  semantics depend on the offset; gate H-05). `human_reviewed` must be
  true/false/null. `human` records require declared evidence from an
  explicit declaration source (never `none` — gate H-05).
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
- `provenance.sources[].source_reference` is enum-constrained per source
  type (§6.2) — schema validation rejects anything else; sensitive free
  text structurally cannot enter this field (G2-07).
- `event_id` derivation is deterministic (§8). **Envelope vs payload**
  (G2-14; gate-5 M-01/L-03): the canonical dict/JSON form (`to_dict()` +
  sorted-keys dump) covers the semantic payload only and EXCLUDES the
  two envelope fields — `recorded_at` (audit metadata that varies per
  scan) and `merged` (derivation state, below); equal events therefore
  serialize byte-identically even across rescans. **Equality is
  OPERATIONAL** (gate-6 L-01): `recorded_at` — pure audit metadata — is
  excluded from equality and hashing, but `merged` PARTICIPATES in both,
  because it decides merge admissibility (§8.3): a leaf and a reduced
  event with identical canonical payloads are deliberately NOT
  interchangeable in sets/caches — dedup must never flip whether a
  subsequent `merge_event_group` call succeeds. Canonical-payload
  equality, when needed, is `canonical_json` comparison. No v0.1 CLI
  command emits raw events (the public JSON artifact is the viz
  contract).
- **Derivation state** (`merged`, gate-4 High / gate-5 M-01): defaults
  to false; set to true ONLY by `merge_event_group` on a multi-input
  reduction, and checked on every input so nested/incremental
  composition is rejected (§8.3). It is envelope-only: never serialized,
  never persisted (the SQLite `events` table has no such column — pinned
  by regression). The boundary it enforces therefore protects the
  **sanctioned in-memory path only** — the scanner's single-pass flat
  reduction over freshly built leaves. Stored events drop derivation
  state by design, so rehydrating persisted events back into
  `merge_event_group` is OUT OF CONTRACT in v0.1 (no CLI path does
  this); the same applies to raw construction or `dataclasses.replace`
  resetting the marker. A future round-trip/import boundary must first
  give derivation state an enforceable persisted representation.

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

`source_reference` is an enum-constrained locator, validated per source
type (G2-07 — a prose prohibition is not a control): `git_trailer` allows
exactly `ai-provider` / `ai-tool` / `ai-mode`; `git_trailer_coauthor`
allows exactly `co-authored-by`; `none` requires null. Future source
types must define their closed locator sets before shipping. Duplicate
`(source_type, source_reference)` keys within one construction dedupe to
the HIGHEST evidence level at the schema boundary (gate H-03 — otherwise
one evidence multiset had order-dependent canonical serializations).
Provenance rows are **local-only data** — they never cross the VizStats
boundary.

## 7. Repository identity

`repository_uid` is stable across machine paths and never published:

- If the repository has an `origin` remote: `remote:v5:<canonical>` using
  the **versioned, INJECTIVE canonicalization algorithm of ADR-016 v5**
  (G2-01; Gate-3 C-01/H-01/M-04; gate-4 M-4/M-5; gate-6 M-02/M-03):
  remote identity requires a positive marker; credentials strip at the
  last `@`; query/fragment strip in every syntax; port tokens are ASCII
  decimal only, normalize to canonical decimal (`:0443` ≡ `:443`), are
  bounded to 0..65535 (violations → not a usable remote → local
  fallback), and absent ports resolve to the scheme default. Alias-convergent
  hosts (documented: github.com) canonicalize as `host/case-folded-path`
  **only on their documented `(scheme, effective-port)` endpoints**
  (`ssh:22` / `https:443` / `git:9418`); every other endpoint — and every
  other host — canonicalizes as `scheme://host:port/path` with scheme
  retained and the effective port explicit — self-delimiting, so no
  concatenation forgery can collide two identities. Changing any rule
  bumps the algorithm version (v3 → v4 and v4 → v5 were exactly such
  changes); different versions never compare equal.
- Otherwise: `local:v5:<full 64-hex sha256(salt || resolved-path)>` over
  the CASE-PRESERVED resolved path (Gate-3 C-02: case-insensitive
  filesystems converge via `Path.resolve()` itself; case-distinct POSIX
  directories correctly split), using the per-install salt created by
  `aiprofile init`. (Full digest, not truncated.)

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

The unit this identity counts is therefore an **AI actor presence**: one
actor tuple (type, provider, tool) was present in one commit (renamed per
G2-02 — "participation event" overstated the unit, since two
same-provider/tool actions in one commit collapse by design; Claude
implementing AND Claude reviewing is ONE presence with the role union).
"Claude implements, Codex reviews" is still 2 presences (different
providers). One unknown record per no-evidence commit is still exactly
one record (empty provider/tool). True per-action participation events
return only when a source supplies a stable occurrence ID (ROADMAP).

### 8.3 Merge rules (same event_id produced more than once)

These rules apply when one scan derives the same identity from several
places (e.g. two trailer groups with the same provider+tool, or a trailer
group plus a matching co-author line), and to future multi-source imports
(notes, git-ai, manual declarations):

- provenance sources: set-union (dedup by `(source_type,
  source_reference)`; a key collision keeps the HIGHER evidence level),
  stored in canonical order (sorted by source type, then locator) so
  serialization never depends on ingestion order (G2-06).
- `evidence_level`: max over sources.
- `roles`: sorted union.
- `contribution_mode`, `human_reviewed` — and the `(provider,
  provider_raw)` / `(model, model_raw)` / `(tool, tool_raw)` PAIRS, each
  resolved atomically from ONE winning leaf (Gate-3 M-10: independent
  per-scalar resolution could pair a canonical value from one source with
  a raw value from another — a provenance statement no source made) —
  are resolved by the canonical, ingestion-order-free rule of ADR-008
  (G2-06): higher
  evidence precedence wins; ties break by source-type priority
  (`git_trailer > git_trailer_coauthor > manual_declaration > none`),
  then lexicographic source locator, then lexicographic value. The rule
  is applied as one N-ary reduction over all leaf productions of the
  identity (never an incremental pairwise fold — pooled ranks are
  fold-order dependent; ADR-008), so the same evidence set in any order
  yields identical events (exhaustively permutation-tested).
- **`activity.timestamp`** (gate-7 M-01): timestamp is not part of event
  identity (§8.1), so same-identity leaves can legally disagree (e.g. a
  future import asserting a different author date). The merged timestamp
  resolves by the SAME strongest-leaf canonical rule as the scalars
  above — higher evidence precedence, then source-type priority, then
  locator, then value — so the reduction stays permutation-pure; the
  first-leaf copy it replaces made canonical bytes depend on input order.
  The final value tie-break is a DETERMINISTIC STRING comparison, not a
  chronological one: offset-aware timestamps at different UTC offsets
  compare digit-by-digit, so a source supplying timestamps in a second
  offset should normalize to a common offset before merge (reviewer
  note, gate-7 — unreachable in v0.1, where all leaves of a commit share
  one CommitRecord author-date string).
- **Leaf-only inputs** (gate-4 High): a multi-input reduction accepts
  leaf productions only, enforced via the `merged` derivation marker
  (§1) — a previously merged result would have its values re-ranked
  against pooled provenance, making nested composition grouping-
  dependent. All leaves of one identity go in ONE call. This guard
  covers the sanctioned in-memory scan path; persisted events drop
  derivation state and are not re-mergeable (§1, gate-5 M-01).
- Across scans, idempotence comes from the scan mechanism itself
  (ADR-014): each scan atomically replaces the repository's scan-derived
  rows, so re-scanning an unchanged repository yields identical state and
  identical counts.

### 8.4 Cherry-pick and cross-repository counting

Identity (§8.1) is keyed on `repository_uid` + `commit_sha` (among the
other §8.1 identity fields), not on the patch content. A cherry-pick (`git cherry-pick`, or any equivalent —
re-committing the same diff by hand) produces a new `commit_sha`, so it is
a **new commit** with its own identity: the same logical change, cherry-
picked once, is counted **again** — once per repository it lands in, and
again within the same repository if picked more than once (e.g. onto
several release branches, each scanned). This holds whether the target is
a different repository (`repository_uid` differs) or the same repository
under a different sha (`repository_uid` matches, `commit_sha` doesn't).

This is **accepted by design**, not a defect: ADR-007 deliberately excludes
`model` and `roles` from identity so that multiple *sources describing the
same participation* merge, but a cherry-pick is not that case — it is a
distinct commit object with its own author date, tree, and (usually) its
own trailer evidence, indistinguishable at the identity layer from an
independent commit that happens to carry the same trailers. **aiprofile
counts commits, not changes**: `ai_attributed_commits` and
`ai_actor_presences` (§8.2) measure how many commits an AI actor was
present in, and a cherry-picked commit is, by git's own model, a different
commit. Tested in `tests/integration/test_cherry_pick.py`: one AI-trailer
commit cherry-picked from repo A into an unrelated repo B (new sha, no
shared history) is scanned as two independent AI actor presences, one per
repository, summed in the published `totals` (§15).

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
  repository_anonymous > full`. (`repository_anonymous` is **reserved
  vocabulary in v0.1** — config validation rejects it with a targeted
  error until anonymous per-repository views exist; G2-12.)
- `excluded` repositories are skipped entirely at scan time AND excluded
  again at aggregation (defense in depth, and it covers rows stored
  before the user flipped the level).
- v0.1 public outputs are aggregate-level only, so the level affects only
  the publishable split (§15). **Labels are policy-based, never
  visibility claims** (G2-04): `full` records the user's explicit
  decision to publish, NOT verified GitHub visibility — the contract
  therefore says `explicitly_publishable` / `anonymous_aggregate`, and
  "public/private" wording is reserved until a collector verifies
  visibility and records how and when it did.

## 10. Provider / model / tool normalization

**The canonical slug sets are schema-owned vocabulary**
(`vocab.CANONICAL_PROVIDERS` / `CANONICAL_TOOLS`): `build_event` rejects
any canonical value outside them, and the privacy boundary independently
collapses non-canonical provider keys into the `unrecognized` bucket
(defense in depth, gate H-02) — an arbitrary string can never pose as
canonical end-to-end. **Providers and tools** normalize through the registry
(`src/aiprofile/registry.py`; ADR-013). Raw source strings are always
preserved in `*_raw`. An unrecognized raw value yields canonical `null`.
Nothing is ever guessed into a canonical slug.

**Models do not use the provider registry** (ADR-013): the canonical ACE
`model` value is `lowercase(trim(model_raw))` when an `AI-Model` declaration is
present, and no model value is invented when it is absent.  In the v0.5
public aggregate (ACE `0.3.0`, ADR-027), aggregation applies the closed,
schema-owned model-family normalizer to that canonical value only:

```text
claude, gpt, gemini, llama, mistral, deepseek, qwen, grok, kimi,
other, unknown
```

Missing/blank canonical values are `unknown`; explicit values outside the
reviewed family prefix/alias table are `other`.  Provider, tool, author,
commit-message, source-style, and `model_raw` values are never consulted for
this classification.  The raw model string remains local-only, just like
other raw trailer values, and never enters `VizStats` or any public artifact.

**Public-output rule for unrecognized values (privacy-critical):** raw
strings are commit-message text and may contain anything, including
private project names. In any public artifact (`profile.json`, SVGs,
or the self-contained `dashboard.html` from ADR-021),
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

**Two-tier vocabulary (round D3, ADR-019):** the v0.1 set above is
single-tier (declaration and auto-match coincide). Starting round D3,
`CANONICAL_PROVIDERS`/`CANONICAL_TOOLS` also carry ten DECLARATION-tier
providers whose auto-match bar (a stable co-author trailer/noreply
identity) is not met: `amp`, `replit`, `moonshot` (display `Kimi`),
`deepseek`, `alibaba` (display `Qwen`), `mistral`, `xai` (display
`Grok`), `zhipu` (display `GLM`), `ollama`, `meta` (display `Llama`).
Their tool slugs: `amp`, `replit-agent`, `kimi-code`, `qwen-code`,
`vibe-code` (`deepseek`/`xai`/`zhipu`/`meta` add no tool slug). A
hand-written `AI-Provider:`/`AI-Tool:` trailer using one of these
resolves and renders with its brand mark; none of them is inferred from
commit history alone. The single exception is `amp`, which ALSO has an
auto-match co-author identity (`amp@ampcode.com`, ADR-019) because it
meets the same evidence bar as the v0.1 set. Declaration-tier membership
is never a claim that the named provider auto-attributes its own
commits.

## 11. Unknown handling

Every commit inside a scan (authored by a configured identity, ADR-015)
that yields **zero** ACE records (no AI presence and no human
declaration) receives exactly one synthetic record:

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
- The v0.5 model-family aggregate is the `0.3.0` minor revision (ADR-027).
  Readers in this release accept stored `0.1.x`, `0.2.x`, and `0.3.x` events;
  new scans write `0.3.0`.  The additive `VizStats.models` contract reuses
  this `schema_version` because event and public-contract revisions move
  together.  A future independently versioned visualization contract must
  add an explicit `viz_schema_version` through a new ADR rather than silently
  relabeling the ACE version.

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
- **AI actor presence** (unit: presences) — one ACE record with
  `actor.type ∈ {ai, mixed}`: this provider/tool tuple was present in
  this commit (§8.2). Several may share one commit; two same-tuple
  actions in one commit are ONE presence by design (G2-02).
- **Human-declared commit** (unit: commits) — no AI events and ≥1 `human`
  event.
- **Unknown commit** (unit: commits) — only `unknown` events.
- **Provider-attributed commits** (unit: commits, per provider) — distinct
  commits with ≥1 event of that provider; the per-provider column may sum
  to more than the AI-attributed total and must never be presented as
  unique commits. Canonical-`null` events group under the reserved
  `unrecognized` slug in public outputs (§10).
- **Provider actor presences / active days** (units: presences / days,
  per provider) — same grouping; provider presence rows sum to total AI
  actor presences (including the `unrecognized` bucket).
- **Model-family attributed commits** (unit: commits, per closed model
  category) — distinct commits with at least one `ai`/`mixed` event whose
  canonical `model` normalizes to that category.  Categories are
  non-exclusive: one commit carrying two model families contributes one to
  each row, while `totals.ai_attributed_commits` remains one.
- **Model-family actor presences / active days** (units: presences / days,
  per category) — the same AI/mixed event population grouped by normalized
  model category.  Presence rows sum exactly to
  `totals.ai_actor_presences`, including `unknown`; active days are the
  cardinality of each category's author-local date set.  Missing model
  evidence is `unknown`, not human, and an explicit value outside the closed
  family table is `other`.
- **Active AI day (author dates)** (unit: days) — a calendar date taken
  from the commit **author date's own UTC offset** (the author's local
  day; mutable git metadata, not verified session timing — G2-18; labels
  must say "author dates") with ≥1 AI actor presence.
- **Evidence totals** (unit: records) — counts per evidence level over
  the population of **all ACE records, every actor type** (G2-05). The
  serialized contract carries `total_records`; categories MUST sum to it,
  and rendered labels MUST name the population.
- **Explicitly publishable commits** (unit: commits) — commits scanned in
  repositories whose resolved publication level is `full` (a user policy
  decision, not verified visibility — G2-04). **Anonymous aggregate
  commits** (unit: commits) — commits scanned in `aggregate_only`
  repositories. The two sum to commits scanned (excluded repositories are
  absent from every metric).
- **AI providers count** (unit: providers) — number of distinct canonical
  provider slugs with ≥1 AI actor presence, **excluding** the
  reserved `unrecognized` bucket.
- The v0.1 reporting period is all-time; `VizStats.period` carries null
  bounds and the label `"All time"` (range filtering is post-v0.1; when it
  lands, boundaries compare against the author-local date, matching
  active-day semantics).

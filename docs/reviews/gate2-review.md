# Gate 2 Independent Architecture Review

Review date: 2026-07-14  
Reviewer posture: independent Principal Software Architect; design-only review  
Design inputs reviewed: `proposal.md`, `landscape.md`, `architecture.md`,
`schema.md`, `mvp.md`, all 15 ADRs under `decisions/`, and `progress.md`.
`docs/ROADMAP.md` was requested as an input but is absent from the repository.

## 1. Executive summary

The project has a credible and differentiated core: a local-first pipeline that
turns explicit Git provenance into profile-level AI-collaboration aggregates,
then crosses a narrow structural privacy boundary before rendering static
README assets. The design correctly refuses source-style inference, preserves
`unknown` as distinct from `human`, distinguishes commits from AI events, and
keeps renderers away from Git and SQLite. These are the right foundations.

The design is not ready for an unconditional Gate 2 approval. Three semantic
defects are load-bearing:

1. Remote repository identity normalization lowercases the path and does not
   fully specify ports, scp-style remotes, Unicode, or host-specific
   case-sensitivity. Distinct repositories can therefore share a
   `repository_uid`, which can merge counts and privacy policies.
2. An ACE “participation event” is actually one provider/tool presence per
   commit. Two distinct participations by the same provider and tool collapse
   to one event. The current name and public metric overstate what is counted.
3. “Public commits” and “private commits” are not based on repository
   visibility; they are based on publication policy. A private repository
   marked `full` is labeled public, producing a semantically false privacy
   metric and a risky user mental model.

The repository also has a gate-integrity problem: `progress.md` states that
implementation is complete and committed, while this Gate 2 review is framed
as occurring before implementation. The requested roadmap is missing. This
does not invalidate the architecture, but it means the review cannot certify
the claimed pre-implementation process.

**Final recommendation: GO WITH CHANGES.** Correct the three semantic defects,
publish the missing roadmap and threat model, reduce the v0.1 schema to fields
with current consumers, and close the OSS licensing gap before calling v0.1 an
open-source release. No redesign or service decomposition is warranted.

## 2. Scores

| Dimension | Score | Rationale |
|---|---:|---|
| Architecture | 7/10 | Clear linear pipeline, good dependency direction, and a strong renderer boundary; repository identity and event semantics need correction. |
| Privacy | 7/10 | Fail-closed defaults and structural redaction are strong; publication labels, CI diagnostics, differencing disclosure, and local-secret handling are incomplete. |
| Maintainability | 8/10 | Small modular monolith, explicit ADRs, stdlib-only runtime, and disposable storage are appropriate; some future vocabulary and hand-built infrastructure are premature. |
| MVP scope | 8/10 | The actual vertical slice is disciplined and valuable; the schema still carries unused concepts, and the next step is too eager to create another Notes format. |

Scoring convention: 10 means the design is ready to implement and publish
without architectural correction, not that it has every possible feature.

## 3. Top strengths

1. **Structural privacy boundary.** `VizStats` excludes repository identifiers,
   paths, emails, SHAs, messages, and raw trailer strings by type, not by a
   late string scrub. Restricting renderers and exporters to this contract is
   the strongest part of the design (`architecture.md` sections 2, 3, and 8).
2. **Correct uncertainty model.** A no-evidence commit becomes `unknown`, never
   `human`. Historical attribution is evidence-based and explicitly prohibits
   code-style inference (`schema.md` sections 2, 6, and 11).
3. **Metric units are mostly explicit.** Unique commits, provider-attributed
   commits, participation events, active days, and evidence events are named
   separately. The design explicitly warns that per-provider commit totals can
   exceed unique AI-attributed commits (`schema.md` section 15).
4. **Renderer isolation.** Renderers consume validated aggregate data only and
   are prohibited from importing storage, Git, or subprocess facilities. Static
   SVG is realistic for GitHub README use; GitHub supports profile READMEs, and
   established generators use the same `<picture>` light/dark pattern.
5. **Appropriate deployment shape.** A modular CLI and SQLite cache are a better
   fit than services, queues, or a hosted database. Full per-repository replace
   is simple, idempotent, and correct for the stated v0.1 scale.
6. **Good non-duplication intent.** The design explicitly rejects line-level
   attribution, generic GitHub statistics, AI detection, and hosted dashboards.
7. **Strong documentation discipline.** The proposal, narrowed MVP, schema, and
   ADRs record rejected options and forward constraints. A new contributor can
   understand the major design choices without reading implementation code.

## 4. Top weaknesses

1. Repository identity is not safely canonicalized across arbitrary Git hosts.
2. “Participation event” is a misleading name for the chosen deduplication unit.
3. Publication policy is presented as verified repository visibility.
4. Evidence totals lack a clear population/denominator in the public contract.
5. The v0.1 schema accepts and stores fields and enum values with no v0.1
   producer or consumer.
6. Equal-precedence merge conflict resolution depends on input order rather
   than an explicit canonical tie-breaker.
7. Privacy analysis focuses on generated files but does not fully cover public
   CI logs, repeated-snapshot differencing, file permissions, symlinks, backups,
   crash traces, and `AIPROFILE_HOME` placed inside a repository.
8. There is no `ROADMAP.md`, no LICENSE, and no concise contributor-facing
   threat model; the repository is understandable but not OSS-ready.

## 5. Critical findings

The following table is the engineering-risk register. “Critical” blocks Gate 2;
“High” must be resolved or explicitly accepted before the affected feature
ships; “Medium” should be planned; “Low” is hardening or clarity work.

| ID | Severity | Description | Impact | Recommendation |
|---|---|---|---|---|
| G2-01 | Critical | `repository_uid` lowercases both host and path, while remote URL normalization is otherwise underspecified. Paths can be case-sensitive outside GitHub; non-default ports, scp syntax, IPv6, query/fragment data, Unicode normalization, and multiple origins are not pinned. | Distinct repositories can be merged. Counts can deduplicate incorrectly, and the most-restrictive policy of one repository can silently govern another. This is both aggregation corruption and a privacy-boundary error. | Canonicalize with a parsed remote identity: lowercase host only by default, preserve path case unless a host-specific rule is documented, retain non-default port, reject credentials after stripping, normalize scp syntax, and test collision pairs. Store a versioned `repository_uid_algorithm`; changing it later requires reconciliation. |
| G2-02 | Critical | ACE identity excludes model and role and has no participation occurrence key. Two same-provider/same-tool actions in one commit collapse, even if one generated and another reviewed. | `ai_participation_events` can undercount, while the UI describes them as actual events. The design prevents inflation but introduces silent conflation. | For v0.1, rename the unit to **AI actor presences** (one provider/tool tuple per commit), including every renderer label and definition. Defer true participation-event counts until a source can supply a stable occurrence ID. If retaining the current name, add an occurrence discriminator and specify cross-source reconciliation; do not use input order or role alone as identity. |
| G2-03 | Critical | `docs/progress.md` says the implementation is complete and committed, but Gate 2 is requested as a pre-implementation design gate. The required `docs/ROADMAP.md` is absent. | The gate cannot serve its intended risk-prevention function, and the authoritative design set is incomplete. A GO could be misread as retroactive implementation approval. | Publish `ROADMAP.md`, reconcile `progress.md` with the actual gate sequence, and state whether this review gates release, refactoring, or only future work. Treat this verdict as design approval with conditions, not implementation certification. |
| G2-04 | Critical | `full` is a user publication level, not verified GitHub visibility, yet `VizStats` labels its commits “public.” | A private repository marked `full` is misreported as public. Users may infer stronger privacy guarantees than exist. | Rename the split to `explicitly_publishable_commits` versus `anonymous_aggregate_commits`, or remove the split in v0.1. Introduce “public/private” only when a collector has verified visibility and records when/how it was verified. |
| G2-05 | High | Evidence totals count ACE events of all actor types, while the headline event count includes only AI/mixed events. The public contract does not state the evidence denominator. | Users can compare unlike populations; evidence chips may not sum to the AI event count and can look like a counting bug. | Choose one invariant: either evidence totals cover AI actor presences only, or rename them “all ACE records by evidence.” Put the denominator in `VizStats`, the SVG label, and contract tests. |
| G2-06 | High | Equal-precedence scalar conflicts use “first non-null wins” under stable scan order. Adapter order, trailer order, or a future importer can change the result. | The same evidence set can yield different model/mode/review values after adapter reordering, violating source-order independence and weakening deterministic output. | Define a canonical conflict rule independent of ingestion order: source-type priority, then normalized source locator, then canonical lexical tie-break; otherwise preserve a conflict set and render neither value. Add permutation tests. |
| G2-07 | High | The design allows free-form `source_reference`, with only a prose prohibition against prompts, paths, and message bodies. | A future adapter can persist sensitive text. It cannot cross the current `VizStats` type, but it can leak through diagnostics, raw exports, migrations, or future tooling. | Replace free-form references with source-specific structured locators and validation. For v0.1, store only the recognized trailer key/type or omit the field. Mark sensitive provenance as local-only in the schema, not only in prose. |
| G2-08 | High | Default diagnostics allow a full commit SHA, and future GitHub Action logs are acknowledged as public. | A private commit SHA is a stable correlator and may expose activity or link data across systems, even when the asset itself is clean. | Never print private-repository SHAs in default or CI mode. Use a scan-local ordinal or keyed diagnostic ID; make raw SHA output an explicit local-only debug opt-in that is forcibly disabled in Action mode. |
| G2-09 | High | “Aggregate-only” still publishes exact counts, provider presence, active-day counts, and repeated generated snapshots. The privacy model does not discuss differencing attacks. | Observers can infer when private activity changed and which provider appeared, especially for a profile with one private repository. Names remain hidden, but activity confidentiality is not guaranteed. | Document aggregate-only as pseudonymous disclosure, not anonymity. Add an optional coarse mode later (rounding, minimum threshold, or manual publish cadence). The v0.1 preview must state exactly which inferences remain possible. |
| G2-10 | High | No LICENSE exists, and the README correctly says all rights are reserved. | The project is not presently open source: users lack permission to copy, modify, or distribute it, and contributors lack a clear inbound/outbound licensing basis. | Choose and add a license before OSS release; add `CONTRIBUTING.md` and a short provenance/licensing policy for registry data and future imported schemas. |
| G2-11 | Medium | The v0.1 schema carries `model`, `model_raw`, `roles`, `contribution_mode`, `human_reviewed`, and `recorded_at` without a current output consumer, plus `mixed` and three evidence levels without a v0.1 producer. The trailer adapter does currently produce the first group; the schema explicitly preserves it for later use. | More validation, migrations, merge rules, and tests are required before the product proves value. The schema suggests public capabilities the release does not provide. | Move unconsumed fields and inactive vocabulary to v0.2 unless early capture is shown to be necessary. The current full re-scan design makes deferral lossless for trailer-derived values, so the schema's capture rationale does not outweigh the v0.1 cost. |
| G2-12 | Medium | `repository_anonymous` and `aggregate_only` are distinct vocabulary with identical v0.1 behavior. | Two policy names imply a distinction users cannot observe and expand the state space and tests. | Keep only `full`/`aggregate_only`/`excluded` in v0.1, or reject `repository_anonymous` until anonymous per-repository views exist. |
| G2-13 | Medium | The schema mandates exactly 40 lowercase hex characters for a commit ID. Git supports SHA-256 repositories with 64-hex object IDs. | Valid repositories can fail unexpectedly; future migration may touch identity and every foreign key. | Explicitly declare SHA-1-only support in v0.1 and fail with a targeted error, or model `object_format` plus variable-length validated object IDs now. Do not silently truncate. |
| G2-14 | Medium | `recorded_at` is optional and excluded from identity, but event serialization is called canonical while rescans can assign different audit times. | “Byte-identical equal events” and reproducible raw event export are ambiguous. | Remove `recorded_at` from v0.1 or define canonical semantic serialization separately from envelope/audit metadata. |
| G2-15 | Medium | `config.py` owns file I/O, configuration shape, and publication-policy resolution. | Policy correctness becomes coupled to persistence concerns as new collectors and UIs arrive. | Keep the modular monolith, but extract a small pure `PublicationPolicy`/resolver module when the second policy consumer appears. Do not create a framework now. |
| G2-16 | Medium | Import isolation is described as checking loaded module graphs for forbidden names. | Runtime import-state tests can be order-dependent and may miss lazy/dynamic imports. | Add a static AST dependency test or a lightweight import-contract script. Keep the runtime test as defense in depth. |
| G2-17 | Medium | The Git Notes roadmap reserves and plans a new ACE notes namespace before a distinct write use case exists. | It risks creating another attribution format alongside Git AI and other notes conventions, adding fetch/push/rewrite/merge behavior users must manage. | Consume existing notes formats first. Do not write `refs/notes/ai-collaboration` until a concrete field cannot be represented by Git AI or trailers and real interoperability tests justify a new format. |
| G2-18 | Medium | Active days use each commit author timestamp's local date, which is mutable metadata and can combine several time zones into one profile calendar. | The metric is reproducible but may not mean the user's actual working day; rewritten dates can move activity. | Label it “commit author-date active days,” document timezone semantics in the card, and add offset-boundary tests. Do not imply session timing. |
| G2-19 | Low | Pure string-built SVG is appropriate for one card, but the security contract is implicit. | Future text fields or renderer features could introduce active content or external references. | Test XML well-formedness, escaping, absence of scripts/`foreignObject`/external URLs, and an allowlist of elements/attributes. |
| G2-20 | Low | The progress ledger mixes current status, historical work log, delegated-task details, and roadmap. | New contributors must read a long operational transcript to learn current state, and it is unclear which document is authoritative. | Keep `progress.md` as a concise current snapshot; move historical run details to an archive or release note, and make `ROADMAP.md` authoritative for future scope. |

## 6. Architecture assessment and recommended changes

### Overall architecture

The linear modular-monolith pipeline is appropriate:

```text
Git collection -> attribution parsing -> ACE normalization -> SQLite cache
-> repository aggregates -> privacy projection -> VizStats -> SVG/JSON
```

The dependency direction is coherent and avoids circular ownership. Collection
and parsing are impure edges; schema and visualization contracts are pure;
storage is behind an explicit module; rendering is downstream-only. SQLite
on-demand aggregation is sufficient for v0.1. A service layer, plugin framework,
ORM, event bus, or materialized aggregate table would be unnecessary.

### Module boundaries

Keep the current modules, with these limited corrections:

1. Treat repository identity normalization as its own pure, versioned domain
   function with collision fixtures. It is too consequential to remain an
   incidental helper in configuration or scanning.
2. Make publication-policy resolution a pure domain function. Extraction into
   a separate module can wait until it has a second consumer.
3. Keep `RepoAggregates` internal and `VizStats` public. Add construction-time
   invariants that tie together metric units and denominators.
4. Do not introduce an `AttributionAdapter` protocol until a second adapter
   ships. The current decision to wait is correct.
5. Do not split `aggregate.py` or `privacy.py` into packages for v0.1. Their
   current boundaries are meaningful and small.

### Scalability

Full HEAD-history enumeration and atomic replacement are acceptable for the
first release. They are O(commits) per scan and will eventually become slow,
but correctness is more valuable than an incremental cache before usage data
exists. The design should establish a measured threshold before adding
incremental scans. Multi-repository support does not require concurrency in the
core; bounded parallel collection can be added later without changing ACE or
`VizStats`.

The first scaling risk is not SQLite throughput; it is identity and provenance
correctness across more sources. Resolve event semantics and repository identity
before adding adapters or GitHub collection.

### Missing and unnecessary abstractions

- Missing now: a versioned repository-identity canonicalizer and explicit
  metric-denominator invariants.
- Missing before network work: an authentication/token boundary and retry/rate-
  limit policy based on official GitHub API semantics.
- Correctly absent: a generic adapter framework, ORM, dependency-injection
  container, renderer plugin system, hosted API, and background worker.
- Premature: a proprietary Git Notes format, inactive ACE vocabulary, and two
  publication states with identical behavior.

## 7. Non-duplication analysis

The core value proposition does not unnecessarily duplicate an established
project. Independent checks support the landscape's main conclusion:

- [Git AI](https://github.com/git-ai-project/git-ai) already tracks line-level
  AI authorship, stores authorship in Git Notes, keeps transcript pointers in
  local SQLite, and exposes `git-ai stats --json`. This project must consume
  that output or its versioned standard; it must not recreate checkpoints,
  line attribution, blame, prompt storage, or rewrite semantics.
- [Git Notes](https://git-scm.com/docs/git-notes/2.50.0.html) already provides
  object-attached metadata, history, rewrite configuration, and merge
  strategies. Use `git notes` as the transport. Do not implement a parallel
  notes store or custom merge engine.
- [GitHub's commits API](https://docs.github.com/en/rest/commits/commits)
  already defines public unauthenticated access, fine-grained read permissions,
  and pagination. Future GitHub collection should wrap this API and reuse a
  mature client or `gh api`; it should not build OAuth, App token minting,
  pagination, caching, and retry behavior ad hoc merely to preserve zero
  dependencies.
- [GitHub Readme Stats](https://github.com/anuraghazra/github-readme-stats)
  already provides generic commit/PR/language cards, theme conventions, and
  `<picture>` light/dark embedding. Reuse layout and embedding conventions, not
  its generic statistics or hosted architecture.
- [lowlighter/metrics](https://github.com/lowlighter/metrics) already provides a
  broad GitHub-profile SVG/JSON generator with many plugins. A post-v0.1
  integration or plugin consuming privacy-safe `profile.json` is preferable to
  building a large family of generic profile cards.

### Functionality that is justified here

- ACE normalization across explicit AI provenance sources.
- Cross-repository, profile-level deduplication of AI collaboration metrics.
- Local privacy policy and a renderer-safe aggregate contract.
- One static AI-collaboration summary SVG and JSON export.

### Functionality to reuse instead

| Need | Reuse/integrate | Do not build |
|---|---|---|
| Line-level AI attribution | Git AI CLI JSON or version-pinned authorship standard | Checkpoints, AI blame, retained-line algorithms, prompt linkage |
| Rich commit metadata transport | Native `git notes` commands and rewrite/merge configuration | Notes database, ref synchronization, merge engine |
| GitHub repository/commit access | Official REST/GraphQL API and mature auth/client libraries | Custom App auth, pagination, rate-limit/cache framework |
| Generic profile statistics | GitHub Readme Stats or lowlighter/metrics | Stars, languages, streaks, trophies, ordinary contribution counts |
| Broad README card catalog | A lowlighter/metrics integration or a stable JSON contract | Theme marketplace, generic chart framework, hosted SVG endpoint |
| Contribution graph | Postpone; later evaluate lowlighter/metrics' MIT-licensed renderer/plugin boundary or another tested static heatmap component | Interactive JavaScript in README, a novel graph engine in v0.1, or code from Platane/snk while its licensing remains unverified |

The current custom summary renderer is justified because its inputs and labels
are domain-specific and its privacy boundary is local. Expansion into generic
cards is not.

## 8. ACE schema assessment

### v0.1 minimum

Keep these required concepts:

- `schema_version`
- deterministic `event_id`
- actor type (`ai`, explicit `human`, `unknown`)
- canonical/raw provider and tool sufficient to identify the actor presence
- activity type fixed to `commit`
- commit author timestamp, explicitly labeled as such
- repository UID plus full object ID
- provenance source type and evidence level

The missing required concept is not another field until the metric is named
correctly. If the product insists on counting true participation events, it
needs a stable source-provided occurrence/disclosure ID. Without that, the
schema can only prove actor presence per commit.

### Move to v0.2

- model and `model_raw`
- roles
- contribution mode
- `human_reviewed`
- `recorded_at`
- free-form `source_reference`
- `mixed` actor production
- inactive `verified`, `imported`, and `inferred` producers
- `repository_anonymous`

Controlled vocabulary may be documented as planned without making values legal
in the v0.1 event schema. A newer schema version should introduce values when a
producer and consumer exist. Old readers already reject unsupported future
major/minor versions, so accepting future values early does not improve forward
compatibility.

### Redundancy and normalization

Canonical plus raw provider/tool values are defensible because registry
normalization can evolve and raw unknowns support local diagnostics. They must
remain local-only. Model canonicalization by lowercase/trim is not truly
canonical across provider naming changes; deferring model is cleaner.

The event envelope and canonical semantic payload should be separated in the
spec. Audit metadata such as `recorded_at` must not make canonical event JSON
nondeterministic. Repository UID normalization must be versioned.

Evidence precedence should represent trust, not convenience. The current
`declared > imported` rule is not universally valid: a user-typed trailer is
not necessarily stronger than a versioned Git AI record. Define precedence by
source class and verification properties, or avoid a global total order and
surface conflicts. At minimum, rename `imported` as an ingestion origin rather
than a quality level; origin and confidence are different dimensions.

## 9. Aggregation semantics

The design correctly separates most units, but it is not yet impossible to mix
them accidentally.

| Metric | Unit | Safe invariant |
|---|---|---|
| commits scanned | unique `(repository_uid, object_id)` pairs | equals publishable + anonymous aggregate commits after policy filtering |
| AI-attributed commits | commits | less than or equal to commits scanned |
| AI actor presences (current event identity) | actor tuples per commit | greater than or equal to AI-attributed commits; may be less than real actions |
| provider-attributed commits | distinct commits per provider | each row is less than or equal to AI-attributed commits; rows may sum above it |
| provider actor presences | actor tuples per provider | rows should sum to total AI actor presences, including `unrecognized` |
| active AI days | author-local calendar dates | less than or equal to distinct dates in scanned commits |
| evidence totals | explicitly chosen event population | categories must sum to that named population, not an implicit different one |

Required contract changes:

1. Replace `ai_participation_events` with `ai_actor_presences` for the current
   identity model, or introduce a real occurrence ID.
2. Rename public/private metrics to policy-based terms until visibility is
   independently known.
3. Add the evidence denominator/population to the serialized contract.
4. Encode invariants in `VizStats` validation and property-based tests.
5. Never display a percentage without a named denominator. Provider commit
   share should use AI-attributed commits, not the sum of provider rows.

One commit with Claude implementing and Codex reviewing remains one unique
commit and two actor presences. One commit with Claude implementing and Claude
reviewing is one actor presence under v0.1—not two events—and must be labeled
accordingly.

## 10. Privacy assessment

### What is well protected

Generated public assets are structurally unable to contain repository names,
UIDs, paths, author emails, commit IDs/messages, branches, prompts, organization
names, or raw trailer strings if—and only if—all writers accept `VizStats`
exclusively. The `unrecognized` bucket closes the most obvious raw-string path.
Excluded repositories are fail-closed at aggregation and omitted from public
counts. Local-first/no-network v0.1 avoids token exposure entirely.

### Remaining leak paths

- Default/Action diagnostics containing private commit SHAs.
- Crash traces or verbose logs containing paths and raw values.
- `source_reference` carrying sensitive free text.
- `AIPROFILE_HOME` placed in a repository, world-readable on a shared machine,
  followed through a symlink, or captured by cloud backup/dotfile tooling.
- Exact repeated aggregates revealing private activity by differencing.
- Future anonymous repository IDs derived from low-entropy names or a leaked
  static salt; ADR-009 correctly warns against reusing the current salt.
- Future raw-event exports bypassing `VizStats`.

The design should add a concise threat model covering assets, stdout, stderr,
logs, local database/config, CI artifacts, backups, symlinks, and repeated
publication. File creation should use owner-only permissions where the platform
supports them, refuse unsafe symlink targets, and warn when `AIPROFILE_HOME` is
inside a Git worktree. Public writers should receive only validated `VizStats`
objects and must never accept arbitrary metadata dictionaries.

No design can guarantee that private activity is unobservable while publishing
exact private aggregate counts. The honest guarantee is identity redaction, not
anonymity. State that distinction prominently.

## 11. Historical attribution

The historical strategy is conceptually correct:

- explicit trailers and known AI identities produce declared evidence;
- no evidence produces `unknown`;
- `unknown` never becomes `human`;
- source-code style and LLM detection are prohibited;
- manual reconciliation, when added, remains declared rather than verified.

Do not treat branch names, commit-message keywords, bot-like style, or model
classification as attribution. PR descriptions and known branches can be
locators for human review, but should not automatically create an inferred
event without a separately documented policy and user confirmation.

The v0.1 author-email filter is explainable but incomplete for bot-authored
commits. Keeping those commits out is safer than assigning them incorrectly.
The future fix should include commits where a configured human identity appears
as a co-author, with fixtures for bot author + human co-author, spoofed
co-authors, and multiple GitHub noreply forms.

## 12. Visualization architecture and README feasibility

The rendering boundary passes the design review subject to static enforcement:

- Renderers consume validated `VizStats` only.
- Renderers must not scan Git, access SQLite, infer attribution, normalize
  providers, apply privacy policy, or recalculate statistics.
- JSON export is another renderer of the same contract, not a privileged path.
- Dependency tests should be static plus runtime, and public-output tests should
  use canary secrets in every upstream string field.

Static SVG is realistic for GitHub README use. The paired light/dark files and
`<picture>` embedding are established patterns. Deterministic snapshots are
appropriate, but should be supplemented with semantic XML assertions so a
snapshot update cannot silently approve active content, missing accessibility
metadata, or incorrect metric labels.

The renderer should remain one summary card in v0.1. Calendars and multiple
cards multiply labeling, accessibility, snapshot, and privacy obligations
without improving attribution correctness.

## 13. Recommended MVP boundary

### Keep in v0.1

1. Explicit scan of one local Git repository root.
2. User author-email filtering.
3. `AI-*` and verified known-AI co-author trailer parsing.
4. Minimal ACE actor-presence normalization.
5. SQLite as a disposable cache with atomic per-repository replacement.
6. All-time profile aggregation with explicit units.
7. Fail-closed aggregate-only policy.
8. One `VizStats` JSON file and one light/dark summary card pair.
9. Aggregate output as an exact publication preview.
10. Fixture, deduplication, rewrite, privacy, and deterministic-render tests.

### Features to remove from v0.1

- `repository_anonymous` policy value.
- Model, role, contribution-mode, human-review, and audit-time storage.
- Inactive actor/evidence vocabulary presented as supported behavior.
- “Public/private commit” labels without verified visibility.
- Any commitment to write a new ACE Git Notes namespace.
- Any claim that the current unit is a true participation event.

### Features to postpone

- Git Notes and Git AI import until actor-presence semantics are fixed.
- Manual reconciliation and `mixed` actors.
- Bot-authored/human-co-authored identity inclusion.
- Directory discovery, multi-repository batch scanning, and incremental scans.
- Period filters and calendars.
- Provider breakdown, evidence, privacy, and history cards.
- GitHub API discovery, fine-grained PATs, GitHub App, and reusable Action.
- Hosted or interactive dashboard.
- Anonymous per-repository views and stable published repository IDs.
- Raw event export and machine-generated JSON Schema.

### Missing before an OSS v0.1 release

- A LICENSE.
- `docs/ROADMAP.md` with authoritative phase order and exit criteria.
- A concise threat model/privacy guarantee document.
- `CONTRIBUTING.md` with setup, test, ADR, registry-evidence, and compatibility
  expectations.
- A minimal sample profile/output and a clean-install smoke test.
- A compatibility statement for Git object format, remote URL forms, Windows
  paths, and supported Python/Git versions.

## 14. Testing strategy recommendations

The proposed tests are a good baseline. Add the following before the affected
features ship.

### Deduplication and aggregation

- Property tests over randomized commits/events asserting unit invariants.
- Permutation tests: the same evidence set in any adapter/trailer order produces
  identical canonical data and aggregates.
- Same provider/tool twice with different roles/modes: pin whether it is one
  actor presence or two true events.
- Duplicate trailer + co-author + imported note describing one actor presence.
- Multiple providers on one commit, including `unrecognized`.
- Evidence-category sum against its explicitly named population.
- Repository UID collision fixtures: path case, port, scp/URL form, credentials,
  trailing slash, `.git`, Unicode, IPv6, and two clones.

### Rewritten Git history

- Amend, interactive rebase, squash, dropped commit, and force-updated HEAD.
- Cherry-pick: a new SHA is a new commit in the current semantics; document and
  test that this can count again across repositories.
- Non-HEAD branch commits excluded, then included after branch switch.
- Scan failure halfway through replacement rolls back to the prior complete
  state.
- Empty result caused by a misconfigured identity cannot silently erase prior
  cache without a prominent warning/confirmation policy.

### Malformed metadata

- Repeated keys, group boundaries, mixed key casing, whitespace-only values,
  folded lines, CRLF/LF, non-ASCII, invalid encoding, NUL, and oversized values.
- `Human-Only` contradiction with recognized and unrecognized provider/tool.
- Spoofed/near-match AI co-author emails and malformed angle brackets.
- Unknown roles/modes generate safe warnings without values in default output.

### Unknown and historical attribution

- No evidence always yields exactly one unknown record.
- Explicit human-only never arises from absence of AI evidence.
- Unknown plus later manual evidence follows a pinned resolution rule.
- Bot author + configured human co-author stays excluded until the future rule
  is intentionally enabled.
- A negative test proving no source-code content enters attribution logic.

### Deterministic and safe SVG/JSON

- Byte stability across time, locale, timezone, hash seed, and provider input
  order for the same injected `generated_on`.
- XML parse, allowed elements/attributes, no scripts, no `foreignObject`, no
  external URLs, no event-handler attributes, and correct escaping.
- Semantic assertions for metric names, units, denominator text, `<title>`, and
  `<desc>` in addition to snapshots.
- Zero, one, six, seven, and very large provider/count layouts.

### Privacy leakage

- Canary/fuzz every upstream string field with distinctive repo, org, path,
  prompt-like, token-like, URL, email, branch, message, model, tool, and raw
  provider values; scan every byte of public output.
- Scan stdout, stderr, default logs, verbose logs, exceptions, and future CI
  logs separately; do not treat “not in `dist/`” as the whole threat model.
- Config removal, policy flip, duplicate UID policy, symlinked output, output
  directory inside source repo, and `AIPROFILE_HOME` inside a worktree.
- Repeated snapshots demonstrating/documenting what exact-count differencing
  reveals.
- Future token canaries in environment, process errors, HTTP logs, and assets.

### Fixture repositories

Build fixtures programmatically and pin Git author/committer dates, identities,
line endings, object format, and branch. Keep both tiny focused fixtures and one
end-to-end mixed repository. Where SHA-256 Git is unavailable, mark the case
explicitly skipped with a reason rather than silently passing.

## 15. OSS readiness

The project is technically understandable to a new contributor. The README has
a clear position, quickstart, attribution example, privacy summary, and metric
definitions. The source tree mirrors the architecture. ADRs explain the design
rather than merely record choices.

It is not yet OSS-ready:

- no license grant exists;
- the requested roadmap is missing;
- `progress.md` contradicts the Gate 2 timing and is too operational for a
  contributor-facing status page;
- contribution and security/privacy-reporting guidance are absent;
- installation is editable-development-only rather than a released package;
- there is no stable compatibility matrix or upgrade/migration policy for
  users beyond the schema ADR.

Resolve licensing first. Then add a short contributor path: install, run the
full test/lint commands, build a fixture, change the registry with primary
evidence, and write/update an ADR for contract changes.

## 16. Recommended architectural changes

Required before Gate 2 closes:

1. Version and harden repository identity normalization.
2. Rename the current participation unit to actor presence, or add a real stable
   occurrence identity.
3. Replace public/private labels with policy-based labels until visibility is
   verified.
4. Define evidence totals' population and encode all cross-metric invariants in
   `VizStats` validation.
5. Replace input-order conflict resolution with a canonical rule or explicit
   conflict representation.
6. Remove or defer unused v0.1 fields/vocabulary.
7. Expand the privacy model to diagnostics, local storage, CI, and differencing.
8. Publish `ROADMAP.md`, reconcile gate status, and add a LICENSE before OSS
   release.

These changes preserve the architecture. They tighten contracts at the places
where later adapters and collectors would otherwise amplify ambiguity.

## 17. Final recommendation

# GO WITH CHANGES

Gate 2 should close only when the four Critical findings (G2-01 through G2-04)
and the evidence-denominator issue (G2-05) are resolved in the design, the
remaining High findings are either fixed or explicitly accepted with an owner
and target version, and the roadmap/gate chronology is corrected. The current
modular-monolith architecture should remain; no rewrite, hosted system, or
generalized plugin framework is recommended.

### Decision

Approve the architectural direction conditionally. Do not approve the current
repository identity, participation-event semantics, or public/private labels as
stable contracts.

### Risks

This was a design review, not an implementation audit. Although implementation
already exists according to `progress.md` and Git history, no claim is made that
the code conforms to these recommendations or that its test results were
independently reproduced here. External project capabilities can also evolve;
the linked primary sources were checked on the review date.

### Required changes

Resolve the four Critical findings, define the evidence denominator, add the
missing roadmap and threat model, and choose a license before an OSS release.

### Next actions

1. Amend the design documents and ADRs for G2-01 through G2-05.
2. Decide which unused ACE fields move to v0.2.
3. Add the specified contract/privacy fixtures before accepting implementation.
4. Run a separate implementation conformance review against the amended design.

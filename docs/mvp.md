# MVP — the exact v0.1 boundary

Status: finalized for v0.1 (2026-07-14; revised same day after the Phase 0
three-lens adversarial review).

v0.1 is the **first vertical slice**, deliberately narrower than the
proposal's §31 list (which is the v0.x roadmap, not this release):

```text
one local Git repository
→ explicit Git trailer attribution
→ normalized ACE event
→ SQLite storage
→ profile-level provider aggregation
→ one polished deterministic SVG summary card (light + dark)
→ JSON profile export
→ tests
```

## 1. Supported input sources

1. Local Git repositories, added explicitly via `aiprofile scan <path>`.
2. Explicit `AI-*` commit trailers (the ACE trailer convention, ADR-005).
3. `Co-authored-by:` trailers matching the known-AI identity registry
   (exact email; name-prefix condition where the entry requires one —
   ADR-013).
4. Explicit human-only declarations via `AI-Mode: Human-Only` (a trailer
   group with no AI provider/tool — ADR-005's carved exception).

## 2. Unsupported in v0.1 (explicit non-goals)

GitHub App / hosted service / account-wide GitHub API scanning; Claude
Code, Codex, Gemini, Copilot session-log adapters; Git AI line-level
import; Git Notes parsing (namespace reserved:
`refs/notes/ai-collaboration`); multi-repository directory discovery;
`reconcile` (manual attribution); `privacy-preview` as a dedicated
command — **in v0.1 `aiprofile aggregate`'s output IS the privacy
preview**: it prints exactly the post-redaction `VizStats` content that
`render` publishes, nothing else (the dedicated command returns when
per-repository publication views exist, post-v0.1); period filtering
(`--from/--to` — all-time only); interactive dashboard; semantic commit
classification; prompt/transcript storage; LOC attribution;
calendars/breakdown/history cards; org administration; billing; IDE
extensions. Historical attribution is never guessed from code style — in
any version.

## 3. CLI commands

```bash
aiprofile init                # create AIPROFILE_HOME (config + salt + db)
aiprofile scan <path> [--full]
                              # register + scan one local repo; default
                              # publication level: aggregate_only
aiprofile aggregate           # compute + print the published contract
                              # (post-redaction VizStats) = privacy preview
aiprofile render [--out DIR]  # write dist/ assets from validated stats
```

Semantics pinned:

- `scan --full` sets the repository's publication level to `full`,
  persisted in config. A repeat `scan` without `--full` never downgrades
  an existing entry. Other level changes (`aggregate_only`, `excluded`)
  are config edits in v0.1 (documented in README).
- `aggregate` stdout contains only post-redaction content. `-v` adds
  local-only detail (skipped-author counts, unrecognized raw provider
  strings, excluded-repository count) — clearly marked local-only.
- All commands support `-v` and exit 0 / 1 (operational error) / 2 (usage).

## 4. Expected files

```text
<AIPROFILE_HOME>/          # default ~/.aiprofile, override via env AIPROFILE_HOME
  config.json              # identities, salt, repositories:
                           #   [{path, repository_uid, publication_level}]
                           # — the ONLY home of publication policy (schema.md §9)
  aiprofile.db             # SQLite — disposable cache of scan results
```

Do not sync `AIPROFILE_HOME` to dotfiles/backups you publish: config
contains the salt and private repository paths (ADR-009).

## 5. Generated outputs

```text
dist/
  summary-light.svg
  summary-dark.svg
  profile.json             # serialized VizStats (the viz data contract)
```

(No `manifest.json` in v0.1 — nothing consumes it until the GitHub Action
lands, post-v0.1.)

README embedding (documented in README):

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".../summary-dark.svg">
  <img alt="AI collaboration summary" src=".../summary-light.svg">
</picture>
```

(Deviation from the proposal's single `summary.svg`: GitHub renders README
images through its asset proxy; paired light/dark assets via `<picture>` is
the reliable, GitHub-native theming mechanism.)

The summary card shows: reporting period ("All time" in v0.1) · unique
commits scanned · AI-attributed commits / AI participation events / active
AI days as accent hero values · number of AI providers · provider-ranked
bars (top 6 + "+N more") with count and percentage, denominator stated in
the table header · unknown count · evidence chips (events) · privacy
chips (inclusion statement, plus a public/private commit split chip when
both sides are nonzero) · generation date (UTC date only) · metric
definition footnote. Card height is dynamic-but-deterministic (collapses
with few providers; ADR-010).

## 6. Privacy defaults

- New repositories: `publication_level = aggregate_only`; `full` is
  explicit opt-in; publication policy lives in config only; a repository
  absent from config is excluded (fail-closed); duplicate entries for one
  uid resolve to the most restrictive level (schema.md §9).
- Public outputs contain only: counts, canonical provider slugs/display
  names (plus the reserved `unrecognized` bucket — never raw strings),
  evidence totals, period, flags, UTC generation date.
- Never in outputs: repository names/uids/paths, org names, branch names,
  commit shas/messages, raw trailer values, prompts, author emails, local
  paths, tokens, excluded-repository counts, timestamps finer than a date.
- `excluded` repositories are skipped at scan time AND re-excluded at
  aggregation (defense in depth).
- Diagnostics hygiene: default warnings name commit sha + trailer key
  only; values only under `--verbose` (architecture §10).
- The local DB and config stay on the machine; nothing is uploaded.
  Deleting `AIPROFILE_HOME` deletes config + database; generated `dist/`
  assets are user-placed files removed separately (a `purge` helper is a
  post-v0.1 candidate).

## 7. Required tests (v0.1 gate)

1. ACE validation: valid events accepted; invalid actor/evidence/
   activity/roles values rejected; required fields enforced; human/unknown
   null-field rules; `event_id` and `to_dict()` determinism; explicit
   schema version.
2. Trailer parsing: single group, multi-group (multi-AI), value
   normalization, missing optionals, malformed values (safe rejection with
   warnings, no invention), unknown AI-Role tokens dropped-with-warning.
3. Human-only: `AI-Mode: Human-Only` alone → one human event (declared);
   contradictory group (human_only + AI provider) → discarded with
   warning.
4. Co-authored-by: registry match → event; name-prefix-conditional entry
   honored; unknown co-author → nothing.
5. No-evidence commit → exactly one unknown event (never human).
6. Duplicate scan idempotence: byte-identical aggregates after re-scan.
7. Unique commits vs participation events (multi-AI fixture: 1 commit,
   2 AI events, providers each credited once).
8. Unknown vs human separation in aggregates.
9. Privacy leak test: aggregate-only fixture repo's name/path/uid/author
   email AND a distinctive unrecognized `AI-Provider` raw value absent
   from every byte of dist/ (the raw value counted under `unrecognized`).
10. Publication-policy resolution: config level flip after scan (no
    rescan) is respected; repo removed from config → excluded from
    aggregates; most-restrictive rule for duplicate uid entries.
11. SVG determinism: byte-identical snapshots (light + dark).
12. SVG accessibility: `<title>`, `<desc>`, metric labels present.
13. Zero-state rendering (new user, no data) is valid and readable.
14. Malformed repository handling: non-repo path → clear `GitError`,
    exit 1.
15. Rewritten history: amend a fixture commit, rescan → counts unchanged,
    old sha absent (ADR-014).
16. Migrations: fresh DB reaches head; version recorded; re-open is a
    no-op.
17. JSON export stability: byte-identical `profile.json` for identical
    inputs; schema version present.

Integration fixtures (programmatically built git repos): human-only commit
(no trailers → unknown), Claude AI-* trailer commit, Codex AI-* trailer
commit, Claude co-author commit, multi-AI commit, malformed trailer commit,
human-declared commit (`AI-Mode: Human-Only`), unrecognized-provider
commit, private aggregate-only repo, duplicate-scan run, amended-commit
rescan.

## 8. Definition of done (v0.1)

```bash
pip install -e ".[dev]"
aiprofile init
aiprofile scan ~/some/repo
aiprofile aggregate
aiprofile render
```

produces the three dist/ assets; the full test suite passes locally with
the count stated; every §7 test exists; the summary card renders correctly
at GitHub README width (~830px) in light and dark; privacy tests 9–10
pass; docs (README quickstart + this docs set) are consistent.

## 9. Known limitations (v0.1)

- Single-repo scans, full re-enumeration + atomic replace each time (fine
  for typical repo sizes; incremental scanning is post-v0.1, constrained
  by ADR-014's forward notes).
- Only trailer evidence; commits made by AI tools that write no trailer
  are honestly `unknown`.
- Bot-*authored* commits are skipped: GitHub Copilot cloud agent, Devin,
  and Jules (its default mode) author commits themselves with the human as
  co-author, and ADR-015 counts commits by the user's author email.
  Post-v0.1 fix: co-author-based identity inclusion (landscape.md §2.3).
- No `mixed` producer, no manual reconciliation yet; superseded scan rows
  are not retained (DB is a cache).
- `human` category is only populated via explicit `AI-Mode: Human-Only`
  trailers — expect ~0 for most users; the card therefore reports unknown
  prominently instead of pretending human counts are known.
- Provider registry recognizes a seeded set of verified spellings;
  unrecognized spellings aggregate under the `unrecognized` bucket in
  public outputs (raw values visible only locally via `aggregate -v`).
- Active days use the commit author's local date (documented; not
  configurable yet). Reporting period is all-time.
- `roles`/`contribution_mode`/`human_reviewed` are captured but not yet
  rendered (schema.md header stance; consumed by post-v0.1 cards).

## 10. Post-v0.1 (ordered candidates)

1. Git Notes adapter (`refs/notes/ai-collaboration`) + git-ai import
   (`imported` evidence tier becomes live).
2. `aiprofile reconcile` (manual declarations; `mixed` producer; requires
   the manual-event-preservation change to the scan replace step —
   schema.md §14) and `Assisted-by:`/`Generated-by:` disclosure-trailer
   parsing (kernel/Fedora/OpenInfra/Apache conventions — landscape.md
   §2.2), plus co-author-based identity inclusion for bot-authored
   commits.
3. Provider contribution calendars + breakdown/evidence/privacy cards
   (consuming the captured roles/mode/review fields), period filtering
   (`--from/--to` with the author-local-date rule), dedicated
   `privacy-preview` with per-repository views, `purge` helper.
4. Multi-repo config scanning + incremental scan.
5. GitHub public-API discovery, then Action packaging (+ `manifest.json`
   when the Action consumes it).

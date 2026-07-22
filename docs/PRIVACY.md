# Privacy guarantees and threat model

Plain statement of what this tool protects, what it deliberately does not
protect, and where the residual risks live (Gate 2 finding G2-09; the
design mechanics are in architecture.md §3 and ADR-009).

## The guarantee, stated honestly

**Identity redaction, not anonymity.** Public outputs (`dist/`) are
structurally unable to contain repository names/uids/paths, organization
names, branch names, commit SHAs or messages, author emails, raw trailer
strings, prompts, tokens, or timestamps finer than a UTC date — the
renderer/exporter input type (`VizStats`) cannot represent them, and leak
tests grep every published byte for canary values.

What is NOT guaranteed: that your aggregate-only activity is
unobservable. Published exact counts change when your activity changes.
An observer comparing snapshots over time can infer *when* aggregate-only
activity occurred, roughly *how much*, and *which provider* appeared —
especially for a profile with a single aggregate-only repository. If that
inference matters to you, publish less often, exclude the repository, or
wait for the planned coarse mode (rounding/minimum thresholds — ROADMAP).

Publication labels are **policy-based**: "explicitly publishable" means
you ran `scan --full`; it is not a claim that the repository is public on
GitHub, and "aggregate-only" is not a claim that it is private.

## Data inventory

| data | where it lives | leaves the machine? |
|---|---|---|
| repo paths, display names, author emails, commit SHAs/dates, trailer values | `AIPROFILE_HOME` (config.json + aiprofile.db) | never (no network code exists in v0.1) |
| salt (local uid derivation) | config.json | never; must never back future *published* anonymous IDs (ADR-009) |
| counts, provider slugs, evidence totals, flags, UTC date | `dist/` assets | yes — that is the product |
| prompts, transcripts, diffs, message bodies | **not collected at all** | — |

## Threat surfaces and mitigations

- **Published assets** — structural `VizStats` boundary; unrecognized raw
  strings collapse to a reserved bucket; leak tests (mvp.md §7 tests
  9–10).
- **stdout/stderr/logs** — default diagnostics carry scan-local ordinals
  and trailer keys only (never SHAs, values, paths — G2-08); SHAs/values
  require `--verbose`; future CI/Action mode must run at default
  verbosity (ADR-011). Crash tracebacks may contain paths — they go to
  the terminal; do not paste them publicly unredacted.
- **CI logs (future Action)** — treated as public output; same rules as
  assets, enforced before the Action ships.
- **Local storage** — `AIPROFILE_HOME` holds private data by design:
  don't sync it into published dotfiles; deleting it deletes config+DB
  (generated `dist/` copies are yours to remove). Implemented hardening:
  owner-only file permissions (0o700 on `AIPROFILE_HOME`, 0o600 on
  `config.json` and `aiprofile.db`, best-effort — POSIX enforces this,
  Windows has no equivalent bits so `os.chmod` there is a documented
  no-op) and a stderr warning at `init` time when `AIPROFILE_HOME` sits
  inside a git worktree. Still planned (ROADMAP): symlink refusal.
- **Snapshot differencing** — see the guarantee above; inherent to
  publishing exact counts.
- **Future anonymous repo IDs** — must use a dedicated secret, never the
  local salt (low-entropy names + leaked config would de-anonymize
  retroactively; ADR-009).
- **Future raw-event exports** — any such tool must pass the same leak
  gates as `dist/`; provenance rows are local-only by schema (§6.2).

## Reporting

Suspected leak: open an issue titled "privacy report" WITHOUT the
sensitive details; the maintainer follows up privately. Fixes to leak
paths ship with a regression test that failed pre-fix.

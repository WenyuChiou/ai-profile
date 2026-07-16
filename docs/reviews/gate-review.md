# Gate 7 remediation verification review

Date: 2026-07-16

Review range: `99333087d603c5de9f96d7fa44f91b6db3062c87..73279cd5897eb9e669a863f60ebc47d3e249bec7`

Reviewer posture: independent Principal Software Engineer; verification only. No production code, test code, architecture, schema, or MVP design was changed during this review.

## Executive summary

The remediation is narrow, architecture-consistent, and generally well tested. Four of the five Gate 7 dispositions are verified closed: timestamp merging is permutation-pure under the documented strongest-leaf order; hero and provider percentages do not fabricate endpoint values; the revised light-theme evidence mark clears the stated contrast threshold; and the sanctioned regeneration command updates both snapshots and README sample assets without drift. The full suite passes with the expected count, Ruff is clean, both evidence ramps pass the independent palette validator, and a fresh synthetic repository produced privacy-clean public assets.

The High privacy finding is not fully closed. `VizStats` validates nested values only during `__post_init__`, but it neither enforces the declared nested dataclass types nor reconstructs the input into an owned immutable graph. A mutable `list` passes for the tuple-annotated `providers` field; more importantly, even a tuple containing a mutable duck-typed row passes, as does a mutable period-like object. After successful construction, changing either display text or the period label is published by both `render_summary()` and `dumps_stats()` without revalidation. This directly contradicts the new architectural guarantee that any validated instance is structurally unable to carry arbitrary private text, regardless of who constructs it.

A second, Low validation gap remains in `generated_on`: the Unicode-aware `\d` pattern with `$` accepts Unicode digit confusables, a trailing newline, and impossible calendar dates such as `2026-99-99`. The supported production builder supplies a real ASCII UTC date, so this is not a normal-path leak, but the contract and documentation claim more than the validator guarantees.

No redesign is required. Both findings are localized contract-hardening fixes, but the reproduced SVG/JSON publication path makes advancement unsafe until the High finding is closed and regression-tested.

## Review basis and verification evidence

The review covered repository guidance; architecture, ACE schema, MVP, privacy threat model, roadmap, progress, proposal, landscape and non-duplication analysis; all ADRs; prior Gate review and disposition records; README and CONTRIBUTING; the complete pinned diff; affected production code; affected tests; snapshots; and committed sample assets.

Commands and observed results:

- `git rev-parse HEAD` -> `73279cd5897eb9e669a863f60ebc47d3e249bec7`.
- `git status --short` before review -> no output (clean working tree).
- `python -m pytest tests -p no:cacheprovider` -> `323 passed, 1 skipped in 29.36s` (exit 0). Two unrelated environment warnings were emitted by globally installed `requests`/`langsmith`; no project test failed.
- `python -m ruff check src tests` -> `All checks passed!`.
- `python tests/unit/test_render_summary.py` -> `Wrote 8 snapshot files` and `Wrote 2 sample assets`; the subsequent `git status --short` remained empty.
- Light ordinal palette validator (`#033d8b,#0550ae,#0969da,#218bff` on `#f6f8fa`) -> `ALL CHECKS PASS`.
- Dark ordinal palette validator (`#a5d6ff,#58a6ff,#388bfd,#1f6feb` on `#161b22`) -> `ALL CHECKS PASS`.
- Snapshot/asset diff inspection -> exactly three light snapshots and the light README sample changed, with two occurrences per file of `#8c959f` -> `#6e7781`; no unrelated geometry, text, or dark-theme drift.
- Public artifact sweep over all snapshots and both committed samples -> zero matches for 40-hex SHAs, emails, local paths, non-xmlns URLs, or GitHub owner/repository paths.
- Fresh end-to-end synthetic scan (`init` -> `scan` -> `render`) with distinctive repository name, organization, remote URL, local path, raw provider, commit message, author email, SHA, repository UID, and salt -> all commands returned 0; all three dist files were byte-swept; `leaks []`; the raw provider appeared only as the public `unrecognized` bucket.

### Direct adversarial probes

- Mutable validated-boundary probes: a valid one-element provider list could be replaced after construction (`svg_leak=True`, `json_leak=True`). Stronger probes kept `providers` as a tuple but supplied a mutable row-like object, then changed its `display_name`; and supplied a mutable period-like object, then changed its `label`. Both tuple-row and period probes likewise produced `svg_leak=True` and `json_leak=True`.
- `dataclasses.replace()` probe with an invalid tuple display name -> correctly rejected with `RenderError`; this confirms the gap is mutability/type enforcement, not the new string comparison itself.
- Date probe -> `2026-07-15`, `2026-99-99`, full-width `２０２６-０７-１５`, Arabic-Indic `٢٠٢٦-٠٧-١٥`, and `"2026-07-15\n"` were all accepted.
- Timestamp probe over all six permutations of three same-identity leaves, including equal-rank/equal-locator conflicts and cross-offset representations -> one canonical output; strongest-leaf/value tie-break winner stable; `merged=True` preserved.
- Percentage probe -> `1/201` renders `<1%`, `200/201` renders `>99%`, exact zero/total remain `0%`/`100%`; 10,000- and 100,000-digit integer ratios also returned the correct compact endpoint labels without overflow.
- Renderer determinism/security -> full pinned state/theme suite passed XML parsing, element allowlist, active-content rejection, coordinate hygiene, dynamic height, width, font-size, and byte-exact snapshot tests.

## Findings

### H-01 — High — The validated `VizStats` object graph is not structurally immutable

**Description:** `src/aiprofile/viz.py:85-96` declares frozen nested dataclasses and a `tuple[ProviderRow, ...]`, but `_validate()` does not enforce those runtime types or defensively rebuild the graph. It accesses attributes by duck typing at `src/aiprofile/viz.py:100-120` and `src/aiprofile/viz.py:194-220`. Consequently, an ordinary provider list passes; a tuple containing a mutable row-like object also passes; and a mutable period-like object passes. The frozen outer dataclass prevents only reassignment of its direct attributes. It does not freeze caller-owned nested objects. Render and export trust the previously validated graph and publish later mutations.

Reproduction:

```python
from dataclasses import dataclass
from aiprofile.render.summary_svg import render_summary
from aiprofile.render.themes import THEMES
from aiprofile.viz import (
    EvidenceTotals, Period, PrivacySplit, Totals, VizStats, dumps_stats,
)

@dataclass
class MutableRow:
    provider: str = "anthropic"
    display_name: str = "Claude"
    attributed_commits: int = 5
    actor_presences: int = 6
    active_days: int = 3

row = MutableRow()
stats = VizStats(
    "0.1.0", Period(None, None, "All time"),
    Totals(10, 5, 6, 0, 5, 3), (row,), 1,
    EvidenceTotals(0, 6, 0, 0, 4, 10),
    PrivacySplit(10, 0, False), "2026-07-15",
)  # accepted even though row is not ProviderRow
row.display_name = "SecretOrg-PrivateRepo"
assert "SecretOrg-PrivateRepo" in render_summary(stats, THEMES["github-light"])
assert "SecretOrg-PrivateRepo" in dumps_stats(stats)
```

The same probe succeeds with a mutable `period` object whose initially valid `label` is changed after construction. Therefore converting only the provider container to a tuple would not close the boundary.

This falsifies the new claims in `docs/architecture.md:109-114`, `docs/progress.md:229-233`, and the Gate 7 disposition that a validated instance cannot carry arbitrary private text regardless of who constructed it. The supported `privacy.build_viz_stats()` path currently supplies a tuple and the fresh end-to-end privacy probe is clean, but the remediation explicitly broadened the guarantee beyond that single constructor.

**Impact:** Library callers, future adapters, tests, or refactors can accidentally retain and mutate nested objects after validation — including a provider list, a row-like object held inside a tuple, or a period-like object — exposing repository names, organization names, prompts, commit messages, paths, or other arbitrary strings in both public SVG and JSON. The central structural privacy guarantee is therefore not enforced as documented.

**Recommendation:** Make `VizStats` own a fully immutable validated graph. Either reject unexpected nested types (`Period`, `Totals`, every `ProviderRow`, `EvidenceTotals`, and `PrivacySplit`, plus a tuple container), or defensively reconstruct all nested inputs into the exact frozen dataclasses and a new tuple before exposing the instance. Add regressions for an externally retained provider list, a tuple containing a mutable row-like object, and a mutable period-like object; after attempted mutation, prove the validated graph and rendered/exported bytes cannot change. Keep enforcement centralized in `VizStats`; do not add renderer-specific sanitization.

### L-01 — Low — `generated_on` accepts non-canonical and invalid dates

**Description:** `src/aiprofile/viz.py:34` defines `_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")`, and `src/aiprofile/viz.py:124` uses `.match()`. Python `\d` accepts Unicode decimal digits, `$` matches before a final newline, and the pattern checks shape rather than calendar validity. Direct construction accepted full-width and Arabic-Indic digits, `"2026-07-15\n"`, and `2026-99-99`.

**Impact:** The normal production builder supplies a real UTC date, so this does not presently expose arbitrary alphabetic text or corrupt aggregation. It does, however, violate the documented ASCII `YYYY-MM-DD`/UTC-date contract and weakens the Gate's claim that every public string field is tightly constrained. Non-canonical output can also break downstream consumers expecting ISO dates.

**Recommendation:** Require a plain string in canonical ASCII ISO date form and validate calendar semantics, for example with strict `[0-9]` matching plus `date.fromisoformat()` and a round-trip equality check. Add regressions for Unicode digits, a final newline, invalid month/day, and a valid leap day.

## Verified areas without findings

### Architecture and dependency direction

- Collection, schema, storage, aggregation, privacy, visualization data, rendering, and export responsibilities remain separated.
- Renderers consume `VizStats` only; they do not scan Git, access SQLite, infer attribution, or recalculate aggregates.
- The provider display mapping moved to schema-owned vocabulary without introducing a cycle. Registry normalization behavior remains unchanged, and render/export import fences pass.
- The remediation adds no runtime dependency, network path, GitHub authentication, or hosted component.

### Schema and merge semantics

- `activity.timestamp` now resolves through the same strongest-leaf rank as other scalar conflicts. Equal-rank ties are deterministic, and input permutations produce byte-identical canonical events.
- `merged` remains operational envelope state, participates in equality/hash, stays out of canonical payload and persistence, and the leaf-only merge boundary remains intact.
- Event identity, evidence precedence, unknown-versus-human separation, and the explicit-evidence-only rule are unchanged. No source-code-style inference exists.

### Aggregation correctness

- Unique commits, AI-attributed commits, AI actor presences, provider-attributed commits, active author-date days, and evidence records remain separately named, validated, and rendered.
- One multi-AI commit counts once in unique/AI-attributed commit totals while contributing multiple actor presences and potentially multiple provider commit credits.
- Evidence categories sum over all ACE records and remain distinct from commit and presence units.
- Duplicate scans, rewritten history, merge permutations, unknown commits, and fixture-repository cases pass.

### Privacy and security on the supported path

- Aggregate-only activity withholds repository identity; excluded repositories fail closed; unrecognized provider text collapses before publication.
- The fresh end-to-end dist sweep and committed snapshot/sample sweeps found no repository names, paths, organizations, URLs, prompts/messages, author emails, SHAs, UIDs, or salt.
- SVG output remains deterministic, XML-well-formed, allowlisted, free of event attributes/external references, and generated from validated aggregate data.
- v0.1 contains no GitHub token handling, authentication, telemetry, or network client.

### Visualization and documentation

- The static SVG strategy remains feasible for GitHub README `<picture>` embedding; width, dynamic height, light/dark outputs, accessibility text, and deterministic samples are pinned.
- `<1%`/`>99%` labels are semantically consistent with their count/bar states and XML-safe.
- The revised light unknown mark clears 3:1; both ordinal ramps independently pass all validator checks.
- Moving arbitrary-name truncation and XML escaping tests to helper-level coverage is acceptable once the structural boundary is actually immutable: those helpers directly own the behaviors, while public-vocabulary rejection is separately tested.
- CONTRIBUTING now documents one authoritative regeneration command, and the byte-exact docs asset drift guard passes.

### MVP scope, non-duplication, and OSS readiness

- No feature creep entered the range: no Git Notes implementation, Git AI line attribution, GitHub API client, generic profile statistics, contribution graph, additional card, dashboard, or session-log adapter.
- The project continues to reuse provenance conventions and renderer patterns without reproducing Git AI, generic README statistics generators, or contribution-snake tooling.
- README, privacy threat model, contribution guidance, ADRs, roadmap, sample assets, and current limitations remain understandable to a new contributor.
- The roadmap honestly retains packaged-install smoke testing, release packaging, permission/symlink hardening, and wider diagnostics canary sweeps as pre-release work.

## Severity summary

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 1 |
| Medium | 0 |
| Low | 1 |

## Final recommendation

NOT READY

# v0.4.3 Public Beta promotion dogfood

Date: 2026-07-26
Evaluation baseline:
`773113562871a99da02d50056a118f993794baac`

## Executive result

The final sealed-box dogfood gate passed. All four roles used only the
canonical `README.md` and the same clean-Linux candidate wheel:

```text
ai_profile_cli-0.4.3-py3-none-any.whl
SHA-256 b3baebac895927897ef39ae86227d3ed89455ed1d925be74cc6cc385468781a8
```

| Role | Result | README-external hints | Blocking friction |
|---|---|---:|---:|
| New user | PASS | 0 | 0 |
| Privacy-sensitive user | PASS | 0 | 0 |
| Multiple-provider user | PASS | 0 | 0 |
| Profile publisher | PASS | 0 | 0 |

Gate totals:

- roles completed: 4/4;
- exact candidate-digest matches: 4/4;
- installation failures: 0;
- configuration dead ends: 0;
- privacy-canary hits: 0/480 comparisons;
- hand-derived aggregation mismatches: 0;
- dashboard filter mismatches/errors/external requests: 0;
- local GitHub Pages configuration dead ends: 0.

Earlier runs against `c0e34bd4...` and `29e76e3f...` were invalidated when
canonical line endings and then the zoom-safe tooltip patch changed the
wheel bytes. No result from either superseded set is counted.

## Isolation and method

Every role used a fresh temporary Git repository, virtual environment, and
`AIPROFILE_HOME`. Product source, tests, other project documents, other-role
artifacts, and orchestrator workflow hints were prohibited. Raw commands,
exit codes, stderr, timings, outputs, screenshots, and reports are retained
outside Git under:

```text
.artifact/promotion/dogfood-v043/
```

The no-product-context synthesizer read only the four natural-language
reports and found no contradiction. The root reviewer then independently
recomputed the following values from raw JSON, command ledgers, output
inventories, and sweep records rather than trusting the synthesis.

## Role evidence

### New user

The role installed the exact wheel offline, verified `aiprofile 0.4.3`, and
completed `init -> scan -> aggregate -> render` on the first valid run.

Observed:

- commits scanned: 2;
- unique AI-attributed commits: 1;
- actor presences: 1;
- human declarations: 0;
- unknown commits: 1;
- outputs: exactly 8.

Evidence:
`.artifact/promotion/dogfood-v043/new-user/report.md`.

### Privacy-sensitive user

The role exercised all three publication levels:

| Mode | Scanned | AI commits | Presences | Daily rows | Result |
|---|---:|---:|---:|---:|---|
| `aggregate_only` | 1 | 1 | 1 | 0 | Totals retained; dates withheld |
| `full` | 1 | 1 | 1 | 1 | Publishable date retained |
| `excluded` | 0 | 0 | 0 | 0 | Repository omitted |

Twenty unique canaries covered repository and organization identities,
absolute and relative paths, prompt, commit subject/body, emails, URL,
branch, source content, raw trailer, full and short SHA, salt, and repository
UID. Each canary was searched as raw UTF-8 bytes across all eight public
outputs in all three modes:

```text
20 canaries * 8 outputs * 3 modes = 480 comparisons
hits = 0
```

An intentional UTF-8 BOM produced a controlled parse failure; restoring the
exact configuration bytes recovered without changing the salt or repository
UID. Evidence:
`.artifact/promotion/dogfood-v043/privacy-user/report.md` and
`evidence/result.json`.

### Multiple-provider user

The fixture contained four commits: one unknown, one `Human-Only`, one with
Anthropic and OpenAI actor groups, and one Anthropic-only declaration.

| Metric | Hand-derived | Observed |
|---|---:|---:|
| Commits scanned | 4 | 4 |
| Unique AI-attributed commits | 2 | 2 |
| AI actor presences | 3 | 3 |
| Claude commits / presences / active days | 2 / 2 / 2 | 2 / 2 / 2 |
| OpenAI commits / presences / active days | 1 / 1 / 1 | 1 / 1 / 1 |
| Human-declared commits | 1 | 1 |
| Unknown commits | 1 | 1 |
| Evidence declared / unknown / total | 4 / 1 / 5 | 4 / 1 / 5 |

The shared commit remained one unique AI commit and two actor presences.
All AI, Claude, and OpenAI dashboard filters matched the same unit
separation. Browser mismatches, console errors, page errors, and external
requests were all zero. Evidence:
`.artifact/promotion/dogfood-v043/multi-provider/report.md`,
`observed-profile.json`, and `dashboard-check.json`.

### Profile publisher

The role built a disposable `USERNAME/USERNAME` repository on `main`,
generated all eight assets, and validated:

- compact and full light/dark Profile sources;
- clickable dashboard link and equivalent alt purpose;
- all relative asset targets;
- GitHub Pages `main` plus `/ (root)` mapping;
- strict UTF-8, SVG parsing, self-contained dashboard, and zero remotes.

There was no local Pages or configuration dead end. A real push and Pages
deployment were intentionally reserved for the maintainer Profile gate after
PyPI publication. Evidence:
`.artifact/promotion/dogfood-v043/profile-publisher/report.md`.

## Exact-wheel browser evidence

The final wheel rendered the headed-browser fixture used by the accessibility
gate. Retained results:

```text
viewport/theme states: 12
provider states: 36
widths: 320, 390, 768, 1440
themes: light, dark, system
accessibility dates visible per state: 294
maximum document overflow: 0
minimum active/legend contrast: 5.011:1
minimum metadata contrast: 5.010:1
200% rendering: document overflow 0; calendar locally scrollable
keyboard/focus/hover/touch/reduced-motion: PASS
console errors / external requests: 0 / 0
```

The contrast check sampled the browser-composited background beneath the
metadata rather than comparing raw tokens. The 200% rendering probe also
confirmed the focused tooltip remained within the viewport.

Evidence:
`.artifact/promotion/browser-v043/exact-wheel-browser/browser-gate.json` and
its retained screenshots.

## Root reconciliation

```text
candidate digest: b3baebac...781a8
new user: commits=2 ai=1 presences=1 unknown=1 outputs=8
privacy: modes=3 comparisons=480 hits=0 outputs-per-mode=8
multi-provider: commits=4 ai=2 presences=3 human=1 unknown=1 evidence=5
dashboard: mismatches=0 errors=0 external-requests=0
publisher: outputs=8 references=valid Pages-local-preconditions=valid
```

## Findings and dispositions

### High — Dogfood must identify the exact published byte sequence

- **Impact:** A role pass on a superseded wheel cannot authorize release.
- **Evidence:** Windows-worktree CRLF and a later tooltip patch each changed
  the wheel digest.
- **Recommendation:** Invalidate the complete role set after any production
  byte change and require a first-action SHA-256 match.
- **Disposition:** Fixed. Only the four final-wheel reports above count.

### Medium — Fixed tooltip clamp could clip at narrow zoomed widths

- **Impact:** Focused or tapped date evidence could be partially unreadable.
- **Evidence:** Independent visual review traced the fixed 140 px center
  clamp.
- **Recommendation:** Clamp using the measured tooltip half-width and a
  viewport margin; retain exact-wheel runtime evidence.
- **Disposition:** Fixed and verified at the 200% rendering gate.

### Low — Isolated evaluation homes trigger a conservative warning

- **Impact:** Roles see a warning because their private test homes live
  beneath the enclosing ignored worktree.
- **Recommendation:** Keep the warning; it accurately discourages real users
  from publishing private state.
- **Disposition:** Accepted as privacy-conservative, non-blocking friction.

## Dogfood verdict

The final candidate passes the dogfood gate: 4/4 roles, one exact digest,
zero external hints, zero privacy leaks, exact aggregation semantics, exact
output sets, and no local configuration or Pages dead end.

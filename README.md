<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/banner-dark.svg">
  <img alt="ai-profile - prove your AI collaboration, privately" src="docs/assets/banner-light.svg" width="100%">
</picture>

# ai-profile

[![tests](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml/badge.svg)](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)](pyproject.toml)

English · [繁體中文](README.zh-TW.md)

Local-first, profile-level **AI collaboration analytics** for your GitHub
README. `aiprofile` scans your local Git repositories for *explicit* AI
provenance — `AI-*` commit trailers and known AI co-author trailers (Claude
Code, Codex, Cursor, Copilot, Aider, …) — normalizes it into a common event
schema (ACE), stores it in a local SQLite database, and renders privacy-safe
SVG cards + a JSON summary you can embed in a GitHub Profile README.

## What it looks like

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/summary-sample-dark.svg">
  <img alt="Sample AI collaboration summary card rendered from synthetic data" src="docs/assets/summary-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/heatmap-sample-dark.svg">
  <img alt="Sample collaboration heatmap: intensity is total commits including your own, hue is the day's AI share" src="docs/assets/heatmap-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/badge-sample-dark.svg">
  <img alt="AI-assisted share badge, verified from git provenance" src="docs/assets/badge-sample-light.svg">
</picture>

Samples rendered from a synthetic showcase fixture; no real repository
data. The heatmap is the view no other tool draws: intensity is your
whole commit rhythm (your own commits included), hue is how much of
each day was AI collaboration.

It is **not** an AI code detector: nothing is ever inferred from code style.
Commits without explicit evidence are honestly reported as `unknown` —
never silently counted as human, never guessed into a provider.

As far as we know it is the only free, local-first, cross-repository,
explicit-provenance profile aggregation tool (line-level attribution
belongs to tools like git-ai; full analysis:
[landscape & positioning](docs/landscape.md)).

Status: **v0.3** — the v0.1 vertical slice (one repo → trailers → SQLite →
aggregate → summary card) plus provider brand identity (15 marks, two
icon sources), the publishable-only isometric daily calendar, and the
collaboration-ratio heatmap + badge. Design docs live in
[`docs/`](docs/):
[architecture](docs/architecture.md) · [ACE schema](docs/schema.md) ·
[MVP boundary](docs/mvp.md) · [landscape & non-duplication](docs/landscape.md)
· [decision records](docs/decisions/).

## Install

Compatibility: Python 3.11–3.14 · git ≥ 2.17 · SHA-1 repositories
(SHA-256 object format fails with a clear error in v0.1) · Windows,
macOS, Linux. Zero runtime dependencies.

```bash
pip install git+https://github.com/WenyuChiou/ai-profile
```

The PyPI package will be **`ai-profile-cli`** (upload in progress;
PyPI's name-similarity rule blocks `ai-profile` because an unrelated
project already holds `aiprofile` — and `pip install aiprofile` gets
you that other project, not this one). Once live:
`pip install ai-profile-cli`.

From a clone (development):

```bash
pip install -e ".[dev]"   # dev extras = pytest + ruff + hypothesis
```

## Quickstart

```bash
aiprofile init            # run from INSIDE one of your repos - seeds your
                          #   identity from that repo's git config user.email
aiprofile scan ~/my/repo  # register + scan (replace with a real path;
                          #   private-safe default)
aiprofile aggregate       # print the published stats = privacy preview
aiprofile render          # write dist/: summary + heatmap + badge SVG
                          #   pairs (light/dark) + profile.json
```

Run **one `render` at a time per output directory** — concurrent renders
into the same directory are unsupported and can publish assets from
different scans.

Only commits authored by your configured identities count (seeded from
`git config user.email` at init; add more emails in
`~/.aiprofile/config.json`).

Run `aiprofile init` **from inside one of your own repos**: identity
seeding reads `git config user.email` in the directory where you run
it, so running from an unrelated folder can seed your global email
instead of the one you actually commit with (or none at all). Check
the seeded identities in `~/.aiprofile/config.json` after init.

Embed in your profile README:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="dist/summary-dark.svg">
  <img alt="AI collaboration summary" src="dist/summary-light.svg">
</picture>
```

## Declaring AI participation (trailers)

**If you commit through Claude Code, Codex, Cursor, Copilot, Aider, or
Amp, you likely have nothing to do**: tools that add their own
co-author trailer (e.g. Claude Code's
`Co-Authored-By: Claude <noreply@anthropic.com>`) are recognized
automatically via a verified identity registry.

For everything else — or for richer detail (model, role, review
status) — declare explicitly with `AI-*` trailers; product names like
`Kimi`, `Claude`, or `Gemini` resolve too:

```text
feat: add aggregation service

AI-Provider: Anthropic
AI-Model: Claude-Sonnet
AI-Tool: Claude-Code
AI-Role: implementation, documentation
AI-Mode: AI-Assisted
AI-Reviewed-By: Human
```

One commit can carry
several **AI actor presences** ("Claude implements, Codex reviews" =
1 unique commit, 2 presences — the two metrics are never conflated; a
presence means "this provider/tool appeared in this commit", so Claude
implementing AND reviewing one commit counts once, honestly). A commit
that is explicitly yours alone: `AI-Mode: Human-Only`.

## Privacy model (defaults are safe)

- Everything stays on your machine; no network calls, no telemetry.
- Every scanned repository defaults to `aggregate_only`: it contributes
  counts, never its name. `scan --full` is the explicit opt-in that marks
  a repository's counts as explicitly publishable (a policy decision you
  make — NOT a claim about GitHub visibility); `excluded` removes a repository entirely.
- Publication policy lives in `config.json` only — edit it and the next
  `aggregate`/`render` respects it, no rescan needed.
- Public outputs contain counts, provider names, evidence totals, and a
  UTC date. Never: repository names/paths, org names, branches, commit
  SHAs or messages, raw trailer strings, emails, or timestamps finer than
  a date. Unrecognized provider spellings are bucketed as "Unrecognized"
  in public assets (see the raw values locally with `aggregate -v`).
- `aiprofile aggregate` prints exactly what would be published — it *is*
  the privacy preview.
- Honest limit: aggregate-only publication is **identity redaction, not
  anonymity**. Repository names never appear, but repeatedly published
  exact counts let an observer infer *when* your aggregate-only activity
  changed and which provider appeared. Full threat model:
  [`docs/PRIVACY.md`](docs/PRIVACY.md). Output labels are policy-based
  ("explicitly publishable" / "aggregate-only"), never claims about
  GitHub visibility.
- Do not sync `~/.aiprofile` into published dotfiles (it holds a salt and
  private repository paths). Deleting that directory deletes all local
  data; generated `dist/` files are yours to remove separately. On
  POSIX the directory and files are owner-only (0700/0600); Windows
  has no equivalent permission bits, so there `os.chmod` is a
  documented no-op — the data still never leaves your machine.

## Metrics, honestly labeled

- **AI-attributed commits** — unique commits with ≥1 explicit AI actor
  presence. Per-provider counts may sum to more than this (multi-AI
  commits) and are labeled as provider-attributed commits, never as
  unique totals. Evidence chips state their population; percentages state
  their denominator; active days are commit author dates.
- **Evidence quality** is first-class: `verified > declared > imported >
  inferred > unknown`. v0.1 produces `declared` (trailers) and `unknown`.

## License

MIT — see [LICENSE](LICENSE). Contributions welcome under
[CONTRIBUTING.md](CONTRIBUTING.md).

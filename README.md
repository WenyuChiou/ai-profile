<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-dark.svg">
  <img alt="" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-light.svg" width="100%">
</picture>

# ai-profile

## Show the evidence behind your AI collaboration.

`ai-profile` turns explicit Git provenance across your local repositories
into privacy-safe GitHub Profile cards and a filterable provider
dashboard—without uploading source code or guessing attribution.

**[Explore the live dashboard →](https://wenyuchiou.github.io/WenyuChiou/dist/dashboard.html)**
· **[Generate yours in four commands](#quickstart)**

[![PyPI](https://img.shields.io/pypi/v/ai-profile-cli.svg)](https://pypi.org/project/ai-profile-cli/)
[![tests](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml/badge.svg)](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/WenyuChiou/ai-profile/blob/main/LICENSE)
[![python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)](https://github.com/WenyuChiou/ai-profile/blob/main/pyproject.toml)

[English](https://github.com/WenyuChiou/ai-profile/blob/main/README.md) ·
[繁體中文](https://github.com/WenyuChiou/ai-profile/blob/main/README.zh-TW.md)

- **Explicit evidence:** attribution comes from `AI-*` trailers and
  verified AI co-author identities—not source-code style.
- **Local-first privacy:** scanning, aggregation, and rendering happen on
  your machine; repository identities stay out of public assets.
- **Profile-ready:** one render produces theme-aware SVG cards, a
  self-contained dashboard, and a machine-readable public summary.

`ai-profile` is not an AI code detector. Commits with no explicit evidence
stay `unknown` (shown as **Unattributed** in the UI); they are never silently
counted as human or assigned to a provider. Add `AI-*` trailers to future
commits when you want their AI participation recorded.

## A real GitHub Profile example

This card contains the maintainer's real public aggregate data. Select it to
open the provider-filterable dashboard.

<a href="https://wenyuchiou.github.io/WenyuChiou/dist/dashboard.html">
  <picture>
    <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/badge-dark.svg">
    <source media="(max-width: 600px)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/badge-light.svg">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/summary-dark.svg">
    <img alt="Open Wenyu Chiou's interactive AI collaboration dashboard" src="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/summary-light.svg">
  </picture>
</a>

The card shows sustained AI collaboration (active AI days and a 12-week
flat activity matrix), breadth across AI providers, and the explicit evidence
totals behind every number. It is a record of declared Git evidence, not
a skill score.

## Why ai-profile?

- Generic GitHub statistics answer **how active** a developer is.
- Line-level attribution tools answer **which lines** a tool changed.
- `ai-profile` answers **how AI participated and what evidence supports
  that claim across repositories**, while keeping the analysis local.

It complements those tools; it does not replace them or infer historical AI
use when Git evidence is absent.

## Install

Requires Python 3.11 or newer and Git 2.17 or newer. The wheel-onboarding
workflow tests Ubuntu, Windows, and macOS on Python 3.12; the full suite also
tests Python 3.11–3.14 on Ubuntu. Repositories must use Git's SHA-1 object
format.

```bash
python -m pip install --upgrade ai-profile-cli
aiprofile --version
```

The package name is `ai-profile-cli`; the installed command is `aiprofile`.
If your shell has not refreshed its script path, use:

```bash
python -m aiprofile --version
```

## Quickstart

Run these commands from the root of one of your repositories:

```bash
aiprofile init
aiprofile scan .
aiprofile aggregate
aiprofile render
```

Use `python -m aiprofile` in place of `aiprofile` for any command if needed.

- `init` creates the local configuration and seeds your identity from
  `git config user.email`.
- `scan` reads commits reachable from the repository's current `HEAD` and
  records commits authored by your configured identities.
- `aggregate` prints the exact privacy-safe statistics eligible for
  publication.
- `render` writes exactly eight files to `dist/`:

```text
badge-dark.svg       heatmap-light.svg   summary-dark.svg
badge-light.svg      profile.json        summary-light.svg
dashboard.html       heatmap-dark.svg
```

Existing commits without explicit AI evidence will appear as `unknown`.
Large unknown counts are an honest result, not a failed scan. Add trailers to
future commits when you want their AI participation credited.

## Configure identities and repository privacy

The configuration file is:

- macOS/Linux: `~/.aiprofile/config.json`
- Windows: `%USERPROFILE%\.aiprofile\config.json`
  (`$HOME\.aiprofile\config.json` in PowerShell)
- custom automation: `$AIPROFILE_HOME/config.json`

Only commits authored by an address in `identities` count. After `init`,
close other `aiprofile` processes, open the file as UTF-8 JSON, and add every
address you use—including GitHub noreply addresses:

```json
{
  "identities": [
    "you@example.com",
    "12345678+username@users.noreply.github.com"
  ],
  "repositories": [],
  "salt": "keep-the-existing-generated-value"
}
```

Keep the generated `salt` unchanged. After a scan, each repository entry also
contains `path`, `repository_uid`, and `publication_level`. Change only
`publication_level` when adjusting privacy:

On Windows, save with an editor's **UTF-8 (no BOM)** option. Windows
PowerShell 5.1's `Set-Content -Encoding utf8` adds a BOM that strict JSON
readers, including this Public Beta, reject. VS Code's default `UTF-8`
encoding is suitable; confirm the file still parses before replacing your
backup.

```json
{
  "path": "/local/path/created-by-scan",
  "repository_uid": "keep-the-existing-generated-value",
  "publication_level": "aggregate_only"
}
```

The allowed values are:

- `aggregate_only` — default; include totals but withhold repository identity
  and daily dates.
- `full` — include identity-redacted daily aggregate activity in date views.
- `excluded` — omit that repository entirely.

`aiprofile scan --full /path/to/repository` is the supported opt-in from
`aggregate_only` to `full`. It does not mean the repository is public on
GitHub, and a later scan without `--full` does not downgrade it. To reduce
publication, edit only the existing entry's `publication_level`, save valid
UTF-8 JSON, then run:

```bash
aiprofile aggregate
aiprofile render
```

If configuration parsing fails, restore the previous valid JSON; do not
delete or regenerate the `salt`, `path`, or `repository_uid`. Always review
`aggregate` before publishing.

## Scan and refresh multiple repositories

Scan each repository once, then aggregate their local records together:

```bash
aiprofile scan /path/to/repository-one
aiprofile scan /path/to/repository-two
aiprofile aggregate
aiprofile render
```

There is no batch refresh command in this Public Beta. To update a
multi-repository profile, rerun `scan` separately in every repository whose
history changed, then rerun `aggregate` and `render`. Run only one `render`
at a time for a given output directory.

## Publish to your GitHub Profile

Run `aiprofile render --out dist` inside your `USERNAME/USERNAME` Profile
repository, commit `dist/`, and place this clickable card in its README:

```html
<a href="https://USERNAME.github.io/USERNAME/dist/dashboard.html">
  <picture>
    <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="dist/badge-dark.svg">
    <source media="(max-width: 600px)" srcset="dist/badge-light.svg">
    <source media="(prefers-color-scheme: dark)" srcset="dist/summary-dark.svg">
    <img alt="Open my interactive AI collaboration dashboard"
         src="dist/summary-light.svg">
  </picture>
</a>
```

Add the heatmap with the same `<picture>` pattern using
`heatmap-{light,dark}.svg`. GitHub READMEs do not execute JavaScript, so the
SVG remains the Profile view and the link opens `dashboard.html`.

To host the dashboard with GitHub Pages:

1. Push `README.md` and `dist/` to the Profile repository's `main` branch.
2. Open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select **main**, **/ (root)**, then **Save**.
5. Open
   `https://USERNAME.github.io/USERNAME/dist/dashboard.html`.

A new Pages deployment can return 404 for a few minutes. Wait for the Pages
workflow to finish, then reload the exact case-sensitive URL. If it still
returns 404, confirm that Pages uses `main` and `/ (root)` and that
`dist/dashboard.html` exists in the pushed commit.

## What gets generated

The static, synthetic previews below demonstrate the complete output family:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-dark.svg">
  <img alt="Synthetic AI collaboration summary card" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/heatmap-sample-dark.svg">
  <img alt="Synthetic commit-activity heatmap; intensity is commit volume and hue is AI share" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/heatmap-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-dark.svg">
  <img alt="Synthetic AI-assisted share badge verified from Git provenance" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-light.svg">
</picture>

The six SVGs are static and GitHub-ready. `dashboard.html` is a self-contained
provider-filterable view with light, dark, and system themes. It loads no
external script, font, tracker, or API. `profile.json` contains the same
validated public aggregate contract used by every renderer.

## Declare AI participation

Known AI co-author identities are recognized automatically. For other tools,
or richer attribution, add one contiguous `AI-*` trailer block after a blank
line in the commit message:

```text
feat: add aggregation service

AI-Provider: Anthropic
AI-Model: Claude-Sonnet
AI-Tool: Claude-Code
AI-Role: implementation, documentation
AI-Mode: AI-Assisted
AI-Reviewed-By: Human
```

Repeat `AI-Provider:` without a blank line between actor groups to declare
another AI actor in the same commit. One commit can therefore equal one
unique AI-attributed commit and multiple actor presences. Use
`AI-Mode: Human-Only` only for an explicitly human-only commit.

Provider declarations are normalized to a canonical provider identity
(typically company-oriented). The dashboard may show the more recognizable
product display name instead: `AI-Provider: Anthropic` is shown as **Claude**.
This is a label-only mapping; it does not change aggregation or counts.

## Privacy

- The CLI makes no network calls, uploads no repository data, and sends no
  telemetry.
- Public assets contain the UTC generation date. They may also contain
  aggregate counts, public provider names, and evidence totals; repository
  activity dates appear only for `full` repositories.
- Public assets never contain repository names or paths, organization names,
  branches, commit SHAs or messages, raw trailers, prompts, or email
  addresses.
- `aggregate` is the publication preview. Review it before committing any
  generated asset.
- Aggregate-only output is identity redaction, not anonymity. Repeated
  publication can reveal when totals changed.
- Never publish or sync `.aiprofile`; it contains private paths, identities,
  repository identifiers, and a local salt.

Read the complete
[privacy model](https://github.com/WenyuChiou/ai-profile/blob/main/docs/PRIVACY.md).

## Metrics and current limitations

- **AI-attributed commits** are unique commits with at least one explicit AI
  actor presence.
- **Actor presences** count distinct provider/tool participation inside a
  commit. Provider totals can exceed unique commit totals.
- **Unknown** remains separate from human.
- Evidence quality is
  `verified > declared > imported > inferred > unknown`.
- Scans cover commits reachable from the current `HEAD`, not every branch.
- Git repositories using SHA-256 object format are not supported yet.
- Bot-authored commits are outside the author-identity scan unless the bot
  address is deliberately configured; some bot-plus-human co-author
  histories may therefore be absent.
- Historical AI use without explicit Git evidence stays unknown. Source-code
  style is never used to reconstruct attribution.

## Help, contributing, and license

Run `aiprofile --help` or `aiprofile COMMAND --help`. Use
[GitHub Issues](https://github.com/WenyuChiou/ai-profile/issues) for bugs and
feature requests; report vulnerabilities through the
[security policy](https://github.com/WenyuChiou/ai-profile/blob/main/SECURITY.md).

Contributions are welcome; see
[CONTRIBUTING.md](https://github.com/WenyuChiou/ai-profile/blob/main/CONTRIBUTING.md).
Licensed under the
[MIT License](https://github.com/WenyuChiou/ai-profile/blob/main/LICENSE);
vendored icon notices are in
[THIRD_PARTY_NOTICES.md](https://github.com/WenyuChiou/ai-profile/blob/main/THIRD_PARTY_NOTICES.md).

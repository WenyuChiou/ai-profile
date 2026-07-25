<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-dark.svg">
  <img alt="ai-profile - prove your AI collaboration, privately" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-light.svg" width="100%">
</picture>

# ai-profile

[![PyPI](https://img.shields.io/pypi/v/ai-profile-cli.svg)](https://pypi.org/project/ai-profile-cli/)
[![tests](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml/badge.svg)](https://github.com/WenyuChiou/ai-profile/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/WenyuChiou/ai-profile/blob/main/LICENSE)
[![python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)](https://github.com/WenyuChiou/ai-profile/blob/main/pyproject.toml)

[English](https://github.com/WenyuChiou/ai-profile/blob/main/README.md) · [繁體中文](https://github.com/WenyuChiou/ai-profile/blob/main/README.zh-TW.md)

Show how you collaborate with AI—not just how often you commit. `aiprofile`
turns explicit AI provenance in your local Git history into evidence-backed,
privacy-safe SVG cards and a self-contained interactive dashboard.

Use it when you want a credible AI portfolio without uploading source code,
guessing attribution from coding style, or exposing repository identities.
It recognizes `AI-*` commit trailers and verified AI co-author identities,
aggregates activity across repositories, and keeps its database on your
machine.

It is not an AI code detector. Commits without explicit evidence remain
`unknown`; they are never guessed to be human or assigned to a provider.

- **Credible:** every AI attribution comes from explicit Git evidence.
- **Private by default:** repository identities stay hidden, and daily dates
  appear only when you explicitly publish them.
- **Profile-ready:** one local workflow produces light and dark summary,
  heatmap, and badge assets plus an interactive provider view.

## Preview

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-dark.svg">
  <img alt="Sample AI collaboration summary card rendered from synthetic data" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/summary-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/heatmap-sample-dark.svg">
  <img alt="Sample collaboration heatmap: intensity is total commits and hue is the day's AI share" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/heatmap-sample-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-dark.svg">
  <img alt="AI-assisted share badge verified from Git provenance" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/badge-sample-light.svg">
</picture>

These samples use synthetic data.

## Install

Requires Python 3.11–3.14 and Git 2.17 or newer. Windows, macOS, and
Linux are supported. Git repositories must use the SHA-1 object format.

```bash
pip install ai-profile-cli
```

The package name is `ai-profile-cli`; the installed command is
`aiprofile`.

## Quickstart

Run these commands from the root of one of your repositories:

```bash
aiprofile init
aiprofile scan .
aiprofile aggregate
aiprofile render
```

- `init` creates the local configuration and seeds your identity from
  `git config user.email`.
- `scan` records commits authored by your configured identities.
- `aggregate` shows the exact privacy-safe statistics that can be published.
- `render` writes six SVG files, `dashboard.html`, and `profile.json` to
  `dist/`.

Only commits authored by identities in `~/.aiprofile/config.json` count.
Review the email seeded by `init` and add any other addresses you commit with.

Scan additional repositories at any time:

```bash
aiprofile scan /path/to/another/repository
```

Repositories default to `aggregate_only`: their counts contribute to the
summary, but their identity and daily dates stay private. `--full` marks that
repository's aggregate activity as explicitly publishable so its dates can
appear in date-based views. This is a policy choice, not a claim about the
repository's GitHub visibility:

```bash
aiprofile scan --full /path/to/repository
```

That choice persists. Scanning the same repository later without `--full`
does not downgrade it. To stop publishing its dates, change its
`publication_level` in `~/.aiprofile/config.json` to `aggregate_only` (keep
identity-redacted aggregate totals) or `excluded` (omit it), then run
`aggregate` and `render` again.

Only run one `render` at a time for a given output directory.

## Add the cards to your GitHub profile

Render inside your GitHub profile repository (`USERNAME/USERNAME`), then
commit the generated `dist/` directory. Add this to its README:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="dist/summary-dark.svg">
  <img alt="AI collaboration summary" src="dist/summary-light.svg">
</picture>
```

Use `heatmap-{light,dark}.svg` or `badge-{light,dark}.svg` in the same
pattern. To refresh your cards, run `scan` again, run `render`, and commit
the updated files.

## Interactive dashboard

`dist/dashboard.html` is a self-contained dashboard generated from the same
validated aggregate data as the SVG cards. Open it directly in a browser to:

- switch between **All AI** and one provider;
- inspect provider-attributed commits, actor presences, and active days
  without mixing those units;
- inspect the publishable daily collaboration window;
- use light, dark, or system color themes.

The file loads no external script, font, tracker, or API. It contains the
same public aggregate fields as `profile.json`, so review `aiprofile
aggregate` before publishing either file.

GitHub READMEs do not execute JavaScript. Keep the SVGs in your Profile
README and link them to `dashboard.html` on GitHub Pages or another static
host. See the
[live profile example](https://wenyuchiou.github.io/WenyuChiou/dist/dashboard.html).

## Declare AI participation

Known AI co-author identities are recognized automatically. For other
tools, or when you want richer attribution, add an `AI-*` trailer block
to the commit message:

```text
feat: add aggregation service

AI-Provider: Anthropic
AI-Model: Claude-Sonnet
AI-Tool: Claude-Code
AI-Role: implementation, documentation
AI-Mode: AI-Assisted
AI-Reviewed-By: Human
```

Repeat the `AI-Provider:` key to declare another AI actor in the same
commit. One commit can therefore equal one unique AI-attributed commit
and multiple actor presences. Use `AI-Mode: Human-Only` only for an
explicitly human-only commit.

## Privacy

- No repository data is uploaded. The CLI makes no network calls and
  sends no telemetry.
- New repositories default to `aggregate_only`. Use `scan --full` as an
  explicit publication decision, or set a repository to `excluded` in
  `~/.aiprofile/config.json`.
- Public assets contain aggregate counts, public provider names, evidence
  totals, and dates. They never contain repository names or paths,
  organization names, branches, commit SHAs or messages, raw trailers,
  or email addresses.
- `aiprofile aggregate` is the publication preview. Review it before
  committing generated assets.
- Aggregate-only output is identity redaction, not anonymity. Repeated
  publication can reveal when totals changed. See the full
  [privacy model](https://github.com/WenyuChiou/ai-profile/blob/main/docs/PRIVACY.md).
- Do not publish or sync `~/.aiprofile`; it contains private repository
  paths, identities, and a local salt.

## Metrics

- **AI-attributed commits** are unique commits with at least one explicit
  AI actor presence.
- **Actor presences** count distinct provider/tool participation within a
  commit. Provider totals can therefore exceed unique commit totals.
- **Unknown** stays separate from human.
- Evidence quality is reported as
  `verified > declared > imported > inferred > unknown`.

## Help and support

Run `aiprofile --help` or `aiprofile COMMAND --help` for command options.
Use [GitHub Issues](https://github.com/WenyuChiou/ai-profile/issues) for
bugs and feature requests. Report vulnerabilities through the
[security policy](https://github.com/WenyuChiou/ai-profile/blob/main/SECURITY.md).

## Contributing and license

Contributions are welcome; see
[CONTRIBUTING.md](https://github.com/WenyuChiou/ai-profile/blob/main/CONTRIBUTING.md).
Licensed under the
[MIT License](https://github.com/WenyuChiou/ai-profile/blob/main/LICENSE).

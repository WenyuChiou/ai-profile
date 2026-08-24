<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-dark.svg">
  <img alt="" src="https://raw.githubusercontent.com/WenyuChiou/ai-profile/main/docs/assets/banner-light.svg" width="100%">
</picture>

# ai-profile

## Show the evidence behind your AI collaboration.

`ai-profile` turns explicit Git provenance across your local repositories into
privacy-safe GitHub Profile cards and a provider-filterable dashboard with a
provider ledger—without uploading source code or guessing
attribution.

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
- **Local-first privacy:** CLI scanning, aggregation, refresh, and rendering happen on
  your machine; repository identities stay out of public assets.
- **Profile-ready:** one render produces theme-aware SVG cards, a
  self-contained dashboard, and a machine-readable public summary.

`ai-profile` is not an AI code detector. Commits with no explicit evidence
stay `unknown` (shown as **Unattributed** in the UI); they are never silently
counted as human or assigned to a provider. Add `AI-*` trailers to future
commits when you want their AI participation recorded.

## A real GitHub Profile example

This card contains the maintainer's real public aggregate data. Select it to
open the provider-filterable dashboard; the card shows explicit provider
participation and evidence totals when the Git history declares AI activity.

<a href="https://wenyuchiou.github.io/WenyuChiou/dist/dashboard.html">
  <picture>
    <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/badge-dark.svg">
    <source media="(max-width: 600px)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/badge-light.svg">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/summary-dark.svg">
    <img alt="Open Wenyu Chiou's interactive AI collaboration dashboard" src="https://raw.githubusercontent.com/WenyuChiou/WenyuChiou/main/dist/summary-light.svg">
  </picture>
</a>

The card shows sustained AI collaboration (active AI days and a 12-week
collaboration pulse — mark height is the day's total commits, the accent
fill rising from the baseline is its AI-attributed share, publishable dates
only), breadth across AI providers, and the explicit evidence totals behind
every number. It is a record of declared Git evidence, not a skill score.

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

## Automate daily updates

Choose one path. Keep private and `aggregate_only` repositories on your own
machine; use GitHub Actions only when every source repository is already
public.

```bash
# Refresh every configured, non-excluded repository now.
aiprofile refresh --out dist
aiprofile refresh --out dist --dry-run

# Or install one daily local job (05:37 in the machine's local time).
aiprofile schedule install --profile-repo /path/to/USERNAME --time 05:37
aiprofile schedule status
aiprofile schedule remove
```

### Refresh every configured repository

`refresh` rescans each configured path once, then aggregates and writes the
same eight files. Aliases do not cause duplicate scans, and `excluded`
repositories remain excluded. A scan, configuration, privacy, or rendering
failure publishes no new generation. `--dry-run` lists which of the eight
files would change without changing configuration, publication policy,
recorded database/WAL content, or output assets. It may create or use the
advisory lock, and SQLite may update transient `-shm` coordination bytes while
reading committed WAL content; neither is published data.

If two configuration entries resolve to the same path but carry different
`repository_uid` values, refresh refuses the whole run before scanning or
reading cached aggregates. Keep the UID created by `scan`; do not copy a UID
between entries or invent a replacement.

Only one refresh can use an `AIPROFILE_HOME` at a time. On the rare filesystem
failure where output rollback is incomplete, the CLI says that partial assets
or recovery backups may remain; inspect the output before committing it.

### Private or local repositories: native scheduler

`schedule install` creates an OS-native user job: Task Scheduler on Windows,
launchd on macOS, or a systemd user timer on Linux. It refreshes
`<profile-repo>/dist` daily and, by default, stages only the eight generated
paths, commits only byte changes, and pushes through the repository's existing
Git authentication only while the remote still equals the captured parent.
Push mode requires one fetch destination and the same single push destination;
multiple or different push URLs fail closed before refresh. The captured
destination is bound to a fixed alias inside a private, isolated Git context;
push and verification never put the URL in argv and cannot be redirected by
later repository, global, `insteadOf`, or `pushInsteadOf` changes. Supported
destinations are credential-free HTTPS, SSH/SCP, Git, file URLs, or local
paths without query strings or fragments. Local paths are resolved from the
Profile repository before the isolated context is created. Shallow and partial
clones are rejected before refresh because scheduled publication requires a
complete local Git history. Use a credential manager, askpass,
or SSH agent; embedded passwords and authorization headers are intentionally
unsupported, and ambient proxy variables are not forwarded. The tool does not persist or log credentials. Add
`--no-push` to create and advance the local exact-eight commit without pushing
it to the remote; use `--dry-run` to preview installation without changing
scheduler state.

The user scheduler and machine must be available. Windows and systemd can
recover missed runs according to their native settings; launchd does not
replay a run missed while the machine was powered off. Detached branches,
changed branch state, protected branches, and rejected pushes fail closed.
Scheduler commits are mechanical and intentionally do not run user commit
hooks or signing.

Before a push-capable run, a clean local checkout is safely fast-forwarded when
the recorded remote branch is ahead and is a verified descendant of local
`HEAD`; the fetch uses the same isolated destination transport as publication.
Deliberate local commits, dirty checkouts, rewinds, deletions, and diverged or
unstable remote tips still fail closed for manual synchronization. A failed
push is retried from the same private pending commit only after an interrupted
branch update and the exact-eight index are safely recovered, and while its
branch, parent, tree, and remote remain unchanged. The actual push uses an
exact-old lease tied to that parent and verifies the remote at the immutable
commit before reporting success or clearing retry state. The private retry
record binds a SHA-256 commitment of the destination, never the URL itself.
Different homes targeting one Profile are
serialized by that Profile's Git metadata lock, and generated bytes are
verified against the completed refresh before the commit is created.

Install the scheduler from a Python environment that will remain in place.
If you move, remove, or upgrade that interpreter or virtual environment, run
`schedule install` again and confirm `schedule status`.

### Public repositories: GitHub Actions

For a Profile sourced entirely from public repositories:

1. Copy [`docs/templates/profile-refresh-caller.yml`](docs/templates/profile-refresh-caller.yml)
   to `.github/workflows/profile-refresh.yml` in the Profile repository.
2. Edit the explicit public `owner/repo` list. Add the identity-email payload
   as the repository secret `AIPROFILE_IDENTITIES`; never put it in `with:`.
3. In **Settings → Pages**, choose **GitHub Actions** as the source, then run
   the workflow once with **Actions → Daily ai-profile refresh → Run workflow**.

The template runs daily at 05:37 UTC and also supports manual dispatch. It
pins the reusable workflow to commit
`d74a3efdf27310162fc8c54b29b8e2782ea66b46`, installs exactly
`ai-profile-cli==0.8.0`, rejects non-public sources before scanning, and
deploys Pages from the exact `published-sha` produced in that run. It uses
only `GITHUB_TOKEN`; no PAT fallback is provided. GitHub-hosted automation is
not local-first processing: it clones only the public repositories you list
and treats them as `full`. Use the local scheduler if any source is private or
`aggregate_only`.

Branch protection can reject the direct asset commit. Scheduled workflows in
public repositories can be disabled after 60 days without repository
activity, forks require Actions to be enabled, and organization Actions
allowlists must permit the pinned actions and reusable workflow. A commit made
with `GITHUB_TOKEN` does not trigger ordinary push workflows or a Pages build,
so the caller performs an explicit, same-run Pages deployment. Use one caller,
not a matrix of overlapping refresh jobs.

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

For manual publication, host the dashboard with GitHub Pages as follows. If
you use the daily Action above, keep **GitHub Actions** as the Pages source and
skip these branch-source steps.

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

The summary card, heatmap, badge, and dashboard share one flat Signal
Console system: calm paper-and-ink surfaces, a blue collaboration signal, a
warm evidence cue, a status line that labels the generation date as a
snapshot, and precise alignment that improves reading without turning
activity into a 3D score or decorative scene.

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
provider-filterable view with the provider ledger, plus light, dark, and system
themes. It loads no
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

When `AI-Model` is present, its canonical value is mapped to a small
schema-owned family vocabulary (for example, `Claude-Sonnet` → **Claude**) and
retained as validated, machine-readable evidence in `profile.json`. Family
commit counts remain intentionally non-exclusive, while actor presences and
active days remain separate measures. Missing model declarations stay
**Unknown**; raw model strings never enter public assets.

## Privacy

- Scanning, aggregation, refresh, and rendering make no network calls and
  send no telemetry. The optional local scheduler may run `git push` through
  a credential manager, askpass, or SSH agent; `ai-profile` does not persist
  or log credentials.
- The optional public Action runs on a GitHub-hosted runner and clones only
  explicit public repositories. Identity emails are passed as a secret and
  are not written to public assets or default workflow logs.
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
- **Model-family rows in `profile.json`** count explicit canonical `AI-Model`
  evidence. A commit can contribute to more than one family row; this does not
  inflate the unique AI-attributed commit headline.
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

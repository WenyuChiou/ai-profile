# Release runbook

This runbook publishes `ai-profile-cli` through PyPI Trusted Publishing.
Release artifacts are immutable: validate the exact wheel and sdist bytes
before upload, then verify the downloaded bytes after publication.

## 1. Prepare the release pull request

1. Start from current `main` with a clean worktree.
2. Update the package version in both `pyproject.toml` and
   `src/aiprofile/__init__.py`.
3. Move release notes out of `Unreleased` in `CHANGELOG.md`.
4. Do not change the ACE schema or CLI contract without the required ADR and
   schema/version process.

Run the standard gates:

```bash
python -m pytest tests -p no:cacheprovider
python -m ruff check src tests scripts
python scripts/check_readme_parity.py
python tests/unit/test_render_summary.py
python tests/unit/test_heatmap_svg.py
git diff --exit-code -- tests/snapshots docs/assets
```

The two regeneration commands must produce no unexplained diff.

For an automation release, also verify that
`tests/unit/test_profile_refresh_workflow.py` pins the copyable caller to the
reviewed reusable-workflow commit, that the workflow's exact package version
matches the candidate version, and that Pages consumes its immutable
`published-sha`. Do not replace the full commit pin with a release tag.
For a scheduler-only patch that does not change the hosted workflow, document
that scope explicitly and keep its reviewed package/commit pair intact; the
release must not silently rebind the immutable public caller. A later hosted
workflow upgrade requires the same reviewed two-commit pin choreography.

## 2. Build and validate artifacts

Build from a clean Linux checkout of the release commit. The canonical
release environment is Ubuntu; Windows and macOS consume and smoke the
resulting universal wheel rather than rebuilding it. Set the frozen ZIP
timestamp from the candidate manifest before building:

```bash
python -m pip install --upgrade build==1.4.3 twine==6.2.0
export SOURCE_DATE_EPOCH="$(python -c 'import json; print(json.load(open("docs/reviews/promotion-candidate.json", encoding="utf-8"))["source_date_epoch"])')"
python -m build
python -m twine check dist/*
python scripts/check_release_artifacts.py \
  --dist-dir dist \
  --expected-version X.Y.Z \
  --write-checksums SHA256SUMS
```

Install and exercise the built wheel rather than the source tree:

```bash
python scripts/release_smoke.py \
  --wheel dist/ai_profile_cli-X.Y.Z-py3-none-any.whl \
  --expected-version X.Y.Z
```

The smoke must run `refresh` from the installed wheel and report eight
outputs, a network-closed CSP dashboard, byte-identical repeated refreshes,
and zero privacy-canary hits. Dry-run must name only the allowlisted eight
filenames and leave configuration, publication policy, recorded database/WAL
content, and output assets unchanged. The advisory lock and transient SQLite
`-shm` coordination bytes are permitted non-data exceptions and must not be
misreported as publication changes.

Before the release PR is submitted, run the frozen four-role dogfood against
that exact wheel. Record its full digest in
`docs/reviews/promotion-candidate.json` and rerun the artifact command with:

```bash
python scripts/check_release_artifacts.py \
  --dist-dir dist \
  --expected-version X.Y.Z \
  --expected-wheel-sha256 <recorded-wheel-sha256>
```

The candidate manifest is a release authorization, not a floating
`latest` pointer. It freezes both the authorized wheel digest and
`SOURCE_DATE_EPOCH`. Any package or public README change requires a rebuild,
new digest, and affected dogfood rerun. Do not substitute a Windows-built
wheel: ZIP platform metadata differs even when every file byte is identical.

## 3. Merge and tag

Merge only after all pull-request checks are green, including:

- `Python 3.11`, `Python 3.12`, `Python 3.13`, and `Python 3.14`
- `Release candidate build`
- `Wheel onboarding (ubuntu-latest / Python 3.12)`
- `Wheel onboarding (windows-latest / Python 3.12)`
- `Wheel onboarding (macos-latest / Python 3.12)`

For v0.7.0, merge the release PR with a merge commit; squash/rebase would make
the copyable caller's immutable C1 pin depend on temporary PR-object retention.
Before deleting the feature branch, require both:

```bash
git fetch origin main
git merge-base --is-ancestor 9c4f276cb437f1866a2c1b407efe54d3790ce811 origin/main
gh api --method GET repos/WenyuChiou/ai-profile/contents/.github/workflows/profile-refresh.yml \
  -f ref=9c4f276cb437f1866a2c1b407efe54d3790ce811 > /dev/null
```

Either failure blocks tagging and branch deletion.

From a clean, up-to-date `main`:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

The tag-triggered publish workflow repeats the full suite and builds one
wheel/sdist bundle in a read-only job. It checks the wheel against the frozen
dogfood digest, validates versions and notices, Twine-checks the pair, records
SHA-256 digests, and retains the bundle. Ubuntu, Windows, and macOS then
download and smoke those same bytes. Only after all three pass do two fresh,
least-privilege jobs publish the retained bundle: one has PyPI OIDC authority;
the other has GitHub Release authority. Neither publication job rebuilds or
executes project dependencies.

The PyPI action skips an already published immutable filename only for
recovery, then the workflow queries PyPI and requires both served digests to
match the retained manifest. The GitHub Release job cannot run until that
check passes. After create/repair, the workflow requires the GitHub Release
asset-name set to equal the wheel, sdist, and `SHA256SUMS`, downloads all
three, byte-compares the public checksum file with the retained checksum
file, and verifies both downloaded packages against that retained manifest.
Its path is idempotent, so a retry can repair a partial multi-service release
without accepting different or additional public assets. Never rebuild or
substitute artifacts between validation and upload.

## 4. Verify the live release

Wait for the publish workflow to finish successfully. Create an empty
`<release-dir>`, download the wheel and sdist from PyPI into
`<release-dir>/dist/`, and download the GitHub Release manifest as
`<release-dir>/SHA256SUMS`. Confirm:

1. Their SHA-256 digests match the GitHub Release `SHA256SUMS`.
2. `python scripts/check_release_artifacts.py --dist-dir <release-dir>/dist
   --artifact-only --tag vX.Y.Z --checksum-file
   <release-dir>/SHA256SUMS` passes. Use artifact-only mode so a later
   source checkout version cannot invalidate a correct historical bundle.
3. A clean virtual environment installs from PyPI and
   `aiprofile --version` reports `X.Y.Z`.
4. The clean install completes `init → scan → aggregate → render`.
5. The PyPI project, GitHub Release, repository homepage, live dashboard,
   README assets, changelog, security policy, and issue links return HTTP
   200.
6. Copy the public caller into a disposable public Profile repository and run
   it twice: first with a controlled byte change, then unchanged. Verify the
   first commit contains exactly eight generated paths, Pages serves the exact
   `published-sha` with HTTP 200, and the second run creates no commit. This
   post-PyPI hosted E2E is a promotion blocker; static workflow tests do not
   replace it.

If any check fails, do not delete or overwrite the release. Stop promotion,
document the defect, and prepare a new patch version.

## 5. Refresh the maintainer Profile

Only after the package gates pass:

1. Install the released PyPI version in a clean environment.
2. Confirm there is one controlled, intended byte change for the scheduler to
   publish—normally the newly released repository commit's explicit evidence.
   If no configured source changed, use an isolated Profile fixture with its
   own remote and Pages target; a no-change run does not prove commit/push.
3. Install the local scheduler from the released wheel with the intended local
   time, confirm `schedule status`, and trigger or wait for one real launcher
   run. Do not manually refresh first: that would consume the change and turn
   this scheduler proof into a no-op.
4. Verify the launcher created one local commit containing only the eight
   generated paths, pushed that commit with the exact-old lease and never an
   unconditional force push, produced a path-free
   last-run outcome, and reached green Pages deployment. Then confirm the next
   no-change run creates no commit.
5. Review `aggregate`, run the privacy canary sweep, inspect the exact-eight
   diff, and confirm publication policies are unchanged. The maintainer home
   contains an `aggregate_only` source, so do not migrate it to the public-only
   Action.
6. Verify the live dashboard and all eight Profile assets. If an isolated
   fixture was necessary in step 2, record that limitation and do not claim a
   maintainer-Profile scheduler E2E until a legitimate source change exercises
   it.

Install from a Python environment that will persist at the same executable
path. After moving, removing, or upgrading that interpreter or virtual
environment, rerun `schedule install` and confirm `schedule status` before
waiting for the next native run.

The scheduler uses an existing credential manager, askpass, or SSH agent and
does not persist or log credentials. It rejects embedded-password/query/
fragment destinations, resolves local paths from the Profile repository, and
does not query or forward authorization headers, Git-config/ambient proxies,
or URL rewrite rules into its isolated push context. Its
mechanical `commit-tree` publication bypasses user commit hooks and signing;
branch protection can reject the exact-old leased push. The lease is bound to
the captured remote parent and is followed by remote-tip confirmation; it is
never an unconditional force push. Push mode also requires one fetch
destination and the same single push destination; multiple/different URLs are
unsupported and fail closed before refresh. Do not claim daily automation
is live until the native registration and one real Profile refresh have both
been observed after release.

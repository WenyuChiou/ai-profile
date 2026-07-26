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

The smoke must report eight outputs, a network-closed CSP dashboard,
byte-identical repeated renders, and zero privacy-canary hits.

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

If any check fails, do not delete or overwrite the release. Stop promotion,
document the defect, and prepare a new patch version.

## 5. Refresh the maintainer Profile

Only after the package gates pass:

1. Install the released PyPI version in a clean environment.
2. Rescan each intended repository.
3. Review `aggregate`.
4. Render the real Profile `dist/`.
5. Run the privacy canary sweep and review the diff.
6. Merge through the Profile repository's normal checks.
7. Wait for GitHub Pages, then verify the live dashboard and Profile assets.

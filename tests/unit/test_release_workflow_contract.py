"""Static guardrails for the least-privilege exact-byte release workflow."""

from __future__ import annotations

import io
import json
import re
import textwrap
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_release_runbook_uses_get_for_immutable_workflow_probe():
    text = (ROOT / "docs" / "RELEASING.md").read_text(encoding="utf-8")
    assert "gh api --method GET repos/WenyuChiou/ai-profile/contents/" in text
    assert "-f ref=9c4f276cb437f1866a2c1b407efe54d3790ce811" in text
    assert "scheduler-only patch" in text
    assert "must not silently rebind the immutable public caller" in text


def _publish_workflow_sections() -> tuple[str, str, str, str, str]:
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(
        encoding="utf-8"
    )
    build_job, remainder = workflow.split("\n  onboarding:", 1)
    onboarding_job, publication_jobs = remainder.split("\n  publish-pypi:", 1)
    pypi_job, github_job = publication_jobs.split("\n  publish-github:", 1)
    return workflow, build_job, onboarding_job, pypi_job, github_job


def _pypi_verifier_script(pypi_job: str) -> str:
    verifier = pypi_job.split("python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
    return textwrap.dedent(verifier)


#: Immutable digests of wheels already published to PyPI. A candidate manifest
#: for a released version must pin exactly that digest; a manifest for any
#: other version must never carry one of them (PR #34 changed package bytes
#: after v0.7.1 while the manifest still authorized the v0.7.1 wheel, so the
#: candidate build skipped onboarding — this pin makes that drift a test
#: failure instead of a CI surprise).
#:
#: v0.8.0 was deliberately absent while the branch still carried version
#: 0.8.0: commit B (`61b7995`) landed after the v0.8.0 tag and changed the
#: README, which is `project.readme` and therefore wheel METADATA, so the
#: branch built `e1f869a9...` while PyPI serves `9cc06f20...` — listing the
#: published digest then would have permanently redded the ci.yml candidate
#: job. The v0.8.1 bump closes that documented gap: the manifest now names a
#: different version, so the published v0.8.0 digest pins here as history.
RELEASED_WHEEL_SHA256 = {
    "0.7.1": "c941b547b41eccca7efdfc99bdf785c6d8c307da8bedace0a73a3d19036df005",
    "0.7.2": "4f65ef450b9637e066cc9acdfba9cb1e688007e500179cb99a41c2a62dc6708f",
    "0.8.0": "9cc06f2052a642bd198fa00d728c75b72fce061dad24c51b72feddf84b07c89e",
    "0.8.1": "1faceac31ac7d9c3a99e3e4678bdfb725f73341e89e5847dc6a578ed8a6bbff9",
}


def _candidate_manifest() -> dict:
    return json.loads(
        (ROOT / "docs" / "reviews" / "promotion-candidate.json").read_text(
            encoding="utf-8"
        )
    )


def test_candidate_manifest_matches_project_version_and_is_a_sha256():
    manifest = _candidate_manifest()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)

    assert version is not None
    assert manifest["version"] == version.group(1)
    assert manifest["wheel"] == f"ai_profile_cli-{version.group(1)}-py3-none-any.whl"
    assert re.fullmatch(r"[0-9a-f]{64}", manifest["wheel_sha256"])
    assert manifest["source_date_epoch"] == 1786320000


def test_candidate_manifest_pins_the_released_v0_8_1_digest_exactly():
    # v0.8.1 is published: the manifest must authorize exactly the released
    # canonical Ubuntu wheel digest — the guard PR #34 introduced, now
    # active for the current version (unlike the documented v0.8.0 gap).
    manifest = _candidate_manifest()
    import aiprofile

    assert manifest["version"] == aiprofile.__version__ == "0.8.1"
    released = RELEASED_WHEEL_SHA256.get(manifest["version"])
    if released is not None:
        assert manifest["wheel_sha256"] == released
    else:
        assert manifest["wheel_sha256"] not in RELEASED_WHEEL_SHA256.values()


def test_v0_8_1_release_notes_are_finalized_before_tagging():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased, released = changelog.split(
        "## [0.8.1] - 2026-08-23 (Public Beta)", 1
    )

    assert unreleased.rstrip().endswith("## [Unreleased]")
    release_081, rest = released.split("## [0.8.0] - 2026-08-23 (Public Beta)", 1)
    assert "Collaboration Pulse" in release_081
    assert "ADR-032" in release_081
    assert "ACE schema" in release_081
    assert "summary card only" in release_081
    release_080, rest = rest.split("## [0.7.2] - 2026-08-23 (Public Beta)", 1)
    assert "Signal Console" in release_080
    assert "ADR-031" in release_080
    assert "snapshot" in release_080
    assert "ACE schema" in release_080
    release_072, rest = rest.split("## [0.7.1] - 2026-08-10 (Public Beta)", 1)
    assert "fast-forward" in release_072
    assert "fail closed" in release_072
    assert "ACE schema" in release_072
    release_071 = rest.split("## [0.7.0]", 1)[0]
    assert "Task Scheduler" in release_071
    assert "UseUnifiedSchedulingEngine" in release_071


def test_publish_workflow_builds_once_fans_out_and_splits_authority():
    workflow, build_job, onboarding_job, pypi_job, github_job = (
        _publish_workflow_sections()
    )
    publication_jobs = f"{pypi_job}\n  publish-github:{github_job}"

    assert workflow.count("python -m build") == 1
    assert '["source_date_epoch"]' in build_job
    assert "export SOURCE_DATE_EPOCH" in build_job
    assert build_job.index('["source_date_epoch"]') < build_job.index("python -m build")
    assert "expected-wheel-sha256" in build_job
    assert "contents: write" not in build_job
    assert "id-token: write" not in build_job
    assert "matrix:\n        os: [ubuntu-latest, windows-latest, macos-latest]" in onboarding_job
    assert "python -m build" not in onboarding_job
    assert "id-token: write" in pypi_job
    assert "contents: write" not in pypi_job
    assert "contents: read" not in pypi_job
    assert "Verify published PyPI digests" in pypi_job
    assert "PyPI serves the exact retained wheel and sdist" in pypi_job
    assert "contents: write" in github_job
    assert "id-token: write" not in github_job
    assert "needs: [build, onboarding, publish-pypi]" in github_job
    assert "GitHub Release asset set differs from the retained bundle" in github_job
    assert "gh release download" in github_job
    assert 'RELEASE_METADATA_ARGS+=(--prerelease)' in github_job
    assert 'if [[ "$GITHUB_REF_NAME" == v0.* ]]' in github_job
    assert 'gh release edit "$GITHUB_REF_NAME"' in github_job
    assert github_job.count('"${RELEASE_METADATA_ARGS[@]}"') == 2
    assert 'IS_PRERELEASE="$(gh release view' in github_job
    assert '[[ "$IS_PRERELEASE" != true ]]' in github_job
    assert github_job.count('gh release ') == github_job.count(
        '--repo "$GITHUB_REPOSITORY"'
    )
    assert 'cmp "$RETAINED_MANIFEST" "$VERIFY_DIR/SHA256SUMS"' in github_job
    assert 'sha256sum --check "$RETAINED_MANIFEST"' in github_job
    assert "GitHub Release assets match the exact retained bundle" in github_job
    assert "python -m build" not in publication_jobs
    assert "find dist -maxdepth" not in workflow

    compile(_pypi_verifier_script(pypi_job), "publish-pypi-verifier", "exec")


def test_pypi_recovery_verifier_rejects_an_unretained_distribution(
    tmp_path,
    monkeypatch,
):
    _, _, _, pypi_job, _ = _publish_workflow_sections()
    expected = {
        "ai_profile_cli-0.4.2-py3-none-any.whl": "a" * 64,
        "ai_profile_cli-0.4.2.tar.gz": "b" * 64,
    }
    (tmp_path / "SHA256SUMS").write_text(
        "".join(f"{digest}  dist/{name}\n" for name, digest in expected.items()),
        encoding="ascii",
    )
    payload = {
        "urls": [
            *[
                {"filename": name, "digests": {"sha256": digest}}
                for name, digest in expected.items()
            ],
            {
                "filename": "ai_profile_cli-0.4.2-cp312-win_amd64.whl",
                "digests": {"sha256": "c" * 64},
            },
        ]
    }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RELEASE_VERSION", "v0.4.2")
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: io.StringIO(json.dumps(payload)),
    )
    monkeypatch.setattr(time, "sleep", lambda seconds: None)

    with pytest.raises(SystemExit, match="did not serve the exact retained bundle"):
        exec(
            compile(
                _pypi_verifier_script(pypi_job),
                "publish-pypi-verifier",
                "exec",
            ),
            {},
        )


@pytest.mark.parametrize("mismatch", [False, True])
def test_pypi_recovery_verifier_accepts_only_matching_digests(
    tmp_path,
    monkeypatch,
    mismatch,
):
    _, _, _, pypi_job, _ = _publish_workflow_sections()
    expected = {
        "ai_profile_cli-0.4.2-py3-none-any.whl": "a" * 64,
        "ai_profile_cli-0.4.2.tar.gz": "b" * 64,
    }
    (tmp_path / "SHA256SUMS").write_text(
        "".join(f"{digest}  dist/{name}\n" for name, digest in expected.items()),
        encoding="ascii",
    )
    observed = dict(expected)
    if mismatch:
        observed["ai_profile_cli-0.4.2-py3-none-any.whl"] = "c" * 64
    payload = {
        "urls": [
            {"filename": name, "digests": {"sha256": digest}}
            for name, digest in observed.items()
        ]
    }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RELEASE_VERSION", "v0.4.2")
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: io.StringIO(json.dumps(payload)),
    )
    monkeypatch.setattr(time, "sleep", lambda seconds: None)

    script = compile(
        _pypi_verifier_script(pypi_job),
        "publish-pypi-verifier",
        "exec",
    )
    if mismatch:
        with pytest.raises(
            SystemExit,
            match="did not serve the exact retained bundle",
        ):
            exec(script, {})
    else:
        exec(script, {})


def test_ci_candidate_build_uses_the_frozen_source_date_epoch():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    candidate_job = workflow.split("\n  candidate:", 1)[1].split("\n  tests:", 1)[0]

    assert '["source_date_epoch"]' in candidate_job
    assert "export SOURCE_DATE_EPOCH" in candidate_job
    assert candidate_job.index('["source_date_epoch"]') < candidate_job.index(
        "python -m build"
    )

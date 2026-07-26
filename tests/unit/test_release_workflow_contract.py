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


def test_candidate_manifest_matches_project_version_and_is_a_sha256():
    manifest = json.loads(
        (ROOT / "docs" / "reviews" / "promotion-candidate.json").read_text(
            encoding="utf-8"
        )
    )
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)

    assert version is not None
    assert manifest["version"] == version.group(1)
    assert re.fullmatch(r"[0-9a-f]{64}", manifest["wheel_sha256"])


def test_publish_workflow_builds_once_fans_out_and_splits_authority():
    workflow, build_job, onboarding_job, pypi_job, github_job = (
        _publish_workflow_sections()
    )
    publication_jobs = f"{pypi_job}\n  publish-github:{github_job}"

    assert workflow.count("python -m build") == 1
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

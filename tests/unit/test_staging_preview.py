"""Staging preview helper + manual-only Pages workflow guardrails.

Pins the v0.5.0 candidate contract, inheriting the prior Gate S from
docs/reviews/promotion-eval-spec-v048.md: the helper is a
deterministic pure function of the wheel bytes and the installed renderer,
writes exactly two files with computed digests, and the staging workflow
stays manual-only, SHA-pinned, least-privilege, and digest-verified
before anything reaches Pages.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from aiprofile.render.dashboard_html import render_dashboard

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "render_staging_dashboard.py"
WORKFLOW = ROOT / ".github" / "workflows" / "staging-preview.yml"

SPEC = importlib.util.spec_from_file_location("render_staging_dashboard", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
staging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(staging)

#: The frozen v0.5.0 candidate digest (docs/reviews/promotion-candidate.json).
PINNED_WHEEL_SHA256 = "dcd407fa5a570b1a47ba3c613998f681c5c992f10f18119ab4f4be457221f245"
PINNED_DASHBOARD_SHA256 = "cace8ed2b4f61affb0661e5ba3beae9de42836cc025ce8334b76b4226609110e"

_FAKE_WHEEL_BYTES = b"deterministic fake wheel bytes for staging preview tests\n"


def _fake_wheel(tmp_path: Path) -> Path:
    wheel = tmp_path / "ai_profile_cli-0.0.0-py3-none-any.whl"
    wheel.write_bytes(_FAKE_WHEEL_BYTES)
    return wheel


def _read_outputs(out_dir: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in out_dir.iterdir()}


def test_helper_is_deterministic_across_runs_and_directories(tmp_path):
    wheel = _fake_wheel(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"

    staging.render_staging(wheel, first)
    staging.render_staging(wheel, second)
    # A rerun into a directory holding only a previous run's outputs is the
    # supported refresh path and must reproduce the same bytes.
    staging.render_staging(wheel, first)

    assert _read_outputs(first) == _read_outputs(second)


def test_manifest_digests_match_the_actual_bytes(tmp_path):
    wheel = _fake_wheel(tmp_path)
    out = tmp_path / "out"
    returned = staging.render_staging(wheel, out)

    manifest = json.loads((out / "staging-manifest.json").read_text(encoding="utf-8"))
    assert manifest == returned
    assert manifest["wheel_sha256"] == hashlib.sha256(_FAKE_WHEEL_BYTES).hexdigest()
    assert (
        manifest["dashboard_sha256"]
        == hashlib.sha256((out / "dashboard.html").read_bytes()).hexdigest()
    )
    assert manifest["format_version"] == staging.MANIFEST_FORMAT
    assert manifest["fixture_id"] == staging.FIXTURE_ID
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["package_version"])
    # No generated timestamp, hostname, or path may ride along.
    assert set(manifest) == {
        "format_version",
        "package_version",
        "wheel_sha256",
        "dashboard_sha256",
        "fixture_id",
    }


def test_helper_writes_exactly_the_two_staging_files(tmp_path):
    out = tmp_path / "out"
    staging.render_staging(_fake_wheel(tmp_path), out)

    assert sorted(p.name for p in out.iterdir()) == [
        "dashboard.html",
        "staging-manifest.json",
    ]


def test_helper_refuses_foreign_output_entries_and_missing_wheels(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "index.html").write_text("stray", encoding="utf-8")
    with pytest.raises(SystemExit, match="unexpected entries"):
        staging.render_staging(_fake_wheel(tmp_path), out)

    with pytest.raises(SystemExit, match="candidate wheel not found"):
        staging.render_staging(tmp_path / "missing.whl", tmp_path / "elsewhere")


def test_output_is_the_exact_unmodified_candidate_render(tmp_path):
    out = tmp_path / "out"
    staging.render_staging(_fake_wheel(tmp_path), out)
    written = (out / "dashboard.html").read_bytes()

    assert written == render_dashboard(staging.build_fixture()).encode("utf-8")

    html = written.decode("utf-8")
    assert "default-src 'none'" in html
    assert "connect-src 'none'" in html
    assert 'id="profileData"' in html
    assert 'aria-label="Filter dashboard by AI provider"' in html
    assert "Model contribution" in html
    assert "model-family evidence" in html
    for token in ("https://", "http://", "fetch(", "XMLHttpRequest", "WebSocket"):
        assert token not in html


def test_fixture_and_outputs_carry_no_private_canary(tmp_path):
    out = tmp_path / "out"
    staging.render_staging(_fake_wheel(tmp_path), out)
    blobs = {
        "helper source": SCRIPT.read_text(encoding="utf-8"),
        "dashboard.html": (out / "dashboard.html").read_text(encoding="utf-8"),
        "staging-manifest.json": (out / "staging-manifest.json").read_text(
            encoding="utf-8"
        ),
    }

    canaries = (
        "wenyu",  # maintainer identity, any casing
        "chiou",
        "gmail",
        "@users.noreply",
        "c:\\users",
        "/home/",
        "/users/",
        "github.com",
    )
    for name, blob in blobs.items():
        lowered = blob.lower()
        for canary in canaries:
            assert canary not in lowered, f"canary {canary!r} in {name}"

    # No commit-SHA-like token may appear in the rendered page, and the two
    # 64-hex manifest digests must be exactly the computed artifact digests.
    assert re.search(r"[0-9a-f]{40}", blobs["dashboard.html"]) is None
    manifest = json.loads(blobs["staging-manifest.json"])
    hex64 = set(re.findall(r"[0-9a-f]{64}", blobs["staging-manifest.json"]))
    assert hex64 == {manifest["wheel_sha256"], manifest["dashboard_sha256"]}


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _job_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [a-z][a-z0-9_-]*:\n|\Z)",
        text,
    )
    assert match is not None, name
    return match.group("body")


def _job_permissions(block: str) -> dict[str, str]:
    match = re.search(
        r"(?ms)^    permissions:\n(?P<body>(?:^      [a-z-]+: \S+\n)+)",
        block,
    )
    assert match is not None
    return dict(
        line.strip().split(": ", 1)
        for line in match.group("body").splitlines()
    )


def test_workflow_is_manual_only():
    text = _workflow_text()
    on_block = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]

    assert on_block.strip() == "workflow_dispatch:"
    assert re.search(
        r"^\s*(push|pull_request|pull_request_target|schedule|workflow_run|workflow_call):",
        text,
        re.MULTILINE,
    ) is None
    assert "if: github.repository == 'WenyuChiou/ai-profile'" in text


def test_workflow_uses_only_the_pinned_action_shas():
    uses = re.findall(r"uses: (\S+)", _workflow_text())

    assert sorted(uses) == sorted(
        [
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
            "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
            "actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b",
            "actions/upload-pages-artifact@56afc609e74202658d3ffba0e8f6dda462b719fa",
            "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e",
        ]
    )


def test_workflow_grants_only_the_minimal_pages_permissions():
    text = _workflow_text()
    build = _job_block(text, "build")
    deploy = _job_block(text, "deploy")

    assert re.findall(r"(?m)^permissions: (.+)$", text) == ["{}"]
    assert _job_permissions(build) == {"contents": "read"}
    assert _job_permissions(deploy) == {"pages": "write", "id-token": "write"}
    assert text.count("permissions:") == 3
    assert "contents: write" not in text
    assert "packages:" not in text
    assert "persist-credentials: false" in text
    assert "pip install" not in deploy
    assert "python -m build" not in deploy
    assert "actions/checkout" not in deploy


def test_workflow_uses_runner_temp_only_inside_step_contexts():
    text = _workflow_text()

    # GitHub's `runner` expression context is unavailable while job-level
    # `env` is parsed. Shell steps receive RUNNER_TEMP directly.
    assert "STAGING_ROOT: ${{ runner.temp }}" not in text
    assert text.count('STAGING_ROOT="$RUNNER_TEMP/aiprofile-staging"') == 3


def test_workflow_verifies_the_exact_candidate_digest_before_pages_upload():
    text = _workflow_text()
    manifest = json.loads(
        (ROOT / "docs" / "reviews" / "promotion-candidate.json").read_text(
            encoding="utf-8"
        )
    )

    # The workflow's hardcoded expectations must be the frozen candidate.
    assert manifest["wheel_sha256"] == PINNED_WHEEL_SHA256
    assert manifest["dashboard_sha256"] == PINNED_DASHBOARD_SHA256
    assert manifest["version"] == "0.5.0"
    assert text.count(PINNED_WHEEL_SHA256) == 3  # artifact check + both job boundaries
    assert "--expected-version 0.5.0" in text
    assert 'manifest["package_version"] == "0.5.0"' in text

    # Both digest verifications happen before anything is uploaded to Pages.
    upload_at = text.index("actions/upload-pages-artifact")
    assert text.rindex(PINNED_WHEEL_SHA256) < upload_at
    assert text.count(PINNED_DASHBOARD_SHA256) == 2
    # The frozen ZIP timestamp is exported before the build it freezes.
    assert text.index('["source_date_epoch"]') < text.index("python -m build")


def test_workflow_renders_in_and_uploads_only_a_fresh_verified_staging_root():
    text = _workflow_text()

    assert "-m venv" in text
    assert 'pip install "$WHEEL"' in text
    assert "pip install -e" not in text
    assert 'scripts/render_staging_dashboard.py' in text
    assert '--out "$STAGING_ROOT/v0.5.0"' in text
    assert "path: ${{ runner.temp }}/aiprofile-staging\n" in text
    assert text.count("assert root.is_dir() and not root.is_symlink()") == 2
    assert text.count('("v0.5.0", "dir")') == 2
    assert text.count('("v0.5.0/dashboard.html", "file")') == 2
    assert text.count('("v0.5.0/staging-manifest.json", "file")') == 2
    assert "assert not any(path.is_symlink()" in text
    assert text.count("json.dumps(manifest, indent=2, sort_keys=True)") == 2
    assert text.count('"synthetic-two-provider-fixture-v2-model-ledger"') == 2
    assert "actions/upload-artifact" in text
    assert "actions/download-artifact" in text


def test_fixture_description_never_claims_human_only():
    """A `DayCell(ai_commits == 0)` fixture day is zero-attributed-AI,
    never provably human (ADR-020 erratum / ADR-022): the staging script's
    own prose must not resurrect the corrected claim."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "human-only" not in text.lower()
    assert "zero-attributed-AI day" in text

"""Regression tests for the exact release-artifact contract."""

from __future__ import annotations

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_release_artifacts.py"
SPEC = importlib.util.spec_from_file_location("check_release_artifacts", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
artifacts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifacts)


def _wheel(path: Path, version: str, *, notice: bool = True) -> None:
    dist_info = f"ai_profile_cli-{version}.dist-info"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{dist_info}/METADATA", f"Name: ai-profile-cli\nVersion: {version}\n")
        archive.writestr(f"{dist_info}/licenses/LICENSE", "MIT")
        if notice:
            archive.writestr(
                f"{dist_info}/licenses/THIRD_PARTY_NOTICES.md",
                "third-party notices",
            )


def _sdist(path: Path, version: str) -> None:
    root = f"ai_profile_cli-{version}"
    with tarfile.open(path, "w:gz") as archive:
        for name, body in (
            ("PKG-INFO", f"Name: ai-profile-cli\nVersion: {version}\n"),
            ("LICENSE", "MIT"),
            ("THIRD_PARTY_NOTICES.md", "third-party notices"),
        ):
            payload = body.encode()
            info = tarfile.TarInfo(f"{root}/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))


def test_release_artifacts_require_both_notices_and_version_parity(tmp_path):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(sdist, version)

    assert (
        artifacts.validate_release_artifacts(
            wheel,
            sdist,
            expected_version=version,
            tag=f"v{version}",
        )
        == version
    )


def test_release_artifacts_reject_wheel_without_third_party_notice(tmp_path):
    version = artifacts._project_version()
    wheel = tmp_path / "broken.whl"
    sdist = tmp_path / "source.tar.gz"
    _wheel(wheel, version, notice=False)
    _sdist(sdist, version)

    with pytest.raises(artifacts.ArtifactContractError, match="THIRD_PARTY_NOTICES"):
        artifacts.validate_release_artifacts(wheel, sdist)


def test_release_artifacts_reject_notice_from_unrelated_dist_info(tmp_path):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version, notice=False)
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr(
            "unrelated-1.0.dist-info/licenses/THIRD_PARTY_NOTICES.md",
            "wrong distribution",
        )
    _sdist(sdist, version)

    with pytest.raises(artifacts.ArtifactContractError, match="THIRD_PARTY_NOTICES"):
        artifacts.validate_release_artifacts(wheel, sdist)


def test_release_artifacts_reject_missing_pkg_info_cleanly(tmp_path):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    root = f"ai_profile_cli-{version}"
    with tarfile.open(sdist, "w:gz") as archive:
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            payload = name.encode()
            info = tarfile.TarInfo(f"{root}/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    with pytest.raises(artifacts.ArtifactContractError, match="missing PKG-INFO"):
        artifacts.validate_release_artifacts(wheel, sdist)


def test_release_directory_rejects_extra_entries_and_verifies_checksums(tmp_path):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(sdist, version)

    artifacts._validate_artifact_set(tmp_path, wheel, sdist, version)
    checksums = tmp_path.parent / "SHA256SUMS"
    artifacts._write_checksums(checksums, wheel, sdist)
    artifacts._verify_checksums(checksums, wheel, sdist)

    (tmp_path / "unexpected.zip").write_bytes(b"extra")
    with pytest.raises(artifacts.ArtifactContractError, match="expected only"):
        artifacts._validate_artifact_set(tmp_path, wheel, sdist, version)


def test_checksum_manifest_is_portable_across_download_directories(tmp_path):
    version = artifacts._project_version()
    original = tmp_path / "dist"
    original.mkdir()
    wheel = original / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = original / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(sdist, version)
    checksums = tmp_path / "SHA256SUMS"
    artifacts._write_checksums(checksums, wheel, sdist)

    relocated = tmp_path / "downloaded-release"
    relocated.mkdir()
    relocated_wheel = relocated / wheel.name
    relocated_sdist = relocated / sdist.name
    relocated_wheel.write_bytes(wheel.read_bytes())
    relocated_sdist.write_bytes(sdist.read_bytes())

    artifacts._verify_checksums(checksums, relocated_wheel, relocated_sdist)
    assert all(
        line.split("  ", 1)[1].startswith("dist/")
        for line in checksums.read_text(encoding="ascii").splitlines()
    )


def test_artifact_only_validation_does_not_require_source_version(tmp_path, monkeypatch):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(sdist, version)
    monkeypatch.setattr(
        artifacts,
        "_project_version",
        lambda: (_ for _ in ()).throw(AssertionError("source must not be read")),
    )

    assert artifacts.validate_release_artifacts(
        wheel,
        sdist,
        expected_version=version,
        check_source=False,
    ) == version


def test_pyproject_declares_both_license_files():
    import tomllib

    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]

    assert project["license-files"] == ["LICENSE", "THIRD_PARTY_NOTICES.md"]

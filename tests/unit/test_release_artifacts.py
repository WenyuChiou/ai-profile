"""Regression tests for the exact release-artifact contract."""

from __future__ import annotations

import importlib.util
import io
import stat
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


def _wheel(
    path: Path,
    version: str,
    *,
    notice: bool = True,
    extra_members: tuple[tuple[str, bytes], ...] = (),
    symlink_members: tuple[tuple[str, str], ...] = (),
) -> None:
    dist_info = f"ai_profile_cli-{version}.dist-info"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{dist_info}/METADATA", f"Name: ai-profile-cli\nVersion: {version}\n")
        archive.writestr(f"{dist_info}/licenses/LICENSE", "MIT")
        if notice:
            archive.writestr(
                f"{dist_info}/licenses/THIRD_PARTY_NOTICES.md",
                "third-party notices",
            )
        for name, payload in extra_members:
            info = zipfile.ZipInfo(name)
            # ZipInfo normalizes the host separator at construction time.
            # Restore the requested raw name so malformed backslash entries
            # can be exercised on Windows too.
            info.filename = name
            info.orig_filename = name
            archive.writestr(info, payload)
        for name, target in symlink_members:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, target)


def _sdist(
    path: Path,
    version: str,
    *,
    extra_members: tuple[tuple[str, bytes], ...] = (),
    outside_members: tuple[tuple[str, bytes], ...] = (),
    special_members: tuple[tuple[str, bytes, str], ...] = (),
) -> None:
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
        for name, payload in extra_members:
            info = tarfile.TarInfo(f"{root}/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        for name, payload in outside_members:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        member_types = {
            "symlink": tarfile.SYMTYPE,
            "hardlink": tarfile.LNKTYPE,
            "fifo": tarfile.FIFOTYPE,
            "sparse": tarfile.GNUTYPE_SPARSE,
            "contiguous": tarfile.CONTTYPE,
        }
        for name, kind, target in special_members:
            info = tarfile.TarInfo(f"{root}/{name}")
            info.type = member_types[kind]
            info.linkname = target
            archive.addfile(info)


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


@pytest.mark.parametrize(
    "member",
    (
        ".hypothesis/constants/cache-entry",
        ".pytest_cache/v/cache/nodeids",
        ".ruff_cache/cache-entry",
        ".mypy_cache/3.12/cache-entry",
        ".tox/py312/cache-entry",
        ".nox/tests/cache-entry",
        ".venv/Lib/site-packages/cache-entry",
        "src/aiprofile/__pycache__/cli.cpython-312.pyc",
        ".coverage",
        ".coverage.hostname.1234",
    ),
)
def test_release_artifacts_reject_generated_cache_members(tmp_path, member):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(sdist, version, extra_members=((member, b"generated cache"),))

    with pytest.raises(artifacts.ArtifactContractError, match="generated cache"):
        artifacts.validate_release_artifacts(wheel, sdist)


@pytest.mark.parametrize(
    "member",
    (
        ".ai/handoff/private.txt",
        ".artifact/release/private.txt",
        ".claude/settings.local.json",
        "build/generated.txt",
        "dist/old-release.whl",
    ),
)
def test_release_artifacts_reject_private_or_generated_root_members(tmp_path, member):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(sdist, version, extra_members=((member, b"C:/Users/private"),))

    with pytest.raises(
        artifacts.ArtifactContractError,
        match="private or generated root member",
    ):
        artifacts.validate_release_artifacts(wheel, sdist)


@pytest.mark.parametrize("member", (".coverage", "unexpected-root-file.txt"))
def test_release_artifacts_reject_members_outside_archive_root(tmp_path, member):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(sdist, version, outside_members=((member, b"outside root"),))

    with pytest.raises(artifacts.ArtifactContractError, match="outside the archive root"):
        artifacts.validate_release_artifacts(wheel, sdist)


def test_release_artifacts_reject_parent_traversal_from_archive_root(tmp_path):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(sdist, version, extra_members=(("../unexpected.txt", b"outside root"),))

    with pytest.raises(artifacts.ArtifactContractError, match="sdist member path"):
        artifacts.validate_release_artifacts(wheel, sdist)


@pytest.mark.parametrize(
    "member",
    (
        "../wheel-traversal-canary.txt",
        "/absolute-wheel-member.txt",
        "C:/drive-qualified-wheel-member.txt",
        "C:drive-relative-wheel-member.txt",
        "nested/nul\x00wheel-member.txt",
        "nested\\backslash-wheel-member.txt",
        "nested//noncanonical-wheel-member.txt",
    ),
)
def test_release_artifacts_reject_unsafe_wheel_member_paths(tmp_path, member):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version, extra_members=((member, b"unsafe"),))
    _sdist(sdist, version)

    with pytest.raises(artifacts.ArtifactContractError, match="wheel member path"):
        artifacts.validate_release_artifacts(wheel, sdist)


def test_release_artifacts_reject_wheel_symlinks(tmp_path):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(
        wheel,
        version,
        symlink_members=(("wheel-link", "../../../outside-canary"),),
    )
    _sdist(sdist, version)

    with pytest.raises(artifacts.ArtifactContractError, match="wheel member type"):
        artifacts.validate_release_artifacts(wheel, sdist)


def test_release_artifacts_reject_duplicate_wheel_members(tmp_path):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    with pytest.warns(UserWarning, match="Duplicate name"):
        _wheel(
            wheel,
            version,
            extra_members=(("duplicate.txt", b"first"), ("duplicate.txt", b"second")),
        )
    _sdist(sdist, version)

    with pytest.raises(artifacts.ArtifactContractError, match="duplicate wheel member"):
        artifacts.validate_release_artifacts(wheel, sdist)


@pytest.mark.parametrize(
    "kind",
    ("symlink", "hardlink", "fifo", "sparse", "contiguous"),
)
def test_release_artifacts_reject_sdist_links_and_special_members(tmp_path, kind):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(
        sdist,
        version,
        special_members=(("unsafe-member", kind, "../../../outside-canary"),),
    )

    with pytest.raises(artifacts.ArtifactContractError, match="sdist member type"):
        artifacts.validate_release_artifacts(wheel, sdist)


@pytest.mark.parametrize(
    "member",
    ("nested//noncanonical-sdist-member.txt", "nested\\backslash-sdist-member.txt"),
)
def test_release_artifacts_reject_noncanonical_sdist_paths(tmp_path, member):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(sdist, version, extra_members=((member, b"unsafe"),))

    with pytest.raises(artifacts.ArtifactContractError, match="sdist member path"):
        artifacts.validate_release_artifacts(wheel, sdist)


def test_release_artifacts_reject_duplicate_sdist_members(tmp_path):
    version = artifacts._project_version()
    wheel = tmp_path / f"ai_profile_cli-{version}-py3-none-any.whl"
    sdist = tmp_path / f"ai_profile_cli-{version}.tar.gz"
    _wheel(wheel, version)
    _sdist(
        sdist,
        version,
        extra_members=(("duplicate.txt", b"first"), ("duplicate.txt", b"second")),
    )

    with pytest.raises(artifacts.ArtifactContractError, match="duplicate sdist member"):
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

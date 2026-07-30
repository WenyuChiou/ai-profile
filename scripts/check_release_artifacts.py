#!/usr/bin/env python3
"""Validate the exact wheel and sdist intended for publication."""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_LICENSE_FILES = ("LICENSE", "THIRD_PARTY_NOTICES.md")
GENERATED_CACHE_DIRS = frozenset(
    {
        ".hypothesis",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
    }
)
FORBIDDEN_ROOT_ENTRIES = frozenset({".ai", ".artifact", ".claude", "build", "dist"})


class ArtifactContractError(RuntimeError):
    """A distribution artifact does not satisfy the release contract."""


def _metadata_version(text: str) -> str:
    match = re.search(r"^Version:\s*(\S+)\s*$", text, flags=re.MULTILINE)
    if match is None:
        raise ArtifactContractError("distribution metadata has no Version field")
    return match.group(1)


def _runtime_version() -> str:
    init_path = REPO_ROOT / "src" / "aiprofile" / "__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "__version__"
                    for target in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise ArtifactContractError(f"could not read __version__ from {init_path}")


def _project_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def _one_artifact(dist_dir: Path, pattern: str, label: str) -> Path:
    matches = sorted(dist_dir.glob(pattern))
    if len(matches) != 1:
        raise ArtifactContractError(
            f"expected exactly one {label} in {dist_dir}, found {len(matches)}"
        )
    return matches[0]


def _check_wheel(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ArtifactContractError(f"{path.name}: expected one METADATA file")
        dist_info = metadata_names[0].removesuffix("/METADATA")
        for required in REQUIRED_LICENSE_FILES:
            if f"{dist_info}/licenses/{required}" not in names:
                raise ArtifactContractError(f"{path.name}: missing {required}")
        metadata = archive.read(metadata_names[0]).decode("utf-8")
    return _metadata_version(metadata)


def _check_sdist(path: Path) -> str:
    with tarfile.open(path, mode="r:gz") as archive:
        names = archive.getnames()
        roots = {name.split("/", 1)[0] for name in names if "/" in name}
        if len(roots) != 1:
            raise ArtifactContractError(f"{path.name}: expected one archive root")
        root = next(iter(roots))
        for name in names:
            try:
                relative = PurePosixPath(name).relative_to(root)
            except ValueError as exc:
                raise ArtifactContractError(
                    f"{path.name}: member is outside the archive root: {name}"
                ) from exc
            if ".." in relative.parts:
                raise ArtifactContractError(
                    f"{path.name}: member is outside the archive root: {name}"
                )
            if relative.parts and relative.parts[0] in FORBIDDEN_ROOT_ENTRIES:
                raise ArtifactContractError(
                    f"{path.name}: private or generated root member is forbidden: {relative}"
                )
            if (
                GENERATED_CACHE_DIRS.intersection(relative.parts)
                or relative.name == ".coverage"
                or relative.name.startswith(".coverage.")
                or relative.suffix in {".pyc", ".pyo"}
            ):
                raise ArtifactContractError(
                    f"{path.name}: generated cache member is forbidden: {relative}"
                )
        for required in REQUIRED_LICENSE_FILES:
            if f"{root}/{required}" not in names:
                raise ArtifactContractError(f"{path.name}: missing {required}")
        try:
            pkg_info_member = archive.getmember(f"{root}/PKG-INFO")
        except KeyError as exc:
            raise ArtifactContractError(f"{path.name}: missing PKG-INFO") from exc
        pkg_info = archive.extractfile(pkg_info_member)
        if pkg_info is None:
            raise ArtifactContractError(f"{path.name}: PKG-INFO is not a regular file")
        metadata = pkg_info.read().decode("utf-8")
    return _metadata_version(metadata)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_artifact_set(dist_dir: Path, wheel: Path, sdist: Path, version: str) -> None:
    expected_names = {
        f"ai_profile_cli-{version}-py3-none-any.whl",
        f"ai_profile_cli-{version}.tar.gz",
    }
    entries = list(dist_dir.iterdir())
    actual_names = {entry.name for entry in entries}
    if actual_names != expected_names:
        raise ArtifactContractError(
            f"{dist_dir}: expected only {sorted(expected_names)}, found {sorted(actual_names)}"
        )
    if {wheel.name, sdist.name} != expected_names:
        raise ArtifactContractError("selected artifacts do not match the canonical filenames")
    for entry in entries:
        if entry.is_symlink() or not entry.is_file():
            raise ArtifactContractError(f"{entry}: artifact must be a regular non-symlink file")


def _checksum_lines(wheel: Path, sdist: Path) -> list[str]:
    return [
        f"{_sha256(path)}  dist/{path.name}"
        for path in sorted((wheel, sdist), key=lambda item: item.name)
    ]


def _write_checksums(path: Path, wheel: Path, sdist: Path) -> None:
    path.write_text("\n".join(_checksum_lines(wheel, sdist)) + "\n", encoding="ascii")


def _verify_checksums(path: Path, wheel: Path, sdist: Path) -> None:
    expected = _checksum_lines(wheel, sdist)
    observed = path.read_text(encoding="ascii").splitlines()
    if observed != expected:
        raise ArtifactContractError(
            f"{path}: checksum manifest mismatch; expected exactly {expected!r}"
        )


def validate_release_artifacts(
    wheel: Path,
    sdist: Path,
    *,
    expected_version: str | None = None,
    tag: str | None = None,
    check_source: bool = True,
    expected_wheel_sha256: str | None = None,
) -> str:
    """Validate notices and version parity; return the agreed version."""
    versions = {"wheel": _check_wheel(wheel), "sdist": _check_sdist(sdist)}
    if check_source:
        versions["pyproject"] = _project_version()
        versions["runtime"] = _runtime_version()
    if expected_version is not None:
        versions["expected"] = expected_version
    if tag is not None:
        if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
            raise ArtifactContractError(f"release tag must be vX.Y.Z, got {tag!r}")
        versions["tag"] = tag[1:]
    if len(set(versions.values())) != 1:
        detail = ", ".join(f"{name}={value}" for name, value in versions.items())
        raise ArtifactContractError(f"version mismatch: {detail}")
    if expected_wheel_sha256 is not None:
        normalized = expected_wheel_sha256.lower()
        if not re.fullmatch(r"[0-9a-f]{64}", normalized):
            raise ArtifactContractError("expected wheel SHA-256 must be 64 hexadecimal digits")
        observed = _sha256(wheel)
        if observed != normalized:
            raise ArtifactContractError(
                f"{wheel.name}: SHA-256 {observed} != expected {normalized}"
            )
    version = next(iter(versions.values()))
    print(f"PASS: artifact contract for ai-profile-cli {version}")
    print(f"  wheel: {wheel}")
    print(f"  sdist: {sdist}")
    print("  required notices: LICENSE, THIRD_PARTY_NOTICES.md")
    return version


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=REPO_ROOT / "dist")
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--sdist", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--tag")
    parser.add_argument(
        "--artifact-only",
        action="store_true",
        help="validate artifact internals without comparing the current source checkout",
    )
    parser.add_argument("--expected-wheel-sha256")
    parser.add_argument("--write-checksums", type=Path)
    parser.add_argument("--checksum-file", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        wheel = args.wheel or _one_artifact(args.dist_dir, "*.whl", "wheel")
        sdist = args.sdist or _one_artifact(args.dist_dir, "*.tar.gz", "sdist")
        version = validate_release_artifacts(
            wheel,
            sdist,
            expected_version=args.expected_version,
            tag=args.tag,
            check_source=not args.artifact_only,
            expected_wheel_sha256=args.expected_wheel_sha256,
        )
        _validate_artifact_set(args.dist_dir, wheel, sdist, version)
        if args.checksum_file is not None:
            _verify_checksums(args.checksum_file, wheel, sdist)
        if args.write_checksums is not None:
            _write_checksums(args.write_checksums, wheel, sdist)
    except (ArtifactContractError, OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"FAIL: artifact contract: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

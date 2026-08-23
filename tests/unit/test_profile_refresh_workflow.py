"""Security and operational contract for public profile automation.

Commit A of the v0.8.0 hosted pin: the reusable workflow installs exactly
``ai-profile-cli==0.8.0``; the caller template still pins the immutable
v0.7.0-era commit A (``9c4f276``) until commit B repins it.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "profile-refresh.yml"
CALLER = ROOT / "docs" / "templates" / "profile-refresh-caller.yml"
COMMIT_A = "9c4f276cb437f1866a2c1b407efe54d3790ce811"

ASSET_NAMES = (
    "badge-dark.svg",
    "badge-light.svg",
    "dashboard.html",
    "heatmap-dark.svg",
    "heatmap-light.svg",
    "profile.json",
    "summary-dark.svg",
    "summary-light.svg",
)
ASSET_PATHS = tuple(f"dist/{name}" for name in ASSET_NAMES)

CHECKOUT_PIN = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_PIN = (
    "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
)
UPLOAD_ARTIFACT_PIN = (
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
)
DOWNLOAD_ARTIFACT_PIN = (
    "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093"
)
CONFIGURE_PAGES_PIN = (
    "actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d"
)
UPLOAD_PAGES_PIN = (
    "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9"
)
DEPLOY_PAGES_PIN = (
    "actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _job_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [a-z][a-z0-9_-]*:\n|\Z)",
        text,
    )
    assert match is not None, name
    return match.group("body")


def _step_script(text: str, name: str) -> str:
    lines = text.splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == f"- name: {name}"
    )
    run = next(
        index
        for index in range(start + 1, len(lines))
        if lines[index].startswith("        run: |")
    )
    body: list[str] = []
    for line in lines[run + 1 :]:
        if line and not line.startswith("          "):
            break
        body.append(line[10:] if line else "")
    return "\n".join(body).rstrip() + "\n"


def _heredoc_python(script: str) -> str:
    return textwrap.dedent(
        script.split("python - <<'PY'\n", 1)[1].split("\nPY", 1)[0]
    )


def _permissions(block: str) -> dict[str, str]:
    match = re.search(
        r"(?ms)^    permissions:\n(?P<body>(?:^      [a-z-]+: \S+\n)+)",
        block,
    )
    assert match is not None
    return dict(
        line.strip().split(": ", 1) for line in match.group("body").splitlines()
    )


def _git(directory: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=directory,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result


def test_reusable_workflow_is_call_only_no_dangerous_triggers():
    text = _text(WORKFLOW)
    on_block = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]

    assert re.search(r"(?m)^  workflow_call:\s*$", on_block)
    for trigger in (
        "push",
        "pull_request",
        "pull_request_target",
        "schedule",
        "workflow_dispatch",
        "repository_dispatch",
        "workflow_run",
    ):
        assert re.search(rf"(?m)^  {trigger}:\s*$", on_block) is None
    assert "never matrix this workflow across profiles" in text


def test_identities_is_a_required_secret_and_never_interpolated():
    text = _text(WORKFLOW)
    on_block = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    run_scripts = "\n".join(
        _step_script(text, name)
        for name in (
            "Validate repositories and identities",
            "Verify every source repository is public",
            "Clone public repositories without credentials",
            "Install released ai-profile",
            "Initialize private ephemeral configuration",
            "Register public repositories and refresh",
            "Publish changed assets only",
        )
    )

    secrets = on_block.split("    secrets:\n", 1)[1]
    assert re.search(
        r"(?ms)^      identities:\n(?:        .*\n)*?        required: true\s*$",
        secrets,
    )
    assert "${{ secrets.identities }}" in text
    assert "${{ inputs.repositories }}" in text
    assert "${{ secrets.identities }}" not in run_scripts
    assert "${{ inputs." not in run_scripts
    assert "eval" not in text
    for line in text.splitlines():
        if "${{ secrets.identities }}" in line:
            assert re.fullmatch(
                r"\s+AIPROFILE_IDENTITIES: \$\{\{ secrets\.identities \}\}",
                line,
            )
        if "${{ inputs.repositories }}" in line:
            assert re.fullmatch(
                r"\s+REPOSITORIES_INPUT: \$\{\{ inputs\.repositories \}\}",
                line,
            )
    assert not re.search(
        r"(?im)^.*(?:echo|printf|print|GITHUB_OUTPUT).*AIPROFILE_IDENTITIES",
        run_scripts,
    )


def test_public_only_enforcement_present_before_clone():
    text = _text(WORKFLOW)
    visibility = _step_script(text, "Verify every source repository is public")
    clone = _step_script(text, "Clone public repositories without credentials")

    assert text.index("gh api") < text.index("git -c credential.helper= clone")
    assert 'gh api "repos/$entry" --jq .visibility' in visibility
    assert '[[ "$visibility" == "public" ]]' in visibility
    assert "GIT_TERMINAL_PROMPT=0" in clone
    assert "GIT_ASKPASS=/bin/false" in clone
    assert "git -c credential.helper= clone --filter=blob:none --no-checkout" in clone
    assert "GH_TOKEN" not in clone
    assert '2>/dev/null' in visibility
    assert '>/dev/null 2>&1' in clone
    assert "Unable to verify public visibility for source repository $index." in visibility
    assert "Unable to clone source repository $index." in clone


def test_repositories_is_the_only_input_and_version_dest_hardcoded():
    text = _text(WORKFLOW)
    refresh_job = _job_block(text, "refresh")
    on_block = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    inputs = on_block.split("    inputs:\n", 1)[1].split("    secrets:\n", 1)[0]

    assert re.findall(r"(?m)^      ([a-z][a-z0-9_-]*):\s*$", inputs) == [
        "repositories"
    ]
    assert text.count("ai-profile-cli==") == 1
    assert 'python -m pip install "ai-profile-cli==0.8.0"' in text
    assert "ai-profile-cli==0.7.0" not in text
    assert "package-version" not in text
    assert "profile-dist-dir" not in text
    assert 'AIPROFILE_HOME="$RUNNER_TEMP/aiprofile-home"' in text
    assert 'aiprofile refresh --out "$RUNNER_TEMP/dist"' in text
    assert "pip install -e" not in text
    assert "actions/checkout" not in refresh_job
    assert re.search(r"(?m)^\s+destination = Path\(\"dist\"\)$", text)


def test_commit_job_stages_exactly_eight_paths_no_git_add_dot():
    text = _text(WORKFLOW)
    commit = _step_script(text, "Publish changed assets only")

    assert "public_paths=(" in commit
    for path in ASSET_PATHS:
        assert commit.count(f'"{path}"') == 1
    assert 'git add -- "${public_paths[@]}"' in commit
    assert 'git status --porcelain -- "${public_paths[@]}"' in commit
    assert 'git commit -q -m "Refresh ai-profile assets" -- "${public_paths[@]}"' in commit
    assert "git add ." not in text
    assert "git add -A" not in text
    assert "git add --all" not in text
    assert 'git commit -q' in commit
    assert 'git push -q' in commit
    assert "Unable to commit refreshed ai-profile assets." in commit
    assert "Unable to push refreshed ai-profile assets." in commit
    assert commit.count(">/dev/null 2>&1") >= 2


def test_permission_split_and_pins():
    text = _text(WORKFLOW)
    refresh = _job_block(text, "refresh")
    commit = _job_block(text, "commit")
    uses = re.findall(r"(?m)^\s+uses: (\S+)(?:\s+#\s+v\S+)?$", text)

    assert re.findall(r"(?m)^permissions: (.+)$", text) == ["{}"]
    assert _permissions(refresh) == {"contents": "read"}
    assert _permissions(commit) == {"contents": "write"}
    assert "id-token:" not in text
    assert "pages:" not in text
    assert "persist-credentials: true" not in refresh
    assert "persist-credentials: true" in commit
    assert uses == [
        SETUP_PYTHON_PIN,
        UPLOAD_ARTIFACT_PIN,
        CHECKOUT_PIN,
        DOWNLOAD_ARTIFACT_PIN,
    ]
    for line in text.splitlines():
        if "uses:" in line:
            assert re.search(r"uses: [^@\s]+@[0-9a-f]{40}\s+#\s+v\S+$", line)
    assert "group: profile-refresh-update-${{ github.repository }}" in text
    assert "cancel-in-progress: false" in text


def test_byte_change_gate_present_before_commit():
    script = _step_script(_text(WORKFLOW), "Publish changed assets only")

    assert script.index("git status --porcelain --") < script.index("git commit -q -m")
    assert 'if [[ -z "$changed" ]]' in script
    assert script.index('if [[ -z "$changed" ]]') < script.index("git commit -q -m")


def test_reusable_exposes_exact_published_commit_for_pages():
    text = _text(WORKFLOW)
    commit = _job_block(text, "commit")
    script = _step_script(text, "Publish changed assets only")

    assert re.search(
        r"(?ms)^    outputs:\n"
        r"      published-sha:\n"
        r"        .*\n"
        r"        value: \$\{\{ jobs\.commit\.outputs\.published-sha \}\}",
        text,
    )
    assert "outputs:\n      published-sha: ${{ steps.publish.outputs.published-sha }}" in commit
    assert "id: publish" in commit
    assert 'published_commit="$(git rev-parse HEAD 2>/dev/null)"' in script
    assert '"$published_commit:refs/heads/$TARGET_BRANCH"' in script
    assert "HEAD:refs/heads" not in script
    assert "published-sha=%s\\n" in script


@pytest.mark.parametrize(
    ("repositories", "identities"),
    [
        ("owner/repo;rm", '["person@example.com"]'),
        ("../../x", '["person@example.com"]'),
        ("owner/repo$(cmd)", '["person@example.com"]'),
        ("", '["person@example.com"]'),
        ("owner/repo", ""),
        ("owner/repo", "[]"),
    ],
)
def test_validation_script_rejects_hostile_values_without_leaking_secret(
    tmp_path,
    monkeypatch,
    capsys,
    repositories,
    identities,
):
    script = _heredoc_python(
        _step_script(_text(WORKFLOW), "Validate repositories and identities")
    )
    monkeypatch.setenv("REPOSITORIES_INPUT", repositories)
    monkeypatch.setenv("AIPROFILE_IDENTITIES", identities)
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))

    compile(script, "profile-refresh-validation", "exec")
    with pytest.raises(SystemExit):
        exec(compile(script, "profile-refresh-validation", "exec"), {})
    captured = capsys.readouterr()
    if identities:
        assert identities not in captured.out + captured.err
    assert not (tmp_path / "repositories.txt").exists()


def test_validation_and_config_scripts_accept_json_or_lines_without_echo(
    tmp_path,
    monkeypatch,
    capsys,
):
    workflow = _text(WORKFLOW)
    validate = _heredoc_python(
        _step_script(workflow, "Validate repositories and identities")
    )
    configure = _heredoc_python(
        _step_script(workflow, "Initialize private ephemeral configuration")
    )
    home = tmp_path / "aiprofile-home"
    home.mkdir()
    (home / "config.json").write_text(
        json.dumps({"identities": [], "repositories": [], "salt": "s" * 64}),
        encoding="utf-8",
    )
    secret = "first@example.com\nsecond@example.com"
    monkeypatch.setenv("REPOSITORIES_INPUT", "Owner/Repo\nowner/second")
    monkeypatch.setenv("AIPROFILE_IDENTITIES", secret)
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("AIPROFILE_HOME", str(home))

    exec(compile(validate, "profile-refresh-validation", "exec"), {})
    exec(compile(configure, "profile-refresh-config", "exec"), {})

    assert (tmp_path / "repositories.txt").read_text(encoding="utf-8") == (
        "Owner/Repo\nowner/second\n"
    )
    config = json.loads((home / "config.json").read_text(encoding="utf-8"))
    assert config["identities"] == ["first@example.com", "second@example.com"]
    assert secret not in capsys.readouterr().out


@pytest.mark.skipif(os.name == "nt", reason="extracted Bash probe runs on POSIX CI")
def test_clone_script_keeps_hostile_repository_text_in_one_argv(tmp_path):
    script = _step_script(
        _text(WORKFLOW), "Clone public repositories without credentials"
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    args_file = tmp_path / "git-args"
    fake_git = bin_dir / "git"
    fake_git.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$FAKE_GIT_ARGS\"\n",
        encoding="utf-8",
    )
    fake_git.chmod(0o700)
    (tmp_path / "repositories.txt").write_text(
        "owner/repo;touch SHOULD_NOT_EXIST\n", encoding="utf-8"
    )
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
        "FAKE_GIT_ARGS": str(args_file),
    }

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "SHOULD_NOT_EXIST").exists()
    args = args_file.read_text(encoding="utf-8").splitlines()
    assert "credential.helper=" in args
    assert "https://github.com/owner/repo;touch SHOULD_NOT_EXIST.git" in args


@pytest.mark.skipif(os.name == "nt", reason="extracted Bash probe runs on POSIX CI")
def test_commit_script_preserves_unrelated_index_and_skips_unchanged(tmp_path):
    script = _step_script(_text(WORKFLOW), "Publish changed assets only")
    repo = tmp_path / "profile"
    remote = tmp_path / "remote.git"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "config", "user.email", "fixture@example.com")
    (repo / "README.md").write_text("profile\n", encoding="utf-8")
    (repo / "unrelated.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md", "unrelated.txt")
    _git(repo, "commit", "-q", "-m", "seed")
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")
    (repo / "unrelated.txt").write_text("staged-user-change\n", encoding="utf-8")
    _git(repo, "add", "unrelated.txt")
    generated = tmp_path / "generated"
    generated.mkdir()
    for name in ASSET_NAMES:
        (generated / name).write_text(f"asset:{name}\n", encoding="utf-8")
    env = {**os.environ, "RUNNER_TEMP": str(tmp_path), "TARGET_BRANCH": "main"}
    output_file = tmp_path / "github-output"
    env["GITHUB_OUTPUT"] = str(output_file)

    first = subprocess.run(
        ["bash", "-c", script],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert first.returncode == 0, first.stderr
    committed = set(_git(repo, "show", "--format=", "--name-only", "HEAD").stdout.split())
    assert committed == set(ASSET_PATHS)
    assert _git(repo, "diff", "--cached", "--name-only").stdout.strip() == (
        "unrelated.txt"
    )
    output_lines = output_file.read_text(encoding="utf-8").splitlines()
    assert len(output_lines) == 1
    assert re.fullmatch(r"published-sha=[0-9a-f]{40}", output_lines[0])
    count = _git(repo, "rev-list", "--count", "HEAD").stdout.strip()

    second = subprocess.run(
        ["bash", "-c", script],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert second.returncode == 0, second.stderr
    assert _git(repo, "rev-list", "--count", "HEAD").stdout.strip() == count
    assert _git(repo, "diff", "--cached", "--name-only").stdout.strip() == (
        "unrelated.txt"
    )
    output_lines = output_file.read_text(encoding="utf-8").splitlines()
    assert len(output_lines) == 2
    assert output_lines[0] == output_lines[1]


@pytest.mark.skipif(os.name == "nt", reason="extracted Bash probe runs on POSIX CI")
@pytest.mark.parametrize(
    ("step_name", "executable"),
    [
        ("Verify every source repository is public", "gh"),
        ("Clone public repositories without credentials", "git"),
    ],
)
def test_source_command_success_hides_raw_command_output(
    tmp_path,
    step_name,
    executable,
):
    script = _step_script(_text(WORKFLOW), step_name)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / executable
    if executable == "gh":
        body = "echo public\necho 'source-success-private-canary' >&2\n"
    else:
        body = (
            "echo 'source-success-private-canary'\n"
            "echo 'https://github.com/owner/private-canary.git' >&2\n"
        )
    fake.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
    fake.chmod(0o700)
    (tmp_path / "repositories.txt").write_text("owner/repo\n", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
    }

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "source-success-private-canary" not in result.stdout + result.stderr
    assert "https://github.com/owner/private-canary.git" not in (
        result.stdout + result.stderr
    )


@pytest.mark.skipif(os.name == "nt", reason="symlink probe runs on POSIX CI")
def test_publish_script_rejects_destination_symlink_without_touching_canary(
    tmp_path,
):
    script = _step_script(_text(WORKFLOW), "Publish changed assets only")
    repo = tmp_path / "profile"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "config", "user.email", "fixture@example.com")
    readme = repo / "README.md"
    readme.write_text("private-canary\n", encoding="utf-8")
    dist = repo / "dist"
    dist.mkdir()
    for name in ASSET_NAMES:
        (dist / name).write_text(f"old:{name}\n", encoding="utf-8")
    (dist / "profile.json").unlink()
    (dist / "profile.json").symlink_to("../README.md")
    _git(repo, "add", "README.md", "dist")
    _git(repo, "commit", "-q", "-m", "seed")
    unrelated = repo / "unrelated.txt"
    unrelated.write_text("staged-user-change\n", encoding="utf-8")
    _git(repo, "add", "unrelated.txt")
    generated = tmp_path / "generated"
    generated.mkdir()
    for name in ASSET_NAMES:
        (generated / name).write_text(f"new:{name}\n", encoding="utf-8")
    before_head = _git(repo, "rev-parse", "HEAD").stdout
    env = {**os.environ, "RUNNER_TEMP": str(tmp_path), "TARGET_BRANCH": "main"}

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 1
    assert result.stderr.strip() == "destination asset bundle is invalid"
    assert readme.read_bytes() == b"private-canary\n"
    assert _git(repo, "rev-parse", "HEAD").stdout == before_head
    assert _git(repo, "diff", "--cached", "--name-only").stdout.strip() == (
        "unrelated.txt"
    )


@pytest.mark.skipif(os.name == "nt", reason="extracted Bash probe runs on POSIX CI")
@pytest.mark.parametrize(
    ("step_name", "failure_phrase"),
    [
        (
            "Verify every source repository is public",
            "Unable to verify public visibility for source repository 1.",
        ),
        (
            "Clone public repositories without credentials",
            "Unable to clone source repository 1.",
        ),
    ],
)
def test_source_command_failures_hide_repository_canaries(
    tmp_path,
    step_name,
    failure_phrase,
):
    script = _step_script(_text(WORKFLOW), step_name)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = "gh" if step_name.startswith("Verify") else "git"
    fake = bin_dir / executable
    fake.write_text(
        "#!/bin/sh\n"
        "echo 'owner/private-canary https://github.com/owner/private-canary.git "
        "deadbeef /private/runner/path' >&2\n"
        "exit 23\n",
        encoding="utf-8",
    )
    fake.chmod(0o700)
    (tmp_path / "repositories.txt").write_text(
        "owner/private-canary\n", encoding="utf-8"
    )
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
    }

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert result.stderr.strip() == failure_phrase
    combined = result.stdout + result.stderr
    for canary in (
        "owner/private-canary",
        "https://github.com/owner/private-canary.git",
        "deadbeef",
        "/private/runner/path",
    ):
        assert canary not in combined


@pytest.mark.skipif(os.name == "nt", reason="extracted Bash probe runs on POSIX CI")
@pytest.mark.parametrize(
    ("fail_command", "failure_phrase"),
    [
        ("commit", "Unable to commit refreshed ai-profile assets."),
        ("push", "Unable to push refreshed ai-profile assets."),
    ],
)
def test_publication_command_failures_hide_git_canaries(
    tmp_path,
    fail_command,
    failure_phrase,
):
    script = _step_script(_text(WORKFLOW), "Publish changed assets only")
    repo = tmp_path / "profile"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "config", "user.email", "fixture@example.com")
    (repo / "README.md").write_text("profile\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "seed")
    generated = tmp_path / "generated"
    generated.mkdir()
    for name in ASSET_NAMES:
        (generated / name).write_text(f"asset:{name}\n", encoding="utf-8")
    real_git = shutil.which("git")
    assert real_git is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "git"
    fake.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = \"{fail_command}\" ] || "
        f"[ \"$2\" = \"{fail_command}\" ]; then\n"
        "  echo 'profile-private-canary https://example.invalid/private "
        "deadbeef /private/runner/path' >&2\n"
        "  exit 24\n"
        "fi\n"
        f"exec {shlex.quote(real_git)} \"$@\"\n",
        encoding="utf-8",
    )
    fake.chmod(0o700)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
        "TARGET_BRANCH": "main",
    }

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 1
    assert result.stderr.strip() == failure_phrase
    combined = result.stdout + result.stderr
    for canary in (
        "profile-private-canary",
        "https://example.invalid/private",
        "deadbeef",
        "/private/runner/path",
    ):
        assert canary not in combined


def test_caller_template_schedule_is_not_top_of_hour_and_has_dispatch():
    text = _text(CALLER)

    assert "workflow_dispatch:" in text
    match = re.search(r"cron: ['\"](\d+) (\d+) \* \* \*['\"]", text)
    assert match is not None
    assert match.group(1) not in {"0", "*"}
    assert match.group(0) == "cron: '37 5 * * *'"
    assert "top-of-hour" in text


def test_caller_template_passes_only_repositories_and_secret_identities():
    text = _text(CALLER)
    refresh = _job_block(text, "refresh-profile")
    with_block = refresh.split("    with:\n", 1)[1].split("    secrets:\n", 1)[0]

    assert re.findall(r"(?m)^      ([a-z][a-z0-9_-]*):", with_block) == [
        "repositories"
    ]
    assert "public repositories only" in text
    assert "OWNER/REPOSITORY" in with_block
    assert "identities: ${{ secrets.AIPROFILE_IDENTITIES }}" in refresh
    assert "package-version" not in text
    assert "profile-dist-dir" not in text
    for line in text.splitlines():
        if "AIPROFILE_IDENTITIES" in line and "Add AIPROFILE_IDENTITIES" not in line:
            assert line.strip() == "identities: ${{ secrets.AIPROFILE_IDENTITIES }}"


def test_caller_uses_exact_immutable_workflow_pin_and_v070_contract():
    text = _text(CALLER)
    uses = re.search(
        r"uses: WenyuChiou/ai-profile/\.github/workflows/"
        r"profile-refresh\.yml@([0-9a-f]{40})",
        text,
    )

    assert uses is not None
    assert uses.group(1) == COMMIT_A
    assert "hardcodes ai-profile-cli==0.7.0" in text
    assert "@v0.7.0" not in text
    assert "@main" not in text
    assert "<COMMIT" not in text


def test_caller_permissions_and_concurrency_cover_all_jobs():
    text = _text(CALLER)
    refresh = _job_block(text, "refresh-profile")
    deploy = _job_block(text, "deploy-pages")

    assert re.findall(r"(?m)^permissions: (.+)$", text) == ["{}"]
    assert _permissions(refresh) == {"contents": "write"}
    assert _permissions(deploy) == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    assert "concurrency:\n  group: profile-refresh-pages-${{ github.repository }}" in text
    assert "cancel-in-progress: false" in text
    assert "profile-refresh-update-" not in text
    assert text.index("concurrency:") < text.index("jobs:")


def test_caller_pages_job_binds_checkout_to_validated_published_sha():
    text = _text(CALLER)
    deploy = _job_block(text, "deploy-pages")
    validate = _step_script(text, "Validate immutable published revision")
    uses = re.findall(r"(?m)^\s+uses: (\S+)(?:\s+#\s+v\S+)?$", deploy)

    assert "needs: refresh-profile" in deploy
    assert "PUBLISHED_SHA: ${{ needs.refresh-profile.outputs.published-sha }}" in deploy
    assert 're.fullmatch(r"[0-9a-f]{40}", value)' in validate
    assert "ref: ${{ needs.refresh-profile.outputs.published-sha }}" in deploy
    assert "ref: ${{ github.sha }}" not in deploy
    assert "ref: ${{ github.event.repository.default_branch }}" not in deploy
    assert uses == [
        CHECKOUT_PIN,
        CONFIGURE_PAGES_PIN,
        UPLOAD_PAGES_PIN,
        DEPLOY_PAGES_PIN,
    ]
    assert "path: _site" in deploy
    for line in deploy.splitlines():
        if "uses:" in line:
            assert re.search(r"uses: [^@\s]+@[0-9a-f]{40}\s+#\s+v\S+$", line)


@pytest.mark.parametrize(
    "value",
    ("", "g" * 40, "a" * 39, "a" * 41, "a" * 40 + "\nref: main", "${{ github.sha }}"),
)
def test_caller_published_sha_validation_rejects_hostile_values(
    value,
    monkeypatch,
    capsys,
):
    script = _heredoc_python(
        _step_script(_text(CALLER), "Validate immutable published revision")
    )
    monkeypatch.setenv("PUBLISHED_SHA", value)

    with pytest.raises(SystemExit, match="published revision is invalid"):
        exec(compile(script, "profile-refresh-published-sha", "exec"), {})
    captured = capsys.readouterr()
    if value:
        assert value not in captured.out + captured.err


def test_caller_published_sha_validation_accepts_commit_a(monkeypatch, capsys):
    script = _heredoc_python(
        _step_script(_text(CALLER), "Validate immutable published revision")
    )
    monkeypatch.setenv("PUBLISHED_SHA", COMMIT_A)

    exec(compile(script, "profile-refresh-published-sha", "exec"), {})

    captured = capsys.readouterr()
    assert captured.out + captured.err == ""


def test_caller_pages_builder_copies_exact_eight_and_rejects_extra(
    tmp_path,
    monkeypatch,
):
    script = _heredoc_python(_step_script(_text(CALLER), "Build exact Pages artifact"))
    dist = tmp_path / "dist"
    dist.mkdir()
    for name in ASSET_NAMES:
        (dist / name).write_text(f"asset:{name}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exec(compile(script, "profile-refresh-pages", "exec"), {})

    target = tmp_path / "_site" / "dist"
    assert sorted(path.name for path in target.iterdir()) == list(ASSET_NAMES)
    assert all(path.is_file() and not path.is_symlink() for path in target.iterdir())
    shutil.rmtree(tmp_path / "_site")
    (dist / "private-canary.txt").write_text("private", encoding="utf-8")
    with pytest.raises(SystemExit, match="unexpected dist asset set"):
        exec(compile(script, "profile-refresh-pages", "exec"), {})
    assert not (tmp_path / "_site").exists()


def test_caller_pages_builder_rejects_nonregular_source_without_output(
    tmp_path,
    monkeypatch,
):
    script = _heredoc_python(_step_script(_text(CALLER), "Build exact Pages artifact"))
    dist = tmp_path / "dist"
    dist.mkdir()
    for name in ASSET_NAMES:
        (dist / name).write_text(f"asset:{name}\n", encoding="utf-8")
    (dist / "profile.json").unlink()
    (dist / "profile.json").mkdir()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="unexpected dist asset set"):
        exec(compile(script, "profile-refresh-pages", "exec"), {})
    assert not (tmp_path / "_site").exists()


@pytest.mark.skipif(os.name == "nt", reason="symlink probe runs on POSIX CI")
def test_caller_pages_builder_rejects_source_symlink_without_touching_canary(
    tmp_path,
    monkeypatch,
):
    script = _heredoc_python(_step_script(_text(CALLER), "Build exact Pages artifact"))
    dist = tmp_path / "dist"
    dist.mkdir()
    canary = tmp_path / "private-canary"
    canary.write_text("private\n", encoding="utf-8")
    for name in ASSET_NAMES:
        (dist / name).write_text(f"asset:{name}\n", encoding="utf-8")
    (dist / "profile.json").unlink()
    (dist / "profile.json").symlink_to(canary)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="unexpected dist asset set"):
        exec(compile(script, "profile-refresh-pages", "exec"), {})
    assert canary.read_bytes() == b"private\n"
    assert not (tmp_path / "_site").exists()


@pytest.mark.skipif(os.name == "nt", reason="symlink probe runs on POSIX CI")
def test_caller_pages_builder_rejects_linked_source_directory(
    tmp_path,
    monkeypatch,
):
    script = _heredoc_python(_step_script(_text(CALLER), "Build exact Pages artifact"))
    outside = tmp_path / "outside"
    outside.mkdir()
    for name in ASSET_NAMES:
        (outside / name).write_text(f"asset:{name}\n", encoding="utf-8")
    (tmp_path / "dist").symlink_to(outside, target_is_directory=True)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="dist asset bundle is unavailable"):
        exec(compile(script, "profile-refresh-pages", "exec"), {})
    assert not (tmp_path / "_site").exists()


@pytest.mark.skipif(os.name == "nt", reason="symlink probe runs on POSIX CI")
def test_caller_pages_builder_rejects_linked_destination_without_touching_canary(
    tmp_path,
    monkeypatch,
):
    script = _heredoc_python(_step_script(_text(CALLER), "Build exact Pages artifact"))
    dist = tmp_path / "dist"
    dist.mkdir()
    for name in ASSET_NAMES:
        (dist / name).write_text(f"asset:{name}\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    canary = outside / "private-canary"
    canary.write_text("private\n", encoding="utf-8")
    (tmp_path / "_site").symlink_to(outside, target_is_directory=True)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="Pages staging directory already exists"):
        exec(compile(script, "profile-refresh-pages", "exec"), {})
    assert canary.read_bytes() == b"private\n"
    assert sorted(path.name for path in outside.iterdir()) == ["private-canary"]


def test_caller_template_documents_operational_facts():
    text = _text(CALLER)

    for phrase in (
        "protected default branch",
        "Actions bot",
        "PR flow",
        "60 days",
        "workflow_dispatch",
        "ONE caller per profile",
        "never a matrix",
        "Allow all actions and reusable workflows",
        "WenyuChiou/ai-profile/.github/workflows/profile-refresh.yml",
        "commits pushed with GITHUB_TOKEN do not trigger",
        "immutable published-sha",
    ):
        assert phrase in text

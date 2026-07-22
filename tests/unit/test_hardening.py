"""Pre-release hardening regressions (Round A hardening batch):

- DB file owner-only permissions (storage/db.py connect()).
- Warning (not failure) when AIPROFILE_HOME sits inside a git work tree.
- cp950-safe argparse help/description text (no non-ASCII punctuation).

Grouped separately from test_config.py because these span cli.py and
storage/db.py rather than config.py alone.
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

import pytest

from aiprofile import cli
from aiprofile.storage.db import connect as db_connect

# ---------------------------------------------------------------------------
# DB file owner-only permissions
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only owner-only permission bits; Windows os.chmod cannot"
    " represent them (see storage.db._restrict_to_owner)",
)
def test_db_file_is_owner_only_on_posix(tmp_path):
    db_path = tmp_path / "aiprofile.db"
    conn = db_connect(db_path)
    try:
        assert stat.S_IMODE(db_path.stat().st_mode) == 0o600
    finally:
        conn.close()


def test_connect_chmods_db_file_owner_only(tmp_path, monkeypatch):
    calls: list[tuple[str, int]] = []
    real_chmod = os.chmod

    def recording_chmod(path, mode):
        calls.append((str(path), mode))
        real_chmod(path, mode)

    monkeypatch.setattr(os, "chmod", recording_chmod)
    db_path = tmp_path / "aiprofile.db"
    conn = db_connect(db_path)
    try:
        assert (str(db_path), 0o600) in calls
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Git-worktree warning (ROADMAP "warn when AIPROFILE_HOME is inside a git
# worktree"). Pure path-walk detection — no subprocess, no git dependency.
# ---------------------------------------------------------------------------


def test_is_inside_git_worktree_true_for_dot_git_dir(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    home = repo / ".aiprofile"
    home.mkdir()
    assert cli._is_inside_git_worktree(home) is True


def test_is_inside_git_worktree_true_for_dot_git_file(tmp_path):
    # A git worktree's/submodule's .git is a FILE with a "gitdir:" pointer,
    # not a directory — detection must accept either shape without opening
    # or parsing the file.
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: ../.git/worktrees/repo\n", encoding="utf-8")
    home = repo / "nested" / ".aiprofile"
    home.mkdir(parents=True)
    assert cli._is_inside_git_worktree(home) is True


def test_is_inside_git_worktree_true_for_nested_home(tmp_path):
    # .git lives several levels above the resolved home directory.
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    home = repo / "a" / "b" / ".aiprofile"
    home.mkdir(parents=True)
    assert cli._is_inside_git_worktree(home) is True


def test_is_inside_git_worktree_false_outside_any_repo(tmp_path, monkeypatch):
    # Not "no .git anywhere in tmp_path's real ancestry": on a machine whose
    # $HOME is itself a dotfiles git worktree (this dev box included —
    # gitio.py's assert_repository docstring calls out the exact same
    # case), pytest's tmp_path lives under a Temp dir that IS inside that
    # worktree, so a real-filesystem negative case would be flaky/false
    # per-machine. Patch Path.exists so no ancestor reports a `.git`,
    # isolating the walk from ambient filesystem state; Path.resolve()
    # (called first, before any .exists() check) needs no patch since it
    # works in non-strict mode without the path existing.
    monkeypatch.setattr(Path, "exists", lambda self: False)
    home = tmp_path / "plain" / ".aiprofile"
    assert cli._is_inside_git_worktree(home) is False


def test_cmd_init_warns_on_stderr_when_home_inside_worktree(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    home = repo / ".aiprofile"
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    # Keep this hermetic and fast: don't shell out to real git for the
    # identity-seeding lookup, which is unrelated to what this test proves.
    monkeypatch.setattr("aiprofile.gitio.config_user_email", lambda cwd: None)

    rc = cli.main(["init"])

    assert rc == 0
    captured = capsys.readouterr()
    assert "git work tree" in captured.err
    assert str(home) in captured.err


def test_cmd_init_does_not_warn_when_home_outside_worktree(tmp_path, monkeypatch, capsys):
    # cli-wiring concern only (does _cmd_init skip the print when detection
    # says False?) — deliberately decoupled from the detector's own
    # filesystem walk, which the pure-function tests above already cover;
    # see the ambient-dotfiles-repo note on the sibling detector test for
    # why a real-filesystem "outside any repo" fixture is unreliable here.
    monkeypatch.setattr(cli, "_is_inside_git_worktree", lambda path: False)
    home = tmp_path / "plain" / ".aiprofile"
    monkeypatch.setenv("AIPROFILE_HOME", str(home))
    monkeypatch.setattr("aiprofile.gitio.config_user_email", lambda cwd: None)

    rc = cli.main(["init"])

    assert rc == 0
    captured = capsys.readouterr()
    assert "git work tree" not in captured.err


# ---------------------------------------------------------------------------
# cp950-safe argparse help/description text: a mangled em-dash on 'scan
# --help' was observed live. Introspect the ACTUAL built parser (what a
# real `--help` renders) rather than grepping source, so the assertion
# tracks real user-facing behavior and cannot be fooled by non-argparse
# strings elsewhere in the file (module docstring, print() output).
# ---------------------------------------------------------------------------


def _all_help_texts() -> list[tuple[str, str]]:
    parser = cli._build_parser()
    texts = [("top-level description", parser.description or "")]
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                texts.append((f"{name} description", subparser.description or ""))
                for sub_action in subparser._actions:
                    if sub_action.help:
                        texts.append((f"{name} {sub_action.dest} help", sub_action.help))
        elif action.help:
            texts.append((f"top-level {action.dest} help", action.help))
    return texts


def test_argparse_help_and_description_strings_are_ascii():
    non_ascii = [
        (label, text) for label, text in _all_help_texts() if not text.isascii()
    ]
    assert non_ascii == []


def test_full_flag_help_renders_ascii_only_on_full_help_text():
    # The exact regression observed live: `aiprofile scan --help`.
    parser = cli._build_parser()
    scan_parser = next(
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    ).choices["scan"]
    rendered = scan_parser.format_help()
    assert rendered.isascii()


def test_all_cli_string_literals_are_ascii():
    """Complements the argparse-tree tests above: those structurally
    cannot see print()/f-string output sites, and three live em-dashes
    survived there (caught in review on a cp950 console). Walk cli.py's
    AST and assert every runtime string constant (including f-string
    literal parts) is ASCII - comments never reach stdout and are
    excluded by construction; docstrings are constants and held to the
    same bar, which is acceptable."""
    import ast
    import inspect

    source = inspect.getsource(cli)
    offenders = [
        (node.lineno, node.value)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and not node.value.isascii()
    ]
    assert offenders == []


def test_all_raised_exception_messages_are_ascii():
    """Sibling of the cli.py sweep: exception messages reach the user's
    console via the AiProfileError handler (architecture.md section 10),
    so they are user-facing output on cp950 consoles too. Walk every
    src/aiprofile module and assert every string constant inside a
    raise statement is ASCII."""
    import ast

    src_root = Path(cli.__file__).parent
    offenders = []
    for py in sorted(src_root.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and node.exc is not None:
                for sub in ast.walk(node.exc):
                    if (
                        isinstance(sub, ast.Constant)
                        and isinstance(sub.value, str)
                        and not sub.value.isascii()
                    ):
                        offenders.append((py.name, sub.lineno, sub.value))
    assert offenders == []

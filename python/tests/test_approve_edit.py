from pathlib import Path

import pytest

from mcp_edit_file_lines.approve_edit import approve_edit
from mcp_edit_file_lines.edit_types import EditOperation
from mcp_edit_file_lines.state_manager import StateManager


def test_approve_edit_applies_change(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    manager = StateManager()
    sid = manager.save_state(
        str(target),
        [EditOperation(startLine=2, endLine=2, content="modified line")],
    )

    diff = approve_edit(sid, manager)
    assert "modified line" in diff
    assert target.read_text(encoding="utf-8") == "line 1\nmodified line\nline 3\n"
    assert manager.get_state(sid) is None


def test_approve_invalid_state_id() -> None:
    manager = StateManager()
    with pytest.raises(ValueError):
        approve_edit("missing", manager)


def test_approve_edit_with_string_match(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    original = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    target.write_text(original, encoding="utf-8")

    manager = StateManager()
    sid = manager.save_state(
        str(target),
        [EditOperation(startLine=2, endLine=2, content="new", strMatch="line 2")],
    )

    approve_edit(sid, manager)
    assert target.read_text(encoding="utf-8") == "line 1\nnew\nline 3\nline 4\nline 5\n"


def test_approve_edit_with_regex_match(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    manager = StateManager()
    sid = manager.save_state(
        str(target),
        [EditOperation(startLine=2, endLine=2, content="new line ${num}", regexMatch=r"line (?P<num>\d+)")],
    )

    approve_edit(sid, manager)
    assert target.read_text(encoding="utf-8") == "line 1\nnew line 2\nline 3\nline 4\nline 5\n"


def test_preserve_state_if_edit_fails(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    original = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    target.write_text(original, encoding="utf-8")

    manager = StateManager()
    sid = manager.save_state(str(target), [EditOperation(startLine=999, endLine=999, content="invalid")])

    with pytest.raises(Exception):
        approve_edit(sid, manager)

    assert manager.get_state(sid) is not None
    assert target.read_text(encoding="utf-8") == original


def test_preserve_state_if_string_match_fails(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    original = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    target.write_text(original, encoding="utf-8")

    manager = StateManager()
    sid = manager.save_state(
        str(target),
        [EditOperation(startLine=2, endLine=2, content="new", strMatch="non-existent")],
    )

    with pytest.raises(Exception):
        approve_edit(sid, manager)

    assert manager.get_state(sid) is not None
    assert target.read_text(encoding="utf-8") == original


def test_preserve_state_if_regex_match_fails(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    original = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    target.write_text(original, encoding="utf-8")

    manager = StateManager()
    sid = manager.save_state(
        str(target),
        [EditOperation(startLine=2, endLine=2, content="new", regexMatch=r"non-existent-\\d+")],
    )

    with pytest.raises(Exception):
        approve_edit(sid, manager)

    assert manager.get_state(sid) is not None
    assert target.read_text(encoding="utf-8") == original


def test_multiple_approvals_in_sequence(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    manager = StateManager()
    sid1 = manager.save_state(str(target), [EditOperation(startLine=1, endLine=1, content="first edit")])
    sid2 = manager.save_state(str(target), [EditOperation(startLine=3, endLine=3, content="second edit")])

    approve_edit(sid1, manager)
    assert target.read_text(encoding="utf-8") == "first edit\nline 2\nline 3\nline 4\nline 5\n"

    approve_edit(sid2, manager)
    assert target.read_text(encoding="utf-8") == "first edit\nline 2\nsecond edit\nline 4\nline 5\n"

    assert manager.get_state(sid1) is None
    assert manager.get_state(sid2) is None


def test_state_deleted_even_if_file_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    original = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    target.write_text(original, encoding="utf-8")

    manager = StateManager()
    sid = manager.save_state(str(target), [EditOperation(startLine=2, endLine=2, content="line 2")])

    approve_edit(sid, manager)
    assert target.read_text(encoding="utf-8") == original
    assert manager.get_state(sid) is None

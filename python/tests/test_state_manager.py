import time

import pytest

from mcp_edit_file_lines.edit_types import EditOperation
from mcp_edit_file_lines.state_manager import StateManager


def test_default_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_EDIT_STATE_TTL", raising=False)
    manager = StateManager()
    assert manager.get_ttl() == 60_000


def test_invalid_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_EDIT_STATE_TTL", "-100")
    with pytest.raises(ValueError):
        StateManager()


def test_state_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_EDIT_STATE_TTL", raising=False)
    manager = StateManager()
    edit = EditOperation(startLine=1, endLine=1, content="new")
    sid = manager.save_state("/tmp/f.txt", [edit])
    state = manager.get_state(sid)
    assert state is not None
    assert state.path == "/tmp/f.txt"
    assert state.edits[0].content == "new"


def test_state_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_EDIT_STATE_TTL", "100")
    manager = StateManager()
    sid = manager.save_state("/tmp/f.txt", [EditOperation(startLine=1, endLine=1, content="x")])
    time.sleep(0.15)
    assert manager.get_state(sid) is None


def test_non_numeric_ttl_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_EDIT_STATE_TTL", "invalid")
    with pytest.raises(ValueError):
        StateManager()


def test_array_style_edits_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_EDIT_STATE_TTL", raising=False)
    manager = StateManager()
    sid = manager.save_state("/tmp/f.txt", [(1, 2, "new content", "old content")])
    assert isinstance(sid, str)
    assert len(sid) == 8


def test_state_id_changes_with_different_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_EDIT_STATE_TTL", raising=False)
    manager = StateManager()
    id1 = manager.save_state("/tmp/f.txt", [EditOperation(startLine=1, endLine=1, content="a")])
    id2 = manager.save_state("/tmp/f.txt", [EditOperation(startLine=1, endLine=1, content="b")])
    assert id1 != id2


def test_regex_match_edit_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_EDIT_STATE_TTL", raising=False)
    manager = StateManager()
    sid = manager.save_state(
        "/tmp/f.txt",
        [EditOperation(startLine=1, endLine=1, content="x", regexMatch=r"\\s*old\\s+content\\s*")],
    )
    state = manager.get_state(sid)
    assert state is not None
    assert state.edits[0].regexMatch == r"\\s*old\\s+content\\s*"


def test_delete_state_and_nonexistent_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_EDIT_STATE_TTL", raising=False)
    manager = StateManager()
    sid = manager.save_state("/tmp/f.txt", [EditOperation(startLine=1, endLine=1, content="x")])
    assert manager.get_state(sid) is not None
    manager.delete_state(sid)
    assert manager.get_state(sid) is None
    manager.delete_state("missing")


def test_cleanup_expired_states_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_EDIT_STATE_TTL", "100")
    manager = StateManager()
    manager.save_state("/tmp/p1.txt", [EditOperation(startLine=1, endLine=1, content="a")])
    manager.save_state("/tmp/p2.txt", [EditOperation(startLine=1, endLine=1, content="b")])
    assert manager.get_active_state_count() == 2
    time.sleep(0.15)
    manager.get_state("any-id")
    assert manager.get_active_state_count() == 0


def test_is_state_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_EDIT_STATE_TTL", raising=False)
    manager = StateManager()
    sid = manager.save_state("/tmp/f.txt", [EditOperation(startLine=1, endLine=1, content="x")])
    assert manager.is_state_valid(sid) is True
    manager.delete_state(sid)
    assert manager.is_state_valid(sid) is False

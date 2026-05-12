import asyncio
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from mcp_edit_file_lines.server import create_server


def _call_tool_sync(server, name: str, arguments: dict):
    return asyncio.run(server._tool_manager.call_tool(name, arguments))


def test_edit_dry_run_then_approve_via_tools(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    server = create_server([str(tmp_path)])

    dry_run_output = _call_tool_sync(
        server,
        "edit_file_lines",
        {
            "p": str(target),
            "e": [{"startLine": 2, "endLine": 2, "content": "modified line"}],
            "dryRun": True,
        },
    )
    assert "State ID:" in dry_run_output
    assert target.read_text(encoding="utf-8") == "line 1\nline 2\nline 3\n"

    state_id = dry_run_output.split("State ID:", 1)[1].splitlines()[0].strip()
    approve_output = _call_tool_sync(server, "approve_edit", {"stateId": state_id})

    assert "modified line" in approve_output
    assert target.read_text(encoding="utf-8") == "line 1\nmodified line\nline 3\n"


def test_get_file_lines_via_tool(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    server = create_server([str(tmp_path)])
    output = _call_tool_sync(
        server,
        "get_file_lines",
        {"path": str(target), "lineNumbers": [2], "context": 1},
    )

    assert "Line 2:" in output
    assert "> 2: beta" in output
    assert " 1: alpha" in output


def test_search_file_via_tool(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta alpha\ngamma\n", encoding="utf-8")

    server = create_server([str(tmp_path)])
    output = _call_tool_sync(
        server,
        "search_file",
        {
            "path": str(target),
            "pattern": "alpha",
            "type": "text",
            "caseSensitive": False,
            "contextLines": 0,
            "maxMatches": 10,
            "wholeWord": False,
            "multiline": False,
        },
    )

    assert "Found 2 matches" in output
    assert "Match 1:" in output


def test_disallowed_path_rejected_by_tool(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    target = outside / "sample.txt"
    target.write_text("x\n", encoding="utf-8")

    server = create_server([str(allowed)])

    with pytest.raises(ToolError, match="outside allowed directories"):
        _call_tool_sync(
            server,
            "get_file_lines",
            {"path": str(target), "lineNumbers": [1], "context": 0},
        )

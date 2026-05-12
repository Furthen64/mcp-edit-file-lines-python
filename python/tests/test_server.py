from pathlib import Path

import pytest

from mcp_edit_file_lines.server import _parse_edits, _validate_path, create_server


def test_server_registers_contract_tool_names(tmp_path: Path) -> None:
    server = create_server([str(tmp_path)])
    tool_names = set(server._tool_manager._tools.keys())
    assert tool_names == {
        "edit_file_lines",
        "approve_edit",
        "get_file_lines",
        "search_file",
    }


def test_validate_path_denies_prefix_trick(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    disallowed_prefix = tmp_path / "allowed-evil"
    allowed.mkdir()
    disallowed_prefix.mkdir()

    with pytest.raises(ValueError, match="outside allowed directories"):
        _validate_path(str(disallowed_prefix / "x.txt"), [str(allowed.resolve())])


def test_validate_path_denies_symlink_escape(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()

    inside_link = allowed / "link.txt"
    outside_file = outside / "target.txt"
    outside_file.write_text("outside", encoding="utf-8")
    inside_link.symlink_to(outside_file)

    with pytest.raises(ValueError, match="symlink target outside allowed directories"):
        _validate_path(str(inside_link), [str(allowed.resolve())])


def test_parse_edits_rejects_both_match_modes() -> None:
    with pytest.raises(ValueError, match="Cannot specify both"):
        _parse_edits(
            [
                {
                    "startLine": 1,
                    "endLine": 1,
                    "content": "x",
                    "strMatch": "a",
                    "regexMatch": "b",
                }
            ]
        )

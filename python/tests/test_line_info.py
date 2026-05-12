from mcp_edit_file_lines.line_info import get_line_info

from conftest import FIXTURES_DIR


def test_get_line_info_with_context() -> None:
    result = get_line_info(str(FIXTURES_DIR / "sample.txt"), [2, 4], 1)
    assert "Line 2:" in result
    assert "> 2: line 2" in result
    assert " 1: line 1" in result
    assert "Line 4:" in result


def test_get_line_info_invalid_lines() -> None:
    result = get_line_info(str(FIXTURES_DIR / "sample.txt"), [0, 9], 0)
    assert "Invalid line number" in result
    assert "file has 6 lines" in result

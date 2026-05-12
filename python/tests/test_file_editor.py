from pathlib import Path

import pytest

from mcp_edit_file_lines.edit_types import EditOperation, MatchNotFoundError
from mcp_edit_file_lines.file_editor import edit_file

from conftest import FIXTURES_DIR


def test_single_line_replace_dry_run() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edit = EditOperation(
        startLine=2,
        endLine=2,
        content='const Button = ({ color = "red", size = "md" }) => {',
    )
    result = edit_file(str(path), [edit], dry_run=True)
    diff = result["diff"]
    assert "color = \"blue\"" in diff
    assert "color = \"red\"" in diff


def test_string_match_replace() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edit = EditOperation(startLine=2, endLine=2, content='"green"', strMatch='"blue"')
    result = edit_file(str(path), [edit], dry_run=True)
    assert "green" in result["diff"]


def test_non_matching_string_raises() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edit = EditOperation(startLine=2, endLine=2, content="new", strMatch="missing")
    with pytest.raises(MatchNotFoundError):
        edit_file(str(path), [edit], dry_run=True)


def test_regex_named_capture_group_replacement() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edit = EditOperation(
        startLine=25,
        endLine=25,
        content="${prefix}White = { bg: ${bg}, text: ${text} }",
        regexMatch=r'(?P<prefix>\w+):\s*\{\s*bg:\s*"(?P<bg>[^"]*)",\s*text:\s*"(?P<text>[^"]*)"',
    )
    result = edit_file(str(path), [edit], dry_run=True)
    assert "lightWhite = { bg: #ffffff, text: #000000 }" in result["diff"]


def test_flexible_whitespace_string_match() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edit = EditOperation(
        startLine=9,
        endLine=9,
        content='description = "Custom description"',
        strMatch='subtitle   =   "Default subtitle"',
    )
    result = edit_file(str(path), [edit], dry_run=True)
    assert 'description = "Custom description"' in result["diff"]


def test_regex_lookaround_replacement() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edit = EditOperation(
        startLine=9,
        endLine=9,
        content="NewDefault",
        regexMatch=r'(?<="Default )[^"]*(?=")',
    )
    result = edit_file(str(path), [edit], dry_run=True)
    assert 'subtitle = "Default NewDefault"' in result["diff"]


def test_overlapping_regex_patterns_rejected() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edits = [
        EditOperation(
            startLine=2,
            endLine=2,
            content="warning",
            regexMatch=r'(?<=color = ")[^"]*(?=")',
        ),
        EditOperation(
            startLine=2,
            endLine=2,
            content="danger",
            regexMatch=r'"[^"]*"',
        ),
    ]
    with pytest.raises(RuntimeError, match="Overlapping regex patterns"):
        edit_file(str(path), edits, dry_run=True)


def test_multiple_non_regex_edits_same_line_rejected() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edits = [
        EditOperation(startLine=2, endLine=2, content="new content 1"),
        EditOperation(startLine=2, endLine=2, content="new content 2"),
    ]
    with pytest.raises(RuntimeError, match="multiple non-regex edits"):
        edit_file(str(path), edits, dry_run=True)


def test_invalid_line_range_rejected() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edit = EditOperation(startLine=100, endLine=101, content="invalid")
    with pytest.raises(ValueError, match="Invalid line range"):
        edit_file(str(path), [edit], dry_run=True)


def test_start_greater_than_end_rejected() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edit = EditOperation(startLine=5, endLine=3, content="invalid")
    with pytest.raises(ValueError, match="start line"):
        edit_file(str(path), [edit], dry_run=True)


def test_multiline_replacement_preserves_indentation() -> None:
    path = FIXTURES_DIR / "test-matches.txt"
    edit = EditOperation(
        startLine=13,
        endLine=18,
        content=(
            "  const cardStyle = useMemo(() => ({\n"
            "    backgroundColor: theme === 'light' ? '#fff' : '#000',\n"
            "    padding: size === 'lg' ? '2rem' : '1rem'\n"
            "  }), [theme, size]);\n"
            "\n"
            "  return ("
        ),
    )
    result = edit_file(str(path), [edit], dry_run=True)
    diff = result["diff"]
    assert "+  const cardStyle = useMemo(() => ({" in diff
    assert "+    backgroundColor: theme === 'light' ? '#fff' : '#000'," in diff
    assert "+  }), [theme, size]);" in diff


def test_write_when_not_dry_run(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("a\nb\nc\n", encoding="utf-8")
    edit = EditOperation(startLine=2, endLine=2, content="bb")
    edit_file(str(target), [edit], dry_run=False)
    assert target.read_text(encoding="utf-8") == "a\nbb\nc\n"

import pytest

from mcp_edit_file_lines.file_search import search_file
from mcp_edit_file_lines.search_types import SearchError, SearchErrorCode, SearchFileArgs

from conftest import FIXTURES_DIR


def test_text_search_basic_match() -> None:
    args = SearchFileArgs(path=str(FIXTURES_DIR / "test-matches.txt"), pattern="Default subtitle")
    result = search_file(str(FIXTURES_DIR / "test-matches.txt"), args)
    assert result.totalMatches >= 1
    assert any("Default subtitle" in m.match for m in result.matches)


def test_text_search_whole_word() -> None:
    args = SearchFileArgs(
        path=str(FIXTURES_DIR / "test-matches.txt"),
        pattern="light",
        wholeWord=True,
    )
    result = search_file(str(FIXTURES_DIR / "test-matches.txt"), args)
    assert result.totalMatches >= 1


def test_regex_search_multiline() -> None:
    args = SearchFileArgs(
        path=str(FIXTURES_DIR / "test-matches.txt"),
        pattern=r"<div[^>]*>[\s\S]*?</div>",
        type="regex",
        multiline=True,
    )
    result = search_file(str(FIXTURES_DIR / "test-matches.txt"), args)
    assert result.totalMatches >= 1


def test_invalid_regex_raises() -> None:
    args = SearchFileArgs(path=str(FIXTURES_DIR / "test-matches.txt"), pattern="([", type="regex")
    with pytest.raises(SearchError) as exc:
        search_file(str(FIXTURES_DIR / "test-matches.txt"), args)
    assert exc.value.code == SearchErrorCode.INVALID_PATTERN

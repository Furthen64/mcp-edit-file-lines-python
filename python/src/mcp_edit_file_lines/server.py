import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .approve_edit import approve_edit
from .edit_types import EditOperation
from .file_editor import edit_file
from .file_search import search_file
from .line_info import get_line_info
from .search_types import SearchError, SearchFileArgs
from .state_manager import StateManager


def _normalize_path(path_value: str) -> str:
    return os.path.normcase(str(Path(path_value).resolve()))


def _expand_home(path_value: str) -> str:
    return str(Path(path_value).expanduser())


def _is_path_allowed(path_value: str, allowed_directories: list[str]) -> bool:
    normalized_path = os.path.normcase(path_value)
    for allowed in allowed_directories:
        try:
            if os.path.commonpath([normalized_path, allowed]) == allowed:
                return True
        except ValueError:
            continue
    return False


def _validate_allowed_directories(raw_dirs: list[str]) -> list[str]:
    allowed: list[str] = []
    for raw in raw_dirs:
        expanded = _expand_home(raw)
        path = Path(expanded)
        if not path.is_dir():
            raise ValueError(f"Error: {raw} is not a directory")
        allowed.append(_normalize_path(expanded))
    return allowed


def _validate_path(requested_path: str, allowed_directories: list[str]) -> str:
    expanded = _expand_home(requested_path)
    resolved = Path(expanded)
    absolute = resolved if resolved.is_absolute() else (Path.cwd() / resolved)
    absolute = Path(os.path.abspath(str(absolute)))

    normalized_requested = os.path.normcase(str(absolute))
    if not _is_path_allowed(normalized_requested, allowed_directories):
        raise ValueError(f"Access denied - path outside allowed directories: {absolute}")

    try:
        real_path = absolute.resolve(strict=True)
        normalized_real = os.path.normcase(str(real_path))
        if not _is_path_allowed(normalized_real, allowed_directories):
            raise ValueError("Access denied - symlink target outside allowed directories")
        return str(real_path)
    except FileNotFoundError:
        parent = absolute.parent
        if not parent.exists():
            raise ValueError(f"Parent directory does not exist: {parent}")
        real_parent = parent.resolve(strict=True)
        normalized_parent = os.path.normcase(str(real_parent))
        if not _is_path_allowed(normalized_parent, allowed_directories):
            raise ValueError("Access denied - parent directory outside allowed directories")
        return str(absolute)


def _parse_edits(raw_edits: list[dict[str, Any]]) -> list[EditOperation]:
    parsed: list[EditOperation] = []

    for edit in raw_edits:
        start_line = int(edit["startLine"])
        end_line = int(edit["endLine"])
        content = str(edit["content"])
        str_match = edit.get("strMatch")
        regex_match = edit.get("regexMatch")

        if start_line > end_line:
            raise ValueError("startLine must not be greater than endLine")
        if str_match and regex_match:
            raise ValueError("Cannot specify both strMatch and regexMatch")

        parsed.append(
            EditOperation(
                startLine=start_line,
                endLine=end_line,
                content=content,
                strMatch=str(str_match) if str_match is not None else None,
                regexMatch=str(regex_match) if regex_match is not None else None,
            )
        )

    return parsed


def create_server(allowed_directory_args: list[str]) -> FastMCP:
    if not allowed_directory_args:
        raise ValueError("Usage: python -m mcp_edit_file_lines <allowed-directory> [additional-directories...]")

    allowed_directories = _validate_allowed_directories(allowed_directory_args)
    state_manager = StateManager()

    mcp = FastMCP("edit-file-lines-python")

    @mcp.tool(description="Make line-based edits to a file with optional dry run.")
    def edit_file_lines(p: str, e: list[dict[str, Any]], dryRun: bool = False) -> str:
        valid_path = _validate_path(p, allowed_directories)
        edits = _parse_edits(e)

        result = edit_file(valid_path, edits, dry_run=dryRun)
        diff = result["diff"]

        if dryRun:
            state_id = state_manager.save_state(valid_path, edits)
            return f"{diff}\nState ID: {state_id}\nUse this ID with approve_edit to apply the changes."

        return str(diff)

    @mcp.tool(name="approve_edit", description="Approve and apply a previously validated dry-run edit.")
    def approve_edit_tool(stateId: str) -> str:
        return approve_edit(stateId, state_manager)

    @mcp.tool(description="Get information and context for specific line numbers in a file.")
    def get_file_lines(path: str, lineNumbers: list[int], context: int = 2) -> str:
        valid_path = _validate_path(path, allowed_directories)
        return get_line_info(valid_path, [int(n) for n in lineNumbers], int(context))

    @mcp.tool(name="search_file", description="Search a file using text or regex patterns with context.")
    def search_file_tool(
        path: str,
        pattern: str,
        type: str = "text",
        caseSensitive: bool = False,
        contextLines: int = 2,
        maxMatches: int = 100,
        wholeWord: bool = False,
        multiline: bool = False,
    ) -> str:
        valid_path = _validate_path(path, allowed_directories)

        args = SearchFileArgs(
            path=valid_path,
            pattern=pattern,
            type=type,
            caseSensitive=caseSensitive,
            contextLines=contextLines,
            maxMatches=maxMatches,
            wholeWord=wholeWord,
            multiline=multiline,
        )

        try:
            result = search_file(valid_path, args)
        except SearchError as error:
            details = f"\nDetails: {error.details}" if error.details else ""
            return f"Search error: {error}{details}"

        lines: list[str] = [
            f"Found {result.totalMatches} matches in {result.executionTime:.1f}ms:",
            f"File size: {result.fileSize / 1024:.1f}KB",
            "",
        ]

        for index, match in enumerate(result.matches, start=1):
            lines.append(f"Match {index}: Line {match.line}, Column {match.column}")
            lines.append("----------------------------------------")

            context_rows = match.context.split("\n")
            try:
                match_line_index = context_rows.index(match.content)
            except ValueError:
                match_line_index = 0
            start_line_number = match.line - match_line_index

            for offset, row in enumerate(context_rows):
                line_number = start_line_number + offset
                indicator = ">" if line_number == match.line else " "
                lines.append(f"{indicator} {line_number:4d} | {row}")
            lines.append("")

        return "\n".join(lines)

    return mcp


def run() -> None:
    server = create_server(sys.argv[1:])
    server.run(transport="stdio")

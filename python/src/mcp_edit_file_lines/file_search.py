import re
import time
from pathlib import Path

from .search_types import (
    SearchError,
    SearchErrorCode,
    SearchFileArgs,
    SearchMatch,
    SearchResult,
)
from .utils import normalize_line_endings

MAX_FILE_SIZE = 10 * 1024 * 1024
EXECUTION_TIMEOUT = 5.0


def _get_position_info(text: str, position: int) -> tuple[int, int]:
    lines = text[:position].split("\n")
    return len(lines), len(lines[-1]) + 1


def _get_context(lines: list[str], match_line_idx: int, context_lines: int) -> str:
    start = max(0, match_line_idx - context_lines)
    end = min(len(lines) - 1, match_line_idx + context_lines)
    return "\n".join(lines[start : end + 1])


def _create_search_regex(args: SearchFileArgs) -> re.Pattern[str]:
    pattern = args.pattern

    if args.type == "text":
        pattern = re.escape(pattern)
        if args.wholeWord:
            pattern = rf"\b{pattern}\b"

    flags = 0
    if not args.caseSensitive:
        flags |= re.IGNORECASE
    if args.multiline:
        flags |= re.MULTILINE

    try:
        return re.compile(pattern, flags)
    except re.error as error:
        raise SearchError(
            f"Invalid {args.type} pattern: {error}",
            SearchErrorCode.INVALID_PATTERN,
            {"pattern": pattern},
        ) from error


def _enforce_timeout(start_time: float) -> None:
    if time.perf_counter() - start_time > EXECUTION_TIMEOUT:
        raise SearchError(
            f"Search execution timed out after {int(EXECUTION_TIMEOUT * 1000)}ms",
            SearchErrorCode.EXECUTION_TIMEOUT,
        )


def _text_search(lines: list[str], pattern: re.Pattern[str], args: SearchFileArgs) -> list[SearchMatch]:
    matches: list[SearchMatch] = []
    started = time.perf_counter()

    for line_idx, line in enumerate(lines):
        _enforce_timeout(started)
        for match in pattern.finditer(line):
            _enforce_timeout(started)
            if len(matches) >= args.maxMatches:
                raise SearchError(
                    f"Maximum number of matches ({args.maxMatches}) exceeded",
                    SearchErrorCode.MAX_MATCHES_EXCEEDED,
                    {"maxMatches": args.maxMatches},
                )
            matches.append(
                SearchMatch(
                    line=line_idx + 1,
                    column=match.start() + 1,
                    content=line,
                    context=_get_context(lines, line_idx, args.contextLines),
                    match=match.group(0),
                    index=match.start(),
                )
            )

    return matches


def _regex_search(
    content: str,
    lines: list[str],
    pattern: re.Pattern[str],
    args: SearchFileArgs,
) -> list[SearchMatch]:
    matches: list[SearchMatch] = []
    started = time.perf_counter()

    for match in pattern.finditer(content):
        _enforce_timeout(started)
        if len(matches) >= args.maxMatches:
            raise SearchError(
                f"Maximum number of matches ({args.maxMatches}) exceeded",
                SearchErrorCode.MAX_MATCHES_EXCEEDED,
                {"maxMatches": args.maxMatches},
            )

        line, column = _get_position_info(content, match.start())
        line_idx = line - 1

        matches.append(
            SearchMatch(
                line=line,
                column=column,
                content=lines[line_idx],
                context=_get_context(lines, line_idx, args.contextLines),
                match=match.group(0),
                index=match.start(),
            )
        )

    return matches


def search_file(filepath: str, args: SearchFileArgs) -> SearchResult:
    start_time = time.perf_counter()

    file_path = Path(filepath)
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise SearchError(
            f"File too large (max {MAX_FILE_SIZE} bytes)",
            SearchErrorCode.FILE_TOO_LARGE,
            {"fileSize": file_size},
        )

    content = normalize_line_endings(file_path.read_text(encoding="utf-8"))
    lines = content.split("\n")

    pattern = _create_search_regex(args)

    if args.type == "text":
        matches = _text_search(lines, pattern, args)
    else:
        matches = _regex_search(content, lines, pattern, args)

    return SearchResult(
        matches=matches,
        totalMatches=len(matches),
        fileSize=file_size,
        executionTime=(time.perf_counter() - start_time) * 1000,
    )

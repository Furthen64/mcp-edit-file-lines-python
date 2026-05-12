import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from .edit_types import EditOperation, EditOperationResult, MatchNotFoundError
from .utils import normalize_line_endings


@dataclass
class LineMetadata:
    content: str
    indentation: str
    original_index: int


class FileEditor:
    def __init__(self, content: str) -> None:
        self.original_content = normalize_line_endings(content)
        self.lines: list[LineMetadata] = []
        for idx, line in enumerate(self.original_content.split("\n")):
            stripped = line.lstrip()
            indent_len = len(line) - len(stripped)
            self.lines.append(
                LineMetadata(
                    content=stripped,
                    indentation=line[:indent_len],
                    original_index=idx,
                )
            )
        self.edits: list[EditOperation] = []
        self.results: dict[int, EditOperationResult] = {}

    def add_edit(self, edit: EditOperation) -> None:
        self._validate_range(edit)

        edit = EditOperation(
            startLine=edit.startLine,
            endLine=edit.endLine,
            content=self._normalize_edit_content(edit.content),
            strMatch=normalize_line_endings(edit.strMatch) if edit.strMatch else None,
            regexMatch=edit.regexMatch,
        )

        if edit.regexMatch:
            self._validate_regex_pattern(edit.regexMatch)

        self.edits.append(edit)

    def _normalize_edit_content(self, content: str) -> str:
        return normalize_line_endings(content)

    def _validate_regex_pattern(self, pattern: str) -> None:
        try:
            re.compile(pattern)
        except re.error as error:
            raise ValueError(f'Invalid regex pattern "{pattern}": {error}') from error

    def _validate_range(self, edit: EditOperation) -> None:
        if edit.startLine > edit.endLine:
            raise ValueError(
                f"Invalid range: start line {edit.startLine} is greater than end line {edit.endLine}"
            )
        total_lines = len(self.lines)
        if edit.startLine < 1 or edit.endLine > total_lines:
            raise ValueError(
                f"Invalid line range: file has {total_lines} lines but range is {edit.startLine}-{edit.endLine}"
            )

    def _get_full_line(self, line_number: int) -> str:
        line = self.lines[line_number - 1]
        return f"{line.indentation}{line.content}"

    def _check_regex_overlap(self, text: str, pattern1: re.Pattern[str], pattern2: re.Pattern[str]) -> bool:
        matches1 = [(m.start(), m.end()) for m in pattern1.finditer(text)]
        matches2 = [(m.start(), m.end()) for m in pattern2.finditer(text)]

        for start1, end1 in matches1:
            for start2, end2 in matches2:
                if (start1 <= start2 < end1) or (start2 <= start1 < end2):
                    return True
        return False

    def _validate_edits(self) -> None:
        line_usage: dict[int, list[EditOperation]] = {}

        for edit in self.edits:
            for line in range(edit.startLine, edit.endLine + 1):
                existing = line_usage.setdefault(line, [])

                if edit.regexMatch:
                    for prior in existing:
                        if prior.regexMatch:
                            if self._check_regex_overlap(
                                self._get_full_line(line),
                                re.compile(edit.regexMatch),
                                re.compile(prior.regexMatch),
                            ):
                                raise ValueError(
                                    f'Overlapping regex patterns on line {line}: "{edit.regexMatch}" and "{prior.regexMatch}"'
                                )

                if not edit.regexMatch and any(not e.regexMatch for e in existing):
                    raise ValueError(f"Line {line} is affected by multiple non-regex edits")

                existing.append(edit)

    def _indent_len(self, text: str) -> int:
        return len(text) - len(text.lstrip())

    def _preserve_indentation(
        self,
        new_content: str,
        original_indentation: str,
        base_indentation: str = "",
    ) -> str:
        lines = new_content.split("\n")
        baseline = self._indent_len(base_indentation or lines[0])
        rebuilt: list[str] = []

        for line in lines:
            rel_indent = max(0, self._indent_len(line) - baseline)
            rebuilt.append(f"{original_indentation}{' ' * rel_indent}{line.lstrip()}")

        return "\n".join(rebuilt)

    def _apply_match_replace(self, line_meta: LineMetadata, edit: EditOperation, line_number: int) -> str:
        full_line = f"{line_meta.indentation}{line_meta.content}"

        if not edit.strMatch and not edit.regexMatch:
            return self._preserve_indentation(edit.content, line_meta.indentation)

        if edit.strMatch:
            normalized_line = normalize_line_endings(full_line)
            normalized_match = normalize_line_endings(edit.strMatch)

            if normalized_match in normalized_line:
                start = normalized_line.index(normalized_match)
                prefix = full_line[:start]
                suffix = full_line[start + len(normalized_match) :]
                if "\n" not in edit.content and "\n" not in normalized_match:
                    return f"{prefix}{edit.content}{suffix}"
                return self._preserve_indentation(edit.content, line_meta.indentation)

            flex_line = re.sub(r"\s+", " ", normalized_line).strip()
            flex_target = re.sub(r"\s+", " ", normalized_match).strip()
            if flex_target not in flex_line:
                raise MatchNotFoundError(line_number, edit.strMatch, False)

            escaped = re.escape(flex_target).replace(r"\ ", r"\s+")
            replacement_regex = re.compile(escaped)

            def repl(_: re.Match[str]) -> str:
                if "\n" not in edit.content:
                    return edit.content
                return self._preserve_indentation(edit.content, line_meta.indentation)

            return replacement_regex.sub(repl, full_line, count=1)

        if edit.regexMatch:
            try:
                regex = re.compile(edit.regexMatch)
            except re.error as error:
                raise ValueError(f'Invalid regex pattern "{edit.regexMatch}": {error}') from error

            if not regex.search(full_line):
                raise MatchNotFoundError(line_number, edit.regexMatch, True)

            def repl(match: re.Match[str]) -> str:
                replacement = edit.content
                if "${" in replacement:
                    groups = match.groupdict()

                    def group_sub(m: re.Match[str]) -> str:
                        return groups.get(m.group(1), "") or ""

                    replacement = re.sub(r"\$\{(\w+)\}", group_sub, replacement)

                if "\n" not in replacement:
                    return replacement
                return self._preserve_indentation(replacement, line_meta.indentation)

            return regex.sub(repl, full_line)

        return full_line

    def apply_edits(self) -> str:
        self._validate_edits()
        sorted_edits = sorted(self.edits, key=lambda e: e.startLine, reverse=True)
        modified_lines = self.lines.copy()

        for edit in sorted_edits:
            start_idx = edit.startLine - 1
            end_idx = edit.endLine - 1

            try:
                if edit.startLine == edit.endLine and (edit.strMatch or edit.regexMatch):
                    line_meta = modified_lines[start_idx]
                    new_content = self._apply_match_replace(line_meta, edit, edit.startLine)
                    stripped = new_content.lstrip()
                    indent_len = len(new_content) - len(stripped)
                    modified_lines[start_idx] = LineMetadata(
                        content=stripped,
                        indentation=new_content[:indent_len],
                        original_index=line_meta.original_index,
                    )
                    self.results[edit.startLine] = EditOperationResult(True, new_content)
                else:
                    first_indent = modified_lines[start_idx].indentation
                    new_content = self._preserve_indentation(edit.content, first_indent)
                    new_meta: list[LineMetadata] = []
                    for idx, line in enumerate(new_content.split("\n")):
                        stripped = line.lstrip()
                        indent_len = len(line) - len(stripped)
                        new_meta.append(
                            LineMetadata(
                                content=stripped,
                                indentation=line[:indent_len],
                                original_index=modified_lines[start_idx].original_index + idx,
                            )
                        )

                    modified_lines[start_idx : end_idx + 1] = new_meta

                    for line_no in range(edit.startLine, edit.endLine + 1):
                        if line_no <= edit.startLine + len(new_meta) - 1:
                            idx = line_no - edit.startLine
                            value = f"{new_meta[idx].indentation}{new_meta[idx].content}"
                        else:
                            value = ""
                        self.results[line_no] = EditOperationResult(True, value)
            except Exception as error:
                original = self.lines[start_idx]
                self.results[edit.startLine] = EditOperationResult(
                    False,
                    f"{original.indentation}{original.content}",
                    str(error),
                )
                raise

        return "\n".join(f"{line.indentation}{line.content}" for line in modified_lines)

    def create_diff(self, modified_content: str, filepath: str) -> str:
        original_lines = self.original_content.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=filepath,
            tofile=filepath,
            fromfiledate="original",
            tofiledate="modified",
        )
        return "".join(diff)


def edit_file(
    filepath: str,
    edits: list[EditOperation],
    dry_run: bool = False,
) -> dict[str, str | dict[int, EditOperationResult]]:
    content = Path(filepath).read_text(encoding="utf-8")

    editor = FileEditor(content)
    for edit in edits:
        editor.add_edit(edit)

    try:
        modified = editor.apply_edits()
        diff = editor.create_diff(modified, filepath)

        if not dry_run:
            Path(filepath).write_text(modified, encoding="utf-8")

        return {"diff": diff, "results": editor.results}
    except MatchNotFoundError:
        raise
    except Exception as error:
        raise RuntimeError(f"Failed to apply edits: {error}") from error

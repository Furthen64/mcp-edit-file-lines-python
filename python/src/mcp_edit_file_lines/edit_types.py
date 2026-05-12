from dataclasses import dataclass


@dataclass
class EditOperation:
    startLine: int
    endLine: int
    content: str
    strMatch: str | None = None
    regexMatch: str | None = None


@dataclass
class EditOperationResult:
    applied: bool
    lineContent: str
    error: str | None = None


class MatchNotFoundError(Exception):
    def __init__(self, line: int, match: str, is_regex: bool) -> None:
        self.line = line
        self.match = match
        self.is_regex = is_regex
        match_type = "regex" if is_regex else "string"
        super().__init__(f'No {match_type} match found for "{match}" on line {line}')

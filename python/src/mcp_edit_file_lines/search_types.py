from dataclasses import dataclass
from enum import Enum
from typing import Any


@dataclass
class SearchMatch:
    line: int
    content: str
    context: str
    match: str
    index: int
    column: int


@dataclass
class SearchResult:
    matches: list[SearchMatch]
    totalMatches: int
    fileSize: int
    executionTime: float


@dataclass
class SearchFileArgs:
    path: str
    pattern: str
    type: str = "text"
    caseSensitive: bool = False
    contextLines: int = 2
    maxMatches: int = 100
    wholeWord: bool = False
    multiline: bool = False


class SearchErrorCode(str, Enum):
    INVALID_PATTERN = "INVALID_PATTERN"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    MAX_MATCHES_EXCEEDED = "MAX_MATCHES_EXCEEDED"


class SearchError(Exception):
    def __init__(self, message: str, code: SearchErrorCode, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details

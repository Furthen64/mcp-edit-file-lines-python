import hashlib
import json
import os
import time
from dataclasses import dataclass

from .edit_types import EditOperation


@dataclass
class EditState:
    path: str
    edits: list[EditOperation]
    timestamp: float


class StateManager:
    def __init__(self) -> None:
        self._states: dict[str, EditState] = {}
        env_ttl = os.getenv("MCP_EDIT_STATE_TTL")
        self._ttl = int(env_ttl) if env_ttl else 60_000
        if self._ttl <= 0:
            raise ValueError("MCP_EDIT_STATE_TTL must be a positive number when set")

    def _now_ms(self) -> float:
        return time.time() * 1000

    def _cleanup(self) -> None:
        now = self._now_ms()
        expired = [sid for sid, state in self._states.items() if now - state.timestamp > self._ttl]
        for sid in expired:
            self._states.pop(sid, None)

    def _generate_state_id(self, path: str, edits: list[EditOperation]) -> str:
        sorted_edits = sorted(edits, key=lambda e: (e.startLine, e.endLine))
        serializable = {
            "path": path,
            "edits": [
                {
                    "startLine": e.startLine,
                    "endLine": e.endLine,
                    "content": e.content,
                    "strMatch": e.strMatch.strip() if isinstance(e.strMatch, str) else None,
                    "regexMatch": e.regexMatch.strip() if isinstance(e.regexMatch, str) else None,
                }
                for e in sorted_edits
            ],
        }
        digest = hashlib.sha256(json.dumps(serializable, sort_keys=True).encode("utf-8")).hexdigest()
        return digest[:8]

    def save_state(self, path: str, edits: list[EditOperation | tuple[int, int, str, str]]) -> str:
        self._cleanup()
        normalized_edits: list[EditOperation] = []

        for edit in edits:
            if isinstance(edit, tuple):
                normalized_edits.append(
                    EditOperation(
                        startLine=edit[0],
                        endLine=edit[1],
                        content=edit[2],
                        strMatch=edit[3].strip() if len(edit) > 3 and edit[3] else None,
                    )
                )
            else:
                normalized_edits.append(
                    EditOperation(
                        startLine=edit.startLine,
                        endLine=edit.endLine,
                        content=edit.content,
                        strMatch=edit.strMatch.strip() if isinstance(edit.strMatch, str) else None,
                        regexMatch=edit.regexMatch.strip() if isinstance(edit.regexMatch, str) else None,
                    )
                )

        state_id = self._generate_state_id(path, normalized_edits)
        self._states[state_id] = EditState(path=path, edits=normalized_edits, timestamp=self._now_ms())
        return state_id

    def get_state(self, state_id: str) -> EditState | None:
        self._cleanup()
        state = self._states.get(state_id)
        if state and self._now_ms() - state.timestamp <= self._ttl:
            return state
        self._states.pop(state_id, None)
        return None

    def delete_state(self, state_id: str) -> None:
        self._cleanup()
        self._states.pop(state_id, None)

    def get_ttl(self) -> int:
        return self._ttl

    def get_active_state_count(self) -> int:
        self._cleanup()
        return len(self._states)

    def is_state_valid(self, state_id: str) -> bool:
        return self.get_state(state_id) is not None

    def clear_all_states(self) -> None:
        self._states.clear()

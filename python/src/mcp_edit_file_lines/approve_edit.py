from .file_editor import edit_file
from .state_manager import StateManager


def approve_edit(state_id: str, state_manager: StateManager) -> str:
    saved_state = state_manager.get_state(state_id)
    if not saved_state:
        raise ValueError("Invalid or expired state ID")

    try:
        result = edit_file(saved_state.path, saved_state.edits, dry_run=False)
        state_manager.delete_state(state_id)
        return result["diff"]
    except Exception:
        raise


def verify_edit_state(state_id: str, state_manager: StateManager) -> bool:
    return state_manager.is_state_valid(state_id)

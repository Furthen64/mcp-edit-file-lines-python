from pathlib import Path

from mcp_edit_file_lines.edit_types import EditOperation
from mcp_edit_file_lines.file_editor import edit_file


def run_smoke() -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"
    target = fixtures_dir / "test-edits.txt"

    result = edit_file(
        str(target),
        [EditOperation(startLine=2, endLine=2, content='line 2:   console.log("Hi");')],
        dry_run=True,
    )
    print(result["diff"])


if __name__ == "__main__":
    run_smoke()

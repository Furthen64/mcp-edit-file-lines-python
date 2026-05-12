from pathlib import Path

from .utils import normalize_line_endings


def get_line_info(file_path: str, line_numbers: list[int], context: int = 0) -> str:
    content = Path(file_path).read_text(encoding="utf-8")
    lines = normalize_line_endings(content).split("\n")
    result: list[str] = []

    unique_line_numbers = sorted(set(line_numbers))

    for line_num in unique_line_numbers:
        line_index = line_num - 1
        if line_index < 0 or line_index >= len(lines):
            result.append(
                f"Line {line_num}: Invalid line number (file has {len(lines)} lines)"
            )
            continue

        start_line = max(0, line_index - context)
        end_line = min(len(lines) - 1, line_index + context)

        result.append(f"Line {line_num}:")
        for idx in range(start_line, end_line + 1):
            prefix = ">" if idx == line_index else " "
            result.append(f"{prefix} {idx + 1}: {lines[idx]}")
        result.append("")

    return "\n".join(result)

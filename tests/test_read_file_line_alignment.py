"""Smoke tests: doc-map line numbers align with deepagents read_file cat -n labels."""

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.utils import LINE_NUMBER_WIDTH, format_content_with_line_numbers

from car_deepagent.paths import repo_root


def _first_displayed_line_number(formatted: str) -> int:
    first_row = formatted.splitlines()[0]
    return int(first_row[:LINE_NUMBER_WIDTH].strip())


def test_offset_math_matches_cat_n_labels():
    start_line, end_line = 3, 5
    offset = start_line - 1
    limit = end_line - start_line + 1
    assert offset == 2
    assert limit == 3


def test_read_file_line_labels_align_with_map_math():
    """FilesystemBackend.read(offset) + formatter matches 1-based map line numbers."""
    start_line, end_line = 3, 5
    offset = start_line - 1
    limit = end_line - start_line + 1

    backend = FilesystemBackend(root_dir=str(repo_root()), virtual_mode=True)
    read_result = backend.read(
        "/docs/interviews/interview_001.md",
        offset=offset,
        limit=limit,
    )

    assert read_result.error is None
    assert read_result.file_data is not None

    raw = read_result.file_data["content"]
    formatted = format_content_with_line_numbers(raw, start_line=offset + 1)

    assert _first_displayed_line_number(formatted) == start_line
    assert len(formatted.splitlines()) == limit

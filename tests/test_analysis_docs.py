from pathlib import Path

from car_deepagent.analysis_docs import (
    AgentContext,
    extract_analysis_doc_paths,
    list_interview_docx_paths,
    normalize_analysis_doc_paths,
    normalize_doc_path,
    resolve_interview_file,
    search_interview_docs,
)
from car_deepagent.paths import interviews_dir, repo_root


def test_list_interview_docx_paths():
    paths = list_interview_docx_paths()
    assert paths == [
        "docs/interviews/interview_001.docx",
        "docs/interviews/interview_002.docx",
        "docs/interviews/interview_003.docx",
    ]


def test_search_interview_docs():
    assert search_interview_docs("001") == [
        "docs/interviews/interview_001.docx",
    ]
    assert search_interview_docs("INTERVIEW_002") == [
        "docs/interviews/interview_002.docx",
    ]
    assert search_interview_docs("") == list_interview_docx_paths()
    assert search_interview_docs("nope") == []


def test_resolve_bare_stem_and_filename():
    assert normalize_doc_path("interview_001") == (
        "docs/interviews/interview_001.docx"
    )
    assert normalize_doc_path("interview_002.docx") == (
        "docs/interviews/interview_002.docx"
    )
    resolved = resolve_interview_file("interview_003")
    assert resolved is not None
    assert resolved.name == "interview_003.docx"
    assert resolved.parent == interviews_dir().resolve()


def test_normalize_doc_path_relative_and_absolute():
    rel = normalize_doc_path("docs/interviews/interview_001.docx")
    assert rel == "docs/interviews/interview_001.docx"
    abs_path = str((interviews_dir() / "interview_002.docx").resolve())
    assert normalize_doc_path(abs_path) == "docs/interviews/interview_002.docx"


def test_normalize_rejects_outside_interviews(tmp_path: Path):
    assert normalize_doc_path("README.md") is None
    assert normalize_doc_path("docs/superpowers/specs/x.docx") is None
    outsider = tmp_path / "fake.docx"
    outsider.write_bytes(b"PK")
    assert normalize_doc_path(str(outsider)) is None


def test_normalize_analysis_doc_paths_dedupes():
    paths = normalize_analysis_doc_paths(
        [
            "docs/interviews/interview_001.docx",
            str((repo_root() / "docs/interviews/interview_001.docx").resolve()),
            "interview_001",
            "docs/interviews/missing.docx",
            "docs/interviews/interview_003.docx",
        ]
    )
    assert paths == [
        "docs/interviews/interview_001.docx",
        "docs/interviews/interview_003.docx",
    ]


def test_extract_from_agent_context_and_dict():
    ctx = AgentContext(
        analysis_doc_paths=["docs/interviews/interview_002.docx"],
    )
    assert extract_analysis_doc_paths(ctx) == [
        "docs/interviews/interview_002.docx",
    ]
    assert extract_analysis_doc_paths(
        {"analysis_doc_paths": ["docs/interviews/interview_001.docx"]}
    ) == ["docs/interviews/interview_001.docx"]
    assert extract_analysis_doc_paths(None) == []
    assert extract_analysis_doc_paths({}) == []

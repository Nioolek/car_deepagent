from car_deepagent.analysis_docs import (
    AgentContext,
    extract_analysis_doc_paths,
    list_interview_md_paths,
    normalize_analysis_doc_paths,
    normalize_doc_path,
    resolve_interview_file,
    search_interview_docs,
)
from car_deepagent.paths import interviews_dir, repo_root


def test_list_interview_md_paths():
    paths = list_interview_md_paths()
    assert paths == [
        "docs/interviews/interview_001.md",
        "docs/interviews/interview_002.md",
        "docs/interviews/interview_003.md",
    ]


def test_search_interview_docs_filters_by_name():
    assert search_interview_docs("001") == [
        "docs/interviews/interview_001.md",
    ]
    assert "docs/interviews/interview_002.md" in search_interview_docs("interview")
    assert search_interview_docs("") == list_interview_md_paths()


def test_resolve_and_normalize_interview_file():
    assert normalize_doc_path("docs/interviews/interview_001.md") == (
        "docs/interviews/interview_001.md"
    )
    assert normalize_doc_path("interview_002.md") == (
        "docs/interviews/interview_002.md"
    )
    assert normalize_doc_path("interview_002") == (
        "docs/interviews/interview_002.md"
    )
    resolved = resolve_interview_file("interview_003")
    assert resolved is not None
    assert resolved.name == "interview_003.md"


def test_normalize_accepts_absolute_under_interviews():
    rel = normalize_doc_path("docs/interviews/interview_001.md")
    assert rel == "docs/interviews/interview_001.md"
    abs_path = str((interviews_dir() / "interview_002.md").resolve())
    assert normalize_doc_path(abs_path) == "docs/interviews/interview_002.md"


def test_normalize_rejects_outside_interviews(tmp_path):
    assert normalize_doc_path("docs/superpowers/specs/x.md") is None
    outsider = tmp_path / "fake.md"
    outsider.write_text("x", encoding="utf-8")
    assert normalize_doc_path(str(outsider)) is None


def test_normalize_analysis_doc_paths_dedupes():
    out = normalize_analysis_doc_paths(
        [
            "docs/interviews/interview_001.md",
            str((repo_root() / "docs/interviews/interview_001.md").resolve()),
            "interview_001",
            "docs/interviews/missing.md",
            "docs/interviews/interview_003.md",
        ]
    )
    assert out == [
        "docs/interviews/interview_001.md",
        "docs/interviews/interview_003.md",
    ]


def test_extract_analysis_doc_paths_from_context():
    assert extract_analysis_doc_paths(
        AgentContext(analysis_doc_paths=["docs/interviews/interview_002.md"])
    ) == ["docs/interviews/interview_002.md"]
    assert extract_analysis_doc_paths(
        {"analysis_doc_paths": ["docs/interviews/interview_001.md"]}
    ) == ["docs/interviews/interview_001.md"]

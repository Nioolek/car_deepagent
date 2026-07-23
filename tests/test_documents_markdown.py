import json
from pathlib import Path

from car_deepagent.tools.documents import doc_id_for_path, inspect_document


def test_doc_id_for_path():
    assert doc_id_for_path("/tmp/interview_001.md") == "interview_001"


def test_inspect_document_reads_interview_md(tmp_path, monkeypatch):
    interviews = tmp_path / "docs" / "interviews"
    interviews.mkdir(parents=True)
    monkeypatch.setattr(
        "car_deepagent.analysis_docs.interviews_dir",
        lambda: interviews,
    )
    monkeypatch.setattr(
        "car_deepagent.analysis_docs.repo_root",
        lambda: tmp_path,
    )
    src = interviews / "interview_x.md"
    src.write_text(
        "# 背景\n\n受访者来自上海。\n\n## 智驾体验\n\nNOA 总体可用。\n",
        encoding="utf-8",
    )
    raw = inspect_document.invoke({"path": "interview_x"})
    data = json.loads(raw)
    assert data["doc_id"] == "interview_x"
    assert data["source_path"] == "/docs/interviews/interview_x.md"
    assert data["chars"] > 0
    assert "智驾体验" in src.read_text(encoding="utf-8")


def test_inspect_document_missing_file():
    raw = inspect_document.invoke({"path": "/no/such/file.md"})
    data = json.loads(raw)
    assert "error" in data

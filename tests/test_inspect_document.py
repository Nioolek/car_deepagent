import json
from pathlib import Path

from car_deepagent.tools import documents as docs


def _patch_interview_dirs(tmp_path, monkeypatch):
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
    return interviews


def test_count_text_volume_lines_and_scripts():
    vol = docs.count_text_volume("Hello 你好\nWorld")
    assert vol["lines"] == 2
    assert vol["chars"] == len("Hello 你好\nWorld")
    assert vol["chars_latin"] == len("HelloWorld")
    assert vol["chars_cjk"] == 2
    assert vol["chars_other"] == vol["chars"] - vol["chars_latin"] - vol["chars_cjk"]


def test_recommendation_thresholds():
    assert docs.recommendation_for_volume(10, 100) == "direct_read"
    assert docs.recommendation_for_volume(500, 100) == "direct_read"
    assert docs.recommendation_for_volume(10, 15000) == "direct_read"
    assert docs.recommendation_for_volume(501, 100) == "delegate"
    assert docs.recommendation_for_volume(10, 15001) == "delegate"


def test_inspect_document_on_interview_markdown(tmp_path, monkeypatch):
    interviews = _patch_interview_dirs(tmp_path, monkeypatch)
    (interviews / "interview_t.md").write_text("短文\n第二行\n", encoding="utf-8")

    raw = docs.inspect_document.invoke({"path": "interview_t"})
    data = json.loads(raw)
    assert data["doc_id"] == "interview_t"
    assert data["lines"] == 2
    assert data["recommendation"] == "direct_read"
    assert data["source_path"] == "/docs/interviews/interview_t.md"
    assert data["markdown_path"] == data["source_path"]
    assert data["thresholds"]["max_lines_direct"] == 500
    assert data["thresholds"]["max_chars_direct"] == 15000


def test_inspect_document_interview_not_found(tmp_path, monkeypatch):
    _patch_interview_dirs(tmp_path, monkeypatch)

    raw = docs.inspect_document.invoke({"path": "no_such_interview"})
    data = json.loads(raw)
    assert "error" in data
    assert "Interview document not found" in data["error"]
    assert "no_such_interview" in data["error"]

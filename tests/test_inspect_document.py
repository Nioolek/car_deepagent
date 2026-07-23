import json
from pathlib import Path

from docx import Document

from car_deepagent.tools import documents as docs


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(path)


def _patch_interview_dirs(tmp_path, monkeypatch):
    interviews = tmp_path / "docs" / "interviews"
    interviews.mkdir(parents=True)
    cache = tmp_path / "md"
    cache.mkdir()
    monkeypatch.setattr(docs, "markdown_cache_dir", lambda: cache)
    monkeypatch.setattr(
        "car_deepagent.analysis_docs.interviews_dir",
        lambda: interviews,
    )
    monkeypatch.setattr(
        "car_deepagent.analysis_docs.repo_root",
        lambda: tmp_path,
    )
    return interviews, cache


def test_count_text_volume_lines_and_scripts():
    text = "Hello 你好\nWorld\n"
    vol = docs.count_text_volume(text)
    assert vol["lines"] == 2  # splitlines drops trailing empty after final \n?
    # Use text without trailing-only empty: "Hello 你好\nWorld" -> 2 lines
    vol = docs.count_text_volume("Hello 你好\nWorld")
    assert vol["lines"] == 2
    assert vol["chars"] == len("Hello 你好\nWorld")
    assert vol["chars_latin"] == len("HelloWorld")
    assert vol["chars_cjk"] == 2  # 你 好
    assert vol["chars_other"] == vol["chars"] - vol["chars_latin"] - vol["chars_cjk"]


def test_recommendation_thresholds():
    assert docs.recommendation_for_volume(10, 100) == "direct_read"
    assert docs.recommendation_for_volume(500, 100) == "direct_read"
    assert docs.recommendation_for_volume(10, 15000) == "direct_read"
    assert docs.recommendation_for_volume(501, 100) == "delegate"
    assert docs.recommendation_for_volume(10, 15001) == "delegate"


def test_inspect_document_on_cached_markdown(tmp_path, monkeypatch):
    md_dir = tmp_path / "md"
    md_dir.mkdir()
    monkeypatch.setattr(docs, "markdown_cache_dir", lambda: md_dir)
    (md_dir / "interview_t.md").write_text("短文\n第二行\n", encoding="utf-8")

    raw = docs.inspect_document.invoke({"path": "interview_t"})
    data = json.loads(raw)
    assert data["doc_id"] == "interview_t"
    assert data["lines"] == 2
    assert data["recommendation"] == "direct_read"
    assert data["markdown_path"].endswith("interview_t.md")
    assert data["thresholds"]["max_lines_direct"] == 500
    assert data["thresholds"]["max_chars_direct"] == 15000


def test_inspect_document_missing_markdown(tmp_path, monkeypatch):
    interviews, _cache = _patch_interview_dirs(tmp_path, monkeypatch)
    _write_docx(interviews / "interview_x.docx", ["背景", "受访者来自上海。"])

    raw = docs.inspect_document.invoke({"path": "interview_x"})
    data = json.loads(raw)
    assert "error" in data
    assert "ensure_document_markdown" in data["error"]


def test_inspect_document_interview_not_found(tmp_path, monkeypatch):
    _patch_interview_dirs(tmp_path, monkeypatch)

    raw = docs.inspect_document.invoke({"path": "no_such_interview"})
    data = json.loads(raw)
    assert "error" in data
    assert "Interview document not found" in data["error"]
    assert "no_such_interview" in data["error"]

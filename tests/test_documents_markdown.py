import json
from pathlib import Path

from docx import Document

from car_deepagent.tools import documents as documents_mod
from car_deepagent.tools.documents import doc_id_for_path, ensure_document_markdown


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(path)


def test_doc_id_for_path():
    assert doc_id_for_path("/tmp/interview_001.docx") == "interview_001"


def test_ensure_document_markdown_creates_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(documents_mod, "markdown_cache_dir", lambda: tmp_path / "md")
    (tmp_path / "md").mkdir()
    src = tmp_path / "interview_x.docx"
    _write_docx(src, ["背景", "受访者来自上海。", "智驾体验", "NOA 总体可用。"])
    raw = ensure_document_markdown.invoke({"path": str(src)})
    data = json.loads(raw)
    assert data["doc_id"] == "interview_x"
    md_path = Path(data["markdown_path"])
    assert md_path.exists()
    text = md_path.read_text(encoding="utf-8")
    assert "智驾体验" in text
    assert data["chars"] > 0


def test_ensure_document_markdown_missing_file():
    raw = ensure_document_markdown.invoke({"path": "/no/such/file.docx"})
    data = json.loads(raw)
    assert "error" in data

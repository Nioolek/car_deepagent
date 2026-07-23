import hashlib
import json

from car_deepagent.tools import documents as docs


def test_save_and_load_doc_map_roundtrip(tmp_path, monkeypatch):
    md = tmp_path / "md"
    maps = tmp_path / "maps"
    md.mkdir()
    maps.mkdir()
    monkeypatch.setattr(docs, "markdown_cache_dir", lambda: md)
    monkeypatch.setattr(docs, "doc_maps_dir", lambda: maps)
    body = "# title\nline2\n"
    (md / "interview_t.md").write_text(body, encoding="utf-8")
    sha = hashlib.sha256(body.encode()).hexdigest()

    payload = {
        "doc_id": "interview_t",
        "sections": [{"start_line": 1, "end_line": 2, "topic": "t", "summary": "s"}],
        "highlights": [{"line": 2, "note": "n"}],
    }
    saved = json.loads(
        docs.save_doc_map.invoke(
            {"doc_id": "interview_t", "map_json": json.dumps(payload, ensure_ascii=False)}
        )
    )
    assert saved["cached"] is False
    assert saved["markdown_sha256"] == sha

    loaded = json.loads(docs.load_doc_map.invoke({"doc_id": "interview_t"}))
    assert loaded["cached"] is True
    assert loaded["sections"][0]["start_line"] == 1


def test_load_doc_map_miss_when_markdown_changed(tmp_path, monkeypatch):
    md = tmp_path / "md"
    maps = tmp_path / "maps"
    md.mkdir()
    maps.mkdir()
    monkeypatch.setattr(docs, "markdown_cache_dir", lambda: md)
    monkeypatch.setattr(docs, "doc_maps_dir", lambda: maps)
    (md / "interview_t.md").write_text("v1\n", encoding="utf-8")
    docs.save_doc_map.invoke(
        {
            "doc_id": "interview_t",
            "map_json": json.dumps(
                {"doc_id": "interview_t", "sections": [], "highlights": []}
            ),
        }
    )
    (md / "interview_t.md").write_text("v2 changed\n", encoding="utf-8")
    loaded = json.loads(docs.load_doc_map.invoke({"doc_id": "interview_t"}))
    assert loaded.get("cached") is False or "error" in loaded or loaded.get("stale") is True


def test_save_doc_map_strips_findings(tmp_path, monkeypatch):
    md = tmp_path / "md"
    maps = tmp_path / "maps"
    md.mkdir()
    maps.mkdir()
    monkeypatch.setattr(docs, "markdown_cache_dir", lambda: md)
    monkeypatch.setattr(docs, "doc_maps_dir", lambda: maps)
    (md / "interview_t.md").write_text("body\n", encoding="utf-8")

    payload = {
        "doc_id": "interview_t",
        "sections": [],
        "highlights": [],
        "findings": [{"line": 1, "text": "request-specific"}],
    }
    docs.save_doc_map.invoke(
        {
            "doc_id": "interview_t",
            "map_json": json.dumps(payload, ensure_ascii=False),
        }
    )
    stored = json.loads((maps / "interview_t.json").read_text(encoding="utf-8"))
    assert "findings" not in stored


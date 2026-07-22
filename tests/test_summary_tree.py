import json

from car_deepagent.tools import documents as docs

SAMPLE_MD = """# 一、背景
用户在上海工作。

# 二、智驾体验
高速 NOA 体验良好，但雨天会接管。

# 三、总结
整体满意。
"""


def test_split_chapters():
    chapters = docs.split_chapters(SAMPLE_MD)
    assert len(chapters) == 3
    assert chapters[0]["chapter_id"] == "1"
    assert "智驾" in chapters[1]["title"]


def test_ensure_summary_tree_builds_once(tmp_path, monkeypatch):
    monkeypatch.setattr(docs, "markdown_cache_dir", lambda: tmp_path / "md")
    monkeypatch.setattr(docs, "summary_trees_dir", lambda: tmp_path / "trees")
    (tmp_path / "md").mkdir()
    (tmp_path / "trees").mkdir()
    (tmp_path / "md" / "interview_t.md").write_text(SAMPLE_MD, encoding="utf-8")

    calls = {"n": 0}

    class FakeMsg:
        content = "章节摘要"

    class FakeModel:
        def invoke(self, messages):
            calls["n"] += 1
            return FakeMsg()

    monkeypatch.setattr(docs, "build_chat_model", lambda: FakeModel())

    raw1 = docs.ensure_summary_tree.invoke({"doc_id": "interview_t"})
    raw2 = docs.ensure_summary_tree.invoke({"doc_id": "interview_t"})
    d1 = json.loads(raw1)
    d2 = json.loads(raw2)
    assert d1["cached"] is False
    assert d2["cached"] is True
    assert calls["n"] == 3

    summary = json.loads(
        docs.get_chapter_summary.invoke(
            {"doc_id": "interview_t", "chapter_id": "2"}
        )
    )
    assert summary["summary"] == "章节摘要"
    excerpt = json.loads(
        docs.get_chapter_excerpt.invoke(
            {"doc_id": "interview_t", "chapter_id": "2", "offset": 0, "limit": 40}
        )
    )
    assert "NOA" in excerpt["excerpt"] or "雨天" in excerpt["excerpt"]


def test_invalid_doc_id_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(docs, "markdown_cache_dir", lambda: tmp_path / "md")
    monkeypatch.setattr(docs, "summary_trees_dir", lambda: tmp_path / "trees")
    (tmp_path / "md").mkdir()
    (tmp_path / "trees").mkdir()

    invalid = "../etc/passwd"
    for tool, args in (
        (docs.ensure_summary_tree, {"doc_id": invalid}),
        (docs.get_chapter_summary, {"doc_id": invalid, "chapter_id": "1"}),
        (
            docs.get_chapter_excerpt,
            {"doc_id": invalid, "chapter_id": "1", "offset": 0, "limit": 40},
        ),
    ):
        data = json.loads(tool.invoke(args))
        assert "error" in data
        assert "Invalid doc_id" in data["error"]

    assert list((tmp_path / "md").iterdir()) == []
    assert list((tmp_path / "trees").iterdir()) == []
    assert not (tmp_path.parent / "etc").exists()

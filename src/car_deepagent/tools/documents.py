from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from langchain_core.tools import tool

from car_deepagent.config import build_chat_model
from car_deepagent.paths import markdown_cache_dir, summary_trees_dir

_DOC_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _doc_id_error(doc_id: str) -> str | None:
    if _DOC_ID_RE.fullmatch(doc_id):
        return None
    return json.dumps({"error": f"Invalid doc_id: {doc_id}"}, ensure_ascii=False)


def doc_id_for_path(path: str | Path) -> str:
    return Path(path).stem


def _docx_to_markdown(path: Path) -> str:
    document = Document(str(path))
    lines: list[str] = []
    for para in document.paragraphs:
        text = (para.text or "").strip()
        if not text:
            continue
        style = (para.style.name or "") if para.style else ""
        if style.startswith("Heading"):
            level_match = re.search(r"(\d+)", style)
            level = int(level_match.group(1)) if level_match else 1
            lines.append("#" * max(1, min(level, 6)) + " " + text)
        else:
            lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


@tool
def ensure_document_markdown(path: str) -> str:
    """Convert a .docx interview report to cached markdown. Returns JSON with doc_id and markdown_path."""
    src = Path(path)
    if not src.exists():
        return json.dumps({"error": f"File not found: {path}"}, ensure_ascii=False)
    if src.suffix.lower() != ".docx":
        return json.dumps({"error": f"Not a .docx file: {path}"}, ensure_ascii=False)
    doc_id = doc_id_for_path(src)
    out = markdown_cache_dir() / f"{doc_id}.md"
    if not out.exists():
        md = _docx_to_markdown(src)
        out.write_text(md, encoding="utf-8")
    text = out.read_text(encoding="utf-8")
    return json.dumps(
        {
            "doc_id": doc_id,
            "markdown_path": str(out),
            "chars": len(text),
            "source_path": str(src.resolve()),
        },
        ensure_ascii=False,
    )


def split_chapters(markdown: str) -> list[dict]:
    heading_re = re.compile(r"^(#{1,3})\s+(.*)$")
    chapters: list[dict] = []
    title = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal title, buf
        if title is None and not any(line.strip() for line in buf):
            buf = []
            return
        text = "\n".join(buf).strip()
        if title is None:
            title = "全文"
        if text:
            chapters.append(
                {
                    "chapter_id": str(len(chapters) + 1),
                    "title": title,
                    "text": text,
                }
            )
        title = None
        buf = []

    for line in markdown.splitlines():
        match = heading_re.match(line.strip())
        if match:
            flush()
            title = match.group(2).strip()
            buf = []
        else:
            buf.append(line)
    flush()
    return chapters


def _tree_path(doc_id: str) -> Path:
    if _doc_id_error(doc_id) is not None:
        raise ValueError(f"Invalid doc_id: {doc_id}")
    return summary_trees_dir() / f"{doc_id}.json"


def _chapter_map(doc_id: str) -> dict[str, dict]:
    if _doc_id_error(doc_id) is not None:
        raise ValueError(f"Invalid doc_id: {doc_id}")
    markdown_path = markdown_cache_dir() / f"{doc_id}.md"
    if not markdown_path.exists():
        return {}
    chapters = split_chapters(markdown_path.read_text(encoding="utf-8"))
    return {chapter["chapter_id"]: chapter for chapter in chapters}


def _summarize_chapter(chapter: dict) -> str:
    try:
        response = build_chat_model().invoke(
            [
                {
                    "role": "system",
                    "content": "请将访谈章节概括为简短、准确的中文摘要。",
                },
                {
                    "role": "user",
                    "content": f"章节：{chapter['title']}\n\n{chapter['text']}",
                },
            ]
        )
        return str(response.content)
    except Exception:
        return f"[fallback]{chapter['text'][:200]}"


@tool
def ensure_summary_tree(doc_id: str) -> str:
    """Build and cache chapter summaries for a cached markdown document."""
    if err := _doc_id_error(doc_id):
        return err
    tree_path = _tree_path(doc_id)
    if tree_path.exists():
        tree = json.loads(tree_path.read_text(encoding="utf-8"))
        return json.dumps(
            {**tree, "cached": True, "tree_path": str(tree_path)},
            ensure_ascii=False,
        )

    markdown_path = markdown_cache_dir() / f"{doc_id}.md"
    if not markdown_path.exists():
        return json.dumps(
            {"error": f"Markdown not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )

    chapters = split_chapters(markdown_path.read_text(encoding="utf-8"))
    tree = {
        "doc_id": doc_id,
        "chapters": [
            {
                "chapter_id": chapter["chapter_id"],
                "title": chapter["title"],
                "summary": _summarize_chapter(chapter),
                "char_count": len(chapter["text"]),
            }
            for chapter in chapters
        ],
    }
    tree_path.parent.mkdir(parents=True, exist_ok=True)
    tree_path.write_text(
        json.dumps(tree, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return json.dumps(
        {**tree, "cached": False, "tree_path": str(tree_path)},
        ensure_ascii=False,
    )


@tool
def get_chapter_summary(doc_id: str, chapter_id: str) -> str:
    """Return one cached chapter summary."""
    if err := _doc_id_error(doc_id):
        return err
    tree_path = _tree_path(doc_id)
    if not tree_path.exists():
        return json.dumps(
            {"error": f"Summary tree not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    chapter = next(
        (
            item
            for item in tree.get("chapters", [])
            if item["chapter_id"] == chapter_id
        ),
        None,
    )
    if chapter is None:
        return json.dumps(
            {"error": f"Chapter not found: {chapter_id}"},
            ensure_ascii=False,
        )
    return json.dumps(
        {"doc_id": doc_id, **chapter},
        ensure_ascii=False,
    )


@tool
def get_chapter_excerpt(
    doc_id: str, chapter_id: str, offset: int = 0, limit: int = 800
) -> str:
    """Return a slice of original chapter text with its citation key."""
    if err := _doc_id_error(doc_id):
        return err
    chapter = _chapter_map(doc_id).get(chapter_id)
    if chapter is None:
        return json.dumps(
            {"error": f"Chapter not found: {chapter_id}"},
            ensure_ascii=False,
        )
    start = max(0, offset)
    excerpt = chapter["text"][start : start + max(0, limit)]
    return json.dumps(
        {
            "doc_id": doc_id,
            "chapter_id": chapter_id,
            "title": chapter["title"],
            "offset": start,
            "limit": max(0, limit),
            "excerpt": excerpt,
            "citation_key": f"[^{doc_id}§{chapter_id}]",
        },
        ensure_ascii=False,
    )

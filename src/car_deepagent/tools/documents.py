from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from langchain_core.tools import tool

from car_deepagent.paths import markdown_cache_dir


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

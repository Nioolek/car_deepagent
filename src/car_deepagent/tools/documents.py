from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.tools import tool

from car_deepagent.analysis_docs import (
    interview_virtual_path,
    normalize_doc_path,
    resolve_interview_file,
    search_interview_docs,
)

MAX_LINES_DIRECT = 500
MAX_CHARS_DIRECT = 15000

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def doc_id_for_path(path: str | Path) -> str:
    return Path(path).stem


def count_text_volume(text: str) -> dict:
    lines = text.splitlines()
    chars = len(text)
    chars_cjk = len(_CJK_RE.findall(text))
    chars_latin = len(_LATIN_RE.findall(text))
    chars_other = max(0, chars - chars_cjk - chars_latin)
    return {
        "lines": len(lines),
        "chars": chars,
        "chars_cjk": chars_cjk,
        "chars_latin": chars_latin,
        "chars_other": chars_other,
    }


def recommendation_for_volume(lines: int, chars: int) -> str:
    if lines > MAX_LINES_DIRECT or chars > MAX_CHARS_DIRECT:
        return "delegate"
    return "direct_read"


def _resolve_source_markdown(path: str) -> tuple[str, Path] | tuple[None, None]:
    """Return (doc_id, absolute .md path) under docs/interviews."""
    resolved = resolve_interview_file(path)
    if resolved is None:
        return None, None
    return doc_id_for_path(resolved), resolved


def volume_summary_for_path(path: str) -> dict | None:
    """Return inspect-like volume fields for a resolvable interview path."""
    doc_id, source_path = _resolve_source_markdown(path)
    if doc_id is None or source_path is None:
        return None
    text = source_path.read_text(encoding="utf-8")
    volume = count_text_volume(text)
    recommendation = recommendation_for_volume(volume["lines"], volume["chars"])
    virtual = interview_virtual_path(doc_id)
    return {
        "doc_id": doc_id,
        "path": normalize_doc_path(path) or normalize_doc_path(doc_id),
        "source_path": virtual,
        **volume,
        "recommendation": recommendation,
        "thresholds": {
            "max_lines_direct": MAX_LINES_DIRECT,
            "max_chars_direct": MAX_CHARS_DIRECT,
        },
    }


@tool
def list_interview_docs(query: str = "") -> str:
    """List interview markdown files under docs/interviews (optional name filter).

    Prefer this over ls/glob when discovering or confirming interview paths.
    Returns JSON: {"files":[{"path","doc_id","virtual_path"},...], "query":...}.
    """
    paths = search_interview_docs(query)
    files = []
    for rel in paths:
        doc_id = Path(rel).stem
        files.append(
            {
                "path": rel,
                "doc_id": doc_id,
                "virtual_path": interview_virtual_path(doc_id),
            }
        )
    return json.dumps(
        {"files": files, "query": (query or "").strip() or None, "count": len(files)},
        ensure_ascii=False,
    )


@tool
def inspect_document(path: str) -> str:
    """Measure interview markdown volume and recommend direct_read vs delegate."""
    summary = volume_summary_for_path(path)
    if summary is None:
        return json.dumps(
            {
                "error": (
                    f"Interview document not found under docs/interviews/: {path}"
                ),
            },
            ensure_ascii=False,
        )
    # Keep tool payload aligned with historical inspect_document fields.
    payload = {
        "doc_id": summary["doc_id"],
        "source_path": summary["source_path"],
        "markdown_path": summary["source_path"],
        "lines": summary["lines"],
        "chars": summary["chars"],
        "chars_cjk": summary["chars_cjk"],
        "chars_latin": summary["chars_latin"],
        "chars_other": summary["chars_other"],
        "recommendation": summary["recommendation"],
        "thresholds": summary["thresholds"],
    }
    return json.dumps(payload, ensure_ascii=False)

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from langchain_core.tools import tool

from car_deepagent.analysis_docs import interview_virtual_path, resolve_interview_file
from car_deepagent.paths import doc_maps_dir

MAX_LINES_DIRECT = 500
MAX_CHARS_DIRECT = 15000

_DOC_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def _doc_id_error(doc_id: str) -> str | None:
    if _DOC_ID_RE.fullmatch(doc_id):
        return None
    return json.dumps({"error": f"Invalid doc_id: {doc_id}"}, ensure_ascii=False)


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


@tool
def inspect_document(path: str) -> str:
    """Measure interview markdown volume and recommend direct_read vs delegate."""
    doc_id, source_path = _resolve_source_markdown(path)
    if doc_id is None or source_path is None:
        return json.dumps(
            {
                "error": (
                    f"Interview document not found under docs/interviews/: {path}"
                ),
            },
            ensure_ascii=False,
        )

    text = source_path.read_text(encoding="utf-8")
    volume = count_text_volume(text)
    recommendation = recommendation_for_volume(volume["lines"], volume["chars"])
    virtual = interview_virtual_path(doc_id)
    return json.dumps(
        {
            "doc_id": doc_id,
            "source_path": virtual,
            "markdown_path": virtual,
            **volume,
            "recommendation": recommendation,
            "thresholds": {
                "max_lines_direct": MAX_LINES_DIRECT,
                "max_chars_direct": MAX_CHARS_DIRECT,
            },
        },
        ensure_ascii=False,
    )


def _doc_map_path(doc_id: str) -> Path:
    if _doc_id_error(doc_id) is not None:
        raise ValueError(f"Invalid doc_id: {doc_id}")
    return doc_maps_dir() / f"{doc_id}.json"


def _interview_md_for_doc_id(doc_id: str) -> Path | None:
    if _doc_id_error(doc_id) is not None:
        return None
    return resolve_interview_file(doc_id)


@tool
def save_doc_map(doc_id: str, map_json: str) -> str:
    """Persist a provenance map (sections + highlights) for an interview markdown."""
    if err := _doc_id_error(doc_id):
        return err
    source_path = _interview_md_for_doc_id(doc_id)
    if source_path is None or not source_path.exists():
        return json.dumps(
            {"error": f"Interview markdown not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )
    try:
        payload = json.loads(map_json)
    except json.JSONDecodeError as exc:
        return json.dumps(
            {"error": f"Invalid map_json: {exc}"},
            ensure_ascii=False,
        )
    if not isinstance(payload, dict):
        return json.dumps(
            {"error": "Invalid map_json: expected a JSON object."},
            ensure_ascii=False,
        )

    markdown = source_path.read_text(encoding="utf-8")
    markdown_sha256 = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    stored = {
        "doc_id": doc_id,
        "markdown_sha256": markdown_sha256,
        "sections": payload.get("sections", []),
        "highlights": payload.get("highlights", []),
    }
    map_path = _doc_map_path(doc_id)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(
        json.dumps(stored, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return json.dumps(
        {**stored, "cached": False, "map_path": str(map_path)},
        ensure_ascii=False,
    )


@tool
def load_doc_map(doc_id: str) -> str:
    """Load a cached provenance map if source markdown sha256 still matches."""
    if err := _doc_id_error(doc_id):
        return err
    map_path = _doc_map_path(doc_id)
    if not map_path.exists():
        return json.dumps(
            {"error": f"Doc map not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )
    source_path = _interview_md_for_doc_id(doc_id)
    if source_path is None or not source_path.exists():
        return json.dumps(
            {"error": f"Interview markdown not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )
    try:
        stored = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.dumps(
            {"error": f"Doc map not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )

    markdown = source_path.read_text(encoding="utf-8")
    markdown_sha256 = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    if stored.get("markdown_sha256") != markdown_sha256:
        return json.dumps(
            {"cached": False, "stale": True, "doc_id": doc_id},
            ensure_ascii=False,
        )
    return json.dumps(
        {**stored, "cached": True, "map_path": str(map_path)},
        ensure_ascii=False,
    )

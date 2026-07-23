from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from docx import Document
from langchain_core.tools import tool

from car_deepagent.analysis_docs import resolve_interview_file
from car_deepagent.paths import doc_maps_dir, markdown_cache_dir

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


def _resolve_markdown_for_inspect(
    path: str,
) -> tuple[str, Path] | tuple[None, None]:
    """Return (doc_id, markdown_path) from interview path/stem or existing cache."""
    stripped = path.strip()
    stem = Path(stripped).stem
    if _DOC_ID_RE.fullmatch(stem):
        cached = markdown_cache_dir() / f"{stem}.md"
        if cached.exists():
            return stem, cached

    resolved = resolve_interview_file(path)
    if resolved is None:
        return None, None

    doc_id = doc_id_for_path(resolved)
    markdown_path = markdown_cache_dir() / f"{doc_id}.md"
    if not markdown_path.exists():
        return None, None
    return doc_id, markdown_path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _markdown_metadata_path(markdown_path: Path) -> Path:
    return markdown_path.with_suffix(".md.meta.json")


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
    """Convert a .docx interview report under docs/interviews to cached markdown.

    Pass a repo path, filename, or stem (e.g. interview_001). Always resolves
    under docs/interviews/. Returns JSON with doc_id and markdown_path.
    """
    resolved = resolve_interview_file(path)
    if resolved is None:
        return json.dumps(
            {
                "error": (
                    f"Interview document not found under docs/interviews/: {path}"
                ),
            },
            ensure_ascii=False,
        )
    src = resolved
    doc_id = doc_id_for_path(src)
    out = markdown_cache_dir() / f"{doc_id}.md"
    metadata_path = _markdown_metadata_path(out)
    source_path = str(src.resolve())
    source_sha256 = _sha256_file(src)
    cache_valid = False
    if out.exists() and metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            cache_valid = (
                metadata.get("source_path") == source_path
                and metadata.get("source_sha256") == source_sha256
            )
        except (OSError, json.JSONDecodeError):
            cache_valid = False
    if not cache_valid:
        md = _docx_to_markdown(src)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        metadata_path.write_text(
            json.dumps(
                {
                    "source_path": source_path,
                    "source_sha256": source_sha256,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    text = out.read_text(encoding="utf-8")
    return json.dumps(
        {
            "doc_id": doc_id,
            "markdown_path": str(out),
            "chars": len(text),
            "source_path": source_path,
            "source_sha256": source_sha256,
        },
        ensure_ascii=False,
    )


@tool
def inspect_document(path: str) -> str:
    """Measure markdown volume and recommend direct_read vs delegate."""
    doc_id, markdown_path = _resolve_markdown_for_inspect(path)
    if doc_id is None or markdown_path is None:
        resolved = resolve_interview_file(path)
        if resolved is not None:
            doc_id = doc_id_for_path(resolved)
            return json.dumps(
                {
                    "error": (
                        f"Markdown not found for doc_id: {doc_id}. "
                        "Call ensure_document_markdown first."
                    ),
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "error": (
                    f"Interview document not found under docs/interviews/: {path}"
                ),
            },
            ensure_ascii=False,
        )

    text = markdown_path.read_text(encoding="utf-8")
    volume = count_text_volume(text)
    recommendation = recommendation_for_volume(volume["lines"], volume["chars"])
    return json.dumps(
        {
            "doc_id": doc_id,
            "markdown_path": str(markdown_path),
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


@tool
def save_doc_map(doc_id: str, map_json: str) -> str:
    """Persist a provenance map (sections + highlights) for a cached markdown doc."""
    if err := _doc_id_error(doc_id):
        return err
    markdown_path = markdown_cache_dir() / f"{doc_id}.md"
    if not markdown_path.exists():
        return json.dumps(
            {"error": f"Markdown not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )
    try:
        payload = json.loads(map_json)
    except json.JSONDecodeError as exc:
        return json.dumps(
            {"error": f"Invalid map_json: {exc}"},
            ensure_ascii=False,
        )

    markdown = markdown_path.read_text(encoding="utf-8")
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
    """Load a cached provenance map if markdown sha256 still matches."""
    if err := _doc_id_error(doc_id):
        return err
    map_path = _doc_map_path(doc_id)
    if not map_path.exists():
        return json.dumps(
            {"error": f"Doc map not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )
    markdown_path = markdown_cache_dir() / f"{doc_id}.md"
    if not markdown_path.exists():
        return json.dumps(
            {"error": f"Markdown not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )
    try:
        stored = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.dumps(
            {"error": f"Doc map not found for doc_id: {doc_id}"},
            ensure_ascii=False,
        )

    markdown = markdown_path.read_text(encoding="utf-8")
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

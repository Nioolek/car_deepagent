from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from car_deepagent.paths import interviews_dir, repo_root


@dataclass
class AgentContext:
    """Run-scoped context from the chat UI / LangGraph Runtime."""

    analysis_doc_paths: list[str] = field(default_factory=list)


def list_interview_docx_paths() -> list[str]:
    """Return repo-relative posix paths for interview .docx files."""
    root = interviews_dir()
    if not root.is_dir():
        return []
    paths = sorted(root.glob("*.docx"))
    repo = repo_root().resolve()
    return [p.resolve().relative_to(repo).as_posix() for p in paths]


def search_interview_docs(query: str | None = None) -> list[str]:
    """List interview docs under docs/interviews, optionally filtered by name.

    Matching is case-insensitive substring on the filename (with or without .docx).
    Empty / whitespace query returns the full list.
    """
    paths = list_interview_docx_paths()
    needle = (query or "").strip().lower()
    if not needle:
        return paths
    return [
        path
        for path in paths
        if needle in Path(path).name.lower() or needle in Path(path).stem.lower()
    ]


def resolve_interview_file(path: str) -> Path | None:
    """Resolve a document reference to an absolute .docx under docs/interviews.

    Accepts:
    - repo-relative paths like docs/interviews/interview_001.docx
    - bare filenames interview_001.docx
    - bare stems interview_001
    - absolute paths that still resolve inside docs/interviews
    """
    raw = (path or "").strip().strip("\"'")
    if not raw:
        return None

    interviews = interviews_dir().resolve()
    repo = repo_root().resolve()
    candidate = Path(raw)
    name = candidate.name
    stem = Path(name).stem if name else ""

    trials: list[Path] = []
    if candidate.is_absolute():
        trials.append(candidate)
    else:
        posix = raw.replace("\\", "/")
        if posix.startswith("docs/interviews/"):
            trials.append(repo / posix)
        if name:
            trials.append(interviews / name)
        if stem and not name.lower().endswith(".docx"):
            trials.append(interviews / f"{stem}.docx")
        elif stem:
            trials.append(interviews / f"{stem}.docx")
        trials.append(repo / candidate)

    seen: set[Path] = set()
    for trial in trials:
        try:
            resolved = trial.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            resolved.relative_to(interviews)
        except ValueError:
            continue
        if resolved.suffix.lower() != ".docx":
            continue
        if resolved.is_file():
            return resolved
    return None


def normalize_doc_path(path: str) -> str | None:
    """Normalize a user/tool path to repo-relative posix under docs/interviews."""
    resolved = resolve_interview_file(path)
    if resolved is None:
        return None
    return resolved.relative_to(repo_root().resolve()).as_posix()


def normalize_analysis_doc_paths(paths: list[str] | None) -> list[str]:
    """Deduplicate and keep only valid interview docx paths (stable order)."""
    if not paths:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in paths:
        normalized = normalize_doc_path(item)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def allowed_doc_ids(paths: list[str]) -> set[str]:
    return {Path(p).stem for p in paths}


def extract_analysis_doc_paths(context: object | None) -> list[str]:
    """Read analysis_doc_paths from Runtime context (dataclass, dict, or None)."""
    if context is None:
        return []
    if isinstance(context, AgentContext):
        return normalize_analysis_doc_paths(context.analysis_doc_paths)
    if isinstance(context, dict):
        raw = context.get("analysis_doc_paths")
        if isinstance(raw, list):
            return normalize_analysis_doc_paths(
                [str(item) for item in raw if item is not None]
            )
        return []
    raw = getattr(context, "analysis_doc_paths", None)
    if isinstance(raw, list):
        return normalize_analysis_doc_paths(
            [str(item) for item in raw if item is not None]
        )
    return []

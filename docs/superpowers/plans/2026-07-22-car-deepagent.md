# car_deepagent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a LangGraph Deep Agent graph that analyzes HarmonyOS Intelligent Mobility interview Word reports (single/multi-doc Q&A, user-profile assist, summary-tree context, footnote citations, todos, skills) debuggable via `graph.astream`.

**Architecture:** `create_deep_agent` main harness + `report_analyst` sub-agent; document work quarantined behind summary-tree tools; skills encode workflows; project `.env` for OpenAI-compatible LLM; no frontend.

**Tech Stack:** Python 3.11+, `deepagents`, `langchain-openai`, `langgraph`, `python-docx`, `python-dotenv`, `tiktoken` (or char/4 fallback), `pytest`

## Global Constraints

- Deliver only an exported LangGraph `graph`; local debug via `graph.astream`; later LangGraph API/Runtime.
- Load LLM from project root `.env`: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_TIMEOUT_MS`. Never commit `.env`.
- Disable default `general-purpose` sub-agent; only expose `report_analyst` via `task`.
- Full reports must not enter main-agent context; use summary tree + chapter excerpts.
- Citations: inline `[^doc_id§chapter_id]` plus end-matter excerpts.
- Summary tree: lazy-build on first analysis, cache under `workspace/cache/`.
- Skills: exactly three directories under `skills/`.
- Sample data is fabricated (non-confidential) `.docx` + mock users.
- Prefer Deep Agents built-ins (`write_todos`, filesystem, summarization) over custom graph nodes.
- Commits must not include `.env` or API keys.

---

## File Structure

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata + dependencies |
| `src/car_deepagent/__init__.py` | Package export of `graph` |
| `src/car_deepagent/paths.py` | Repo-root / data / cache path helpers |
| `src/car_deepagent/config.py` | Load `.env`, build `ChatOpenAI` |
| `src/car_deepagent/tools/user_profile.py` | `get_user_profile` tool |
| `src/car_deepagent/tools/documents.py` | docx→md, summary tree, chapter access |
| `src/car_deepagent/tools/tokens.py` | `estimate_tokens` tool |
| `src/car_deepagent/subagents/report_analyst.py` | Sub-agent spec dict |
| `src/car_deepagent/graph.py` | `create_deep_agent` → `graph` |
| `skills/*/SKILL.md` | Three skills |
| `data/users/*.json` | Mock profiles |
| `docs/interviews/*.docx` | Fake interview reports |
| `scripts/generate_sample_docs.py` | Generate fake docx + users |
| `scripts/smoke_astream.py` | Local astream smoke |
| `tests/...` | Unit tests per task |

---

### Task 1: Project scaffold, paths, and LLM config

**Files:**
- Create: `pyproject.toml`
- Create: `src/car_deepagent/__init__.py`
- Create: `src/car_deepagent/paths.py`
- Create: `src/car_deepagent/config.py`
- Create: `tests/test_config.py`
- Modify: `README.md` (minimal run notes)

**Interfaces:**
- Produces: `repo_root() -> Path`, `load_settings() -> Settings`, `build_chat_model() -> ChatOpenAI`
- Settings fields: `api_key: str`, `base_url: str`, `model: str`, `timeout_ms: int`

- [ ] **Step 1: Write failing tests for paths + settings**

```python
# tests/test_config.py
from car_deepagent.config import load_settings
from car_deepagent.paths import repo_root


def test_repo_root_contains_pyproject():
    root = repo_root()
    assert (root / "pyproject.toml").exists()


def test_load_settings_reads_env(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "LLM_API_KEY=test-key",
                "LLM_BASE_URL=https://example.com/v1",
                "LLM_MODEL=test-model",
                "LLM_TIMEOUT_MS=12345",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CAR_DEEPAGENT_ENV_FILE", str(env))
    s = load_settings()
    assert s.api_key == "test-key"
    assert s.base_url == "https://example.com/v1"
    assert s.model == "test-model"
    assert s.timeout_ms == 12345
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/admin/car_deepagent && python -m pytest tests/test_config.py -v`  
Expected: FAIL (module/package missing)

- [ ] **Step 3: Add `pyproject.toml` and package skeleton**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "car-deepagent"
version = "0.1.0"
description = "HarmonyOS interview report analysis deep agent"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "deepagents>=0.4.0",
  "langchain-openai>=0.3.0",
  "langgraph>=0.4.0",
  "python-docx>=1.1.0",
  "python-dotenv>=1.0.0",
  "tiktoken>=0.7.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/car_deepagent/__init__.py
"""car_deepagent package."""

__all__ = ["graph"]


def __getattr__(name: str):
    if name == "graph":
        from car_deepagent.graph import get_graph

        return get_graph()
    raise AttributeError(name)
```

```python
# src/car_deepagent/paths.py
from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return repository root (directory containing pyproject.toml)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate repo root with pyproject.toml")


def data_users_dir() -> Path:
    return repo_root() / "data" / "users"


def interviews_dir() -> Path:
    return repo_root() / "docs" / "interviews"


def cache_dir() -> Path:
    path = repo_root() / "workspace" / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def summary_trees_dir() -> Path:
    path = cache_dir() / "summary_trees"
    path.mkdir(parents=True, exist_ok=True)
    return path


def markdown_cache_dir() -> Path:
    path = cache_dir() / "markdown"
    path.mkdir(parents=True, exist_ok=True)
    return path
```

```python
# src/car_deepagent/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from car_deepagent.paths import repo_root


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    timeout_ms: int


def _env_file_path() -> Path:
    override = os.environ.get("CAR_DEEPAGENT_ENV_FILE")
    if override:
        return Path(override)
    return repo_root() / ".env"


def load_settings() -> Settings:
    load_dotenv(_env_file_path(), override=False)
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    timeout_raw = os.environ.get("LLM_TIMEOUT_MS", "60000").strip()
    if not api_key or not base_url or not model:
        raise RuntimeError(
            "Missing LLM_API_KEY / LLM_BASE_URL / LLM_MODEL in .env "
            f"(looked at {_env_file_path()})"
        )
    return Settings(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_ms=int(timeout_raw),
    )


def build_chat_model() -> ChatOpenAI:
    s = load_settings()
    return ChatOpenAI(
        model=s.model,
        api_key=s.api_key,
        base_url=s.base_url,
        timeout=s.timeout_ms / 1000.0,
    )
```

- [ ] **Step 4: Install package editable and run tests**

Run:
```bash
cd /home/admin/car_deepagent
python -m pip install -e ".[dev]"
python -m pytest tests/test_config.py -v
```
Expected: PASS

- [ ] **Step 5: Update README with local debug notes (no secrets)**

Include:
```bash
pip install -e ".[dev]"
# ensure .env exists (from .env.example); do not commit .env
python scripts/smoke_astream.py
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/car_deepagent/__init__.py src/car_deepagent/paths.py src/car_deepagent/config.py tests/test_config.py README.md
git commit -m "feat: scaffold package, paths, and LLM config"
```

---

### Task 2: `get_user_profile` tool + mock users

**Files:**
- Create: `src/car_deepagent/tools/__init__.py`
- Create: `src/car_deepagent/tools/user_profile.py`
- Create: `data/users/U001.json`
- Create: `data/users/U002.json`
- Create: `data/users/U003.json`
- Create: `tests/test_user_profile.py`

**Interfaces:**
- Consumes: `data_users_dir()`
- Produces: `@tool get_user_profile(user_id: str | None = None, name: str | None = None) -> str` (JSON string; miss returns `{"found": false, ...}`)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_user_profile.py
import json

from car_deepagent.tools.user_profile import get_user_profile


def test_get_user_by_id():
    raw = get_user_profile.invoke({"user_id": "U001"})
    data = json.loads(raw)
    assert data["found"] is True
    assert data["profile"]["user_id"] == "U001"


def test_get_user_by_name():
    raw = get_user_profile.invoke({"name": "陈思远"})
    data = json.loads(raw)
    assert data["found"] is True


def test_user_miss():
    raw = get_user_profile.invoke({"user_id": "NOPE"})
    data = json.loads(raw)
    assert data["found"] is False
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `pytest tests/test_user_profile.py -v`  
Expected: FAIL import/tool missing

- [ ] **Step 3: Add mock users + tool**

Create `data/users/U001.json`:
```json
{
  "user_id": "U001",
  "name": "陈思远",
  "city": "上海",
  "vehicle": "问界 M7",
  "purchase_stage": "已提车 6 个月",
  "ads_package": "高阶智驾",
  "age_range": "30-35",
  "notes": "通勤高速较多，关注 NOA 稳定性"
}
```

Create `data/users/U002.json`:
```json
{
  "user_id": "U002",
  "name": "林婉清",
  "city": "深圳",
  "vehicle": "智界 R7",
  "purchase_stage": "已提车 2 个月",
  "ads_package": "基础辅助驾驶",
  "age_range": "25-30",
  "notes": "城市通勤，重视座舱与语音交互"
}
```

Create `data/users/U003.json`:
```json
{
  "user_id": "U003",
  "name": "周启明",
  "city": "杭州",
  "vehicle": "享界 S9",
  "purchase_stage": "已提车 1 年",
  "ads_package": "高阶智驾",
  "age_range": "40-45",
  "notes": "长途自驾多，关注泊车与 OTA"
}
```

```python
# src/car_deepagent/tools/__init__.py
"""Agent tools."""
```

```python
# src/car_deepagent/tools/user_profile.py
from __future__ import annotations

import json

from langchain_core.tools import tool

from car_deepagent.paths import data_users_dir


def _load_all_profiles() -> list[dict]:
    profiles: list[dict] = []
    root = data_users_dir()
    if not root.exists():
        return profiles
    for path in sorted(root.glob("*.json")):
        profiles.append(json.loads(path.read_text(encoding="utf-8")))
    return profiles


@tool
def get_user_profile(user_id: str | None = None, name: str | None = None) -> str:
    """Lookup a mock HarmonyOS Intelligent Mobility user profile by user_id or name."""
    if not user_id and not name:
        return json.dumps(
            {"found": False, "error": "Provide user_id or name"},
            ensure_ascii=False,
        )
    profiles = _load_all_profiles()
    for p in profiles:
        if user_id and p.get("user_id") == user_id:
            return json.dumps({"found": True, "profile": p}, ensure_ascii=False)
        if name and p.get("name") == name:
            return json.dumps({"found": True, "profile": p}, ensure_ascii=False)
    return json.dumps(
        {"found": False, "user_id": user_id, "name": name},
        ensure_ascii=False,
    )
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/test_user_profile.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/users src/car_deepagent/tools tests/test_user_profile.py
git commit -m "feat: add mock user profiles and get_user_profile tool"
```

---

### Task 3: Word → markdown conversion tool

**Files:**
- Create: `src/car_deepagent/tools/documents.py`
- Create: `tests/test_documents_markdown.py`

**Interfaces:**
- Produces:
  - `doc_id_for_path(path: str | Path) -> str`
  - `ensure_document_markdown(path: str) -> str` tool returning JSON `{"doc_id","markdown_path","chars"}` or `{"error":...}`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_documents_markdown.py
import json
from pathlib import Path

from docx import Document

from car_deepagent.tools.documents import doc_id_for_path, ensure_document_markdown


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(path)


def test_doc_id_for_path():
    assert doc_id_for_path("/tmp/interview_001.docx") == "interview_001"


def test_ensure_document_markdown_creates_cache(tmp_path, monkeypatch):
    from car_deepagent import paths as paths_mod

    monkeypatch.setattr(paths_mod, "markdown_cache_dir", lambda: tmp_path / "md")
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
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `pytest tests/test_documents_markdown.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement conversion in `documents.py`**

```python
# src/car_deepagent/tools/documents.py
from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from langchain_core.tools import tool

from car_deepagent.config import build_chat_model
from car_deepagent.paths import markdown_cache_dir, summary_trees_dir


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
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/test_documents_markdown.py -v`  
Expected: PASS

Note: tests monkeypatch `car_deepagent.paths.markdown_cache_dir`; `documents.py` imports the function by name, so monkeypatch must target `car_deepagent.tools.documents.markdown_cache_dir` instead if the symbol was bound at import. Implementers should either import `paths` module and call `paths.markdown_cache_dir()`, or monkeypatch `documents.markdown_cache_dir`. Prefer calling via `paths.markdown_cache_dir()` and patching `documents.markdown_cache_dir` in tests for reliability.

- [ ] **Step 5: Commit**

```bash
git add src/car_deepagent/tools/documents.py tests/test_documents_markdown.py
git commit -m "feat: convert interview docx to cached markdown"
```

---

### Task 4: Summary tree lazy build + chapter accessors

**Files:**
- Modify: `src/car_deepagent/tools/documents.py`
- Create: `tests/test_summary_tree.py`

**Interfaces:**
- Produces:
  - `split_chapters(markdown: str) -> list[dict]` with `{chapter_id, title, text}`
  - `@tool ensure_summary_tree(doc_id: str) -> str`
  - `@tool get_chapter_summary(doc_id: str, chapter_id: str) -> str`
  - `@tool get_chapter_excerpt(doc_id: str, chapter_id: str, offset: int = 0, limit: int = 800) -> str`
- Tree JSON: `{"doc_id", "chapters":[{"chapter_id","title","summary","char_count"}]}`
- Split on markdown `#{1,3}` headings.
- Summaries via module-global `build_chat_model().invoke`; on failure use `[fallback]` + first 200 chars.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_summary_tree.py
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
        docs.get_chapter_summary.invoke({"doc_id": "interview_t", "chapter_id": "2"})
    )
    assert summary["summary"] == "章节摘要"
    excerpt = json.loads(
        docs.get_chapter_excerpt.invoke(
            {"doc_id": "interview_t", "chapter_id": "2", "offset": 0, "limit": 40}
        )
    )
    assert "NOA" in excerpt["excerpt"] or "雨天" in excerpt["excerpt"]
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `pytest tests/test_summary_tree.py -v`  
Expected: FAIL

- [ ] **Step 3: Extend `documents.py`**

Add `split_chapters`, `_tree_path`, `_chapter_map`, `_summarize_chapter`, `ensure_summary_tree`, `get_chapter_summary`, `get_chapter_excerpt` exactly as specified in the design:

- `ensure_summary_tree` returns `cached: false` on first build and writes `summary_trees_dir()/"{doc_id}.json"`; second call returns `cached: true` without extra LLM calls.
- Use module-level `build_chat_model` so tests can monkeypatch `docs.build_chat_model`.
- `get_chapter_excerpt` returns `citation_key` like `[^{doc_id}§{chapter_id}]`.

Reference implementation sketch:

```python
def split_chapters(markdown: str) -> list[dict]:
    lines = markdown.splitlines()
    chapters: list[dict] = []
    current_title = "全文"
    current_lines: list[str] = []
    heading_re = re.compile(r"^(#{1,3})\s+(.*)$")

    def flush():
        nonlocal current_title, current_lines
        text = "\n".join(current_lines).strip()
        if text:
            chapters.append(
                {
                    "chapter_id": str(len(chapters) + 1),
                    "title": current_title.strip() or f"章节{len(chapters)+1}",
                    "text": text,
                }
            )
        current_lines = []

    for line in lines:
        m = heading_re.match(line.strip())
        if m:
            if current_lines or chapters:
                flush()
            elif not chapters and current_lines:
                flush()
            if current_lines:
                flush()
            # flush previous content before switching title
            if chapters or current_lines:
                pass
            flush_pending = True
            if any(current_lines) or (chapters and current_title != m.group(2)):
                if current_lines:
                    flush()
            current_title = m.group(2).strip()
        else:
            current_lines.append(line)
    if current_lines:
        flush()
    for i, ch in enumerate(chapters, start=1):
        ch["chapter_id"] = str(i)
    return chapters
```

Implementers should write a clean heading splitter (do not copy the messy sketch above literally). Correct algorithm:

```python
def split_chapters(markdown: str) -> list[dict]:
    heading_re = re.compile(r"^(#{1,3})\s+(.*)$")
    chapters: list[dict] = []
    title = None
    buf: list[str] = []

    def flush():
        nonlocal title, buf
        if title is None and not any(x.strip() for x in buf):
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
        m = heading_re.match(line.strip())
        if m:
            flush()
            title = m.group(2).strip()
            buf = []
        else:
            buf.append(line)
    flush()
    return chapters
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/test_summary_tree.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/car_deepagent/tools/documents.py tests/test_summary_tree.py
git commit -m "feat: lazy summary tree and chapter excerpt tools"
```

---

### Task 5: `estimate_tokens` tool

**Files:**
- Create: `src/car_deepagent/tools/tokens.py`
- Create: `tests/test_tokens.py`

**Interfaces:**
- Produces: `@tool estimate_tokens(text: str) -> str` JSON `{"tokens": int, "method": "tiktoken"|"char_div_4"}`

- [ ] **Step 1: Write failing test**

```python
# tests/test_tokens.py
import json

from car_deepagent.tools.tokens import estimate_tokens


def test_estimate_tokens_positive():
    raw = estimate_tokens.invoke({"text": "你好，鸿蒙智行访谈。" * 10})
    data = json.loads(raw)
    assert data["tokens"] > 0
    assert data["method"] in {"tiktoken", "char_div_4"}
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement**

```python
# src/car_deepagent/tools/tokens.py
from __future__ import annotations

import json

from langchain_core.tools import tool


def _count(text: str) -> tuple[int, str]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text)), "tiktoken"
    except Exception:  # noqa: BLE001
        return max(1, len(text) // 4), "char_div_4"


@tool
def estimate_tokens(text: str) -> str:
    """Estimate token count for a text blob to decide whether to compact context."""
    tokens, method = _count(text or "")
    return json.dumps({"tokens": tokens, "method": method}, ensure_ascii=False)
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/car_deepagent/tools/tokens.py tests/test_tokens.py
git commit -m "feat: add estimate_tokens tool"
```

---

### Task 6: Generate fabricated interview Word docs

**Files:**
- Create: `scripts/generate_sample_docs.py`
- Create: `docs/interviews/interview_001.docx` (via script)
- Create: `docs/interviews/interview_002.docx`
- Create: `docs/interviews/interview_003.docx`
- Create: `tests/test_sample_docs_exist.py`

**Interfaces:**
- Script creates 3 `.docx` with Heading styles: 背景、购车旅程、座舱与HMI、智驾/NOA、服务与OTA、总结
- Map: 001→U001 陈思远, 002→U002 林婉清, 003→U003 周启明
- `interview_001` body length `>= 20000` Chinese characters
- Mark documents as 虚构样例，非真实用户数据

- [ ] **Step 1: Write existence test**

```python
# tests/test_sample_docs_exist.py
from car_deepagent.paths import interviews_dir


def test_three_interviews_exist():
    d = interviews_dir()
    for name in ("interview_001.docx", "interview_002.docx", "interview_003.docx"):
        assert (d / name).exists(), name
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement generator and run it**

`scripts/generate_sample_docs.py` should use `python-docx` `Document.add_heading` / `add_paragraph`, fabricate Q&A interview content about 鸿蒙智行 products, pad interview_001 until char count >= 20000, save under `docs/interviews/`, print counts.

Run: `python scripts/generate_sample_docs.py`  
Expected: three files written

- [ ] **Step 4: Run existence test — PASS**

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_sample_docs.py docs/interviews tests/test_sample_docs_exist.py
git commit -m "feat: add fabricated HarmonyOS interview docx samples"
```

---

### Task 7: Skills (three SKILL.md files)

**Files:**
- Create: `skills/single-report-analysis/SKILL.md`
- Create: `skills/multi-report-synthesis/SKILL.md`
- Create: `skills/user-profile-lookup/SKILL.md`
- Create: `tests/test_skills_exist.py`

**Interfaces:**
- Deep Agents loads `skills=[str(repo_root() / "skills")]`
- Each SKILL.md starts with YAML frontmatter `name` + `description`

- [ ] **Step 1: Write existence/frontmatter test**

```python
# tests/test_skills_exist.py
from car_deepagent.paths import repo_root


def test_three_skills_have_frontmatter():
    root = repo_root() / "skills"
    names = [
        "single-report-analysis",
        "multi-report-synthesis",
        "user-profile-lookup",
    ]
    for name in names:
        text = (root / name / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---")
        assert f"name: {name}" in text
        assert "description:" in text
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Write skill bodies**

`skills/single-report-analysis/SKILL.md`:
```markdown
---
name: single-report-analysis
description: Analyze one HarmonyOS interview .docx with summary-tree tools and footnote citations.
---

# Single report analysis

1. `write_todos` for plan steps.
2. `ensure_document_markdown` then `ensure_summary_tree`.
3. Prefer `task` → `report_analyst` for the heavy read.
4. Use chapter summaries first; `get_chapter_excerpt` only for evidence.
5. Final answer MUST use inline footnotes like `[^interview_001§2]` and an end section `## 参考文献摘录`.
6. Never paste the full report into the parent context.
```

`skills/multi-report-synthesis/SKILL.md`:
```markdown
---
name: multi-report-synthesis
description: Compare multiple interview reports via parallel report_analyst tasks then synthesize.
---

# Multi report synthesis

1. Todo: one item per document + final synthesis.
2. Issue multiple `task(report_analyst)` calls in one turn when possible.
3. Synthesize contrasts/agreements; keep per-doc footnotes.
4. Optionally call `get_user_profile` when user identity is known.
```

`skills/user-profile-lookup/SKILL.md`:
```markdown
---
name: user-profile-lookup
description: Load mock user CRM profile and reconcile with interview findings.
---

# User profile lookup

1. Extract user_id or name from query/report.
2. Call `get_user_profile`.
3. If found, cross-check vehicle/stage/ads claims vs report.
4. If not found, continue with report-only and state the miss.
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add skills tests/test_skills_exist.py
git commit -m "feat: add three analysis skills"
```

---

### Task 8: `report_analyst` sub-agent + main `graph`

**Files:**
- Create: `src/car_deepagent/subagents/__init__.py`
- Create: `src/car_deepagent/subagents/report_analyst.py`
- Create: `src/car_deepagent/graph.py`
- Create: `tests/test_graph_builds.py`

**Interfaces:**
- Produces: `build_graph()`, `get_graph()`, module `graph` for Runtime import
- Sub-agent name: `report_analyst`
- Main tools: `get_user_profile`, document tools, `estimate_tokens`
- Sub-agent tools: document tools + `estimate_tokens` (no user profile required)
- Disable default GP via `HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False))` registered under model id keys
- `skills=[str(repo_root() / "skills")]`

- [ ] **Step 1: Write graph build test (no live LLM)**

```python
# tests/test_graph_builds.py
from langchain_openai import ChatOpenAI

from car_deepagent import graph as graph_mod
from car_deepagent.config import Settings


def test_build_graph_returns_compiled_graph(monkeypatch):
    monkeypatch.setattr(
        graph_mod,
        "load_settings",
        lambda: Settings("k", "https://example.com/v1", "m", 60000),
    )
    monkeypatch.setattr(
        graph_mod,
        "build_chat_model",
        lambda: ChatOpenAI(model="m", api_key="k", base_url="https://example.com/v1"),
    )
    g = graph_mod.build_graph()
    assert hasattr(g, "astream")
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement subagent + graph**

```python
# src/car_deepagent/subagents/__init__.py
"""Subagent specs."""
```

```python
# src/car_deepagent/subagents/report_analyst.py
from __future__ import annotations

from car_deepagent.tools.documents import (
    ensure_document_markdown,
    ensure_summary_tree,
    get_chapter_excerpt,
    get_chapter_summary,
)
from car_deepagent.tools.tokens import estimate_tokens

REPORT_ANALYST_PROMPT = """你是单篇鸿蒙智行用户访谈分析子代理。
流程：ensure_document_markdown → ensure_summary_tree → 阅读相关章节摘要 → 必要时 get_chapter_excerpt。
输出必须包含行内脚注 [^doc_id§chapter_id]，并在末尾给出参考文献摘录。
不要把全文塞进回复；只返回结构化分析结论。
"""


def build_report_analyst_subagent() -> dict:
    return {
        "name": "report_analyst",
        "description": (
            "Analyze one interview .docx using summary-tree tools and return "
            "footnoted findings for the parent agent."
        ),
        "system_prompt": REPORT_ANALYST_PROMPT,
        "tools": [
            ensure_document_markdown,
            ensure_summary_tree,
            get_chapter_summary,
            get_chapter_excerpt,
            estimate_tokens,
        ],
    }
```

```python
# src/car_deepagent/graph.py
from __future__ import annotations

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)

from car_deepagent.config import Settings, build_chat_model, load_settings
from car_deepagent.paths import repo_root
from car_deepagent.subagents.report_analyst import build_report_analyst_subagent
from car_deepagent.tools.documents import (
    ensure_document_markdown,
    ensure_summary_tree,
    get_chapter_excerpt,
    get_chapter_summary,
)
from car_deepagent.tools.tokens import estimate_tokens
from car_deepagent.tools.user_profile import get_user_profile

MAIN_PROMPT = """你是鸿蒙智行用户调研访谈分析智能体。
能力：单篇/多篇报告分析、用户画像交叉验证、todo 规划、脚注溯源。
规则：
1. 长文必须通过 report_analyst 或摘要树工具处理，禁止把全文读进主上下文。
2. 多篇时尽量并行 task(report_analyst)。
3. 回答使用 [^doc§chapter] 脚注，并附 ## 参考文献摘录。
4. 需要用户信息时调用 get_user_profile。
5. 使用 write_todos 跟踪步骤；上下文将满时用 estimate_tokens 并依赖内置压缩。
"""


def _disable_general_purpose(settings: Settings) -> None:
    profile = HarnessProfile(
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    )
    for key in {
        "car-deepagent",
        settings.model,
        f"openai:{settings.model}",
    }:
        register_harness_profile(key, profile)


def build_graph():
    settings = load_settings()
    _disable_general_purpose(settings)
    model = build_chat_model()
    skills_dir = str(repo_root() / "skills")
    return create_deep_agent(
        model=model,
        tools=[
            get_user_profile,
            ensure_document_markdown,
            ensure_summary_tree,
            get_chapter_summary,
            get_chapter_excerpt,
            estimate_tokens,
        ],
        system_prompt=MAIN_PROMPT,
        skills=[skills_dir],
        subagents=[build_report_analyst_subagent()],
    )


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# LangGraph Runtime entry: import graph from car_deepagent.graph
try:
    graph = build_graph()
except Exception:
    graph = None
```

If installed `deepagents` uses different import paths for harness profiles, adapt imports while keeping behavior: GP disabled + only `report_analyst` sync subagent.

- [ ] **Step 4: Run unit test — expect PASS**

Run: `pytest tests/test_graph_builds.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/car_deepagent/subagents src/car_deepagent/graph.py src/car_deepagent/__init__.py tests/test_graph_builds.py
git commit -m "feat: wire create_deep_agent graph and report_analyst"
```

---

### Task 9: Smoke `astream` script + end-to-end checklist

**Files:**
- Create: `scripts/smoke_astream.py`
- Modify: `README.md`

**Interfaces:**
- CLI: `python scripts/smoke_astream.py [--mode single|multi|profile]`
- Prints streamed events; uses `thread_id` in config for multi-turn readiness

- [ ] **Step 1: Implement smoke script**

```python
# scripts/smoke_astream.py
from __future__ import annotations

import argparse
import asyncio

from car_deepagent.graph import get_graph
from car_deepagent.paths import interviews_dir


async def run(mode: str) -> None:
    graph = get_graph()
    docs = interviews_dir()
    p1 = docs / "interview_001.docx"
    p2 = docs / "interview_002.docx"
    if mode == "single":
        content = f"请分析这份访谈中用户对 NOA 的态度，并给出脚注溯源。文档：{p1}"
    elif mode == "multi":
        content = f"对比两份访谈对座舱语音的评价差异。文档：{p1} 与 {p2}"
    else:
        content = f"结合用户画像 U001，分析访谈结论是否一致。文档：{p1}"

    config = {"configurable": {"thread_id": f"smoke-{mode}"}}
    async for event in graph.astream(
        {"messages": [{"role": "user", "content": content}]},
        config=config,
        stream_mode=["updates", "messages"],
    ):
        print(event)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=["single", "multi", "profile"], default="single"
    )
    args = parser.parse_args()
    asyncio.run(run(args.mode))


if __name__ == "__main__":
    main()
```

Adapt `stream_mode` to the installed LangGraph version if needed.

- [ ] **Step 2: Run full unit suite**

Run: `pytest -v`  
Expected: all PASS

- [ ] **Step 3: Manual smoke (network + valid `.env`)**

```bash
python scripts/smoke_astream.py --mode single
python scripts/smoke_astream.py --mode multi
python scripts/smoke_astream.py --mode profile
```

Expected:
- streamed tool calls / todos / final message
- footnotes containing `[^`
- `workspace/cache/summary_trees/` created
- second single-doc run reuses summary tree cache

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_astream.py README.md
git commit -m "feat: add astream smoke script for local debugging"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Graph-only delivery + astream debug | 8, 9 |
| OpenAI-compatible `.env` | 1 |
| Mock user profiles | 2 |
| Summary tree lazy + cache | 4 |
| Inline footnote citations | 7, 8 prompts |
| Three skills | 7 |
| Doc tools / read files | 3, 4 |
| Sub-agent parallel via `task` | 8 |
| Todos built-in | 8 |
| Token estimate + built-in compact | 5, 8 |
| Fake Word interviews | 6 |
| Multi-turn thread_id | 9 |
| No frontend | honored |
| Secrets not in git | Global + Task 1 |

## Self-review notes

- No TBD placeholders remain in executable steps.
- Tool names are consistent across tasks.
- Task 3 tests must monkeypatch the same module attribute `documents` uses for cache dirs.
- Task 4 includes a corrected `split_chapters` algorithm; ignore the intermediate messy sketch.
- Task 8 allows adapting Deep Agents harness import paths to the installed version without changing tool contracts.

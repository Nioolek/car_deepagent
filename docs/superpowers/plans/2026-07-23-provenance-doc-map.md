# Provenance Doc Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace chapter summary trees with `inspect_document` size routing plus a `report_analyst` workflow that returns line-numbered provenance maps aligned with deepagents `read_file` (1-based cat -n).

**Architecture:** Custom tools measure volume and persist maps under `workspace/cache/doc_maps/` (agent FS writes are denied). Main agent routes short docs to direct `read_file`/`grep` and long docs to `task(report_analyst)`. Subagent paginates markdown, returns sections/highlights/findings with `§L` footnotes, then `save_doc_map`.

**Tech Stack:** Python 3.11+, pytest, deepagents FilesystemBackend, existing `ensure_document_markdown` / `AnalysisDocPathsMiddleware`.

## Global Constraints

- Delegate when `lines > 500` OR `chars > 15000`; else `direct_read`.
- Provenance line numbers are **1-based** and must match `read_file` display; drill-down uses `offset = start_line - 1`.
- Remove `ensure_summary_tree` / `get_chapter_summary` / heading split as the main path.
- Persist maps via custom tools (not agent `write_file`).
- Do not commit `.env` or secrets.
- TDD per task; skip git commit steps unless the user asked to commit.

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/car_deepagent/paths.py` | Add `doc_maps_dir()`; keep or deprecate `summary_trees_dir` |
| `src/car_deepagent/tools/documents.py` | Volume helpers, `inspect_document`, map save/load; delete chapter-tree tools |
| `src/car_deepagent/fs_permissions.py` | Allow `/workspace/cache/doc_maps/**`; drop summary_trees requirement |
| `src/car_deepagent/middleware/analysis_docs.py` | Guard inspect/map tools; doc_maps read paths; drop summary-tree guards |
| `src/car_deepagent/subagents/report_analyst.py` | New workflow prompt + tools |
| `src/car_deepagent/graph.py` | Wire tools + MAIN_PROMPT line footnotes / routing |
| `skills/*/SKILL.md` | Line-map routing + `§L` citations |
| `agent-chat-ui/src/lib/tool-labels.ts` | Chinese labels for new tools |
| `tests/test_inspect_document.py` | Volume + recommendation |
| `tests/test_doc_map.py` | save/load sha cache |
| `tests/test_summary_tree.py` | Delete or replace (no chapter tree) |
| `README.md` | Brief citation / routing note |

---

### Task 1: Volume helpers + `inspect_document`

**Files:**
- Modify: `src/car_deepagent/tools/documents.py`
- Modify: `src/car_deepagent/paths.py` (only if needed for markdown resolve)
- Create: `tests/test_inspect_document.py`

**Interfaces:**
- Produces:
  - `MAX_LINES_DIRECT = 500`, `MAX_CHARS_DIRECT = 15000`
  - `count_text_volume(text: str) -> dict` with keys `lines`, `chars`, `chars_cjk`, `chars_latin`, `chars_other`
  - `recommendation_for_volume(lines: int, chars: int) -> Literal["direct_read", "delegate"]`
  - `@tool inspect_document(path: str) -> str` JSON

- [ ] **Step 1: Write failing tests**

Create `tests/test_inspect_document.py`:

```python
import json

from car_deepagent.tools import documents as docs


def test_count_text_volume_lines_and_scripts():
    text = "Hello 你好\nWorld\n"
    vol = docs.count_text_volume(text)
    assert vol["lines"] == 2  # splitlines drops trailing empty after final \n? 
    # Use text without trailing-only empty: "Hello 你好\nWorld" -> 2 lines
    vol = docs.count_text_volume("Hello 你好\nWorld")
    assert vol["lines"] == 2
    assert vol["chars"] == len("Hello 你好\nWorld")
    assert vol["chars_latin"] == len("HelloWorld")
    assert vol["chars_cjk"] == 2  # 你 好
    assert vol["chars_other"] == vol["chars"] - vol["chars_latin"] - vol["chars_cjk"]


def test_recommendation_thresholds():
    assert docs.recommendation_for_volume(10, 100) == "direct_read"
    assert docs.recommendation_for_volume(501, 100) == "delegate"
    assert docs.recommendation_for_volume(10, 15001) == "delegate"


def test_inspect_document_on_cached_markdown(tmp_path, monkeypatch):
    md_dir = tmp_path / "md"
    md_dir.mkdir()
    monkeypatch.setattr(docs, "markdown_cache_dir", lambda: md_dir)
    (md_dir / "interview_t.md").write_text("短文\n第二行\n", encoding="utf-8")

    raw = docs.inspect_document.invoke({"path": "interview_t"})
    data = json.loads(raw)
    assert data["doc_id"] == "interview_t"
    assert data["lines"] == 2
    assert data["recommendation"] == "direct_read"
    assert data["markdown_path"].endswith("interview_t.md")
    assert data["thresholds"]["max_lines_direct"] == 500
```

Note: If `inspect_document` resolves via `resolve_interview_file` only, prefer accepting bare `doc_id` when markdown cache exists (see Step 3). Tests should match the chosen resolve rule.

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd /home/admin/car_deepagent && .venv/bin/pytest tests/test_inspect_document.py -v
```

Expected: import/attribute errors for missing symbols.

- [ ] **Step 3: Implement**

In `documents.py`:

```python
MAX_LINES_DIRECT = 500
MAX_CHARS_DIRECT = 15000
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_LATIN_RE = re.compile(r"[A-Za-z]")


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


def _resolve_markdown_for_inspect(path: str) -> tuple[str, Path] | tuple[None, None]:
    """Return (doc_id, markdown_path) from interview path/stem or existing cache."""
    # 1) If markdown_cache_dir()/f"{stem}.md" exists for sanitized stem, use it
    # 2) Else resolve_interview_file + ensure cache exists (require md already, or call ensure logic)
    ...


@tool
def inspect_document(path: str) -> str:
    """Measure markdown volume and recommend direct_read vs delegate."""
    ...
```

Resolve rules (locked for implementer):

1. Strip path; take stem as candidate `doc_id` if `_DOC_ID_RE` matches.
2. If `markdown_cache_dir() / f"{doc_id}.md"` exists → use it.
3. Else `resolve_interview_file(path)`; if found, `doc_id = stem`, require markdown cache file (if missing return error asking to call `ensure_document_markdown` first).

Return JSON including `thresholds`.

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd /home/admin/car_deepagent && .venv/bin/pytest tests/test_inspect_document.py -v
```

- [ ] **Step 5: Commit** (only if user asked)

---

### Task 2: `save_doc_map` / `load_doc_map`

**Files:**
- Modify: `src/car_deepagent/paths.py`
- Modify: `src/car_deepagent/tools/documents.py`
- Create: `tests/test_doc_map.py`

**Interfaces:**
- Consumes: `count_text_volume` / markdown cache from Task 1
- Produces:
  - `doc_maps_dir() -> Path`
  - `@tool save_doc_map(doc_id: str, map_json: str) -> str`
  - `@tool load_doc_map(doc_id: str) -> str`
  - Cached payload includes `markdown_sha256`, `sections`, `highlights` (not request-specific `findings`)

- [ ] **Step 1: Failing tests**

```python
import json
import hashlib

from car_deepagent.tools import documents as docs


def test_save_and_load_doc_map_roundtrip(tmp_path, monkeypatch):
    md = tmp_path / "md"
    maps = tmp_path / "maps"
    md.mkdir(); maps.mkdir()
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
    md = tmp_path / "md"; maps = tmp_path / "maps"
    md.mkdir(); maps.mkdir()
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
```

For stale miss, prefer JSON `{"cached": false, "stale": true, "doc_id": ...}` (no error) so the subagent continues.

- [ ] **Step 2: Run — expect FAIL**

```bash
.venv/bin/pytest tests/test_doc_map.py -v
```

- [ ] **Step 3: Implement**

`paths.py`:

```python
def doc_maps_dir() -> Path:
    path = cache_dir() / "doc_maps"
    path.mkdir(parents=True, exist_ok=True)
    return path
```

`documents.py`: validate `doc_id`; read markdown; sha256; write `{doc_id}.json` with `markdown_sha256` + sections/highlights stripped of findings; load compares sha.

- [ ] **Step 4: Run — expect PASS**

```bash
.venv/bin/pytest tests/test_doc_map.py tests/test_inspect_document.py -v
```

- [ ] **Step 5: Commit** (if requested)

---

### Task 3: Remove chapter summary tree tools

**Files:**
- Modify: `src/car_deepagent/tools/documents.py` (delete tree tools/helpers)
- Delete or rewrite: `tests/test_summary_tree.py`
- Modify: `tests/test_fs_permissions.py` if it asserts summary_trees
- Modify: `src/car_deepagent/fs_permissions.py`

**Interfaces:**
- Removes: `ensure_summary_tree`, `get_chapter_summary`, `split_chapters`, `_summarize_chapter`, `_tree_path`
- Keep: `ensure_document_markdown`, `inspect_document`, map tools, `doc_id_for_path`

- [ ] **Step 1: Update fs permissions tests first (fail on missing doc_maps)**

In `fs_permissions.py`:

```python
ALLOWED_READ_GLOBS = (
    "/skills/**",
    "/docs/interviews/**",
    "/workspace/cache/markdown/**",
    "/workspace/cache/doc_maps/**",
)
```

Remove `/workspace/cache/summary_trees/**` from the required allowlist (optional: leave directory helper unused).

Update `tests/test_fs_permissions.py` expectations accordingly.

- [ ] **Step 2: Delete chapter APIs from `documents.py`; replace `test_summary_tree.py`**

Keep `test_split_chapters` **only if** `split_chapters` remains — prefer delete both.

New `tests/test_summary_tree.py` can be deleted; move any still-needed markdown ensure tests to `test_documents_markdown.py`.

- [ ] **Step 3: Fix compile errors in graph/subagent imports temporarily by removing imports in same PR task** (or Task 4 immediately after). Prefer doing graph wiring in Task 4 the same session so the package imports.

Minimal stub avoidance: Task 3 ends with documents.py clean; Task 4 must land before full pytest.

- [ ] **Step 4: Run**

```bash
.venv/bin/pytest tests/test_inspect_document.py tests/test_doc_map.py tests/test_fs_permissions.py tests/test_documents_markdown.py -v
```

- [ ] **Step 5: Commit** (if requested)

---

### Task 4: Wire graph, subagent, middleware, skills, UI labels

**Files:**
- Modify: `src/car_deepagent/graph.py`
- Modify: `src/car_deepagent/subagents/report_analyst.py`
- Modify: `src/car_deepagent/middleware/analysis_docs.py`
- Modify: `skills/single-report-analysis/SKILL.md`
- Modify: `skills/multi-report-synthesis/SKILL.md` (footnotes only if needed)
- Modify: `agent-chat-ui/src/lib/tool-labels.ts`
- Modify: `tests/test_analysis_docs_middleware.py`
- Modify: `tests/test_skills_exist.py` if MAIN_PROMPT assertions mention old rules
- Modify: `README.md` (short citation note)

**Interfaces:**
- Main tools: `get_user_profile`, `ensure_document_markdown`, `inspect_document`, `load_doc_map`, `save_doc_map`, `estimate_tokens`
- Subagent tools: same doc tools + `estimate_tokens` (filesystem `read_file`/`grep` via middleware)
- Middleware doc-id tools: `inspect_document`, `load_doc_map`, `save_doc_map` (path/doc_id extraction as appropriate)

- [ ] **Step 1: Failing middleware tests for doc_maps / inspect**

Add tests:

- block `read_file` on `/workspace/cache/doc_maps/other.json` when picker selects interview_001
- allow `inspect_document` for allowed doc_id
- deny `inspect_document` / `load_doc_map` for other doc_id

Update `_DOC_ID_TOOLS` / path guards; replace `_SUMMARY_TREE_RE` with `_DOC_MAP_RE = r"^/workspace/cache/doc_maps/([^/]+)\.json$"`.

Instruction block: mention `inspect_document` + line map + `§L` footnotes; remove summary-tree wording.

- [ ] **Step 2: Implement middleware + run those tests**

- [ ] **Step 3: Rewrite `report_analyst.py`**

```python
REPORT_ANALYST_PROMPT = """你是单篇访谈文档分析子代理（无结构 markdown 友好）。
Workflow（必须按序）：
1. ensure_document_markdown（如尚未转换）→ inspect_document → load_doc_map。
2. 若 load_doc_map.cached=true：基于地图回答用户问题；需要原文时用 read_file(offset=行号-1, limit=...) 或 grep。
3. 若无缓存：用 read_file 分页阅读（limit=150~200），自建 sections（start_line/end_line 为 read_file 显示的 1-based 行号）与 highlights。
4. findings 使用脚注 [^doc_id§L123] 或 [^doc_id§L100-L150]，并给 references 摘录。
5. save_doc_map 只保存 sections+highlights（不要把整份 findings 塞进缓存）。
6. 最终回复必须是一个 JSON 对象，字段：doc_id, markdown_path, sections, highlights, findings, references。
禁止把全文一次性读进回复。
"""
```

Tools list: `ensure_document_markdown`, `inspect_document`, `load_doc_map`, `save_doc_map`, `estimate_tokens`, middleware `[AnalysisDocPathsMiddleware()]`.

- [ ] **Step 4: Update `MAIN_PROMPT` in `graph.py`**

Routing rules:

1. FS allowlist includes doc_maps / markdown / skills / interviews (no summary_trees).
2. `ensure_document_markdown` → `inspect_document`；`direct_read` 可分页 read_file；`delegate` 必须 `task(report_analyst)`，禁止主 agent 通读长文。
3. 脚注 `[^doc§L…]` + `## 参考文献摘录`。
4. Parallel tasks for multi-doc.
5. profile / todos / estimate_tokens as before.

Register tools: drop summary tree; add inspect + maps.

- [ ] **Step 5: Update skills + tool-labels + README**

`single-report-analysis` instructions:

1. todos  
2. ensure markdown → inspect  
3. direct_read vs task(report_analyst)  
4. drill-down with read_file/grep using map lines  
5. `[^doc§L…]` footnotes  

Remove chapter excerpt / summary-tree language.

Labels:

```ts
inspect_document: "检查文档体量",
load_doc_map: "加载文档地图",
save_doc_map: "保存文档地图",
```

Remove chapter summary/excerpt labels if still present.

- [ ] **Step 6: Fix `test_skills_exist` / `test_main_prompt_*` if they assert old strings**

- [ ] **Step 7: Full related pytest**

```bash
cd /home/admin/car_deepagent && .venv/bin/pytest -q
```

Expected: all green.

- [ ] **Step 8: Commit** (if requested)

---

### Task 5: Line-number alignment smoke (unit)

**Files:**
- Create: `tests/test_read_file_line_alignment.py` (optional but recommended)

- [ ] **Step 1: Test**

Using FilesystemBackend + markdown under repo virtual path `/workspace/cache/markdown/...` OR tmp mapped via monkeypatch if backend root is repo:

```python
def test_offset_math_matches_cat_n_labels():
    # Write a known file under workspace/cache/markdown in repo or use backend read formatting helper
    from deepagents.backends.utils import format_content_with_line_numbers  # if exported
    # OR call backend.read + middleware formatter
    start_line, end_line = 3, 5
    offset = start_line - 1
    limit = end_line - start_line + 1
    assert offset == 2 and limit == 3
```

Prefer calling real `FilesystemBackend.read` + `format_content_with_line_numbers` from deepagents to assert first displayed number equals `start_line`.

- [ ] **Step 2: PASS**

- [ ] **Step 3: Commit** (if requested)

---

## Spec coverage checklist

| Spec item | Task |
|---|---|
| `inspect_document` volume + recommendation | 1 |
| Thresholds 500 / 15000 | 1 |
| `save_doc_map` / `load_doc_map` + sha | 2 |
| Remove chapter tree tools | 3 |
| FS allow doc_maps | 3 |
| Routing prompts / skills / §L citations | 4 |
| Subagent workflow + JSON return | 4 |
| Middleware guards | 4 |
| Line alignment with read_file | 5 |

## Self-review notes

- No TBD steps; stale map returns `cached: false` + `stale: true`.
- `chars_latin` = ASCII `A-Za-z` only; `chars_cjk` = `\u4e00-\u9fff` + `\u3400-\u4dbf`.
- Findings are request-specific and not required in saved map.

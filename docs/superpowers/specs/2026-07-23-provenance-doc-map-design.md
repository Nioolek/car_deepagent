# Provenance Doc Map via Subagent Workflow

Date: 2026-07-23  
Status: Approved for implementation planning  
Related: `2026-07-22-car-deepagent-design.md`, `2026-07-23-skills-format-and-prompt-design.md`

## 1. Goal

Replace heading-based chapter summary trees with a **size-aware routing + subagent workflow** that:

1. Inspects document volume (lines, total chars, CJK chars, Latin chars).
2. Lets the **main agent read short docs directly**.
3. Delegates **long unstructured markdown** to a subagent that builds a **line-numbered provenance map**.
4. Lets the main agent drill down with `read_file` (line pagination) or `grep`, using map line numbers that match deepagents’ `read_file` display.

## 2. Decisions (locked)

| Topic | Choice |
|---|---|
| Document shape | Mostly **unstructured `.md`** (no reliable heading structure) |
| Long-doc strategy | Subagent **workflow** (paginate → analyze → structured return), not programmatic fixed chunking as the primary path |
| Old chapter tree | **A — replace**: remove `ensure_summary_tree` / `get_chapter_summary` / heading split as the main path |
| Size gate (default) | `delegate` if `lines > 500` **OR** `chars > 15000`; else `direct_read` |
| Line numbers | Must match deepagents `read_file` **1-based cat -n** labels (`offset` is 0-based; display line = `offset + 1`) |
| Search | Reuse built-in `grep` on cached markdown; no new search engine |

## 3. deepagents `read_file` line semantics (constraint)

- Tool docs: results use **cat -n** format; line numbers start at **1**.
- API: `offset` is **0-indexed** line start; `limit` is max **lines**.
- Formatting: `format_content_with_line_numbers(..., start_line=offset + 1)`.

All provenance fields (`start_line`, `end_line`, `highlights[].line`) are **1-based** and must equal the numbers the model sees in `read_file` output.

Main-agent drill-down:

```text
read_file(file_path=..., offset=start_line - 1, limit=end_line - start_line + 1)
```

## 4. Tools

### 4.1 Keep

- `ensure_document_markdown(path)` — docx → cached `/workspace/cache/markdown/<doc_id>.md` (virtual path under backend).
- `estimate_tokens` — unchanged.
- Built-in `read_file`, `grep`, `ls`, `glob`, `task`.

### 4.2 Add: `inspect_document`

Input: `path` or `doc_id` (resolve via existing interview / markdown cache rules).

Output JSON example:

```json
{
  "doc_id": "interview_001",
  "markdown_path": "/workspace/cache/markdown/interview_001.md",
  "lines": 12040,
  "chars": 186000,
  "chars_cjk": 120000,
  "chars_latin": 40000,
  "chars_other": 26000,
  "recommendation": "delegate",
  "thresholds": {"max_lines_direct": 500, "max_chars_direct": 15000}
}
```

Counting rules:

- `lines`: number of lines after `splitlines()` (empty file → 0).
- `chars`: `len(text)`.
- `chars_cjk`: Unicode letters in CJK ranges (approx. `\u4e00-\u9fff` plus common CJK extension blocks used in interviews; document exact set in code comments).
- `chars_latin`: ASCII letters `A-Za-z` count (or Unicode Latin letters — pick one and test it).
- `recommendation`: `direct_read` | `delegate` from thresholds above.

Also enrich `ensure_document_markdown` return to include the same volume fields when convenient (optional; `inspect_document` is the source of truth for routing).

### 4.3 Remove

- `ensure_summary_tree`
- `get_chapter_summary`
- `split_chapters` / `_summarize_chapter` / `_tree_path` (unless a tiny helper remains unused — prefer delete)
- `workspace/cache/summary_trees/` as the active cache (may leave dir empty; new cache under `doc_maps/`)

### 4.4 Optional cache: doc map

Path: `/workspace/cache/doc_maps/<doc_id>.json`  
Key: `markdown_sha256`. On hit, subagent (or a thin `ensure_doc_map` helper) may return cached map without re-reading. V1 may implement cache write from subagent via `write_file` **or** a small `save_doc_map` tool; prefer a dedicated `ensure_doc_map` / `save_doc_map` only if write permissions block agent writes (current FS deny-all writes → **need a custom tool to persist maps**).

**Locked for V1:** add `save_doc_map(doc_id, map_json)` and optionally `load_doc_map(doc_id)` that read/write under `workspace/cache/doc_maps/` with sha validation — because filesystem writes are denied for the agent.

## 5. Routing (prompts + skills)

Main agent / skills:

1. `ensure_document_markdown` if needed.
2. `inspect_document`.
3. If `direct_read` → paginated `read_file` / `grep` as needed; answer with line footnotes.
4. If `delegate` → `task(report_analyst)` with the user question + `doc_id` / markdown path; **do not** load the full long file into the parent context.
5. After map returns → selective `read_file` / `grep` for evidence; preserve footnotes.

Update `AnalysisDocPathsMiddleware` to guard `inspect_document` / `save_doc_map` / `load_doc_map` like other doc tools; drop summary-tree path guards; allow `/workspace/cache/doc_maps/<allowed>.json`.

## 6. Subagent workflow (`report_analyst`)

Rewrite system prompt as an imperative workflow:

1. Confirm markdown path; call `load_doc_map` — if valid cache hit for current sha, return it (plus findings for the user question).
2. Else `inspect_document` (sanity).
3. Paginate `read_file` (e.g. `limit=150`–`200`) covering the file; build sections as you go. Prefer semantic boundaries (blank lines / topic shifts) when obvious; otherwise ~100–150 line windows with slight overlap noted in adjacent sections.
4. Record **highlights** with exact 1-based line numbers for quotable claims.
5. Answer the user question in `findings` with footnotes `[^doc_id§L123]` or `[^doc_id§L100-L150]`.
6. `save_doc_map` with the map payload (without necessarily duplicating long findings if map is reused later — store `sections` + `highlights`; findings may be request-specific and returned only in the task result).

### 6.1 Required return shape (task result)

```json
{
  "doc_id": "interview_001",
  "markdown_path": "/workspace/cache/markdown/interview_001.md",
  "sections": [
    {
      "start_line": 1,
      "end_line": 120,
      "topic": "购车动机与决策",
      "summary": "……"
    }
  ],
  "highlights": [
    {"line": 842, "note": "雨天 NOA 会主动接管"}
  ],
  "findings": [
    "受访者对雨天 NOA 偏谨慎[^interview_001§L842]。"
  ],
  "references": [
    {
      "key": "[^interview_001§L842]",
      "excerpt": "……",
      "lines": "L842"
    }
  ]
}
```

## 7. Citation format (update)

Inline: `[^interview_001§L842]` or `[^interview_001§L100-L150]`  

End matter `## 参考文献摘录` must include short excerpts with line range.

Deprecate `§chapter_id` in skills / prompts / README.

## 8. FS permissions

- Keep `/workspace/cache/markdown/**`
- Add `/workspace/cache/doc_maps/**` (read allow for agent; writes only via custom save tool bypassing deny, same pattern as other custom tools)
- Remove or stop requiring `/workspace/cache/summary_trees/**` in allowlist (can leave for backward compatibility empty)

## 9. Tests

- `inspect_document` counts lines/chars/cjk/latin; recommendation thresholds.
- Middleware: picker blocks other docs’ maps/markdown; allows skills.
- Subagent prompt / tool list no longer references summary tree tools.
- Citation / skill docs mention line footnotes.
- Remove or rewrite `test_summary_tree.py` into doc-map / inspect tests.
- Optional: unit test that `read_file` line labels align with map math (`offset = L - 1`).

## 10. Non-goals

- Building a vector index or new search service.
- Requiring headings in interview markdown.
- Auto-injecting full markdown into the system prompt.
- Perfect linguistic sentence segmentation (best-effort windows OK).

## 11. Success criteria

1. Short docs: main agent can answer without `task`.
2. Long docs: parent does not ingest full text; receives a line map + findings.
3. Drill-down `read_file` line numbers match map and tool output.
4. Old chapter summary tools gone from graph/subagent registrations.
5. Relevant unit tests green.

# Markdown-Only Interview Sources

Date: 2026-07-23  
Status: Approved for implementation planning  
Related: `2026-07-23-provenance-doc-map-design.md`, `2026-07-22-car-deepagent-design.md`

## 1. Goal

Switch interview **source of truth** from Word (`.docx` → cached markdown) to **native Markdown** under `docs/interviews/*.md`. Agents analyze these files directly; remove docx conversion and the `python-docx` dependency.

## 2. Decisions (locked)

| Topic | Choice |
|---|---|
| Input format | **A — Markdown only** (no docx support) |
| Storage | Source files live at `docs/interviews/<doc_id>.md` |
| Cache markdown copy | **Not required** — read `/docs/interviews/<doc_id>.md` directly (virtual path) |
| Doc maps | Keep `workspace/cache/doc_maps/<doc_id>.json` keyed by `doc_id` + **source file** `sha256` |
| Conversion tool | **Remove** `ensure_document_markdown`, `_docx_to_markdown`, related meta files under `workspace/cache/markdown/` as the active pipeline |

## 3. Behavior after change

### 3.1 Resolve / list

- `list_interview_*` / UI API: glob `docs/interviews/*.md` (not `.docx`).
- `resolve_interview_file` (rename conceptually to interview markdown resolve): accept repo-relative path, bare filename, or stem → absolute `.md` under `docs/interviews/` only.
- `normalize_doc_path` → `docs/interviews/<stem>.md`.
- `allowed_doc_ids` unchanged (stems).

### 3.2 Tools

| Tool | Change |
|---|---|
| `inspect_document` | Resolve to interviews `.md`; volume stats from that file; `markdown_path` field may be renamed to `source_path` **or** keep key `markdown_path` as the virtual posix path for compatibility (prefer keep key name `markdown_path` meaning “text source path” OR add `source_path` and keep both — **prefer** return `source_path: "/docs/interviews/<id>.md"` and deprecate cache path). |
| `load_doc_map` / `save_doc_map` | Hash the interviews `.md` content (not cache copy). |
| `ensure_document_markdown` | **Delete**. |

Prompts / skills / subagent: drop “ensure_document_markdown first”; start with `inspect_document` on the interview path/stem.

### 3.3 Filesystem + middleware

- Keep allow-read: `/docs/interviews/**`, `/workspace/cache/doc_maps/**`, `/skills/**`.
- `/workspace/cache/markdown/**` may remain allowlisted for backward-compat empty dir, or be removed from allowlist if unused — **prefer remove** from `ALLOWED_READ_GLOBS` once nothing reads it.
- Picker guards: treat `/docs/interviews/<id>.md` as the primary content path (already partially guarded); stop requiring `/workspace/cache/markdown/` for analysis.

### 3.4 Frontend

- `api/files/interviews`: list `*.md`.
- Interview picker / file-path helpers: `.md` extension and labels.
- Preview allowlist: interview `.md` under `docs/interviews`.

### 3.5 Sample data & scripts

- Replace sample `.docx` generation with writing `.md` fixtures under `docs/interviews/`.
- Update `scripts/generate_sample_docs.py`, `scripts/smoke_astream.py`, `tests/test_sample_docs_exist.py`.

### 3.6 Dependencies

- Remove `python-docx` from `pyproject.toml` (and lockfile when refreshing).

## 4. Migration notes

- Existing `workspace/cache/markdown/*` and `.md.meta.json` are obsolete; safe to ignore or delete locally (not required in git).
- Any UI threads storing `analysis_doc_paths` with `.docx` need re-selection as `.md`.
- Cite paths in footnotes/docs as `docs/interviews/<id>.md`.

## 5. Tests

- Resolve/list only `.md`; reject `.docx`.
- `inspect_document` / maps keyed off interviews md sha.
- Middleware picker with `docs/interviews/interview_001.md`.
- No imports of `docx` / `ensure_document_markdown`.
- UI unit/route tests if present for extension filter.

## 6. Non-goals

- Supporting both docx and md.
- Building a second copy under `workspace/cache/markdown/` for analysis.
- Changing provenance map JSON shape beyond source path / sha input file.

## 7. Success criteria

1. End-to-end path: select `docs/interviews/*.md` → `inspect_document` → direct_read or `report_analyst` → `§L` citations without any docx step.
2. `python-docx` not required to install/run the agent.
3. Relevant unit tests green.

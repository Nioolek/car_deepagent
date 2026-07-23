---
name: single-report-analysis
description: Analyze a single HarmonyOS Intelligent Mobility (鸿蒙智行) user interview Word report (.docx). Use when the user asks about one interview document, one doc path, NOA/智驾/座舱态度, 单篇报告分析, or footnote-cited findings from a single report.
license: MIT
metadata:
  version: "1.0"
  domain: interview-analysis
---

# Single report analysis

## When to Use

- User provides **one** `.docx` interview path
- Questions about a single interviewee's attitudes (NOA, 座舱, OTA, NPS, etc.)
- Requests for footnoted analysis of one report

## Instructions

1. Call `write_todos` to plan steps.
2. `ensure_document_markdown` then `ensure_summary_tree` for the document.
3. Prefer `task` → `report_analyst` for heavy reading so the parent context stays small.
4. Use chapter summaries first; for citation evidence use `read_file` on `/workspace/cache/markdown/<doc_id>.md` with line `offset`/`limit` (do not paste the full report).
5. Final answer MUST include inline footnotes like `[^interview_001§2]` and an end section `## 参考文献摘录`.
6. Never paste the full report into the parent context.

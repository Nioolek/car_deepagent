---
name: single-report-analysis
description: Analyze a single HarmonyOS Intelligent Mobility (鸿蒙智行) user interview markdown report (.md). Use when the user asks about one interview document, one doc path, NOA/智驾/座舱态度, 单篇报告分析, or footnote-cited findings from a single report.
license: MIT
metadata:
  version: "1.0"
  domain: interview-analysis
---

# Single report analysis

## When to Use

- User provides **one** `.md` interview path under `docs/interviews/`
- Questions about a single interviewee's attitudes (NOA, 座舱, OTA, NPS, etc.)
- Requests for footnoted analysis of one report

## Instructions

1. Call `write_todos` to plan steps.
2. Call `inspect_document` on the interview path or stem.
3. If inspection recommends `direct_read`, paginate with `read_file`; if it recommends `delegate`, call `task(report_analyst)` and do not read the long document in the parent context. Instruct the subagent to `read_file(..., offset=0, limit=50000)` once (full file).
4. Drill down with `read_file` or `grep` on `/docs/interviews/<doc_id>.md`, using line ranges from the document map (do not paste the full report).
5. Final answer MUST include inline footnotes exactly like `[^interview_001§L123]` or `[^interview_001§L100-L150]` (no extra text inside the brackets) and an end section `## 参考文献摘录`. If you used `task(report_analyst)`, rewrite its findings/references into that final answer (keep line footnotes); do not end with only a wrap-up paragraph.
6. Never paste the full report into the parent context.

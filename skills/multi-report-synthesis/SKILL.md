---
name: multi-report-synthesis
description: Compare and synthesize multiple HarmonyOS interview reports. Use when the user provides two or more .md paths, asks to 对比/综合/差异分析 across interviews, or wants a multi-document synthesis with per-doc footnotes.
license: MIT
metadata:
  version: "1.0"
  domain: interview-analysis
---

# Multi report synthesis

## When to Use

- User provides **two or more** interview `.md` paths
- Asks to compare (对比), synthesize (综合), or find differences across reports
- Wants cross-interview themes with citations

## Instructions

1. `write_todos`: one item per document + a final synthesis step.
2. For **each** document, call `inspect_document`.
3. Follow each inspection recommendation: for `direct_read`, paginate with `read_file`; for `delegate`, call `task(report_analyst)` and do not read the long document in the parent context. Tell the subagent to read each assigned file once with `read_file(..., offset=0, limit=50000)`. Never delegate every document without inspecting it first.
4. When multiple documents recommend `delegate`, issue their `task(report_analyst)` calls in one turn when possible (parallel).
5. Synthesize contrasts and agreements; keep per-document line footnotes exactly as `[^doc§L123]` or `[^doc§L100-L150]` (no comma lists inside brackets).
6. Optionally call `get_user_profile` when a user identity is known.
7. End with `## 参考文献摘录` covering all cited docs.

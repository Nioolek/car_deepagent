---
name: multi-report-synthesis
description: Compare and synthesize multiple HarmonyOS interview reports. Use when the user provides two or more .docx paths, asks to 对比/综合/差异分析 across interviews, or wants a multi-document synthesis with per-doc footnotes.
license: MIT
metadata:
  version: "1.0"
  domain: interview-analysis
---

# Multi report synthesis

## When to Use

- User provides **two or more** interview `.docx` paths
- Asks to compare (对比), synthesize (综合), or find differences across reports
- Wants cross-interview themes with citations

## Instructions

1. `write_todos`: one item per document + a final synthesis step.
2. Issue multiple `task(report_analyst)` calls in one turn when possible (parallel).
3. Synthesize contrasts and agreements; keep per-document footnotes (`[^doc§chapter]`).
4. Optionally call `get_user_profile` when a user identity is known.
5. End with `## 参考文献摘录` covering all cited docs.

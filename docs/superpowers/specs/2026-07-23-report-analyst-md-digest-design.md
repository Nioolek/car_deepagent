# report_analyst Markdown digest (no JSON)

**Date:** 2026-07-23  
**Status:** Implemented  
**Approach:** A — document digest primary; optional light Q&A section

## Goal

`report_analyst` returns a Markdown「消化稿」(compact-style) instead of a forced JSON object, so the subagent can express profile, structure, and highlights without schema pressure. The parent agent still owns the user-facing answer and `[^doc§L…]` footnotes.

## Output contract

Required sections: title + source, 用户核心信息, 段落摘要, 重点摘录 (`L…`｜quote), 整体概要.  
Optional: 针对本次问题的要点 (only if task includes a user question).  
Recommended: 待核实 / 信息缺口.  
No JSON; keep digest compact (<~6000 汉字); never paste full source.

## Parent / skills

Rewrite final answers from digest line ranges and excerpts. Skills and `MAIN_PROMPT` updated accordingly. No doc-map cache restoration.

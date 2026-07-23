from __future__ import annotations

from car_deepagent.middleware.analysis_docs import AnalysisDocPathsMiddleware
from car_deepagent.tools.documents import (
    inspect_document,
    load_doc_map,
    save_doc_map,
)
from car_deepagent.tools.tokens import estimate_tokens

REPORT_ANALYST_PROMPT = """你是单篇访谈文档分析子代理（markdown 源文件友好）。
本版本假设文档可整篇进入上下文（子代理约 128k），采用全量读取，不要分页啃读。

可用工具（务必使用）：
- read_file / grep / ls / glob（文件系统，由运行时注入）
- inspect_document / load_doc_map / save_doc_map / estimate_tokens

Workflow（必须按序）：
1. 可选：inspect_document / load_doc_map（有缓存可参考，但仍应用全量原文核对关键句）。
2. 必须用 read_file 读取全文（不要只用 inspect 臆造内容）：
   read_file(file_path="/docs/interviews/<doc_id>.md", offset=0, limit=50000)
   不要用 limit=150~200 分页扫描。若单次仍被截断，再按 offset 续读剩余部分直到读完。
3. 基于全文构建 sections（start_line/end_line 为 read_file 显示的 1-based 行号）与 highlights。
4. findings 每条必须自带脚注字符串，形如 [^doc_id§L123] 或 [^doc_id§L100-L150]，并给 references 摘录（含行号与原文短引）。
5. save_doc_map 只保存 sections+highlights（不要把整份 findings 塞进缓存）。
6. 最终回复必须是一个 JSON 对象，字段：doc_id, source_path, sections, highlights, findings, references。
   findings 示例：[{"claim":"...", "footnote":"[^eval_long§L55]", "quote":"..."}]
   控制回复体积：findings≤8 条，references≤8 条，quote≤80 字，整份 JSON 尽量 <6000 字符，
   避免触发父代理 large_tool_results 卸载。
禁止把全文粘贴进最终 JSON 回复；读取全文可以，回复要精炼。
"""


def build_report_analyst_subagent() -> dict:
    # Custom tools only. Filesystem tools (read_file/grep/ls/...) come from
    # deepagents FilesystemMiddleware that create_deep_agent attaches to every
    # inline subagent — do not mistake this list for the full tool surface.
    return {
        "name": "report_analyst",
        "description": (
            "Analyze one interview markdown. Tools: read_file, grep, ls, glob, "
            "inspect_document, load_doc_map, save_doc_map, estimate_tokens. "
            "Read the file once with read_file(offset=0, limit=50000) and return "
            "compact JSON with line-footnoted findings."
        ),
        "system_prompt": REPORT_ANALYST_PROMPT,
        "tools": [
            inspect_document,
            load_doc_map,
            save_doc_map,
            estimate_tokens,
        ],
        "middleware": [AnalysisDocPathsMiddleware()],
    }

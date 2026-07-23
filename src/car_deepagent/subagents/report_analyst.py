from __future__ import annotations

from car_deepagent.middleware.analysis_docs import AnalysisDocPathsMiddleware
from car_deepagent.tools.documents import (
    inspect_document,
    load_doc_map,
    save_doc_map,
)
from car_deepagent.tools.tokens import estimate_tokens

REPORT_ANALYST_PROMPT = """你是单篇访谈文档分析子代理（markdown 源文件友好）。
Workflow（必须按序）：
1. inspect_document → load_doc_map。
2. 若 load_doc_map.cached=true：基于地图回答用户问题；需要原文时用 read_file(offset=行号-1, limit=...) 或 grep。
3. 若无缓存：用 read_file 分页阅读（limit=150~200），自建 sections（start_line/end_line 为 read_file 显示的 1-based 行号）与 highlights。
4. findings 每条必须自带脚注字符串，形如 [^doc_id§L123] 或 [^doc_id§L100-L150]，并给 references 摘录（含行号与原文短引）。
5. save_doc_map 只保存 sections+highlights（不要把整份 findings 塞进缓存）。
6. 最终回复必须是一个 JSON 对象，字段：doc_id, source_path, sections, highlights, findings, references。
   findings 示例：[{"claim":"...", "footnote":"[^eval_long§L55]", "quote":"..."}]
禁止把全文一次性读进回复。
"""


def build_report_analyst_subagent() -> dict:
    return {
        "name": "report_analyst",
        "description": (
            "Analyze one interview document with a provenance line map and return "
            "structured, line-footnoted findings for the parent agent."
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

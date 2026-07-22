from __future__ import annotations

from car_deepagent.tools.documents import (
    ensure_document_markdown,
    ensure_summary_tree,
    get_chapter_excerpt,
    get_chapter_summary,
)
from car_deepagent.tools.tokens import estimate_tokens

REPORT_ANALYST_PROMPT = """你是单篇鸿蒙智行用户访谈分析子代理。
流程：ensure_document_markdown → ensure_summary_tree → 阅读相关章节摘要 → 必要时 get_chapter_excerpt。
输出必须包含行内脚注 [^doc_id§chapter_id]，并在末尾给出参考文献摘录。
不要把全文塞进回复；只返回结构化分析结论。
"""


def build_report_analyst_subagent() -> dict:
    return {
        "name": "report_analyst",
        "description": (
            "Analyze one interview .docx using summary-tree tools and return "
            "footnoted findings for the parent agent."
        ),
        "system_prompt": REPORT_ANALYST_PROMPT,
        "tools": [
            ensure_document_markdown,
            ensure_summary_tree,
            get_chapter_summary,
            get_chapter_excerpt,
            estimate_tokens,
        ],
    }

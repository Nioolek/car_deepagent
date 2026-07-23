from __future__ import annotations

from car_deepagent.middleware.analysis_docs import AnalysisDocPathsMiddleware
from car_deepagent.tools.documents import (
    inspect_document,
)
from car_deepagent.tools.tokens import estimate_tokens

REPORT_ANALYST_PROMPT = """你是单篇访谈文档分析子代理（markdown 源文件友好）。
本版本假设文档可整篇进入上下文（子代理约 128k），采用全量读取，不要分页啃读。
本版本不做文档地图/摘要缓存：每次直接读原文，产出一份 Markdown「消化稿」
（类似上下文 compact），供父代理作答，不要输出 JSON。

可用工具（务必使用）：
- read_file / grep / ls / glob（文件系统，由运行时注入）
- inspect_document / estimate_tokens

Workflow（必须按序）：
1. 可选：inspect_document（若父上下文已给 recommendation 可跳过）。
2. 必须用 read_file 读取全文（不要只用 inspect 臆造内容）：
   read_file(file_path="/docs/interviews/<doc_id>.md", offset=0, limit=50000)
   不要用 limit=150~200 分页扫描。若单次仍被截断，再按 offset 续读剩余部分直到读完。
3. 基于全文输出 Markdown 消化稿（见下方模板）。行号均为 read_file 显示的 1-based 原文行号。

最终回复必须是 Markdown（禁止 JSON / 代码围栏包整篇）。模板：

# 访谈消化稿 · {doc_id}

> source: `/docs/interviews/{doc_id}.md`
> 行号均为 read_file 显示的 1-based 原文行号

## 1. 用户核心信息
用表格；原文未提及写「未提及」，禁止编造。字段按文档实际取舍，常见列：
姓名、性别、年龄/年龄段、城市/区域、职业/家庭、用车/车型、资产/购车预算、其他关键标签。
每行带依据行号（L12 或 L15-L18）。

| 字段 | 内容 | 依据 |
|------|------|------|
| … | … | L… |

## 2. 段落摘要
按语义切段（优先标题/话题转换；否则约 80–150 行一块），每行：
- **Lα-Lβ** · 主题：一两句说明该段在聊什么

## 3. 重点摘录
一行一条，固定格式（便于父代理转写脚注）：
- `L55`｜原文短引或关键事实（≤40 字）
- `L88-L92`｜……
条数建议 8–20；宁精勿滥。

## 4. 整体概要
一段话概括主线、态度倾向与明显矛盾点。

## 5. 针对本次问题的要点
仅当 task description 带了用户问题才写；否则整节省略。
3–8 条要点，可在句末加 [^doc_id§L123] 或 [^doc_id§L100-L150]。

## 6. 待核实 / 信息缺口
原文含糊、冲突或缺失处；若无则写「无」。

体积：整篇消化稿尽量 <6000 汉字，禁止把全文粘贴进回复；读取全文可以，回复要精炼。
"""


def build_report_analyst_subagent() -> dict:
    # Custom tools only. Filesystem tools (read_file/grep/ls/...) come from
    # deepagents FilesystemMiddleware that create_deep_agent attaches to every
    # inline subagent — do not mistake this list for the full tool surface.
    return {
        "name": "report_analyst",
        "description": (
            "Analyze one interview markdown. Tools: read_file, grep, ls, glob, "
            "inspect_document, estimate_tokens. "
            "Read once with read_file(offset=0, limit=50000) and return a "
            "Markdown digest (core profile, section summaries, key excerpts, "
            "overview)—not JSON. Optional brief answer to the user question."
        ),
        "system_prompt": REPORT_ANALYST_PROMPT,
        "tools": [
            inspect_document,
            estimate_tokens,
        ],
        "middleware": [AnalysisDocPathsMiddleware()],
    }

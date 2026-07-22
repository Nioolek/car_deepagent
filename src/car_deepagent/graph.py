from __future__ import annotations

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)

from car_deepagent.config import Settings, build_chat_model, load_settings
from car_deepagent.paths import repo_root
from car_deepagent.subagents.report_analyst import build_report_analyst_subagent
from car_deepagent.tools.documents import (
    ensure_document_markdown,
    ensure_summary_tree,
    get_chapter_excerpt,
    get_chapter_summary,
)
from car_deepagent.tools.tokens import estimate_tokens
from car_deepagent.tools.user_profile import get_user_profile

MAIN_PROMPT = """你是鸿蒙智行用户调研访谈分析智能体。
能力：单篇/多篇报告分析、用户画像交叉验证、todo 规划、脚注溯源。
规则：
1. 长文必须通过 report_analyst 或摘要树工具处理，禁止把全文读进主上下文。
2. 多篇时尽量并行 task(report_analyst)。
3. 回答使用 [^doc§chapter] 脚注，并附 ## 参考文献摘录。
4. 需要用户信息时调用 get_user_profile。
5. 使用 write_todos 跟踪步骤；上下文将满时用 estimate_tokens 并依赖内置压缩。
"""


def _disable_general_purpose(settings: Settings) -> None:
    profile = HarnessProfile(
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    )
    for key in {
        "car-deepagent",
        settings.model,
        f"openai:{settings.model}",
    }:
        register_harness_profile(key, profile)


def build_graph():
    settings = load_settings()
    _disable_general_purpose(settings)
    model = build_chat_model()
    return create_deep_agent(
        model=model,
        tools=[
            get_user_profile,
            ensure_document_markdown,
            ensure_summary_tree,
            get_chapter_summary,
            get_chapter_excerpt,
            estimate_tokens,
        ],
        system_prompt=MAIN_PROMPT,
        skills=[str(repo_root() / "skills")],
        subagents=[build_report_analyst_subagent()],
    )


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# LangGraph Runtime entry: import graph from car_deepagent.graph
try:
    graph = build_graph()
except Exception:
    graph = None

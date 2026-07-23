from __future__ import annotations

import logging

from deepagents import (
    FilesystemPermission,
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)
from deepagents.backends.filesystem import FilesystemBackend

from car_deepagent.analysis_docs import AgentContext
from car_deepagent.config import Settings, build_chat_model, load_settings
from car_deepagent.fs_permissions import build_filesystem_permissions
from car_deepagent.middleware import (
    AnalysisDocPathsMiddleware,
    SkillCommandMiddleware,
)
from car_deepagent.paths import repo_root
from car_deepagent.subagents.report_analyst import build_report_analyst_subagent
from car_deepagent.tools.documents import (
    inspect_document,
    list_interview_docs,
    load_doc_map,
    save_doc_map,
)
from car_deepagent.tools.tokens import estimate_tokens
from car_deepagent.tools.user_profile import get_user_profile

logger = logging.getLogger(__name__)

MAIN_PROMPT = """你是鸿蒙智行用户调研访谈分析智能体。
能力：单篇/多篇报告分析、用户画像交叉验证、todo 规划、脚注溯源、skills。

规则：
1. 文件系统只允许读取：/skills/**、/docs/interviews/**、/workspace/cache/doc_maps/**。
   访谈报告为 docs/interviews/*.md；可用完整路径、虚拟路径（/docs/interviews/...）、
   文件名或 stem（如 interview_001）。若运行上下文提供了 analysis_doc_paths（界面勾选），
   本轮只能分析这些路径，不要打开列表外的访谈文档。
   查找访谈文件时优先 list_interview_docs，不要用 ls/glob 在仓库根盲搜。
2. 每篇文档先判断阅读策略：若运行上下文已给出 lines/chars/recommendation，
   可跳过 inspect_document，直接按 recommendation 执行；否则先 inspect_document
   （path 可用 /docs/interviews/<id>.md 或 stem）。
   recommendation=direct_read 时可由主 agent 用 read_file 分页读取；
   recommendation=delegate 时必须调用 task(report_analyst)，禁止主 agent 通读长文。
3. 多篇文档时尽量在同一轮并行调用多个 task(report_analyst)；对比题优先加载
   multi-report-synthesis skill，不要重复加载无关 skill。
4. 最终回答必须自洽完整：内联脚注格式必须严格为 [^doc§L123] 或 [^doc_id§L100-L150]
   （括号内不要夹杂其它文字/标记名/逗号列表），并附 ## 参考文献摘录。
   多行引用只用 [^doc§L11-L16]，禁止 [^doc§L11,L14-L16] 这类写法。
   若调用了 task(report_analyst)，必须把子代理 findings/references
   转写进最终回答（保留行号脚注）。带脚注的完整正文应出现在最后一条对用户可见的回复中；
   不要在完整分析之后再追加一条不含脚注的空泛收尾。
   用户已给出明确路径时直接 inspect_document，不必先 list_interview_docs。
5. 需要用户信息时调用 get_user_profile。
6. 使用 write_todos 跟踪步骤（合并更新，避免连续多次只改 status）；
   上下文将满时用 estimate_tokens 并依赖内置压缩。
"""

SKILLS_SOURCE = ("/skills/", "Project")


def _disable_general_purpose(settings: Settings) -> None:
    profile = HarnessProfile(
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        excluded_tools=frozenset({"execute"}),
    )
    for key in {
        "car-deepagent",
        "openai",
        settings.model,
        f"openai:{settings.model}",
    }:
        register_harness_profile(key, profile)


def build_graph():
    settings = load_settings()
    _disable_general_purpose(settings)
    model = build_chat_model()
    backend = FilesystemBackend(root_dir=str(repo_root()), virtual_mode=True)
    permissions: list[FilesystemPermission] = build_filesystem_permissions()
    return create_deep_agent(
        model=model,
        tools=[
            get_user_profile,
            list_interview_docs,
            inspect_document,
            load_doc_map,
            save_doc_map,
            estimate_tokens,
        ],
        system_prompt=MAIN_PROMPT,
        skills=[SKILLS_SOURCE],
        backend=backend,
        permissions=permissions,
        context_schema=AgentContext,
        middleware=[
            SkillCommandMiddleware(backend=backend),
            AnalysisDocPathsMiddleware(),
        ],
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
    logger.exception(
        "Failed to build LangGraph graph at import; "
        "set LLM_* in .env or call get_graph() after configuring settings."
    )
    graph = None

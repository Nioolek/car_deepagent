from __future__ import annotations

import json
import re
from typing import Any, Callable

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from car_deepagent.analysis_docs import (
    allowed_doc_ids,
    extract_analysis_doc_paths,
    normalize_doc_path,
)

_DOC_PATH_TOOLS = frozenset({"ensure_document_markdown"})
_DOC_ID_TOOLS = frozenset(
    {
        "ensure_summary_tree",
        "get_chapter_summary",
    }
)
_MARKDOWN_CACHE_RE = re.compile(r"^/workspace/cache/markdown/([^/]+)\.md$")
_SUMMARY_TREE_RE = re.compile(r"^/workspace/cache/summary_trees/([^/]+)\.json$")


def _paths_from_runtime(runtime: Any) -> list[str]:
    if runtime is None:
        return []
    return extract_analysis_doc_paths(getattr(runtime, "context", None))


def _instruction_block(paths: list[str]) -> str:
    bullets = "\n".join(f"- {path}" for path in paths)
    return (
        "本轮用户已在界面选择分析文档。你必须且只能分析下列路径对应的访谈报告，"
        "不要打开或引用列表之外的访谈文件：\n"
        f"{bullets}\n"
        "调用 ensure_document_markdown 时使用上述路径；"
        "摘要树相关工具的 doc_id 必须是这些文件的文件名（不含扩展名）；"
        "用 read_file 读原文时只允许 "
        "`/workspace/cache/markdown/<上述 doc_id>.md`。"
    )


def _denied_tool_message(request: ToolCallRequest, message: str) -> ToolMessage:
    tool_call_id = ""
    if isinstance(request.tool_call, dict):
        tool_call_id = str(request.tool_call.get("id") or "")
    return ToolMessage(
        content=json.dumps({"error": message}, ensure_ascii=False),
        tool_call_id=tool_call_id,
        name=str(
            request.tool_call.get("name")
            if isinstance(request.tool_call, dict)
            else ""
        )
        or None,
    )


def _deny_read_file_if_needed(
    request: ToolCallRequest,
    paths: list[str],
    args: dict,
) -> ToolMessage | None:
    raw = args.get("file_path") or args.get("path")
    if not isinstance(raw, str) or not raw.strip():
        return _denied_tool_message(
            request,
            "本轮已选择分析文档，read_file 需要 file_path 参数。",
        )
    posix = raw.replace("\\", "/").strip()
    if posix.startswith("/skills/"):
        return None

    allowed = allowed_doc_ids(paths)
    markdown_match = _MARKDOWN_CACHE_RE.match(posix)
    if markdown_match:
        doc_id = markdown_match.group(1)
        if doc_id not in allowed:
            return _denied_tool_message(
                request,
                "markdown 不在本轮选择的分析文档列表中："
                f"{doc_id}；允许：{', '.join(sorted(allowed))}",
            )
        return None

    tree_match = _SUMMARY_TREE_RE.match(posix)
    if tree_match:
        doc_id = tree_match.group(1)
        if doc_id not in allowed:
            return _denied_tool_message(
                request,
                "summary tree 不在本轮选择的分析文档列表中："
                f"{doc_id}；允许：{', '.join(sorted(allowed))}",
            )
        return None

    if "docs/interviews/" in posix or posix.startswith("/docs/interviews/"):
        normalized = normalize_doc_path(posix)
        if normalized is None or normalized not in paths:
            return _denied_tool_message(
                request,
                "路径不在本轮选择的分析文档列表中："
                f"{raw}；允许：{', '.join(paths)}",
            )
        return None

    return None


class AnalysisDocPathsMiddleware(AgentMiddleware):
    """Inject selected interview paths into the model prompt and guard doc tools."""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        paths = _paths_from_runtime(request.runtime)
        if not paths:
            return handler(request)

        block = _instruction_block(paths)
        existing = request.system_message
        if existing is None:
            system_message = SystemMessage(content=block)
        else:
            base = existing.text if hasattr(existing, "text") else str(existing.content)
            system_message = SystemMessage(content=f"{base}\n\n{block}")

        return handler(request.override(system_message=system_message))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Any],
    ) -> ModelResponse:
        paths = _paths_from_runtime(request.runtime)
        if not paths:
            return await handler(request)

        block = _instruction_block(paths)
        existing = request.system_message
        if existing is None:
            system_message = SystemMessage(content=block)
        else:
            base = existing.text if hasattr(existing, "text") else str(existing.content)
            system_message = SystemMessage(content=f"{base}\n\n{block}")

        return await handler(request.override(system_message=system_message))

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        denied = self._deny_if_needed(request)
        if denied is not None:
            return denied
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> ToolMessage | Command:
        denied = self._deny_if_needed(request)
        if denied is not None:
            return denied
        return await handler(request)

    def _deny_if_needed(self, request: ToolCallRequest) -> ToolMessage | None:
        paths = _paths_from_runtime(getattr(request, "runtime", None))
        if not paths:
            return None

        tool_call = request.tool_call if isinstance(request.tool_call, dict) else {}
        name = str(tool_call.get("name") or "")
        args = tool_call.get("args") or {}
        if not isinstance(args, dict):
            args = {}

        if name in _DOC_PATH_TOOLS:
            raw_path = args.get("path")
            if not isinstance(raw_path, str):
                return _denied_tool_message(
                    request,
                    "本轮已选择分析文档，ensure_document_markdown 需要 path 参数。",
                )
            normalized = normalize_doc_path(raw_path)
            if normalized is None or normalized not in paths:
                return _denied_tool_message(
                    request,
                    "路径不在本轮选择的分析文档列表中："
                    f"{raw_path}；允许：{', '.join(paths)}",
                )
            return None

        if name in _DOC_ID_TOOLS:
            doc_id = args.get("doc_id")
            if not isinstance(doc_id, str):
                return _denied_tool_message(
                    request,
                    f"本轮已选择分析文档，{name} 需要 doc_id 参数。",
                )
            allowed = allowed_doc_ids(paths)
            if doc_id not in allowed:
                return _denied_tool_message(
                    request,
                    "doc_id 不在本轮选择的分析文档列表中："
                    f"{doc_id}；允许：{', '.join(sorted(allowed))}",
                )
            return None

        if name in {"read_file", "read"}:
            return _deny_read_file_if_needed(request, paths, args)

        return None

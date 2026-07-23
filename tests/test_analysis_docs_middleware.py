import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from car_deepagent.analysis_docs import AgentContext
from car_deepagent.middleware.analysis_docs import AnalysisDocPathsMiddleware


def test_wrap_model_call_noop_without_paths():
    mw = AnalysisDocPathsMiddleware()
    request = MagicMock(spec=ModelRequest)
    request.runtime = SimpleNamespace(context=AgentContext())
    request.system_message = SystemMessage(content="base")
    handler = MagicMock(return_value="ok")

    assert mw.wrap_model_call(request, handler) == "ok"
    handler.assert_called_once_with(request)
    request.override.assert_not_called()


def test_wrap_model_call_appends_instruction():
    mw = AnalysisDocPathsMiddleware()
    request = MagicMock(spec=ModelRequest)
    request.runtime = SimpleNamespace(
        context=AgentContext(
            analysis_doc_paths=["docs/interviews/interview_001.docx"],
        )
    )
    request.system_message = SystemMessage(content="base prompt")
    overridden = MagicMock(name="overridden")
    request.override.return_value = overridden
    handler = MagicMock(return_value="ok")

    assert mw.wrap_model_call(request, handler) == "ok"
    handler.assert_called_once_with(overridden)
    kwargs = request.override.call_args.kwargs
    system = kwargs["system_message"]
    assert "base prompt" in system.content
    assert "docs/interviews/interview_001.docx" in system.content
    assert "只能分析" in system.content or "仅允许" in system.content


def test_wrap_tool_call_blocks_out_of_list_path():
    mw = AnalysisDocPathsMiddleware()
    request = ToolCallRequest(
        tool_call={
            "name": "ensure_document_markdown",
            "args": {"path": "docs/interviews/interview_002.docx"},
            "id": "tc1",
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=SimpleNamespace(
            context=AgentContext(
                analysis_doc_paths=["docs/interviews/interview_001.docx"],
            )
        ),
    )
    handler = MagicMock()
    result = mw.wrap_tool_call(request, handler)
    handler.assert_not_called()
    assert isinstance(result, ToolMessage)
    payload = json.loads(str(result.content))
    assert "error" in payload
    assert "interview_002" in payload["error"]


def test_wrap_tool_call_allows_selected_path():
    mw = AnalysisDocPathsMiddleware()
    request = ToolCallRequest(
        tool_call={
            "name": "ensure_document_markdown",
            "args": {"path": "docs/interviews/interview_001.docx"},
            "id": "tc2",
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=SimpleNamespace(
            context=AgentContext(
                analysis_doc_paths=["docs/interviews/interview_001.docx"],
            )
        ),
    )
    handler = MagicMock(return_value=ToolMessage(content="ok", tool_call_id="tc2"))
    result = mw.wrap_tool_call(request, handler)
    handler.assert_called_once_with(request)
    assert result.content == "ok"


def test_wrap_tool_call_allows_inspect_document_for_selected_doc_id():
    mw = AnalysisDocPathsMiddleware()
    request = ToolCallRequest(
        tool_call={
            "name": "inspect_document",
            "args": {"path": "interview_001"},
            "id": "tc3",
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=SimpleNamespace(
            context=AgentContext(
                analysis_doc_paths=["docs/interviews/interview_001.docx"],
            )
        ),
    )
    handler = MagicMock(return_value=ToolMessage(content="ok", tool_call_id="tc3"))
    result = mw.wrap_tool_call(request, handler)
    handler.assert_called_once_with(request)
    assert result.content == "ok"


def test_wrap_tool_call_blocks_inspect_document_for_other_doc_id():
    mw = AnalysisDocPathsMiddleware()
    request = ToolCallRequest(
        tool_call={
            "name": "inspect_document",
            "args": {"path": "interview_003"},
            "id": "tc-inspect-denied",
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=SimpleNamespace(
            context=AgentContext(
                analysis_doc_paths=["docs/interviews/interview_001.docx"],
            )
        ),
    )
    handler = MagicMock()
    result = mw.wrap_tool_call(request, handler)
    handler.assert_not_called()
    assert "interview_003" in str(result.content)


def test_wrap_tool_call_blocks_load_doc_map_for_other_doc_id():
    mw = AnalysisDocPathsMiddleware()
    request = ToolCallRequest(
        tool_call={
            "name": "load_doc_map",
            "args": {"doc_id": "interview_003"},
            "id": "tc-map-denied",
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=SimpleNamespace(
            context=AgentContext(
                analysis_doc_paths=["docs/interviews/interview_001.docx"],
            )
        ),
    )
    handler = MagicMock()
    result = mw.wrap_tool_call(request, handler)
    handler.assert_not_called()
    assert "interview_003" in str(result.content)


def test_wrap_tool_call_blocks_other_markdown_via_read_file():
    mw = AnalysisDocPathsMiddleware()
    request = ToolCallRequest(
        tool_call={
            "name": "read_file",
            "args": {"file_path": "/workspace/cache/markdown/interview_002.md"},
            "id": "tc4",
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=SimpleNamespace(
            context=AgentContext(
                analysis_doc_paths=["docs/interviews/interview_001.docx"],
            )
        ),
    )
    handler = MagicMock()
    result = mw.wrap_tool_call(request, handler)
    handler.assert_not_called()
    assert "interview_002" in str(result.content)


def test_wrap_tool_call_blocks_other_doc_map_via_read_file():
    mw = AnalysisDocPathsMiddleware()
    request = ToolCallRequest(
        tool_call={
            "name": "read_file",
            "args": {"file_path": "/workspace/cache/doc_maps/other.json"},
            "id": "tc-map-read-denied",
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=SimpleNamespace(
            context=AgentContext(
                analysis_doc_paths=["docs/interviews/interview_001.docx"],
            )
        ),
    )
    handler = MagicMock()
    result = mw.wrap_tool_call(request, handler)
    handler.assert_not_called()
    assert "other" in str(result.content)


def test_wrap_tool_call_allows_skill_read_file_with_picker():
    mw = AnalysisDocPathsMiddleware()
    request = ToolCallRequest(
        tool_call={
            "name": "read_file",
            "args": {"file_path": "/skills/single-report-analysis/SKILL.md"},
            "id": "tc5",
            "type": "tool_call",
        },
        tool=None,
        state={},
        runtime=SimpleNamespace(
            context=AgentContext(
                analysis_doc_paths=["docs/interviews/interview_001.docx"],
            )
        ),
    )
    handler = MagicMock(return_value=ToolMessage(content="ok", tool_call_id="tc5"))
    result = mw.wrap_tool_call(request, handler)
    handler.assert_called_once_with(request)
    assert result.content == "ok"

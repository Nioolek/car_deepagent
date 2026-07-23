from dataclasses import dataclass

from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime, get_runtime
from typing_extensions import TypedDict

from car_deepagent.analysis_docs import AgentContext
from car_deepagent.middleware.analysis_docs import AnalysisDocPathsMiddleware
from car_deepagent.subagents.report_analyst import build_report_analyst_subagent


class _State(TypedDict, total=False):
    messages: list
    seen_paths: list[str]


@dataclass
class _BackendStub:
    pass


def test_report_analyst_subagent_installs_picker_guard():
    spec = build_report_analyst_subagent()

    assert any(
        isinstance(middleware, AnalysisDocPathsMiddleware)
        for middleware in spec["middleware"]
    )


def test_deepagents_task_forwards_parent_runtime_context_to_subagent():
    def capture_context(_state):
        context = get_runtime().context
        return {
            "messages": [
                AIMessage(content=",".join(context.analysis_doc_paths))
            ]
        }

    middleware = SubAgentMiddleware(
        backend=_BackendStub(),
        subagents=[
            {
                "name": "report_analyst",
                "description": "Capture the selected document paths.",
                "runnable": RunnableLambda(capture_context),
            }
        ],
    )
    task_tool = middleware.tools[0]

    def invoke_task(state: _State, runtime: Runtime, config):
        tool_runtime = ToolRuntime(
            state=state,
            context=runtime.context,
            config=config,
            stream_writer=runtime.stream_writer,
            tool_call_id="task-call",
            store=runtime.store,
            tools=[],
        )
        command = task_tool.func(
            description="Analyze the selected interview.",
            subagent_type="report_analyst",
            runtime=tool_runtime,
        )
        content = command.update["messages"][0].content
        return {"seen_paths": content.split(",")}

    graph = (
        StateGraph(_State, context_schema=AgentContext)
        .add_node("invoke_task", invoke_task)
        .add_edge(START, "invoke_task")
        .add_edge("invoke_task", END)
        .compile()
    )

    selected = ["docs/interviews/interview_001.md"]
    result = graph.invoke(
        {},
        context=AgentContext(analysis_doc_paths=selected),
    )

    assert result["seen_paths"] == selected

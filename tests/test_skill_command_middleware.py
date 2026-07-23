from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from deepagents.backends.filesystem import FilesystemBackend

from car_deepagent.middleware.skill_command import SkillCommandMiddleware
from car_deepagent.paths import repo_root


def _backend():
    return FilesystemBackend(root_dir=str(repo_root()), virtual_mode=True)


def test_before_agent_injects_for_known_skill():
    mw = SkillCommandMiddleware(backend=_backend())
    state = {
        "messages": [
            HumanMessage(
                content="/single-report-analysis 总结座舱评价",
                id="h1",
            )
        ]
    }
    update = mw.before_agent(state, runtime=None)
    assert update is not None
    messages = update["messages"]
    # Pattern: RemoveMessage + rebuilt list (same as PatchToolCallsMiddleware)
    humans = [m for m in messages if getattr(m, "type", None) == "human"]
    assert humans
    assert humans[-1].content == "总结座舱评价"
    ais = [m for m in messages if isinstance(m, AIMessage) and m.tool_calls]
    assert ais
    assert ais[-1].tool_calls[0]["name"] == "read_file"
    assert "/skills/single-report-analysis/SKILL.md" in str(
        ais[-1].tool_calls[0]["args"]
    )
    tools = [m for m in messages if isinstance(m, ToolMessage)]
    assert tools
    assert "single-report-analysis" in tools[-1].content or "Single report" in tools[-1].content
    assert "When to Use" in tools[-1].content or "## When to Use" in tools[-1].content


def test_before_agent_passthrough_unknown_slash():
    mw = SkillCommandMiddleware(backend=_backend())
    original = HumanMessage(content="/not-a-skill hello", id="h2")
    state = {"messages": [original]}
    assert mw.before_agent(state, runtime=None) is None


def test_before_agent_idempotent():
    mw = SkillCommandMiddleware(backend=_backend())
    state = {
        "messages": [
            HumanMessage(content="/single-report-analysis 问一次", id="h3"),
        ]
    }
    first = mw.before_agent(state, runtime=None)
    assert first is not None
    # Simulate state after apply: drop RemoveMessage sentinel for second call
    rebuilt = [m for m in first["messages"] if getattr(m, "type", None) != "remove"]
    second = mw.before_agent({"messages": rebuilt}, runtime=None)
    assert second is None


def test_before_agent_no_slash_unchanged():
    mw = SkillCommandMiddleware(backend=_backend())
    state = {"messages": [HumanMessage(content="普通问题", id="h4")]}
    assert mw.before_agent(state, runtime=None) is None


def test_before_agent_injects_for_multimodal_text_blocks():
    """Agent Chat UI sends content as [{type: text, text: ...}]."""
    mw = SkillCommandMiddleware(backend=_backend())
    state = {
        "messages": [
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "/single-report-analysis 总结座舱评价",
                    }
                ],
                id="h5",
            )
        ]
    }
    update = mw.before_agent(state, runtime=None)
    assert update is not None
    humans = [m for m in update["messages"] if getattr(m, "type", None) == "human"]
    assert humans[-1].content == "总结座舱评价"
    ais = [m for m in update["messages"] if isinstance(m, AIMessage) and m.tool_calls]
    assert ais[-1].tool_calls[0]["name"] == "read_file"

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from deepagents.backends.protocol import BackendProtocol
from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    RemoveMessage,
)
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime

from car_deepagent.paths import repo_root
from car_deepagent.skill_commands import (
    build_skill_load_messages,
    discover_skill_names,
    human_message_text,
    parse_skill_command,
    skill_md_virtual_path,
)

logger = logging.getLogger(__name__)

SKILL_CMD_ID_PREFIX = "skill-cmd-"


class SkillCommandMiddleware(AgentMiddleware):
    """Force-load a skill when the latest human message starts with /skill-name."""

    def __init__(
        self,
        backend: BackendProtocol,
        skills_root: Path | None = None,
    ) -> None:
        super().__init__()
        self._backend = backend
        self._skills_root = skills_root or (repo_root() / "skills")

    def before_agent(
        self,
        state: AgentState,
        runtime: Runtime[Any] | None,
    ) -> dict[str, Any] | None:  # noqa: ARG002
        messages: list[AnyMessage] = list(state.get("messages") or [])
        if not messages:
            return None

        last_human_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], HumanMessage):
                last_human_idx = i
                break
        if last_human_idx is None:
            return None

        human = messages[last_human_idx]
        text = human_message_text(human.content)
        known = discover_skill_names(self._skills_root)
        cmd = parse_skill_command(text, known)
        if cmd is None:
            return None

        path = skill_md_virtual_path(cmd.name)
        for msg in messages[last_human_idx + 1 :]:
            if not isinstance(msg, AIMessage):
                continue
            for tc in msg.tool_calls or []:
                tc_id = tc.get("id") or ""
                args = tc.get("args") or {}
                if (
                    tc.get("name") == "read_file"
                    and tc_id.startswith(SKILL_CMD_ID_PREFIX)
                    and args.get("file_path") == path
                ):
                    return None

        result = self._backend.read(path, offset=0, limit=1000)
        if getattr(result, "error", None) or not getattr(
            result,
            "file_data",
            None,
        ):
            logger.warning(
                "Skill command read failed for %s: %s",
                path,
                getattr(result, "error", None),
            )
            return None

        file_data = result.file_data
        body = (
            file_data.get("content")
            if isinstance(file_data, dict)
            else getattr(file_data, "content", None)
        )
        if not isinstance(body, str) or not body.strip():
            logger.warning("Skill command empty body for %s", path)
            return None

        tool_call_id = f"{SKILL_CMD_ID_PREFIX}{uuid.uuid4().hex[:12]}"
        ai_msg, tool_msg = build_skill_load_messages(
            skill_name=cmd.name,
            skill_body=body,
            tool_call_id=tool_call_id,
        )

        new_human = HumanMessage(content=cmd.remainder, id=human.id)
        rebuilt: list[AnyMessage] = [
            *messages[:last_human_idx],
            new_human,
            ai_msg,
            tool_msg,
            *messages[last_human_idx + 1 :],
        ]
        return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *rebuilt]}

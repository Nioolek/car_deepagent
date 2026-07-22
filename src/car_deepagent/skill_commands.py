from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage

_COMMAND_RE = re.compile(
    r"^/([a-z0-9]+(?:-[a-z0-9]+)*)(?:\s+|$)(.*)$",
    re.DOTALL,
)


@dataclass(frozen=True)
class SkillCommand:
    name: str
    remainder: str


def discover_skill_names(skills_root: Path) -> set[str]:
    if not skills_root.is_dir():
        return set()
    names: set[str] = set()
    for child in skills_root.iterdir():
        if child.is_dir() and (child / "SKILL.md").is_file():
            names.add(child.name)
    return names


def parse_skill_command(text: str, known_skills: set[str]) -> SkillCommand | None:
    stripped = text.lstrip()
    match = _COMMAND_RE.match(stripped)
    if not match:
        return None
    name = match.group(1)
    if name not in known_skills:
        return None
    remainder = match.group(2).strip()
    return SkillCommand(name=name, remainder=remainder)


def skill_md_virtual_path(name: str) -> str:
    return f"/skills/{name}/SKILL.md"


def build_skill_load_messages(
    *,
    skill_name: str,
    skill_body: str,
    tool_call_id: str,
) -> tuple[AIMessage, ToolMessage]:
    path = skill_md_virtual_path(skill_name)
    ai = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {"file_path": path, "limit": 1000},
                "id": tool_call_id,
                "type": "tool_call",
            }
        ],
    )
    tool = ToolMessage(
        content=skill_body,
        tool_call_id=tool_call_id,
        name="read_file",
    )
    return ai, tool

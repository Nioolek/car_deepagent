from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage

from car_deepagent.paths import repo_root
from car_deepagent.skill_commands import (
    build_skill_load_messages,
    discover_skill_names,
    human_message_text,
    parse_skill_command,
    skill_md_virtual_path,
)


def test_discover_skill_names():
    names = discover_skill_names(repo_root() / "skills")
    assert names == {
        "single-report-analysis",
        "multi-report-synthesis",
        "user-profile-lookup",
    }


def test_parse_known_skill_strips_command():
    known = discover_skill_names(repo_root() / "skills")
    cmd = parse_skill_command(
        "/single-report-analysis 总结 interview_001 座舱评价",
        known,
    )
    assert cmd is not None
    assert cmd.name == "single-report-analysis"
    assert cmd.remainder == "总结 interview_001 座舱评价"


def test_parse_known_skill_empty_remainder():
    known = {"single-report-analysis"}
    cmd = parse_skill_command("/single-report-analysis", known)
    assert cmd is not None
    assert cmd.remainder == ""


def test_parse_unknown_slash_returns_none():
    known = discover_skill_names(repo_root() / "skills")
    assert parse_skill_command("/not-a-skill hello", known) is None


def test_parse_mid_message_slash_ignored():
    known = {"single-report-analysis"}
    assert parse_skill_command("请看 /single-report-analysis 文档", known) is None


def test_parse_trims_leading_whitespace():
    known = {"user-profile-lookup"}
    cmd = parse_skill_command("  /user-profile-lookup U001", known)
    assert cmd is not None
    assert cmd.remainder == "U001"


def test_skill_md_virtual_path():
    assert skill_md_virtual_path("multi-report-synthesis") == (
        "/skills/multi-report-synthesis/SKILL.md"
    )


def test_build_skill_load_messages():
    ai, tool = build_skill_load_messages(
        skill_name="single-report-analysis",
        skill_body="# Skill body\n",
        tool_call_id="skill-cmd-test-1",
    )
    assert isinstance(ai, AIMessage)
    assert isinstance(tool, ToolMessage)
    assert len(ai.tool_calls) == 1
    tc = ai.tool_calls[0]
    assert tc["name"] == "read_file"
    assert tc["id"] == "skill-cmd-test-1"
    assert tc["args"]["file_path"] == "/skills/single-report-analysis/SKILL.md"
    assert tc["args"]["limit"] == 1000
    assert tool.tool_call_id == "skill-cmd-test-1"
    assert tool.name == "read_file"
    assert tool.content == "# Skill body\n"


def test_human_message_text_string_and_blocks():
    assert human_message_text("hello") == "hello"
    assert (
        human_message_text([{"type": "text", "text": "/skill hi"}])
        == "/skill hi"
    )
    assert human_message_text([]) == ""
    assert human_message_text(None) == ""

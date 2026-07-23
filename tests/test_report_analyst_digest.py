"""report_analyst returns a Markdown digest, not JSON."""

from car_deepagent.subagents.report_analyst import (
    REPORT_ANALYST_PROMPT,
    build_report_analyst_subagent,
)


def test_report_analyst_prompt_requires_markdown_digest_not_json():
    prompt = REPORT_ANALYST_PROMPT
    assert "不要输出 JSON" in prompt or "禁止 JSON" in prompt
    assert "用户核心信息" in prompt
    assert "段落摘要" in prompt
    assert "重点摘录" in prompt
    assert "整体概要" in prompt
    assert "`L55`｜" in prompt or "L55`｜" in prompt
    assert "最终回复必须是一个 JSON" not in prompt


def test_report_analyst_description_mentions_markdown_digest():
    spec = build_report_analyst_subagent()
    description = spec["description"]
    assert "Markdown" in description or "markdown" in description.lower()
    assert "JSON" in description  # explicitly says not JSON
    assert "not JSON" in description or "—not JSON" in description

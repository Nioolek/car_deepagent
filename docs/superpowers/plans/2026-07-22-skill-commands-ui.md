# Skill Slash Commands + Chat UI Readability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Force-load known skills via leading `/skill-name` by injecting a synthetic `read_file` transcript, and make chat tools readable (Chinese labels, thinking → tools → answer, visible “已加载 skill”).

**Architecture:** Pure parser + `SkillCommandMiddleware.before_agent` (Deep Agents / LangChain `AgentMiddleware`) rewrites the latest human message and inserts `AIMessage(tool_calls=[read_file…])` + `ToolMessage` with real `SKILL.md` body. Frontend keeps detecting loads via `extractLoadedSkills`, improves tool chrome, and reorders assistant bubble sections.

**Tech Stack:** Python 3.11+, pytest, `deepagents` / `langchain.agents.middleware`, `FilesystemBackend`, Next.js `agent-chat-ui` (React).

## Global Constraints

- Unknown `/xxx` → treat as normal user text (no error UI, no strip).
- Known skill only when name matches an existing `skills/<name>/` directory with `SKILL.md`.
- Backend-only injection; frontend never injects skill markdown.
- Synthetic tool name must be `read_file` with `file_path=/skills/<name>/SKILL.md` so existing Skills panel works.
- On skill file read failure: leave human message unchanged; no synthetic messages; log warning.
- Do not add `/` autocomplete in this plan.
- Do not commit `.env` or secrets.
- Follow TDD: failing test → implement → pass → commit per task.

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/car_deepagent/skill_commands.py` | Parse `/skill`, list known skills, build synthetic messages |
| `src/car_deepagent/middleware/skill_command.py` | `SkillCommandMiddleware.before_agent` |
| `src/car_deepagent/middleware/__init__.py` | Package export |
| `src/car_deepagent/graph.py` | Register middleware; prompt note about preloaded skills |
| `tests/test_skill_commands.py` | Parser + synthetic builder unit tests |
| `tests/test_skill_command_middleware.py` | Middleware behavior unit tests |
| `agent-chat-ui/src/lib/tool-labels.ts` | Chinese tool display names + skill-load summary helper |
| `agent-chat-ui/src/lib/extract-loaded-skills.ts` | Keep path detection; minor exports if needed |
| `agent-chat-ui/src/components/thread/messages/tool-calls.tsx` | Chinese labels; skill load summary on results |
| `agent-chat-ui/src/components/thread/messages/ai.tsx` | Render order: reasoning → tools → answer |
| `agent-chat-ui/src/components/thread/skill-panel.tsx` | Copy note that `/skill` also marks 已加载 |
| `README.md` | Document `/skill-name` usage |

---

### Task 1: Skill command parser + synthetic message builder

**Files:**
- Create: `src/car_deepagent/skill_commands.py`
- Create: `tests/test_skill_commands.py`

**Interfaces:**
- Produces:
  - `KNOWN_SKILL_PATTERN` / parsing via `parse_skill_command(text: str, known_skills: set[str]) -> SkillCommand | None`
  - `@dataclass SkillCommand`: `name: str`, `remainder: str`
  - `discover_skill_names(skills_root: Path) -> set[str]`
  - `skill_md_virtual_path(name: str) -> str` → `/skills/{name}/SKILL.md`
  - `build_skill_load_messages(*, skill_name: str, skill_body: str, tool_call_id: str) -> tuple[AIMessage, ToolMessage]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_skill_commands.py`:

```python
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage

from car_deepagent.paths import repo_root
from car_deepagent.skill_commands import (
    build_skill_load_messages,
    discover_skill_names,
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_commands.py -v`

Expected: FAIL with `ModuleNotFoundError` / import error for `car_deepagent.skill_commands`.

- [ ] **Step 3: Implement `skill_commands.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_skill_commands.py -v`

Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add src/car_deepagent/skill_commands.py tests/test_skill_commands.py
git commit -m "$(cat <<'EOF'
feat: parse /skill commands and build synthetic read_file messages

EOF
)"
```

---

### Task 2: SkillCommandMiddleware + wire into graph

**Files:**
- Create: `src/car_deepagent/middleware/__init__.py`
- Create: `src/car_deepagent/middleware/skill_command.py`
- Modify: `src/car_deepagent/graph.py`
- Create: `tests/test_skill_command_middleware.py`

**Interfaces:**
- Consumes: `parse_skill_command`, `discover_skill_names`, `build_skill_load_messages`, `skill_md_virtual_path` from Task 1
- Produces: `class SkillCommandMiddleware(AgentMiddleware)` with `before_agent(self, state, runtime) -> dict | None`
- Constructor: `SkillCommandMiddleware(backend: BackendProtocol, skills_root: Path | None = None)`
- Idempotency: if messages after the latest human already contain a `read_file` tool_call whose `file_path` is `/skills/<name>/SKILL.md` and `id` starts with `skill-cmd-`, return `None`

- [ ] **Step 1: Write the failing middleware tests**

Create `tests/test_skill_command_middleware.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_command_middleware.py -v`

Expected: FAIL importing `SkillCommandMiddleware`.

- [ ] **Step 3: Implement middleware**

`src/car_deepagent/middleware/__init__.py`:

```python
from car_deepagent.middleware.skill_command import SkillCommandMiddleware

__all__ = ["SkillCommandMiddleware"]
```

`src/car_deepagent/middleware/skill_command.py`:

```python
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

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
    parse_skill_command,
    skill_md_virtual_path,
)

logger = logging.getLogger(__name__)

SKILL_CMD_ID_PREFIX = "skill-cmd-"


class SkillCommandMiddleware(AgentMiddleware):
    """Force-load a skill when the latest human message starts with /skill-name."""

    def __init__(self, backend: Any, skills_root: Path | None = None) -> None:
        super().__init__()
        self._backend = backend
        self._skills_root = skills_root or (repo_root() / "skills")

    def before_agent(self, state: AgentState, runtime: Runtime[Any] | None) -> dict[str, Any] | None:  # noqa: ARG002
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
        text = human.content if isinstance(human.content, str) else ""
        known = discover_skill_names(self._skills_root)
        cmd = parse_skill_command(text, known)
        if cmd is None:
            return None

        path = skill_md_virtual_path(cmd.name)
        # Idempotency: already injected for this turn
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
        if getattr(result, "error", None) or not getattr(result, "file_data", None):
            logger.warning("Skill command read failed for %s: %s", path, getattr(result, "error", None))
            return None

        file_data = result.file_data
        body = file_data.content if hasattr(file_data, "content") else str(file_data)
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
```

- [ ] **Step 4: Wire into `graph.py`**

Update `MAIN_PROMPT` rule 1 to add:

```text
若本轮消息历史中已有针对某 `/skills/<name>/SKILL.md` 的 `read_file` 结果
（含用户用 /skill-name 命令触发的加载），不要重复读取该文件，直接按 skill 指令执行。
```

In `build_graph()`, pass middleware:

```python
from car_deepagent.middleware import SkillCommandMiddleware

# inside build_graph, after backend = ...
return create_deep_agent(
    ...
    backend=backend,
    middleware=[SkillCommandMiddleware(backend=backend)],
    subagents=[build_report_analyst_subagent()],
)
```

- [ ] **Step 5: Run middleware + existing skill tests**

Run:

```bash
uv run pytest tests/test_skill_command_middleware.py tests/test_skill_commands.py tests/test_skills_exist.py tests/test_graph_builds.py -v
```

Expected: all PASS. If `ReadResult.file_data.content` shape differs, adjust middleware to match the backend’s actual attribute (inspect failing assertion / `result` repr).

- [ ] **Step 6: Commit**

```bash
git add src/car_deepagent/middleware src/car_deepagent/graph.py tests/test_skill_command_middleware.py
git commit -m "$(cat <<'EOF'
feat: inject skill SKILL.md via /skill slash command middleware

EOF
)"
```

---

### Task 3: Frontend — tool Chinese labels + skill load summary

**Files:**
- Create: `agent-chat-ui/src/lib/tool-labels.ts`
- Modify: `agent-chat-ui/src/components/thread/messages/tool-calls.tsx`
- Modify: `agent-chat-ui/src/components/thread/skill-panel.tsx` (help text only)

**Interfaces:**
- Produces:
  - `toolDisplayName(name: string): string`
  - `skillLoadSummaryFromToolArgs(args: unknown): string | null` — returns `已加载 skill：{label}（{name}）` or null
  - `skillLoadSummaryFromToolResult(message: ToolMessage-like): string | null` — if companion path detectable from content headers optional; prefer pairing via call args in UI

- [ ] **Step 1: Add `tool-labels.ts`**

```typescript
import { KNOWN_SKILLS } from "@/lib/extract-loaded-skills";

const TOOL_LABELS: Record<string, string> = {
  read_file: "读取文件",
  read: "读取文件",
  write_file: "写入文件",
  write_todos: "更新待办",
  ls: "列出目录",
  glob: "匹配文件",
  grep: "搜索内容",
  edit_file: "编辑文件",
  execute: "执行命令",
  task: "子任务",
  ensure_document_markdown: "转换文档",
  ensure_summary_tree: "构建摘要树",
  get_chapter_summary: "章节摘要",
  get_chapter_excerpt: "章节摘录",
  get_user_profile: "用户画像",
  estimate_tokens: "估算 Token",
};

const SKILL_PATH_RE =
  /\/skills\/([a-z0-9]+(?:-[a-z0-9]+)*)\/SKILL\.md(?:$|\?|#)/i;

export function toolDisplayName(name: string | undefined | null): string {
  if (!name) return "工具";
  return TOOL_LABELS[name] ?? name;
}

export function skillNameFromPath(path: string): string | null {
  const match = path.replace(/\\/g, "/").match(SKILL_PATH_RE);
  return match?.[1] ?? null;
}

export function skillLoadSummaryFromPath(path: string): string | null {
  const name = skillNameFromPath(path);
  if (!name) return null;
  const known = KNOWN_SKILLS.find((s) => s.name === name);
  const label = known?.label ?? name;
  return `已加载 skill：${label}（${name}）`;
}

export function pathFromToolArgs(args: unknown): string | null {
  if (!args || typeof args !== "object") return null;
  const record = args as Record<string, unknown>;
  for (const key of ["file_path", "path", "filepath"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}
```

- [ ] **Step 2: Update `ToolCalls` header**

In `tool-calls.tsx`, import helpers. Replace raw `{tc.name}` heading with:

```tsx
{toolDisplayName(tc.name)}
{(() => {
  const path = pathFromToolArgs(tc.args);
  const summary = path ? skillLoadSummaryFromPath(path) : null;
  return summary ? (
    <span className="ml-2 text-sm font-normal text-indigo-700">{summary}</span>
  ) : null;
})()}
```

Keep `tc.id` code chip as today (optional: hide `skill-cmd-*` ids to reduce noise — prefer keep for debug).

- [ ] **Step 3: Update `ToolResult` header**

Replace `"Tool Result:"` with `"工具结果："` and use `toolDisplayName(message.name)`.

If `message.name` is `read_file` / `read` and content looks like a skill (contains `name: <skill>` frontmatter) **or** we cannot see args: still show a generic skill summary only when content includes a path line — simpler approach for this task:

Pass optional skill summary only from ToolCalls side; for ToolResult, if content starts with `---` and matches `/name: ([a-z0-9-]+)/` against `KNOWN_SKILLS`, show the same `已加载 skill：…` line under the header.

```tsx
function skillSummaryFromSkillMarkdown(content: unknown): string | null {
  if (typeof content !== "string") return null;
  const m = content.match(/^---[\s\S]*?^name:\s*([a-z0-9-]+)/m);
  if (!m) return null;
  const name = m[1];
  if (!KNOWN_SKILLS.some((s) => s.name === name)) return null;
  return skillLoadSummaryFromPath(`/skills/${name}/SKILL.md`);
}
```

Show that summary in the ToolResult header row when present.

- [ ] **Step 4: Update Skills panel help text**

```tsx
Agent 通过 read_file 加载 /skills/…/SKILL.md，或使用 /skill-name 命令后，此处标记为已加载。
```

- [ ] **Step 5: Typecheck**

Run: `cd agent-chat-ui && pnpm exec tsc --noEmit`

Expected: exit 0 (or only pre-existing unrelated errors — fix any new errors from this task).

- [ ] **Step 6: Commit**

```bash
git add agent-chat-ui/src/lib/tool-labels.ts \
  agent-chat-ui/src/components/thread/messages/tool-calls.tsx \
  agent-chat-ui/src/components/thread/skill-panel.tsx
git commit -m "$(cat <<'EOF'
feat(ui): Chinese tool labels and skill-loaded summaries

EOF
)"
```

---

### Task 4: Frontend — message order thinking → tools → answer

**Files:**
- Modify: `agent-chat-ui/src/components/thread/messages/ai.tsx`

**Interfaces:**
- Consumes: existing `ReasoningBlock`, `ToolCalls`, `MarkdownText`
- Produces: same components, reordered

- [ ] **Step 1: Reorder `AssistantMessage` non-tool-result branch**

Current order is roughly: reasoning → contentString → tool calls.  
Change to: reasoning → tool calls → contentString → CustomComponent → Interrupt → chrome.

Concrete JSX order inside the `else` branch of `isToolResult`:

```tsx
{reasoning && (
  <ReasoningBlock reasoning={reasoning} defaultOpen={isLastMessage} />
)}

{!hideToolCalls && (
  <>
    {(hasToolCalls && toolCallsHaveContents && (
      <ToolCalls toolCalls={message.tool_calls} />
    )) ||
      (hasAnthropicToolCalls && (
        <ToolCalls toolCalls={anthropicStreamedToolCalls} />
      )) ||
      (hasToolCalls && <ToolCalls toolCalls={message.tool_calls} />)}
  </>
)}

{contentString.length > 0 && (
  <div className="py-1">
    <MarkdownText>{contentString}</MarkdownText>
  </div>
)}

{message && <CustomComponent message={message} thread={thread} />}
{/* Interrupt + BranchSwitcher + CommandBar unchanged below */}
```

Note: tool **results** are separate `tool` type messages rendered as their own `AssistantMessage` rows (existing behavior). Ordering within an AI message bubble is what this task fixes; do not merge tool result messages into the AI bubble unless already done elsewhere.

- [ ] **Step 2: Typecheck**

Run: `cd agent-chat-ui && pnpm exec tsc --noEmit`

Expected: exit 0 for changes in this file.

- [ ] **Step 3: Commit**

```bash
git add agent-chat-ui/src/components/thread/messages/ai.tsx
git commit -m "$(cat <<'EOF'
fix(ui): render thinking then tools then answer

EOF
)"
```

---

### Task 5: README + end-to-end verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document slash commands**

In the UI startup section (near the example question), add:

```markdown
也可用 slash 强制加载 skill（命令名 = `skills/` 下目录名）：

```text
/single-report-analysis 请总结 docs/interviews/interview_001.docx 中用户对座舱语音的评价，并给出脚注溯源。
```

可用：`/single-report-analysis`、`/multi-report-synthesis`、`/user-profile-lookup`。  
未知的 `/xxx` 会当作普通问题，不做命令处理。

命令成功时，回复中会出现 `read_file` 工具卡（摘要含「已加载 skill」），Skills 面板对应项变为「已加载」。
```

- [ ] **Step 2: Run full backend test suite**

Run: `uv run pytest -v`

Expected: all PASS.

- [ ] **Step 3: Manual smoke (if `langgraph dev` + UI available)**

1. Restart `uv run langgraph dev` so middleware loads.
2. In UI send: `/single-report-analysis 用一句话说明该 skill 要求的脚注格式`
3. Confirm: tool card shows 已加载 skill；Skills 面板 已加载；顺序为思考（若有）→ 工具 → 回答.
4. Send: `/not-a-skill 你好` → normal reply, no skill injection.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: document /skill slash commands in README

EOF
)"
```

---

## Spec coverage (self-review)

| Spec item | Task |
|---|---|
| Leading `/known-skill` strip + inject synthetic read_file | 1–2 |
| Unknown `/xxx` as normal question | 2 (`passthrough` test) |
| Read failure → unchanged human, no synth | 2 (middleware returns None on read error) |
| Backend-only injection | 2 |
| Visible load in reply + Skills panel | 3 (+ existing extractLoadedSkills) |
| thinking → tools → answer | 4 |
| Chinese tool labels + collapse (existing collapse kept) | 3 |
| No `/` autocomplete | out of scope (not tasked) |
| README examples | 5 |
| Unit + smoke | 1, 2, 5 |

## Placeholder / consistency check

- Tool call id prefix `skill-cmd-` used in middleware and idempotency checks.
- Virtual path always `/skills/<name>/SKILL.md`.
- `toolDisplayName` / `skillLoadSummaryFromPath` names stable across Task 3 steps.

# Skill Slash Commands + Chat UI Readability

Date: 2026-07-22  
Status: Approved for implementation planning  
Related: `2026-07-22-car-deepagent-design.md`, `2026-07-22-agent-chat-ui-frontend-design.md`

## 1. Goal

1. Let users force-load a skill with `/skill-name …` (deterministic), aligned with Claude Code–style slash skills.
2. Make skill load **visible in the chat reply** (tool transcript + Skills panel).
3. Improve tool/message readability: Chinese labels, thinking → tools → answer order, collapsed long tool payloads.

## 2. Decisions (locked)

| Topic | Choice |
|---|---|
| Load semantics | **A** — deterministic inject of skill body into this turn’s context |
| Industry alignment | Claude Code: slash = prompt/skill body injection; plus **synthetic `read_file` tool_call + ToolMessage** so transcript/UI match progressive disclosure |
| Unknown `/xxx` | Treat as a **normal user question** (no error bubble, no command list) |
| Frontend scope | **B** — message order + Chinese tool labels + collapse; Skills panel wired to command load; **no** `/` autocomplete menu |
| Who injects skill body | **Backend only** (middleware / graph entry); frontend only renders |

## 3. Slash command behavior

### 3.1 Syntax

- Match only at the **start** of the human message (full message text, leading whitespace trimmed first):
  - `^/([a-z0-9]+(?:-[a-z0-9]+)*)(?:\s+|$)(.*)$` with `re.DOTALL` so the remainder may span lines
- Command name = skill directory name under `skills/`:
  - `/single-report-analysis`
  - `/multi-report-synthesis`
  - `/user-profile-lookup`
- At most **one** skill command per message (first match only).
- Mid-message `/foo` (e.g. URLs, prose) is never treated as a command.

### 3.2 Known skill

1. Strip `/name` from the human message; remaining text is the user question (empty remainder allowed).
2. Read `/skills/<name>/SKILL.md` via the same `FilesystemBackend` used by the agent.
3. Prepend a **synthetic transcript** before the model runs:
   - `AIMessage` with `tool_calls=[{ name: "read_file", args: { file_path: "/skills/<name>/SKILL.md", limit: 1000 }, id: "<stable-unique-id>" }]`
   - `ToolMessage` with `tool_call_id` matching, `name: "read_file"`, `content` = real SKILL.md body
4. Continue the normal agent turn. System guidance: if this turn already has a skill `read_file` result, do not re-read that path; follow the skill instructions.
5. Skills panel and tool UI detect load via existing `read_file` path heuristics (`extractLoadedSkills`).

### 3.3 Unknown `/…` or non-command

- If the leading token looks like `/something` but **no** matching skill exists → **do not** strip or inject; pass the full original text as a normal user question.
- Messages with no leading slash → unchanged progressive disclosure (model may `read_file` skills on its own).

### 3.4 Skill file missing / read failure

- Do not synthesize a fake tool result.
- Leave the human message **unchanged** (do not strip `/name`) and continue as a normal turn.
- Log a warning server-side; no dedicated user-facing error bubble.

### 3.5 Placement

- Implement at graph entry / middleware wrapping the Deep Agent so both `langgraph dev` and `scripts/smoke_astream.py` share behavior.
- Do not rely on the Next.js client to inject skill markdown.

## 4. Frontend readability

### 4.1 Visible skill load on command

- Synthetic `read_file` appears as a normal tool call + result in the assistant turn.
- Tool header: Chinese label (e.g. 读取文件 / 加载 Skill); highlight skill path in args.
- Tool result: default collapsed; summary line `已加载 skill：{中文名}（{name}）` when path matches `/skills/<name>/SKILL.md`.
- Skills side panel: mark that skill **已加载** as soon as the synthetic (or real) `read_file` is in messages. Optional defensive: optimistic mark if human originally started with `/known-name` (primary path remains tool transcript).
- No floating badge overlay on the answer.

### 4.2 Message order

Within one assistant message bubble, render in this order:

1. 思考过程 (reasoning)
2. Tool calls / tool results
3. Final answer (markdown)

(Current UI may show thinking → answer → tools; fix to match the original frontend design spec.)

### 4.3 Tool labels and collapse

- Maintain a Chinese display-name map for common tools (`read_file`, `write_todos`, document/summary tools, `get_user_profile`, `estimate_tokens`, `task`, etc.). Unknown tools fall back to raw name.
- Keep / tighten default collapse for long args and results.
- Keep “hide tool calls” control; Chinese copy.

### 4.4 Out of scope this iteration

- Input `/` autocomplete menu (Claude Code–style picker)
- Dedicated error UI for unknown commands
- Changing skill auto-routing beyond existing progressive disclosure

## 5. Testing

- Unit: parser (known strip, unknown passthrough, only leading match); synthetic message `id` / path / content alignment.
- Integration / smoke: `/single-report-analysis …` produces `read_file` → that `SKILL.md` in the stream; agent is not required to call the same path again.
- Frontend checks: order thinking → tools → answer; skill tool card shows Chinese “已加载” summary; Skills panel shows loaded.

## 6. Docs

- Root README: document the three `/skill-name` examples; note that unknown `/…` is treated as a normal question.

## 7. Success criteria

- User types `/single-report-analysis <question>` and sees in the reply a tool card showing the skill was loaded, plus Skills panel **已加载**.
- `/not-a-skill hello` is answered as a normal chat turn with no special command handling.
- Tool stream is readable in Chinese and ordered thinking → tools → answer.

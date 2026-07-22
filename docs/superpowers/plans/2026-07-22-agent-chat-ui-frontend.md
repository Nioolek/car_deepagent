# Agent Chat UI Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Customize vendored `agent-chat-ui` into car_deepagent’s chat frontend: no config screen, no LangSmith key UX, default local `agent` graph, todos + tools + thinking + file preview.

**Architecture:** Keep Next.js Agent Chat UI; strip setup form; hard-default `http://localhost:2024` / `agent`; add Todo panel + reasoning block + preview API/drawer; add root `langgraph.json`.

**Tech Stack:** Next.js (existing), `@langchain/langgraph-sdk`, pnpm, `langgraph-cli`, optional `mammoth` for docx text in Node.

## Global Constraints

- Defaults: `NEXT_PUBLIC_API_URL=http://localhost:2024`, `NEXT_PUBLIC_ASSISTANT_ID=agent` (env override OK).
- No entry config form; no client LangSmith API key UI.
- File preview allowlist: `docs/`, `workspace/cache/`, `data/` only.
- Todo state key: `todos` (`list[{content,status}]`).
- Do not commit `.env` or secrets.
- Prefer surgical edits under `agent-chat-ui/`.

---

## File Structure

| Path | Responsibility |
|---|---|
| `langgraph.json` | Export graph id `agent` |
| `pyproject.toml` | Add `langgraph-cli` to dev deps |
| `agent-chat-ui/.env.example` | Local defaults, no LangSmith required |
| `agent-chat-ui/src/providers/Stream.tsx` | Defaults, remove setup form |
| `agent-chat-ui/src/lib/api-key.tsx` | Stop requiring localStorage key |
| `agent-chat-ui/src/app/api/[..._path]/route.ts` | Optional proxy without forced LangSmith key |
| `agent-chat-ui/src/components/thread/todo-panel.tsx` | Todo UI |
| `agent-chat-ui/src/components/thread/messages/reasoning.tsx` | Thinking block |
| `agent-chat-ui/src/components/thread/file-preview.tsx` | Preview drawer |
| `agent-chat-ui/src/lib/file-paths.ts` | Path detection helpers |
| `agent-chat-ui/src/app/api/files/preview/route.ts` | Allowlisted file preview API |
| `agent-chat-ui/src/components/thread/messages/ai.tsx` | Wire reasoning + path links |
| `agent-chat-ui/src/components/thread/messages/tool-calls.tsx` | Path buttons + expand |
| `agent-chat-ui/src/components/thread/index.tsx` | Layout: todos + preview |
| `README.md` | Dual-process startup |

---

### Task 1: LangGraph packaging + CLI dep

**Files:**
- Create: `langgraph.json`
- Modify: `pyproject.toml` (put `langgraph-cli` under `[project.optional-dependencies] dev`, remove accidental `[dependency-groups]` if present)
- Modify: `README.md` (agent server startup section)

- [ ] **Step 1: Add `langgraph.json`**

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/car_deepagent/graph.py:graph"
  },
  "env": ".env"
}
```

- [ ] **Step 2: Ensure CLI available**

```bash
uv sync --extra dev
uv run langgraph validate -c langgraph.json
```

Expected: validate succeeds (or fix path per CLI error).

- [ ] **Step 3: Document in README** dual terminal startup (`langgraph dev` + `pnpm dev`).

- [ ] **Step 4: Commit**

```bash
git add langgraph.json pyproject.toml README.md uv.lock
git commit -m "chore: add langgraph.json and CLI for local agent server"
```

---

### Task 2: Remove config screen + LangSmith client UX

**Files:**
- Modify: `agent-chat-ui/src/providers/Stream.tsx`
- Modify: `agent-chat-ui/src/lib/api-key.tsx`
- Modify: `agent-chat-ui/src/providers/Thread.tsx` (if it depends on apiKey form)
- Modify: `agent-chat-ui/src/app/api/[..._path]/route.ts`
- Modify: `agent-chat-ui/.env.example`

- [ ] **Step 1: Defaults helper**

In `Stream.tsx`, resolve:

```ts
const DEFAULT_API_URL = "http://localhost:2024";
const DEFAULT_ASSISTANT_ID = "agent";
const apiUrl = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
const assistantId = process.env.NEXT_PUBLIC_ASSISTANT_ID || DEFAULT_ASSISTANT_ID;
```

Always render `StreamSession` with these values; **delete** the setup `<form>` branch.

- [ ] **Step 2: apiKey**

Pass `apiKey={undefined}` (or null) into `useStream` for local. Remove localStorage get/set for required auth. Keep `getApiKey()` returning null if unused, or delete call sites.

- [ ] **Step 3: Proxy route**

For local, UI talks directly to `NEXT_PUBLIC_API_URL` (2024), so proxy may be unused. Still neutralize forced `"remove-me"` keys:

```ts
initApiPassthrough({
  apiUrl: process.env.LANGGRAPH_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:2024",
  apiKey: process.env.LANGSMITH_API_KEY || undefined,
  runtime: "edge",
});
```

If the helper rejects undefined apiKey, omit the field or pass empty string per package types.

- [ ] **Step 4: `.env.example`**

```bash
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=agent
# LANGSMITH_API_KEY=   # optional, only for remote LangSmith deployments
```

- [ ] **Step 5: Smoke build**

```bash
cd agent-chat-ui && pnpm install && pnpm exec tsc --noEmit
```

Expected: no type errors from removed form.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(ui): skip setup form and drop LangSmith key UX"
```

---

### Task 3: Todo panel

**Files:**
- Create: `agent-chat-ui/src/components/thread/todo-panel.tsx`
- Modify: `agent-chat-ui/src/providers/Stream.tsx` (`StateType` add `todos?`)
- Modify: `agent-chat-ui/src/components/thread/index.tsx`

- [ ] **Step 1: Extend state type**

```ts
export type TodoItem = {
  content: string;
  status: "pending" | "in_progress" | "completed";
};
export type StateType = {
  messages: Message[];
  ui?: UIMessage[];
  todos?: TodoItem[];
};
```

- [ ] **Step 2: Implement `TodoPanel`**

Read `useStreamContext().values?.todos ?? []`. Render list with status badges. Empty: “暂无待办”.

- [ ] **Step 3: Mount** in thread layout (right rail above or below history), visible on desktop; collapsible on mobile.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(ui): show Deep Agents todos from stream state"
```

---

### Task 4: Thinking / reasoning display

**Files:**
- Create: `agent-chat-ui/src/components/thread/messages/reasoning.tsx`
- Create: `agent-chat-ui/src/lib/extract-reasoning.ts`
- Modify: `agent-chat-ui/src/components/thread/messages/ai.tsx`

- [ ] **Step 1: Extractor**

```ts
export function extractReasoning(message: Message): string | null {
  // 1) content array blocks type reasoning|thinking
  // 2) additional_kwargs.reasoning / reasoning_content
  // return joined text or null
}
```

- [ ] **Step 2: `ReasoningBlock`** collapsible; defaultOpen for last message.

- [ ] **Step 3: Render above markdown answer in `AssistantMessage`.**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(ui): render model thinking/reasoning blocks"
```

---

### Task 5: File preview API + drawer + path links

**Files:**
- Create: `agent-chat-ui/src/lib/file-paths.ts`
- Create: `agent-chat-ui/src/lib/repo-root.ts`
- Create: `agent-chat-ui/src/app/api/files/preview/route.ts`
- Create: `agent-chat-ui/src/components/thread/file-preview.tsx`
- Modify: `tool-calls.tsx`, `ai.tsx`, `thread/index.tsx`
- Modify: `agent-chat-ui/package.json` (add `mammoth` if used)

- [ ] **Step 1: Path helpers**

Detect strings matching allowlisted relative/absolute paths ending in `.docx|.md|.json|.txt` or containing `docs/`, `workspace/cache/`, `data/`.

- [ ] **Step 2: Preview API**

- Resolve repo root: walk up from `process.cwd()` until `pyproject.toml` + `src/car_deepagent` exist (works when cwd is `agent-chat-ui` or repo root).
- Normalize path; ensure `resolved.startsWith(allowRoot)`.
- Return `{ path, mediaType, content }` or error JSON.

Docx: use `mammoth.extractRawText({ path })` in Node runtime (`export const runtime = "nodejs"`).

- [ ] **Step 3: `FilePreviewProvider` + drawer**

Context: `{ openPath(path: string) }`. Drawer fetches `/api/files/preview?path=...`.

- [ ] **Step 4: Wire path buttons** in ToolCalls args/results and markdown/path chips.

- [ ] **Step 5: Manual check**

```bash
# with pnpm dev running
curl -s 'http://localhost:3000/api/files/preview?path=docs/interviews/interview_001.docx' | head
```

Expected: JSON with extracted text; `../etc/passwd` → 403.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(ui): allowlisted file preview for docs and tool paths"
```

---

### Task 6: Tool display polish + defaults

**Files:**
- Modify: `tool-calls.tsx` (long content collapse defaults)
- Modify: `thread/index.tsx` (`hideToolCalls` default false — already false; ensure toggle label 中文化 optional)

- [ ] Ensure tool results expand/collapse works for long JSON and shows path open buttons.
- [ ] Commit: `feat(ui): improve tool call/result presentation`

---

### Task 7: README + end-to-end smoke

**Files:**
- Modify: root `README.md`
- Modify: `agent-chat-ui/README.md` (short car_deepagent-specific note at top)

- [ ] Document:
  1. `uv run langgraph dev`
  2. `cd agent-chat-ui && pnpm install && pnpm dev`
  3. Open UI, send a question with interview path; verify todos/tools/thinking/preview

- [ ] Manual E2E (network): one chat turn against live agent; confirm no config page; confirm tool cards; confirm todo updates if agent writes todos.

- [ ] Commit: `docs: document UI + langgraph dual-process startup`

---

## Spec coverage

| Spec item | Task |
|---|---|
| No config screen + defaults | 2 |
| No LangSmith key UX | 2 |
| langgraph.json `agent` | 1 |
| Todos panel | 3 |
| Thinking display | 4 |
| File preview A+C | 5 |
| Tool calls shown | 5–6 |
| README startup | 1, 7 |

## Self-review notes

- Todo field confirmed as `todos` in LangChain `PlanningState`.
- Preview must use Node runtime for mammoth/fs.
- UI should call LangGraph at `:2024` directly (not require LangSmith proxy) for V1.

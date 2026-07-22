# car_deepagent Frontend Design Spec

Date: 2026-07-22  
Status: Approved for implementation planning  
Base: vendored `agent-chat-ui/` (LangChain Agent Chat UI)

## 1. Goal

Customize `agent-chat-ui` into the car_deepagent product frontend:

- No entry configuration screen; default to the local car_deepagent graph
- Remove LangSmith key collection / client-side LangSmith auth UX
- Show todos, tool calls, and model thinking/reasoning
- File preview: clickable paths from messages/tools + expandable tool excerpts (option D)

Backend remains the existing Deep Agents graph. Frontend connects via LangGraph server (`langgraph.dev` / API).

## 2. Decisions (locked)

| Topic | Choice |
|---|---|
| Approach | Modify existing `agent-chat-ui/` (Approach 1) |
| Defaults | `NEXT_PUBLIC_API_URL=http://localhost:2024`, `NEXT_PUBLIC_ASSISTANT_ID=agent` |
| Config override | Env vars only; no UI config form |
| LangSmith | No client API-key UI; local runs without LangSmith key |
| File preview | A + C: whitelist path preview + expandable tool excerpts |
| Graph export name | `agent` → `car_deepagent.graph:graph` via root `langgraph.json` |

## 3. Architecture

```text
Browser (Next.js agent-chat-ui)
  │  useStream → http://localhost:2024 (or env)
  │  Graph ID: agent
  │
  ├─ Chat main: messages (thinking → tools → answer)
  ├─ Todo panel: stream.values.todos
  └─ File preview drawer ← GET /api/files/preview?path=...
                              │
                              └─ reads only docs/ | workspace/cache/ | data/

LangGraph server (langgraph dev :2024)
  └─ graphs.agent = car_deepagent.graph:graph
```

## 4. Feature details

### 4.1 Remove config screen / default agent

- Change `agent-chat-ui/src/providers/Stream.tsx` so missing URL/assistant never shows the setup form when defaults exist.
- Hard-default to `http://localhost:2024` and `agent` if env unset.
- Remove form fields: Deployment URL, Assistant/Graph ID, LangSmith API Key, Agent Builder switch.
- On connection failure: toast with remediation; stay on chat shell.

### 4.2 Remove LangSmith client auth UX

- Stop reading/writing `localStorage` key `lg:chat:apiKey` for required auth.
- Pass `apiKey: undefined` for local development.
- Remove Agent Builder / `langsmith-api-key` scheme UI.
- Soften or neutralize `src/app/api/[..._path]/route.ts` so production proxy does not require a placeholder LangSmith key for local-style setups (keep optional `LANGSMITH_API_KEY` only if proxying a remote LangSmith deployment later — V1 local path does not need it).
- Update `agent-chat-ui/.env.example` and root README accordingly.

### 4.3 Tool call display

- Keep `ToolCalls` / `ToolResult`; default `hideToolCalls` to `false`.
- Improve long JSON expand/collapse.
- Detect file-like paths in args/results (e.g. `.docx`, `.md`, `.json` under known roots) and render as buttons that open the preview drawer.

### 4.4 Todo display

- Extend stream state typing to include `todos` (Deep Agents `write_todos` state).
- Add a Todo panel (sidebar or sticky rail) listing items with status: `pending` | `in_progress` | `completed`.
- Update live from `stream.values`; empty state when absent.

If the live graph uses a slightly different field name, align UI to the actual state key discovered during implementation (document the final key in code comments / README).

### 4.5 Thinking / reasoning display

- Extract from AI messages:
  - content blocks with `type` in `{reasoning, thinking}`
  - and/or `additional_kwargs.reasoning` / provider-specific reasoning fields
- Render a collapsible “思考过程” section above the final answer for that message.
- Latest streaming turn expanded by default; older turns collapsed.
- If no reasoning present: omit the section (no fake placeholder).

### 4.6 File preview

- New route: `agent-chat-ui/src/app/api/files/preview/route.ts`
- Query: `path` (absolute or repo-relative)
- Allowlist roots (resolved against car_deepagent repo root):
  - `docs/`
  - `workspace/cache/`
  - `data/`
- Reject path escape (`..`, symlink escape if detectable) with 403
- Missing file → 404
- Render:
  - `.md` / `.txt` / `.json` → text
  - `.docx` → server-side text extract (reuse python via child process **or** lightweight JS docx parse; prefer a Node-side approach in Next to avoid spawning Python from the UI process — e.g. `mammoth` / `jszip` text extract). Choice finalized in implementation plan; must not block UI if extract fails (return error JSON).
- UI: right-side `FilePreview` drawer with path + content; tool excerpts get “在预览中打开” when path detected.

### 4.7 LangGraph packaging

Add repo-root `langgraph.json` roughly:

```json
{
  "graphs": {
    "agent": "./src/car_deepagent/graph.py:graph"
  },
  "env": ".env",
  "dependencies": ["."]
}
```

Exact schema must match the installed `langgraph-cli` version during implementation.

## 5. Startup (documented)

```bash
# Terminal 1 — agent
cd /path/to/car_deepagent
uv sync
uv run langgraph dev   # serves :2024, graph id agent

# Terminal 2 — UI
cd agent-chat-ui
pnpm install
pnpm dev               # typically :3000
```

## 6. Error handling

| Case | Behavior |
|---|---|
| Graph `/info` fail | Toast; remain in chat chrome |
| Preview path outside allowlist | 403 + UI message |
| Preview missing file | 404 + UI message |
| Docx extract fail | Error payload; drawer shows message |
| No reasoning | Hide thinking block |
| No todos | Empty todo panel |

## 7. Non-goals (V1)

- Production multi-tenant auth
- Full visual rebrand
- Agent Builder flows
- Arbitrary filesystem browser
- Backend analysis algorithm changes (except documenting/aligning todo state key if needed)

## 8. Security

- Preview API is read-only
- Paths normalized; must remain under allowlisted roots
- No LangSmith secrets in client bundles
- Do not commit `.env` files

## 9. Implementation principles

- Prefer surgical edits inside `agent-chat-ui/` over rewrites
- Reuse existing tool-call components
- Keep car_deepagent Python package as source of truth for the agent
- Update root README with dual-process startup

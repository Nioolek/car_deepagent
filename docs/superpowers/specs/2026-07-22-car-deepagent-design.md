# car_deepagent Design Spec

Date: 2026-07-22  
Status: Approved for implementation planning  
Stack: LangChain Deep Agents (`create_deep_agent`) → LangGraph graph

## 1. Goal

Build a research-interview analysis agent for HarmonyOS Intelligent Mobility (鸿蒙智行) user interview reports.

**Input:** user query + document path(s) (Word `.docx`).  
**Output stream:** thinking, tool calls, tool results, todo updates, final model summary with inline citation footnotes.

V1 delivers **only the compiled LangGraph graph**. Production hosts it via LangGraph API/Runtime. Local debug uses `graph.astream(...)`. No frontend in V1; event shapes must remain frontend-ready.

## 2. Decisions (locked)

| Topic | Choice |
|---|---|
| Delivery | Graph only; LangGraph API/Runtime later; debug via `astream` |
| Architecture | `create_deep_agent` harness (Approach 1) |
| LLM | OpenAI-compatible; load project `.env` (copied from `/home/admin/sha/.env`) |
| Secrets | `.env` gitignored; `.env.example` committed |
| User profile | Local mock JSON under `data/users/` |
| Long documents | Summary tree; drill into original text for detail |
| Summary tree lifecycle | Lazy build on first analysis; cache for reuse |
| Citations | Inline footnotes `[^doc§section]` + end-of-answer excerpts |
| Skills | Minimal set of three |
| Frontend | Out of scope for V1 |

## 3. Architecture

```text
Input: { messages, doc_paths[] }
              │
              ▼
┌─────────────────────────────────────────┐
│ Main Deep Agent (create_deep_agent)     │
│ - write_todos (built-in)                │
│ - skills (progressive disclosure)       │
│ - get_user_profile                      │
│ - doc tools (docx→md, summary tree)     │
│ - token estimate / compact helpers      │
│ - task → report_analyst (parallel OK)   │
│ - built-in summarization / offloading   │
└─────────────────────────────────────────┘
           │ task(report_analyst) × N
           ▼
┌─────────────────────────────────────────┐
│ Sub-agent: report_analyst               │
│ - ensure/read summary tree              │
│ - select relevant chapter summaries     │
│ - drill to original excerpts            │
│ - return footnoted findings             │
└─────────────────────────────────────────┘
              │
              ▼
astream / Runtime events → thinking, tools, todos, final answer
```

### 3.1 Components

| Component | Responsibility |
|---|---|
| Exported `graph` | Compiled Deep Agent graph for Runtime and local `astream` |
| `report_analyst` sub-agent | Single-document analysis with isolated context |
| Skills | Task playbooks loaded on demand |
| `get_user_profile` | Read mock user JSON |
| Document tools | Convert Word, build/read summary tree, fetch chapter text |
| Sample data | Fake interview Word docs + mock users |
| Cache | Summary trees under `workspace/cache/` (gitignored) |

### 3.2 Repository layout (V1)

```text
car_deepagent/
  .env                 # local secrets (ignored)
  .env.example         # committed template
  .gitignore
  README.md
  pyproject.toml
  src/car_deepagent/
    __init__.py
    graph.py           # create_deep_agent → export graph
    config.py          # load .env, model factory
    tools/
      user_profile.py
      documents.py     # docx convert, summary tree, chapter fetch
      tokens.py        # token estimate helpers
    subagents/
      report_analyst.py
  skills/
    single-report-analysis/SKILL.md
    multi-report-synthesis/SKILL.md
    user-profile-lookup/SKILL.md
  docs/
    interviews/        # fake .docx reports
    superpowers/specs/ # this design
  data/users/          # mock user profiles
  workspace/cache/     # summary trees (ignored)
  scripts/
    smoke_astream.py   # local debug entry
```

## 4. Data flows

### 4.1 Input / session

- V1 input is message-based: the user message includes the natural-language query and absolute/relative `.docx` paths (one or many). No separate required state schema beyond LangGraph messages; Runtime can still pass `thread_id` for multi-turn.
- Multi-turn: LangGraph thread / checkpointer continuity (`thread_id`). Local smoke uses `MemorySaver`; Runtime supplies its own checkpointer.

### 4.2 Single-report analysis

1. Main agent writes todos; loads `single-report-analysis` skill.
2. Dispatches `task(report_analyst)` with doc path + question.
3. Sub-agent: if no summary-tree cache → convert docx→markdown → build chapter summary tree → persist cache; else load cache.
4. Select relevant chapter summaries; drill into original excerpts when needed.
5. Return findings with inline footnotes; main agent produces final answer + end-matter excerpts.

### 4.3 Multi-report analysis

1. Todos: per-doc analysis + synthesis.
2. Fan-out parallel `task(report_analyst)` calls in one turn when possible.
3. Main agent loads `multi-report-synthesis`, compares findings, preserves per-doc section citations.

### 4.4 User-profile assist

1. Extract lookup key (user id / name) from query or report metadata.
2. Call `get_user_profile`.
3. Cross-check profile vs report claims in the final answer.
4. Missing profile → continue with report-only analysis and note the miss.

### 4.5 Token / compact

- Full ~50k-character reports never enter the main agent context wholesale.
- Heavy work stays in sub-agent + summary tree + selective excerpt reads.
- Use Deep Agents built-in summarization / tool-result offloading as the primary compact mechanism (no separate custom compact node in V1).
- Expose `estimate_tokens`; when nearing budget, the agent should rely on built-in summarization and/or shrink tool outputs before continuing.
- If still over budget, reduce drill-down breadth (fewer chapters).

## 5. Skills (V1)

| Skill | When to load | Instructs agent to |
|---|---|---|
| `single-report-analysis` | One doc path / single-doc question | Ensure tree → analyze → footnote |
| `multi-report-synthesis` | Multiple docs / compare questions | Parallel `task` → synthesize → keep citations |
| `user-profile-lookup` | Need CRM-like context | Call `get_user_profile` → reconcile with reports |

Each skill is a directory with `SKILL.md` (Agent Skills frontmatter + body). Progressive disclosure: metadata at startup, full body when needed.

## 6. Tools

### 6.1 Built-in (Deep Agents)

- `write_todos` — planning; state-visible for future frontend
- Filesystem tools (`ls`, `read_file`, `write_file`, `grep`, `glob`, …) scoped to workspace
- `task` — spawn `report_analyst` only. Disable the default general-purpose sub-agent in V1 to keep delegation deterministic.

### 6.2 Custom

| Tool | Behavior |
|---|---|
| `get_user_profile(user_id \| name)` | Load `data/users/{id}.json` or search by name; structured miss if absent |
| `ensure_document_markdown(path)` | Convert `.docx` → cached `.md` under workspace via `python-docx` |
| `ensure_summary_tree(doc_id)` | If cache missing: split markdown into chapters (headings / interview section markers), call the configured LLM once per chapter to write short summaries, persist tree JSON; if cache exists: return path/metadata only |
| `get_chapter_summary(doc_id, chapter_id)` | Return one chapter summary |
| `get_chapter_excerpt(doc_id, chapter_id, optional offset/limit)` | Return original text slice for citation |
| `estimate_tokens(text \| messages)` | Rough token count for compact decisions |

Fake reports are generated as real `.docx` files with `python-docx`.

## 7. Citation format

Inline:

```text
受访者对高阶智驾的信任仍偏谨慎[^interview_001§3.2]。
```

End of answer:

```text
## 参考文献摘录
[^interview_001§3.2]: 「……原文片段……」（docs/interviews/interview_001.docx · 第三章 · 智驾体验）
```

Sub-agent outputs must already include footnotes so the main agent can preserve them during synthesis.

## 8. Streaming / observability

Consumers of `astream` (and later Runtime) should observe:

- Model token / reasoning stream
- Tool call + tool result events
- Todo state changes from `write_todos`
- Sub-agent task streams when available (`stream.subagents`)
- Final AI message

V1 does not build UI; these event types are the contract for a future frontend.

## 9. Configuration

Load from project root `.env`:

```text
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-flash
LLM_TIMEOUT_MS=60000
```

Model construction: OpenAI-compatible chat model pointing at `LLM_BASE_URL`.  
Never commit `.env`. Commit `.env.example` only.

## 10. Sample data (fabricated, non-sensitive)

Because real interviews are confidential, V1 ships **fake** HarmonyOS Intelligent Mobility user interview reports:

- 2–3 `.docx` files under `docs/interviews/`
- Full interview structure: background, purchase journey, cockpit/HMI, ADS/NOA experience, service/OTA, NPS-style wrap-up
- Length: aim toward long-form; at least one doc long enough to exercise summary-tree + compact paths
- Matching `data/users/*.json` profiles (id, vehicle, stage, demographics as mock fields)

## 11. Error handling

| Case | Behavior |
|---|---|
| Missing / non-docx path | Tool error string; agent asks for correction; thread continues |
| Summary-tree build failure | Do not write corrupt cache; surface error; keep partial md if valid |
| User profile miss | Explicit miss; continue report-only |
| LLM timeout | Honor `LLM_TIMEOUT_MS`; one tool-level retry where safe; error in stream |
| Context overflow | Estimate → compact → narrow chapter drill-down |

## 12. Testing (V1)

- Smoke: `scripts/smoke_astream.py` single-doc, multi-doc, profile lookup
- Assert summary tree created once and reused
- Assert final answer contains footnote markers
- Assert todos appear in streamed/state updates
- No frontend, auth, real CRM, or production deploy config

## 13. Non-goals (V1)

- Web/UI
- Real user databases or HTTP CRM
- Auth / tenancy
- Evaluation harness beyond smoke
- Hard-coded multi-node custom LangGraph replacing Deep Agents

## 14. Implementation principles

- Prefer Deep Agents built-ins over custom graph nodes.
- Keep main-agent context small; quarantine document work in `report_analyst`.
- Cache summary trees; never re-ingest full text into the parent context.
- Skills encode process; tools encode I/O; prompts stay thin.
- Secrets stay local; example env is the only env artifact in git.

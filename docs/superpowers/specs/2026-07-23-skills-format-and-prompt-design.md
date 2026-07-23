# Skills Format Alignment + System Prompt Dedup

Date: 2026-07-23  
Status: Approved for implementation planning  
Related: `2026-07-22-car-deepagent-design.md`, `2026-07-22-skill-commands-ui-design.md`

## 1. Goal

1. Align project `skills/*/SKILL.md` frontmatter with the [Agent Skills specification](https://agentskills.io/specification) as consumed by deepagents `SkillsMiddleware`.
2. Stop duplicating skill-loading instructions in `MAIN_PROMPT`; rely on deepagents’ built-in **Skills System** injection when `skills=` is set.
3. Fix the awkward source label `**Skills Skills**` caused by bare path `"/skills/"`.

## 2. Confirmed behavior (deepagents)

When `create_deep_agent(..., skills=[...])` is used, deepagents appends `SkillsMiddleware`, which:

1. Scans each skill source for `*/SKILL.md`, parses YAML frontmatter into metadata.
2. Injects a **Skills System** section into the system prompt (name, description, path, progressive-disclosure `read_file` guidance with `limit=1000`).

Project skills are already discoverable under `/skills/`. No custom Skills System template is required for this change.

## 3. Decisions (locked)

| Topic | Choice |
|---|---|
| Frontmatter scope | Align required/optional fields to Agent Skills / deepagents (option **A**) |
| System prompt strategy | Remove skill-load rules from `MAIN_PROMPT`; use deepagents default Skills System only (option **A**) |
| Source registration | Use labeled tuple `("/skills/", "Project")` so the prompt shows `**Project Skills**` |
| Skill body language / structure | Out of scope (keep existing English Instructions / When to Use) |
| Custom Chinese Skills System template | Out of scope |
| Slash `/skill-name` middleware | Unchanged; synthetic `read_file` transcript remains |

## 4. Frontmatter alignment

### 4.1 Required shape (per skill)

Each `skills/<name>/SKILL.md` must:

| Field | Rule |
|---|---|
| `name` | Required; 1–64 chars; lowercase `a-z` / digits / single hyphens; no leading/trailing/consecutive hyphens; **must equal directory name** |
| `description` | Required; 1–1024 chars; describe **what** + **when**; prefer a single YAML scalar line (no need for `>` folded block) |
| `license` | Optional; keep `MIT` if present |
| `metadata` | Optional; string→string map only (e.g. `version: "1.0"`, `domain: interview-analysis`) |
| `compatibility` / `allowed-tools` | Optional; not required for this change |

### 4.2 Skills in scope

- `single-report-analysis`
- `multi-report-synthesis`
- `user-profile-lookup`

Normalize descriptions to single-line scalars while preserving trigger keywords (中文触发词保留). Do not rename directories or `name` fields.

### 4.3 Body

Markdown body has no Agent Skills format restrictions. Leave `## When to Use` / `## Instructions` as-is for this change (content quality pass is a separate follow-up if needed).

## 5. System prompt changes (`graph.py`)

### 5.1 Remove from `MAIN_PROMPT`

Delete rule **1** (match Skills System → `read_file` → do not re-read if already loaded). That guidance is already covered by deepagents’ Skills System fragment (except the project-specific “already loaded via `/skill`” tip, which we explicitly drop per decision).

Renumber remaining domain rules (filesystem allowlist, long-doc via `report_analyst`, parallel tasks, footnotes, `get_user_profile`, todos / `estimate_tokens`).

### 5.2 Skills source

```python
SKILLS_SOURCE = ("/skills/", "Project")
# passed as: skills=[SKILLS_SOURCE]
```

Do not pass a custom `system_prompt=` to `SkillsMiddleware` (keep deepagents default template).

## 6. Tests

- Keep / extend `tests/test_skills_exist.py`:
  - Three skills still listable via `_list_skills(backend, "/skills/")`.
  - Frontmatter: `name` matches directory; `description` non-empty and ≤1024; name charset rules.
- Add assertion that `SkillsMiddleware(sources=[("/skills/", "Project")])` formats locations containing `**Project Skills**` and not `**Skills Skills**`.
- Existing slash-command / middleware tests remain green without behavioral change.

## 7. Non-goals

- Rewriting skill instruction bodies into Chinese.
- Auto-injecting full `SKILL.md` bodies into the system prompt (progressive disclosure stays).
- Changing `SkillCommandMiddleware` or frontend Skills panel.
- Installing or depending on external `skills-ref` CLI (optional local validation only if already available; not a CI requirement for this change).

## 8. Success criteria

1. Frontmatter of all three skills complies with Agent Skills constraints used by deepagents.
2. `MAIN_PROMPT` no longer instructs how to load skills via `read_file`.
3. Injected Skills System lists the three skills under `**Project Skills**`.
4. Relevant unit tests pass.

# Skills Format + Prompt Dedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align three project skills’ YAML frontmatter with the Agent Skills / deepagents spec, and remove duplicate skill-loading instructions from `MAIN_PROMPT` so deepagents’ built-in Skills System is the sole loader.

**Architecture:** Keep progressive disclosure via `SkillsMiddleware`. Register skills as a labeled source tuple `("/skills/", "Project")`. Domain rules stay in `MAIN_PROMPT`; skill discovery/load guidance comes only from deepagents’ default Skills System fragment.

**Tech Stack:** Python 3.11+, pytest, deepagents `SkillsMiddleware` / `_list_skills`, PyYAML (already pulled in by deepagents).

## Global Constraints

- Frontmatter must satisfy Agent Skills: `name` 1–64, lowercase alnum + single hyphens, equals directory name; `description` 1–1024, WHAT + WHEN.
- Do not rename skill directories or `name` fields.
- Do not customize `SkillsMiddleware`’s `system_prompt` template.
- Do not change `SkillCommandMiddleware` or frontend Skills panel.
- Do not rewrite skill instruction bodies into Chinese.
- Do not commit `.env` or secrets.
- Follow TDD: failing test → implement → pass → commit per task (skip commit if the user asked not to commit).

---

## File Structure

| Path | Responsibility |
|---|---|
| `skills/single-report-analysis/SKILL.md` | Normalize frontmatter to single-line `description` |
| `skills/multi-report-synthesis/SKILL.md` | Same |
| `skills/user-profile-lookup/SKILL.md` | Same |
| `src/car_deepagent/graph.py` | Strip skill-load rules from `MAIN_PROMPT`; labeled `SKILLS_SOURCE` |
| `tests/test_skills_exist.py` | Agent Skills frontmatter checks + Project Skills label |
| `docs/superpowers/specs/2026-07-23-skills-format-and-prompt-design.md` | Spec (already written; no edit required unless drift) |

---

### Task 1: Agent Skills frontmatter validation + normalize SKILL.md

**Files:**
- Modify: `tests/test_skills_exist.py`
- Modify: `skills/single-report-analysis/SKILL.md`
- Modify: `skills/multi-report-synthesis/SKILL.md`
- Modify: `skills/user-profile-lookup/SKILL.md`

**Interfaces:**
- Consumes: `repo_root()`, skill dirs under `skills/`
- Produces: stricter frontmatter assertions; three SKILL.md files with single-line `description` scalars

- [ ] **Step 1: Write the failing / stricter tests**

Replace / extend `tests/test_skills_exist.py` so it includes:

```python
from __future__ import annotations

import re

import yaml
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware, _list_skills

from car_deepagent.paths import repo_root

REQUIRED_SECTIONS = ("## When to Use", "## Instructions")
SKILL_NAMES = [
    "single-report-analysis",
    "multi-report-synthesis",
    "user-profile-lookup",
]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    match = FRONTMATTER_RE.match(text)
    assert match, "missing YAML frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def test_three_skills_have_frontmatter():
    root = repo_root() / "skills"
    for name in SKILL_NAMES:
        text = (root / name / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---")
        data = _parse_frontmatter(text)
        assert data.get("name") == name
        assert "description" in data
        for section in REQUIRED_SECTIONS:
            assert section in text, f"{name} missing {section}"


def test_skill_frontmatter_matches_agent_skills_spec():
    root = repo_root() / "skills"
    for name in SKILL_NAMES:
        text = (root / name / "SKILL.md").read_text(encoding="utf-8")
        # Prefer single-line description scalar (no folded `>` block)
        assert re.search(r"^description:\s*>\s*$", text, re.MULTILINE) is None, (
            f"{name}: use a single-line description scalar, not folded `>`"
        )
        data = _parse_frontmatter(text)
        skill_name = str(data["name"]).strip()
        description = str(data["description"]).strip()
        assert 1 <= len(skill_name) <= 64
        assert NAME_RE.fullmatch(skill_name), skill_name
        assert skill_name == name
        assert 1 <= len(description) <= 1024
        assert "\n" not in description
        metadata = data.get("metadata") or {}
        assert isinstance(metadata, dict)
        for key, value in metadata.items():
            assert isinstance(key, str)
            assert isinstance(value, (str, int, float)), f"{name} metadata[{key}]"


def test_skills_listable_via_filesystem_backend():
    backend = FilesystemBackend(root_dir=str(repo_root()), virtual_mode=True)
    skills = _list_skills(backend, "/skills/")
    names = {s["name"] for s in skills}
    assert names == set(SKILL_NAMES)
    for skill in skills:
        assert skill["path"].startswith("/skills/")
        assert skill["path"].endswith("/SKILL.md")
        assert skill["description"]


def test_skills_source_label_is_project():
    backend = FilesystemBackend(root_dir=str(repo_root()), virtual_mode=True)
    mw = SkillsMiddleware(backend=backend, sources=[("/skills/", "Project")])
    locations = mw._format_skills_locations()
    assert "**Project Skills**" in locations
    assert "**Skills Skills**" not in locations
```

Note: `test_skills_source_label_is_project` does not depend on `graph.py` yet; it locks the intended source shape. Keep it in this file for Task 1; Task 2 will assert `graph.SKILLS_SOURCE` matches.

- [ ] **Step 2: Run tests to verify the frontmatter assertion fails**

Run:

```bash
cd /home/admin/car_deepagent && .venv/bin/pytest tests/test_skills_exist.py::test_skill_frontmatter_matches_agent_skills_spec -v
```

Expected: FAIL with message about folded `>` description (current SKILL.md files use `description: >`).

- [ ] **Step 3: Normalize the three SKILL.md frontmatter blocks**

Only change the YAML frontmatter; leave the Markdown body untouched.

`skills/single-report-analysis/SKILL.md` frontmatter:

```yaml
---
name: single-report-analysis
description: Analyze a single HarmonyOS Intelligent Mobility (鸿蒙智行) user interview Word report (.docx). Use when the user asks about one interview document, one doc path, NOA/智驾/座舱态度, 单篇报告分析, or footnote-cited findings from a single report.
license: MIT
metadata:
  version: "1.0"
  domain: interview-analysis
---
```

`skills/multi-report-synthesis/SKILL.md` frontmatter:

```yaml
---
name: multi-report-synthesis
description: Compare and synthesize multiple HarmonyOS interview reports. Use when the user provides two or more .docx paths, asks to 对比/综合/差异分析 across interviews, or wants a multi-document synthesis with per-doc footnotes.
license: MIT
metadata:
  version: "1.0"
  domain: interview-analysis
---
```

`skills/user-profile-lookup/SKILL.md` frontmatter:

```yaml
---
name: user-profile-lookup
description: Look up a mock CRM user profile and reconcile it with interview findings. Use when the user mentions user_id (e.g. U001), a name like 陈思远/林婉清/周启明, 用户画像, CRM, or asks to cross-check profile vs report claims.
license: MIT
metadata:
  version: "1.0"
  domain: interview-analysis
---
```

After each `---`, keep the existing `# ...` body exactly as before.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /home/admin/car_deepagent && .venv/bin/pytest tests/test_skills_exist.py -v
```

Expected: all tests in the file PASS.

- [ ] **Step 5: Commit** (only if the user asked to commit)

```bash
git add tests/test_skills_exist.py \
  skills/single-report-analysis/SKILL.md \
  skills/multi-report-synthesis/SKILL.md \
  skills/user-profile-lookup/SKILL.md
git commit -m "$(cat <<'EOF'
fix: align skill frontmatter with Agent Skills spec

EOF
)"
```

---

### Task 2: Dedup MAIN_PROMPT + labeled skills source

**Files:**
- Modify: `tests/test_skills_exist.py` (add graph assertions)
- Modify: `src/car_deepagent/graph.py`

**Interfaces:**
- Consumes: Task 1’s `SKILLS_SOURCE` label convention `("/skills/", "Project")`
- Produces: `graph.SKILLS_SOURCE == ("/skills/", "Project")`; `MAIN_PROMPT` without skill-load / `read_file` SKILL guidance

- [ ] **Step 1: Write the failing graph tests**

Append to `tests/test_skills_exist.py`:

```python
def test_main_prompt_does_not_duplicate_skills_loading():
    from car_deepagent import graph as graph_mod

    prompt = graph_mod.MAIN_PROMPT
    assert "Skills System" not in prompt
    assert "read_file" not in prompt
    assert "/skills/<skill-name>/SKILL.md" not in prompt
    assert "limit=1000" not in prompt
    # Domain rules remain
    assert "report_analyst" in prompt
    assert "get_user_profile" in prompt
    assert "[^doc§chapter]" in prompt


def test_skills_source_is_labeled_project_tuple():
    from car_deepagent import graph as graph_mod

    assert graph_mod.SKILLS_SOURCE == ("/skills/", "Project")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /home/admin/car_deepagent && .venv/bin/pytest \
  tests/test_skills_exist.py::test_main_prompt_does_not_duplicate_skills_loading \
  tests/test_skills_exist.py::test_skills_source_is_labeled_project_tuple -v
```

Expected: FAIL (`Skills System` still in prompt; `SKILLS_SOURCE` is still `"/skills/"`).

- [ ] **Step 3: Update `graph.py`**

Set:

```python
SKILLS_SOURCE = ("/skills/", "Project")
```

Replace `MAIN_PROMPT` with:

```python
MAIN_PROMPT = """你是鸿蒙智行用户调研访谈分析智能体。
能力：单篇/多篇报告分析、用户画像交叉验证、todo 规划、脚注溯源、skills。

规则：
1. 文件系统只允许读取：/skills/**、/docs/interviews/**、
   /workspace/cache/summary_trees/**、/workspace/cache/markdown/**。
   访谈 Word 报告一律在 docs/interviews/ 下查找；可用完整路径、文件名或 stem
   （如 interview_001）。若运行上下文提供了 analysis_doc_paths（界面勾选），
   本轮只能分析这些路径，不要打开列表外的访谈文档。
2. 长文必须通过 report_analyst 或摘要树工具处理，禁止把全文读进主上下文。
3. 多篇时尽量并行 task(report_analyst)。
4. 回答使用 [^doc§chapter] 脚注，并附 ## 参考文献摘录。
5. 需要用户信息时调用 get_user_profile。
6. 使用 write_todos 跟踪步骤；上下文将满时用 estimate_tokens 并依赖内置压缩。
"""
```

Keep `skills=[SKILLS_SOURCE]` unchanged in `create_deep_agent(...)`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /home/admin/car_deepagent && .venv/bin/pytest tests/test_skills_exist.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit** (only if the user asked to commit)

```bash
git add tests/test_skills_exist.py src/car_deepagent/graph.py
git commit -m "$(cat <<'EOF'
fix: rely on deepagents Skills System for skill loading

EOF
)"
```

---

### Task 3: Regression — slash commands + permissions still green

**Files:**
- Test only (no production edits expected): `tests/test_skill_commands.py`, `tests/test_skill_command_middleware.py`, `tests/test_fs_permissions.py`, `tests/test_skills_exist.py`

**Interfaces:**
- Consumes: Task 1–2 outcomes
- Produces: green regression on skill-adjacent suites

- [ ] **Step 1: Run the related test suites**

```bash
cd /home/admin/car_deepagent && .venv/bin/pytest \
  tests/test_skills_exist.py \
  tests/test_skill_commands.py \
  tests/test_skill_command_middleware.py \
  tests/test_fs_permissions.py -v
```

Expected: all PASS.

- [ ] **Step 2: If anything fails, fix only the regressions introduced by Tasks 1–2**

Likely causes: none expected. Slash command paths still `/skills/<name>/SKILL.md`. Permissions still allow `/skills/**`.

- [ ] **Step 3: Re-run until green**

Same command as Step 1. Expected: PASS.

- [ ] **Step 4: Commit** (only if the user asked to commit and there were fix commits; otherwise skip)

No new commit if Step 1 was already green.

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Frontmatter Agent Skills alignment | Task 1 |
| Single-line `description` | Task 1 |
| Remove MAIN_PROMPT skill-load rules | Task 2 |
| `skills=[("/skills/", "Project")]` | Task 2 |
| No custom Skills System template | Task 2 (unchanged middleware) |
| Slash middleware unchanged | Task 3 regression |
| Success criteria / tests | Tasks 1–3 |

## Self-review notes

- No TBD/placeholder steps.
- `SKILLS_SOURCE` type becomes `tuple[str, str]`; `create_deep_agent(skills=[...])` already accepts `SkillSource` unions.
- Dropped “already loaded via `/skill` do not re-read” tip intentionally per spec.

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


def test_main_prompt_does_not_duplicate_skills_loading():
    from car_deepagent import graph as graph_mod

    prompt = graph_mod.MAIN_PROMPT
    assert "Skills System" not in prompt
    assert "/skills/<skill-name>/SKILL.md" not in prompt
    assert "limit=1000" not in prompt
    # Domain rules remain
    assert "report_analyst" in prompt
    assert "get_user_profile" in prompt
    assert "[^doc§L123]" in prompt


def test_skills_source_is_labeled_project_tuple():
    from car_deepagent import graph as graph_mod

    assert graph_mod.SKILLS_SOURCE == ("/skills/", "Project")

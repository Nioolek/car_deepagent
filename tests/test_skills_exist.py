from car_deepagent.paths import repo_root


REQUIRED_SECTIONS = ("## When to Use", "## Instructions")


def test_three_skills_have_frontmatter():
    root = repo_root() / "skills"
    names = [
        "single-report-analysis",
        "multi-report-synthesis",
        "user-profile-lookup",
    ]
    for name in names:
        text = (root / name / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---")
        assert f"name: {name}" in text
        assert "description:" in text
        for section in REQUIRED_SECTIONS:
            assert section in text, f"{name} missing {section}"


def test_skills_listable_via_filesystem_backend():
    from deepagents.backends.filesystem import FilesystemBackend
    from deepagents.middleware.skills import _list_skills

    backend = FilesystemBackend(root_dir=str(repo_root()), virtual_mode=True)
    skills = _list_skills(backend, "/skills/")
    names = {s["name"] for s in skills}
    assert names == {
        "single-report-analysis",
        "multi-report-synthesis",
        "user-profile-lookup",
    }
    for skill in skills:
        assert skill["path"].startswith("/skills/")
        assert skill["path"].endswith("/SKILL.md")
        assert skill["description"]

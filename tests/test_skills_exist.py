from car_deepagent.paths import repo_root


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

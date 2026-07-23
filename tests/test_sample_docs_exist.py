from car_deepagent.paths import interviews_dir


def test_sample_interview_markdown_files_exist():
    for name in ("interview_001.md", "interview_002.md", "interview_003.md"):
        path = interviews_dir() / name
        assert path.is_file(), f"missing {path}"


def test_sample_interview_markdown_contains_expected_markers():
    expected = {
        "interview_001.md": ("U001", "陈思远", "上海", "问界 M7"),
        "interview_002.md": ("U002", "林婉清", "深圳", "智界 R7"),
        "interview_003.md": ("U003", "周启明", "杭州", "享界 S9"),
    }
    for name, markers in expected.items():
        text = (interviews_dir() / name).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in text, f"{name} missing {marker}"


def test_sample_interview_001_has_sections():
    text = (interviews_dir() / "interview_001.md").read_text(encoding="utf-8")
    assert "## 背景" in text
    assert "## 智驾/NOA" in text
    assert "虚构样例" in text

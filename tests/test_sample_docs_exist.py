from car_deepagent.paths import interviews_dir


def test_three_interviews_exist():
    directory = interviews_dir()
    for name in ("interview_001.docx", "interview_002.docx", "interview_003.docx"):
        assert (directory / name).exists(), name

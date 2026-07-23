from deepagents.middleware.filesystem import _check_fs_permission

from car_deepagent.fs_permissions import (
    ALLOWED_READ_GLOBS,
    build_filesystem_permissions,
)


def test_allowed_read_globs_cover_required_roots():
    assert "/skills/**" in ALLOWED_READ_GLOBS
    assert "/docs/interviews/**" in ALLOWED_READ_GLOBS
    assert "/workspace/cache/markdown/**" in ALLOWED_READ_GLOBS
    assert "/workspace/cache/doc_maps/**" in ALLOWED_READ_GLOBS


def test_permissions_allow_whitelisted_reads():
    rules = build_filesystem_permissions()
    assert (
        _check_fs_permission(rules, "read", "/skills/single-report-analysis/SKILL.md")
        == "allow"
    )
    assert (
        _check_fs_permission(rules, "read", "/docs/interviews/interview_001.docx")
        == "allow"
    )
    assert (
        _check_fs_permission(
            rules,
            "read",
            "/workspace/cache/markdown/interview_001.md",
        )
        == "allow"
    )
    assert (
        _check_fs_permission(
            rules,
            "read",
            "/workspace/cache/doc_maps/interview_001.json",
        )
        == "allow"
    )


def test_permissions_deny_other_reads_and_all_writes():
    rules = build_filesystem_permissions()
    assert _check_fs_permission(rules, "read", "/README.md") == "deny"
    assert _check_fs_permission(rules, "read", "/src/car_deepagent/graph.py") == "deny"
    assert _check_fs_permission(rules, "read", "/data/users/U001.json") == "deny"
    assert _check_fs_permission(rules, "read", "/docs/superpowers/specs/x.md") == "deny"
    assert (
        _check_fs_permission(rules, "write", "/docs/interviews/interview_001.docx")
        == "deny"
    )
    assert _check_fs_permission(rules, "write", "/skills/x/SKILL.md") == "deny"

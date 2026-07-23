from __future__ import annotations

from deepagents import FilesystemPermission

# Virtual paths under FilesystemBackend(root_dir=repo, virtual_mode=True).
ALLOWED_READ_GLOBS = (
    "/skills/**",
    "/docs/interviews/**",
    "/workspace/cache/doc_maps/**",
)


def build_filesystem_permissions() -> list[FilesystemPermission]:
    """Allow-list agent filesystem reads; deny everything else (read + write).

    First matching rule wins. Custom tools (document/profile) bypass this and
    already resolve only under interviews / cache / data as implemented.
    """
    return [
        FilesystemPermission(
            operations=["read"],
            paths=list(ALLOWED_READ_GLOBS),
            mode="allow",
        ),
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/**"],
            mode="deny",
        ),
    ]

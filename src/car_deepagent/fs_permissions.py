from __future__ import annotations

from deepagents import FilesystemPermission

# Virtual paths under FilesystemBackend(root_dir=repo, virtual_mode=True).
# Include bare directory roots so ls/glob on /skills or /docs/interviews work
# (/** globs alone do not match the directory path without a trailing segment).
# /large_tool_results/** is required: deepagents offloads oversized tool payloads
# there and instructs the model to read_file/grep those paths.
ALLOWED_READ_GLOBS = (
    "/skills",
    "/skills/",
    "/skills/**",
    "/docs/interviews",
    "/docs/interviews/",
    "/docs/interviews/**",
    "/workspace/cache/doc_maps",
    "/workspace/cache/doc_maps/",
    "/workspace/cache/doc_maps/**",
    "/large_tool_results",
    "/large_tool_results/",
    "/large_tool_results/**",
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

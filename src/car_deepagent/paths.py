from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return repository root (directory containing pyproject.toml)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate repo root with pyproject.toml")


def data_users_dir() -> Path:
    return repo_root() / "data" / "users"


def interviews_dir() -> Path:
    return repo_root() / "docs" / "interviews"


def cache_dir() -> Path:
    path = repo_root() / "workspace" / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def summary_trees_dir() -> Path:
    path = cache_dir() / "summary_trees"
    path.mkdir(parents=True, exist_ok=True)
    return path


def markdown_cache_dir() -> Path:
    path = cache_dir() / "markdown"
    path.mkdir(parents=True, exist_ok=True)
    return path

from __future__ import annotations

import json

from langchain_core.tools import tool

from car_deepagent.paths import data_users_dir


def _load_all_profiles() -> list[dict]:
    profiles: list[dict] = []
    root = data_users_dir()
    if not root.exists():
        return profiles
    for path in sorted(root.glob("*.json")):
        profiles.append(json.loads(path.read_text(encoding="utf-8")))
    return profiles


@tool
def get_user_profile(user_id: str | None = None, name: str | None = None) -> str:
    """Lookup a mock HarmonyOS Intelligent Mobility user profile by user_id or name."""
    if not user_id and not name:
        return json.dumps(
            {"found": False, "error": "Provide user_id or name"},
            ensure_ascii=False,
        )
    profiles = _load_all_profiles()
    for p in profiles:
        if user_id and p.get("user_id") == user_id:
            return json.dumps({"found": True, "profile": p}, ensure_ascii=False)
        if name and p.get("name") == name:
            return json.dumps({"found": True, "profile": p}, ensure_ascii=False)
    return json.dumps(
        {"found": False, "user_id": user_id, "name": name},
        ensure_ascii=False,
    )

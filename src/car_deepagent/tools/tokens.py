from __future__ import annotations

import json

from langchain_core.tools import tool


def _count(text: str) -> tuple[int, str]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text)), "tiktoken"
    except Exception:  # noqa: BLE001
        return max(1, len(text) // 4), "char_div_4"


@tool
def estimate_tokens(text: str) -> str:
    """Estimate token count for a text blob to decide whether to compact context."""
    tokens, method = _count(text or "")
    return json.dumps({"tokens": tokens, "method": method}, ensure_ascii=False)

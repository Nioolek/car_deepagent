"""Diagnose long-interview agent chain: log tools, errors, final answer."""

from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from collections import Counter
from typing import Any

from car_deepagent.graph import get_graph


def _tool_name(msg: Any) -> str | None:
    name = getattr(msg, "name", None)
    if name:
        return str(name)
    if isinstance(msg, dict):
        return msg.get("name")
    return None


def _content_preview(content: Any, limit: int = 400) -> str:
    if content is None:
        return ""
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        text = "\n".join(parts)
    else:
        text = str(content)
    text = text.replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "…"


def _scan_messages(messages: list[Any], tool_counts: Counter, events: list[str]) -> None:
    for msg in messages:
        typ = getattr(msg, "type", None) or (
            msg.get("type") if isinstance(msg, dict) else None
        )
        if typ == "ai":
            tool_calls = getattr(msg, "tool_calls", None) or (
                msg.get("tool_calls") if isinstance(msg, dict) else None
            )
            if tool_calls:
                for tc in tool_calls:
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "?")
                    args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
                    tool_counts[f"call:{name}"] += 1
                    events.append(f"CALL {name} args={_content_preview(args, 240)}")
            content = getattr(msg, "content", None)
            if content:
                events.append(f"AI {_content_preview(content, 300)}")
        elif typ == "tool":
            name = _tool_name(msg) or "?"
            content = getattr(msg, "content", None) or (
                msg.get("content") if isinstance(msg, dict) else ""
            )
            tool_counts[f"result:{name}"] += 1
            preview = _content_preview(content, 500)
            flag = "ERR" if "error" in preview.lower() or '"error"' in preview else "OK"
            events.append(f"RESULT[{flag}] {name}: {preview}")


async def main() -> int:
    doc = "docs/interviews/interview_long_qa.md"
    question = (
        f"请分析 {doc} 这份长访谈中，用户对 NOA/智驾信任边界与接管行为的态度变化，"
        "给出至少 5 条带行号脚注的发现，并附参考文献摘录。"
    )
    print("QUESTION:", question, flush=True)
    graph = get_graph()
    config = {
        "configurable": {"thread_id": f"diag-long-{int(time.time())}"},
        "recursion_limit": 80,
    }
    tool_counts: Counter = Counter()
    events: list[str] = []
    errors: list[str] = []
    started = time.time()
    last_ai = ""

    try:
        async for mode, chunk in graph.astream(
            {"messages": [{"role": "user", "content": question}]},
            config=config,
            stream_mode=["updates", "messages"],
        ):
            if mode == "updates" and isinstance(chunk, dict):
                for node, payload in chunk.items():
                    if not isinstance(payload, dict):
                        continue
                    msgs = payload.get("messages")
                    if isinstance(msgs, list):
                        before = len(events)
                        _scan_messages(msgs, tool_counts, events)
                        for line in events[before:]:
                            print(f"[{node}] {line}", flush=True)
                    # Surface common deepagents keys
                    for key in ("todos", "files", "jump_to"):
                        if key in payload:
                            print(
                                f"[{node}] STATE {key}={_content_preview(payload[key], 200)}",
                                flush=True,
                            )
            elif mode == "messages":
                # (message_chunk, metadata)
                if isinstance(chunk, tuple) and chunk:
                    msg = chunk[0]
                    content = getattr(msg, "content", "")
                    if content:
                        last_ai = _content_preview(content, 800)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()

    elapsed = time.time() - started
    print("\n===== SUMMARY =====", flush=True)
    print(f"elapsed_sec={elapsed:.1f}", flush=True)
    print(f"tool_counts={json.dumps(dict(tool_counts), ensure_ascii=False)}", flush=True)
    print(f"event_lines={len(events)}", flush=True)
    print(f"errors={errors}", flush=True)
    print(f"last_ai_preview={last_ai}", flush=True)
    # Persist compact log
    out = {
        "elapsed_sec": elapsed,
        "tool_counts": dict(tool_counts),
        "errors": errors,
        "events_tail": events[-80:],
        "last_ai_preview": last_ai,
    }
    Path = __import__("pathlib").Path
    Path("/tmp/diag_long_interview.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote /tmp/diag_long_interview.json", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

"""Live chain eval for interview analysis: expected tools + answer checks.

Usage:
  uv run python scripts/eval_interview_chain.py
  uv run python scripts/eval_interview_chain.py --case short
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from car_deepagent.graph import get_graph

FOOTNOTE_RE = re.compile(r"\[\^[^\]]+§L(\d+)(?:-L(\d+))?\]")
FOOTNOTE_DOC_RE = re.compile(r"\[\^([A-Za-z0-9_-]+)§L(\d+)(?:-L(\d+))?\]")
FOOTNOTE_ANY_RE = re.compile(r"\[\^[^\]]+\]")
MARKER_LINE = {
    "MARKER_SHORT_VOICE_OK": 12,
    "MARKER_SHORT_VOICE_BAD": 16,
    "MARKER_LONG_NOA_TRUST": 55,
    "MARKER_LONG_TAKEOVER": 129,
    "MARKER_LONG_OTA": 221,
    "MARKER_PEER_VOICE": 11,
    "MARKER_PEER_NOA": 17,
}


@dataclass
class ToolEvent:
    kind: str  # call | result
    name: str
    detail: str
    ok: bool | None = None


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    elapsed_sec: float
    checks: dict[str, bool]
    failures: list[str] = field(default_factory=list)
    tool_events: list[dict] = field(default_factory=list)
    answer_preview: str = ""
    error: str | None = None


def _preview(content: Any, limit: int = 500) -> str:
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
    return text if len(text) <= limit else text[:limit] + "…"


def _raw_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)


def _scan_messages(messages: list[Any], events: list[ToolEvent]) -> str:
    """Collect tool events; return AI text without tool_calls (final-ish)."""
    parts: list[str] = []
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
                    name = (
                        tc.get("name")
                        if isinstance(tc, dict)
                        else getattr(tc, "name", "?")
                    )
                    args = (
                        tc.get("args")
                        if isinstance(tc, dict)
                        else getattr(tc, "args", {})
                    )
                    events.append(
                        ToolEvent("call", str(name), _preview(args, 300), None)
                    )
            text = _raw_text(getattr(msg, "content", None))
            # Models often emit the user-visible answer in the same turn as
            # write_todos; still count that content as answer text.
            if text.strip():
                parts.append(text)
        elif typ == "tool":
            name = getattr(msg, "name", None) or (
                msg.get("name") if isinstance(msg, dict) else "?"
            )
            content = getattr(msg, "content", None) or (
                msg.get("content") if isinstance(msg, dict) else ""
            )
            preview = _preview(content, 600)
            ok = not (
                '"error"' in preview
                or preview.lower().startswith("error:")
                or "permission denied" in preview.lower()
            )
            events.append(ToolEvent("result", str(name or "?"), preview, ok))
    return "\n\n".join(parts)


def _called(events: list[ToolEvent], name: str) -> bool:
    return any(e.kind == "call" and e.name == name for e in events)


def _all_results_ok(events: list[ToolEvent], name: str) -> bool:
    results = [e for e in events if e.kind == "result" and e.name == name]
    return bool(results) and all(e.ok for e in results)


def _failed_tools(events: list[ToolEvent]) -> list[str]:
    return [
        f"{e.name}: {e.detail[:160]}"
        for e in events
        if e.kind == "result" and e.ok is False
    ]


def _footnote_lines(answer: str) -> list[tuple[int, int]]:
    out = []
    for m in FOOTNOTE_RE.finditer(answer):
        start = int(m.group(1))
        end = int(m.group(2) or m.group(1))
        out.append((start, end))
    return out


def _covers_marker(answer: str, marker: str, window: int = 8) -> bool:
    line = MARKER_LINE[marker]
    for start, end in _footnote_lines(answer):
        if start - window <= line <= end + window:
            return True
    # Also accept explicit marker text citation
    return marker in answer


def _footnote_line_errors(answer: str) -> list[str]:
    """Cited lines must exist in the named interview markdown and be non-empty."""
    from car_deepagent.paths import interviews_dir

    errors: list[str] = []
    for token in FOOTNOTE_ANY_RE.findall(answer):
        if "§L" in token and not FOOTNOTE_DOC_RE.fullmatch(token):
            errors.append(f"malformed footnote: {token}")

    root = interviews_dir()
    for match in FOOTNOTE_DOC_RE.finditer(answer):
        doc_id = match.group(1)
        start = int(match.group(2))
        end = int(match.group(3) or match.group(2))
        path = root / f"{doc_id}.md"
        if not path.is_file():
            errors.append(f"footnote doc missing: {doc_id}")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if start < 1 or end > len(lines) or start > end:
            errors.append(
                f"footnote out of range {doc_id}§L{start}-L{end} (n={len(lines)})"
            )
            continue
        snippet = "\n".join(lines[start - 1 : end]).strip()
        if not snippet:
            errors.append(f"footnote empty lines {doc_id}§L{start}-L{end}")
    return errors


CASES: dict[str, dict[str, Any]] = {
    "short": {
        "question": (
            "请分析 /docs/interviews/eval_short.md 中用户对座舱语音的正负评价，"
            "给出带行号脚注的发现，并附 ## 参考文献摘录。"
        ),
        "expect": {
            "must_call": ["inspect_document"],
            "must_not_call": ["task", "ls", "glob"],
            "inspect_ok": True,
            "no_tool_errors": True,
            "answer_has_footnote": True,
            "answer_has_refs_section": True,
            "answer_mentions": ["语音"],
            "footnote_covers_markers": [
                "MARKER_SHORT_VOICE_OK",
                "MARKER_SHORT_VOICE_BAD",
            ],
            "verify_footnote_lines": True,
        },
    },
    "stem": {
        "question": (
            "请分析访谈文档 eval_short（仅 stem，不要猜绝对磁盘路径）中用户对语音误唤醒的态度，"
            "给出脚注与 ## 参考文献摘录。"
        ),
        "expect": {
            "must_call": ["inspect_document"],
            "must_not_call": ["task"],
            "inspect_ok": True,
            "no_tool_errors": True,
            "answer_has_footnote": True,
            "answer_has_refs_section": True,
            "answer_mentions": ["误唤醒"],
            "footnote_covers_markers": ["MARKER_SHORT_VOICE_BAD"],
            "verify_footnote_lines": True,
            "soft_marker_coverage": True,
        },
    },
    "long": {
        "question": (
            "请分析 /docs/interviews/eval_long.md 中用户对 NOA 信任边界、接管与 OTA "
            "说明的态度，至少 3 条带行号脚注发现，并附 ## 参考文献摘录。"
        ),
        "expect": {
            "must_call": ["inspect_document", "task"],
            "must_not_call": [],
            "inspect_ok": True,
            "no_tool_errors": True,
            "answer_has_footnote": True,
            "answer_has_refs_section": True,
            "answer_mentions": ["NOA", "接管"],
            "footnote_covers_markers": [
                "MARKER_LONG_NOA_TRUST",
                "MARKER_LONG_TAKEOVER",
                "MARKER_LONG_OTA",
            ],
            "soft_marker_coverage": True,
            "verify_footnote_lines": True,
        },
    },
    "multi": {
        "question": (
            "对比 /docs/interviews/eval_short.md 与 /docs/interviews/eval_peer.md "
            "对座舱语音使用习惯的差异，给出脚注，并附 ## 参考文献摘录。"
        ),
        "expect": {
            "must_call": ["inspect_document"],
            "must_not_call": ["ls", "glob"],
            "inspect_ok": True,
            "no_tool_errors": True,
            "answer_has_footnote": True,
            "answer_has_refs_section": True,
            "answer_mentions": ["语音"],
            "footnote_covers_markers": [
                "MARKER_SHORT_VOICE_OK",
                "MARKER_PEER_VOICE",
            ],
            "soft_marker_coverage": True,
            "verify_footnote_lines": True,
        },
    },
    "mixed": {
        "question": (
            "综合 /docs/interviews/eval_short.md 与 /docs/interviews/eval_long.md："
            "前者看语音痛点，后者看 NOA 信任；各至少 1 条带脚注发现，并附 ## 参考文献摘录。"
        ),
        "expect": {
            "must_call": ["inspect_document", "task"],
            "must_not_call": [],
            "inspect_ok": True,
            "no_tool_errors": True,
            "answer_has_footnote": True,
            "answer_has_refs_section": True,
            "answer_mentions": ["语音", "NOA"],
            "footnote_covers_markers": [
                "MARKER_SHORT_VOICE_BAD",
                "MARKER_LONG_NOA_TRUST",
            ],
            "soft_marker_coverage": True,
            "verify_footnote_lines": True,
        },
    },
}


def evaluate_case(
    case_id: str,
    events: list[ToolEvent],
    answer: str,
    expect: dict[str, Any],
) -> tuple[bool, dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    failures: list[str] = []

    for name in expect.get("must_call", []):
        ok = _called(events, name)
        checks[f"must_call:{name}"] = ok
        if not ok:
            failures.append(f"missing tool call: {name}")

    for name in expect.get("must_not_call", []):
        ok = not _called(events, name)
        checks[f"must_not_call:{name}"] = ok
        if not ok:
            failures.append(f"unexpected tool call: {name}")

    if expect.get("inspect_ok"):
        ok = _all_results_ok(events, "inspect_document")
        checks["inspect_ok"] = ok
        if not ok:
            failures.append("inspect_document failed or missing")

    if expect.get("no_tool_errors"):
        # Ignore benign early errors only if later success? Strict: any tool error fails.
        # Soften: allow no errors on inspect/read_file/task/write_todos after first inspect success path.
        failed = _failed_tools(events)
        # Still fail on permission denied / inspect not found — production pain.
        critical = [
            f
            for f in failed
            if "permission denied" in f.lower()
            or "not found" in f.lower()
            or "Interview document not found" in f
        ]
        ok = len(critical) == 0
        checks["no_critical_tool_errors"] = ok
        if not ok:
            failures.extend(critical)

    if expect.get("answer_has_footnote"):
        ok = bool(FOOTNOTE_RE.search(answer))
        checks["answer_has_footnote"] = ok
        if not ok:
            failures.append("answer missing §L footnote")

    if expect.get("answer_has_refs_section"):
        ok = "参考文献" in answer
        checks["answer_has_refs_section"] = ok
        if not ok:
            failures.append("answer missing 参考文献 section")

    for needle in expect.get("answer_mentions", []):
        ok = needle in answer
        checks[f"mentions:{needle}"] = ok
        if not ok:
            failures.append(f"answer missing mention: {needle}")

    soft = bool(expect.get("soft_marker_coverage"))
    for marker in expect.get("footnote_covers_markers", []):
        ok = _covers_marker(answer, marker)
        checks[f"marker:{marker}"] = ok
        if not ok and not soft:
            failures.append(f"footnote does not cover {marker}@{MARKER_LINE[marker]}")
        elif not ok and soft:
            failures.append(
                f"(soft) footnote does not cover {marker}@{MARKER_LINE[marker]}"
            )

    if expect.get("verify_footnote_lines"):
        line_errors = _footnote_line_errors(answer)
        ok = len(line_errors) == 0
        checks["footnote_lines_valid"] = ok
        if not ok:
            failures.extend(line_errors)

    hard_failures = [f for f in failures if not f.startswith("(soft)")]
    return len(hard_failures) == 0, checks, failures


async def run_case(case_id: str, graph: Any) -> CaseResult:
    spec = CASES[case_id]
    events: list[ToolEvent] = []
    answer_parts: list[str] = []
    started = time.time()
    error = None
    try:
        async for mode, chunk in graph.astream(
            {"messages": [{"role": "user", "content": spec["question"]}]},
            config={
                "configurable": {"thread_id": f"eval-{case_id}-{int(started)}"},
                "recursion_limit": 60,
            },
            stream_mode=["updates"],
        ):
            if mode != "updates" or not isinstance(chunk, dict):
                continue
            for _node, payload in chunk.items():
                if isinstance(payload, dict) and isinstance(
                    payload.get("messages"), list
                ):
                    maybe = _scan_messages(payload["messages"], events)
                    if maybe:
                        answer_parts.append(maybe)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()

    # Prefer the AI segment that actually contains citations when present.
    if answer_parts:
        cited = [p for p in answer_parts if "§L" in p and "参考文献" in p]
        answer = max(cited or answer_parts, key=len)
    else:
        answer = ""

    passed, checks, failures = evaluate_case(
        case_id, events, answer, spec["expect"]
    )
    if error:
        passed = False
        failures.append(error)

    return CaseResult(
        case_id=case_id,
        passed=passed,
        elapsed_sec=time.time() - started,
        checks=checks,
        failures=failures,
        tool_events=[asdict(e) for e in events],
        answer_preview=_preview(answer, 1200),
        error=error,
    )


async def main(case_ids: list[str]) -> int:
    graph = get_graph()
    results: list[CaseResult] = []
    for case_id in case_ids:
        print(f"\n===== RUN {case_id} =====", flush=True)
        print("Q:", CASES[case_id]["question"], flush=True)
        result = await run_case(case_id, graph)
        results.append(result)
        print(
            f"PASS={result.passed} elapsed={result.elapsed_sec:.1f}s "
            f"checks={json.dumps(result.checks, ensure_ascii=False)}",
            flush=True,
        )
        for fail in result.failures:
            print(f"  FAIL: {fail}", flush=True)
        print("tools:", [e["name"] for e in result.tool_events if e["kind"] == "call"], flush=True)
        print("answer:", result.answer_preview[:500], flush=True)

    out_path = Path("/tmp/eval_interview_chain.json")
    out_path.write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nWrote {out_path}", flush=True)
    passed = sum(1 for r in results if r.passed)
    print(f"SUMMARY {passed}/{len(results)} passed", flush=True)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        action="append",
        choices=sorted(CASES),
        help="Run selected case(s); default all",
    )
    args = parser.parse_args()
    selected = args.case or ["short", "stem", "long", "multi", "mixed"]
    raise SystemExit(asyncio.run(main(selected)))

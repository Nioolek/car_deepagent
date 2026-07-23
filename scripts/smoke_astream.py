from __future__ import annotations

import argparse
import asyncio

from car_deepagent.graph import get_graph
from car_deepagent.paths import interviews_dir


async def run(mode: str) -> None:
    graph = get_graph()
    docs = interviews_dir()
    p1 = docs / "interview_001.md"
    p2 = docs / "interview_002.md"

    if mode == "single":
        content = f"请分析这份访谈中用户对 NOA 的态度，并给出脚注溯源。文档：{p1}"
    elif mode == "multi":
        content = f"对比两份访谈对座舱语音的评价差异。文档：{p1} 与 {p2}"
    else:
        content = f"结合用户画像 U001，分析访谈结论是否一致。文档：{p1}"

    config = {"configurable": {"thread_id": f"smoke-{mode}"}}
    async for event in graph.astream(
        {"messages": [{"role": "user", "content": content}]},
        config=config,
        stream_mode=["updates", "messages"],
    ):
        print(event, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stream a local end-to-end car_deepagent smoke run."
    )
    parser.add_argument(
        "--mode",
        choices=["single", "multi", "profile"],
        default="single",
        help="analysis scenario to run (default: single)",
    )
    args = parser.parse_args()
    asyncio.run(run(args.mode))


if __name__ == "__main__":
    main()

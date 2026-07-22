# car_deepagent

基于 [Deep Agents](https://github.com/langchain-ai/deepagents) / LangGraph 的鸿蒙智行用户访谈报告分析智能体。

支持：单篇/多篇 Word 报告问答、用户画像交叉验证、摘要树长文处理、脚注溯源、todo 规划、skills。V1 只交付可编译的 `graph`，本地用 `astream` 调试；后续可挂 LangGraph API / Runtime。

## 环境要求

- Python >= 3.11
- 推荐使用 [uv](https://github.com/astral-sh/uv)
- OpenAI 兼容的大模型 API（当前默认 DeepSeek）

## 1. 克隆与安装

```bash
git clone git@github.com:Nioolek/car_deepagent.git
cd car_deepagent
uv sync --extra dev
```

也可用 pip：

```bash
python -m pip install -e ".[dev]"
```

## 2. 配置模型密钥

复制示例环境变量并填入真实值（**不要提交 `.env`**）：

```bash
cp .env.example .env
```

`.env` 字段：

| 变量 | 说明 |
|---|---|
| `LLM_API_KEY` | API Key |
| `LLM_BASE_URL` | OpenAI 兼容 Base URL，例如 `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 模型名，例如 `deepseek-v4-flash` |
| `LLM_TIMEOUT_MS` | 超时（毫秒），默认 `60000` |

本机若已有上级目录 `/home/admin/sha/.env`，也可直接复制：

```bash
cp /home/admin/sha/.env .env
```

## 3. 启动 Agent Chat UI（双进程）

前端位于 `agent-chat-ui/`（Next.js）。本地开发需要打开两个终端，分别启动 LangGraph agent 与 UI：

**终端 1 — LangGraph agent 服务：**

```bash
uv sync --extra dev
uv run langgraph dev
```

默认监听 `http://127.0.0.1:2024`，图 ID 为 `agent`（见根目录 `langgraph.json`）。

**终端 2 — Next.js 前端：**

```bash
cd agent-chat-ui
pnpm install
pnpm dev
```

浏览器打开 `http://localhost:3000`。UI 默认直连
`http://localhost:2024` 的 `agent` 图，不显示连接配置页，也不要求 LangSmith API Key。
如需覆盖默认值，可将 `agent-chat-ui/.env.example` 复制为 `.env.local` 后修改。

在输入框中发送带访谈文件路径的问题，例如：

```text
请总结 docs/interviews/interview_001.docx 中用户对座舱语音的评价，并给出脚注溯源。
```

运行过程中可在界面中查看：

- Skills 面板：Agent 用 `read_file` 加载 `/skills/…/SKILL.md` 后标记「已加载」
- agent 的 todo 列表及状态更新
- 工具调用参数与工具结果
- 模型 thinking / reasoning 内容
- 回答中 `docs/`、`data/`、`workspace/cache/` 下文件的安全预览

## 4. 启动 / 本地调试（无 UI，推荐脚本）

本地也可直接加载 graph 并流式运行（不启动 Web UI）：

```bash
# 单篇报告分析（默认）
uv run python scripts/smoke_astream.py --mode single

# 多篇对比
uv run python scripts/smoke_astream.py --mode multi

# 报告 + 用户画像交叉验证
uv run python scripts/smoke_astream.py --mode profile
```

脚本会：

1. 读取根目录 `.env` 构建模型
2. 加载 `car_deepagent.graph:graph`
3. 用样例访谈 `docs/interviews/*.docx` 发起问题
4. 通过 `graph.astream` 打印思考/工具/todo/最终回答

预期现象：

- 流式输出中出现工具调用（如 `ensure_document_markdown`、`ensure_summary_tree`、`task` / `get_user_profile`）
- 最终回答含 `[^interview_xxx§n]` 脚注与 `## 参考文献摘录`
- 摘要树缓存写入 `workspace/cache/summary_trees/`（已 gitignore）

## 5. 自定义问题（Python）

```python
import asyncio
from car_deepagent.graph import get_graph

async def main():
    graph = get_graph()
    doc = "docs/interviews/interview_001.docx"
    query = f"请总结用户对座舱语音的评价，并给出脚注溯源。文档：{doc}"
    config = {"configurable": {"thread_id": "demo-1"}}  # 多轮对话复用同一 thread_id

    async for event in graph.astream(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
        stream_mode=["updates", "messages"],
    ):
        print(event, flush=True)

asyncio.run(main())
```

多轮对话：保持相同 `thread_id`，继续向 `messages` 追加用户问题即可。

## 6. LangGraph API / Runtime 挂载

导出入口：

```text
car_deepagent.graph:graph
```

按你的 LangGraph Runtime / `langgraph.json` 配置将该模块图挂上即可；本地开发仍优先用上一节的 `astream`。

## 7. 测试

```bash
uv run pytest -v
```

重新生成伪造访谈样例（可选）：

```bash
uv run python scripts/generate_sample_docs.py
```

## 目录速览

```text
src/car_deepagent/     # graph、tools、subagents
skills/                # 三个分析 skill
docs/interviews/       # 伪造 Word 访谈样例
data/users/            # mock 用户画像
scripts/smoke_astream.py
workspace/cache/       # 运行时缓存（不入库）
```

## License

TBD

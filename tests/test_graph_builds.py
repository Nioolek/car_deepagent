from langchain_openai import ChatOpenAI

from car_deepagent import graph as graph_mod
from car_deepagent.config import Settings


def test_build_graph_returns_compiled_graph(monkeypatch):
    monkeypatch.setattr(
        graph_mod,
        "load_settings",
        lambda: Settings("k", "https://example.com/v1", "m", 60000, thinking=False),
    )
    monkeypatch.setattr(
        graph_mod,
        "build_chat_model",
        lambda: ChatOpenAI(
            model="m",
            api_key="k",
            base_url="https://example.com/v1",
        ),
    )
    g = graph_mod.build_graph()
    assert hasattr(g, "astream")

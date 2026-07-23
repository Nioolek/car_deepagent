from car_deepagent.config import ReasoningChatOpenAI, Settings
from car_deepagent import graph as graph_mod
from deepagents.profiles.harness.harness_profiles import _harness_profile_for_model


def test_build_graph_returns_compiled_graph(monkeypatch):
    settings = Settings("k", "https://example.com/v1", "m", 60000, thinking=False)
    monkeypatch.setattr(graph_mod, "load_settings", lambda: settings)
    monkeypatch.setattr(
        graph_mod,
        "build_chat_model",
        lambda: ReasoningChatOpenAI(
            model="m",
            api_key="k",
            base_url="https://example.com/v1",
        ),
    )
    g = graph_mod.build_graph()
    assert hasattr(g, "astream")


def test_openai_compatible_model_matches_harness_profile():
    """OpenAI-standard client must match openai:{model} so GP/execute stay off."""
    settings = Settings("k", "https://api.deepseek.com/v1", "deepseek-v4-flash", 60000)
    graph_mod._disable_general_purpose(settings)
    model = ReasoningChatOpenAI(
        model=settings.model,
        api_key="k",
        base_url=settings.base_url,
    )
    profile = _harness_profile_for_model(model, None)
    assert profile.general_purpose_subagent is not None
    assert profile.general_purpose_subagent.enabled is False
    assert "execute" in (profile.excluded_tools or frozenset())

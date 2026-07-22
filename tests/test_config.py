from car_deepagent.config import load_settings
from car_deepagent.paths import repo_root


def test_repo_root_contains_pyproject():
    root = repo_root()
    assert (root / "pyproject.toml").exists()


def test_load_settings_reads_env(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "LLM_API_KEY=test-key",
                "LLM_BASE_URL=https://example.com/v1",
                "LLM_MODEL=test-model",
                "LLM_TIMEOUT_MS=12345",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CAR_DEEPAGENT_ENV_FILE", str(env))
    s = load_settings()
    assert s.api_key == "test-key"
    assert s.base_url == "https://example.com/v1"
    assert s.model == "test-model"
    assert s.timeout_ms == 12345

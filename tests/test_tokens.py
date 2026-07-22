import json

from car_deepagent.tools.tokens import estimate_tokens


def test_estimate_tokens_positive():
    raw = estimate_tokens.invoke({"text": "你好，鸿蒙智行访谈。" * 10})
    data = json.loads(raw)
    assert data["tokens"] > 0
    assert data["method"] in {"tiktoken", "char_div_4"}

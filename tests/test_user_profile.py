import json

from car_deepagent.tools.user_profile import get_user_profile


def test_get_user_by_id():
    raw = get_user_profile.invoke({"user_id": "U001"})
    data = json.loads(raw)
    assert data["found"] is True
    assert data["profile"]["user_id"] == "U001"


def test_get_user_by_name():
    raw = get_user_profile.invoke({"name": "陈思远"})
    data = json.loads(raw)
    assert data["found"] is True


def test_user_miss():
    raw = get_user_profile.invoke({"user_id": "NOPE"})
    data = json.loads(raw)
    assert data["found"] is False

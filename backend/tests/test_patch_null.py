"""PATCH 에 NOT NULL 필드를 명시적 null 로 보내면 500 대신 422 여야 한다."""

import pytest

from tests.conftest import create_item, create_skill


@pytest.fixture
def targets(client, make_user, make_prediction):
    """(url, headers) 를 리소스 종류별로 만든다."""
    h, _ = make_user()
    admin_h, _ = make_user(admin=True)
    return {
        "items": (f"/items/{create_item(client, h)['id']}", h),
        "skill-items": (f"/skill-items/{create_skill(client, h)['id']}", h),
        "predictions": (f"/predictions/{make_prediction(admin_h)['id']}", admin_h),
    }


@pytest.mark.parametrize(
    ("kind", "field"),
    [
        ("items", "title"),
        ("items", "end_time"),
        ("skill-items", "title"),
        ("predictions", "title"),
        ("predictions", "end_time"),
        ("predictions", "yes_odds"),
        ("predictions", "status"),
    ],
)
def test_null_on_required_field_is_422(client, targets, kind, field):
    url, headers = targets[kind]
    r = client.patch(url, json={field: None}, headers=headers)
    assert r.status_code == 422, r.text
    assert r.json()["detail"][0]["field"] == field


@pytest.mark.parametrize(("kind", "field"), [("items", "buy_now_price"), ("items", "description")])
def test_null_clears_optional_field(client, targets, kind, field):
    url, headers = targets[kind]
    r = client.patch(url, json={field: None}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()[field] is None


def test_review_rating_null_is_422(client, make_user):
    h, _ = make_user()
    assert client.patch("/reviews/1", json={"rating": None}, headers=h).status_code == 422

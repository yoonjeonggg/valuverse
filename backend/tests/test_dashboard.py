"""마이페이지 통합 요약 테스트 (GET /users/me/dashboard)."""

from datetime import timedelta

from app.core.timeutils import now


def _item(client, headers):
    return client.post(
        "/items",
        json={
            "title": "대시보드 상품",
            "start_price": 1000,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    ).json()


def _dash(client, headers):
    r = client.get("/users/me/dashboard", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_dashboard_empty_defaults(client, make_user):
    h, user = make_user()
    d = _dash(client, h)
    assert d["user_id"] == user["id"]
    assert d["points"] == 0
    assert d["unread_notifications"] == 0
    assert d["attendance_streak"] == 0
    assert d["auction"] == {
        "selling_ongoing": 0,
        "sold": 0,
        "won": 0,
        "active_bids": 0,
    }
    assert d["prediction_bets"] == {"pending": 0, "won": 0, "lost": 0}


def test_dashboard_reflects_activity(client, make_user):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()

    item = _item(client, seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=buyer_h)

    seller_d = _dash(client, seller_h)
    assert seller_d["auction"]["selling_ongoing"] == 1

    buyer_d = _dash(client, buyer_h)
    assert buyer_d["auction"]["active_bids"] == 1

    client.post(f"/items/{item['id']}/close", headers=seller_h)
    assert _dash(client, buyer_h)["auction"]["won"] == 1
    assert _dash(client, seller_h)["auction"]["sold"] == 1
    # 낙찰 알림
    assert _dash(client, buyer_h)["unread_notifications"] >= 1


def test_dashboard_checkin_streak(client, make_user):
    h, _ = make_user()
    client.post("/points/check-in", headers=h)
    d = _dash(client, h)
    assert d["attendance_streak"] == 1
    assert d["points"] > 0


def test_dashboard_requires_auth(client):
    assert client.get("/users/me/dashboard").status_code == 401

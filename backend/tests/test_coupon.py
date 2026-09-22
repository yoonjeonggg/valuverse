"""포인트 쿠폰 교환/사용 테스트 (FR-PRD-08)."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.timeutils import now
from app.models.user import User
from tests.conftest import TestingSessionLocal


def test_catalog_is_public(client):
    rows = client.get("/points/coupons/catalog").json()
    keys = {r["key"] for r in rows}
    assert "fee_10" in keys


def test_redeem_deducts_points_and_issues_coupon(client, make_user, set_points, get_points):
    h, user = make_user()
    set_points(user["id"], 1000)
    r = client.post("/points/coupons/fee_10/redeem", headers=h)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["discount_percent"] == 10
    assert c["is_used"] is False
    assert get_points(h) == 1000 - 350


def test_redeem_rejected_without_points(client, make_user):
    h, _ = make_user()
    r = client.post("/points/coupons/fee_10/redeem", headers=h)
    assert r.status_code == 400


def test_redeem_race_rejects_using_fresh_balance(client, make_user, set_points):
    """요청 시작 시점엔 잔액이 충분해 보였어도(메모리상 stale 값), 그 사이 다른
    요청이 이미 잔액을 다 써버렸다면 최신 잔액 기준으로 거부해야 한다."""
    h, user = make_user()
    set_points(user["id"], 350)  # fee_10 쿠폰 가격과 정확히 일치

    from app.services.economy_service import redeem_coupon

    session = TestingSessionLocal()
    stale_user = session.query(User).filter(User.id == user["id"]).one()
    assert stale_user.points == 350  # 메모리상으론 교환 가능해 보임

    other = TestingSessionLocal()
    other.query(User).filter(User.id == user["id"]).update({"points": 0})
    other.commit()
    other.close()

    with pytest.raises(HTTPException) as exc:
        redeem_coupon(session, stale_user, "fee_10")
    assert exc.value.status_code == 400
    session.close()


def test_redeem_unknown_key_404(client, make_user, set_points):
    h, user = make_user()
    set_points(user["id"], 1000)
    assert client.post("/points/coupons/nope/redeem", headers=h).status_code == 404


def test_list_and_use_coupon(client, make_user, set_points):
    h, user = make_user()
    set_points(user["id"], 1000)
    coupon = client.post("/points/coupons/fee_5/redeem", headers=h).json()

    listed = client.get("/users/me/coupons?unused=true", headers=h).json()
    assert [c["id"] for c in listed] == [coupon["id"]]

    used = client.post(f"/points/coupons/{coupon['id']}/use", headers=h)
    assert used.status_code == 200
    assert used.json()["is_used"] is True

    assert client.post(f"/points/coupons/{coupon['id']}/use", headers=h).status_code == 409
    assert client.get("/users/me/coupons?unused=true", headers=h).json() == []


def test_cannot_use_others_coupon(client, make_user, set_points):
    h, user = make_user()
    other_h, _ = make_user()
    set_points(user["id"], 1000)
    coupon = client.post("/points/coupons/fee_5/redeem", headers=h).json()
    assert client.post(
        f"/points/coupons/{coupon['id']}/use", headers=other_h
    ).status_code == 403


def test_expired_coupon_cannot_be_used(client, make_user, set_points):
    h, user = make_user()
    set_points(user["id"], 1000)
    coupon = client.post("/points/coupons/fee_5/redeem", headers=h).json()

    session = TestingSessionLocal()
    from app.models.economy import Coupon

    session.query(Coupon).filter(Coupon.id == coupon["id"]).update(
        {"expires_at": now() - timedelta(days=1)}
    )
    session.commit()
    session.close()

    assert client.post(
        f"/points/coupons/{coupon['id']}/use", headers=h
    ).status_code == 409

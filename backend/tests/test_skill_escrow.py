"""스킬 경매 예약·에스크로 정산 흐름 테스트."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.timeutils import now
from app.models.user import User
from tests.conftest import TestingSessionLocal


def _create_skill(client, headers, price=3000):
    r = client.post(
        "/skill-items",
        json={"title": "1:1 파이썬 과외", "start_price": price},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _book(client, seller_h, skill_id, buyer_id, amount=3000):
    r = client.post(
        "/skill-bookings",
        json={
            "skill_item_id": skill_id,
            "buyer_id": buyer_id,
            "amount": amount,
            "scheduled_at": (now() + timedelta(days=2)).isoformat(),
        },
        headers=seller_h,
    )
    return r


# ---------- 예약 생성 = 낙찰 + 에스크로 보관 ----------
def test_booking_deducts_buyer_points_into_escrow(
    client, make_user, set_points, get_points
):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)

    r = _book(client, seller_h, skill["id"], buyer["id"], amount=3000)
    assert r.status_code == 201, r.text

    assert get_points(buyer_h) == 2000          # 3000 보관
    assert get_points(seller_h) == 0            # 아직 정산 전
    assert client.get(f"/skill-items/{skill['id']}").json()["status"] == "awarded"


def test_booking_rejected_when_buyer_short_on_points(client, make_user, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 1000)
    skill = _create_skill(client, seller_h)
    r = _book(client, seller_h, skill["id"], buyer["id"], amount=3000)
    assert r.status_code == 400


def test_booking_rejected_for_non_seller(client, make_user, set_points):
    seller_h, seller = make_user()
    other_h, other = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    r = _book(client, other_h, skill["id"], buyer["id"])
    assert r.status_code == 403


def test_double_booking_conflicts(client, make_user, set_points):
    seller_h, seller = make_user()
    b1_h, b1 = make_user()
    b2_h, b2 = make_user()
    set_points(b1["id"], 5000)
    set_points(b2["id"], 5000)
    skill = _create_skill(client, seller_h)
    assert _book(client, seller_h, skill["id"], b1["id"]).status_code == 201
    assert _book(client, seller_h, skill["id"], b2["id"]).status_code == 409


# ---------- 완료 정산 ----------
def test_complete_settles_escrow_to_seller(client, make_user, set_points, get_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, skill["id"], buyer["id"], amount=3000).json()

    r = client.post(f"/skill-bookings/{booking['id']}/complete", headers=buyer_h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"
    assert get_points(seller_h) == 3000
    assert get_points(buyer_h) == 2000
    assert client.get(f"/skill-items/{skill['id']}").json()["status"] == "closed"


def test_complete_only_by_buyer(client, make_user, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, skill["id"], buyer["id"]).json()
    r = client.post(f"/skill-bookings/{booking['id']}/complete", headers=seller_h)
    assert r.status_code == 403


def test_complete_twice_conflicts(client, make_user, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, skill["id"], buyer["id"]).json()
    assert client.post(
        f"/skill-bookings/{booking['id']}/complete", headers=buyer_h
    ).status_code == 200
    r = client.post(f"/skill-bookings/{booking['id']}/complete", headers=buyer_h)
    assert r.status_code == 409


# ---------- 노쇼 ----------
def test_seller_no_show_refunds_buyer(client, make_user, set_points, get_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, skill["id"], buyer["id"], amount=3000).json()

    r = client.post(
        f"/skill-bookings/{booking['id']}/no-show",
        json={"party": "seller"},
        headers=buyer_h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "no_show"
    assert get_points(buyer_h) == 5000   # 전액 환불
    assert get_points(seller_h) == 0


def test_buyer_no_show_settles_to_seller(client, make_user, set_points, get_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, skill["id"], buyer["id"], amount=3000).json()

    r = client.post(
        f"/skill-bookings/{booking['id']}/no-show",
        json={"party": "buyer"},
        headers=seller_h,
    )
    assert r.status_code == 200, r.text
    assert get_points(seller_h) == 3000
    assert get_points(buyer_h) == 2000   # 노쇼한 구매자는 포인트를 잃는다


# ---------- 취소 환불 ----------
def test_cancel_booking_refunds_buyer(client, make_user, set_points, get_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, skill["id"], buyer["id"], amount=3000).json()

    r = client.delete(f"/skill-bookings/{booking['id']}", headers=buyer_h)
    assert r.status_code == 204
    assert get_points(buyer_h) == 5000
    assert client.get(f"/skill-items/{skill['id']}").json()["status"] == "closed"


def test_patch_booking_cannot_force_status(client, make_user, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, skill["id"], buyer["id"]).json()
    r = client.patch(
        f"/skill-bookings/{booking['id']}",
        json={"status": "completed"},
        headers=buyer_h,
    )
    assert r.status_code == 400


# ---------- 직접 에스크로 결제 동시성 ----------
def test_escrow_race_rejects_using_fresh_balance(client, make_user, set_points):
    """요청 시작 시점엔 잔액이 충분해 보였어도(메모리상 stale 값), 그 사이 다른
    요청이 이미 잔액을 다 써버렸다면 최신 잔액 기준으로 거부해야 한다."""
    payer_h, payer = make_user()
    _, payee = make_user()
    set_points(payer["id"], 1000)

    from app.services.skill_service import create_escrow
    from app.schemas.skill import EscrowCreate

    session = TestingSessionLocal()
    stale_payer = session.query(User).filter(User.id == payer["id"]).one()
    assert stale_payer.points == 1000  # 메모리상으론 결제 가능해 보임

    other = TestingSessionLocal()
    other.query(User).filter(User.id == payer["id"]).update({"points": 0})
    other.commit()
    other.close()

    payload = EscrowCreate(item_id=1, payee_id=payee["id"], amount=1000)
    with pytest.raises(HTTPException) as exc:
        create_escrow(session, stale_payer, payload)
    assert exc.value.status_code == 400
    session.close()

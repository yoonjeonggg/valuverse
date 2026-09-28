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


def _request(client, seller_h, skill_id, buyer_id, amount=3000):
    """판매자의 예약 요청 (아직 포인트 차감 없음)."""
    return client.post(
        "/skill-bookings",
        json={
            "skill_item_id": skill_id,
            "buyer_id": buyer_id,
            "amount": amount,
            "scheduled_at": (now() + timedelta(days=2)).isoformat(),
        },
        headers=seller_h,
    )


def _book(client, seller_h, buyer_h, skill_id, buyer_id, amount=3000):
    """예약 요청 + 구매자 수락까지 (에스크로 보관된 진행중 예약)."""
    r = _request(client, seller_h, skill_id, buyer_id, amount)
    assert r.status_code == 201, r.text
    accepted = client.post(f"/skill-bookings/{r.json()['id']}/accept", headers=buyer_h)
    assert accepted.status_code == 200, accepted.text
    return accepted


# ---------- 예약 요청 -> 구매자 수락 = 낙찰 + 에스크로 보관 ----------
def test_booking_deducts_buyer_points_into_escrow(
    client, make_user, set_points, get_points
):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)

    req = _request(client, seller_h, skill["id"], buyer["id"], amount=3000)
    assert req.status_code == 201, req.text
    assert req.json()["status"] == "pending"
    assert get_points(buyer_h) == 5000          # 수락 전에는 차감되지 않는다

    r = client.post(f"/skill-bookings/{req.json()['id']}/accept", headers=buyer_h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "in_progress"

    assert get_points(buyer_h) == 2000          # 3000 보관
    assert get_points(seller_h) == 0            # 아직 정산 전
    assert client.get(f"/skill-items/{skill['id']}").json()["status"] == "awarded"


def test_booking_rejected_when_buyer_short_on_points(client, make_user, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 1000)
    skill = _create_skill(client, seller_h)
    req = _request(client, seller_h, skill["id"], buyer["id"], amount=3000).json()
    r = client.post(f"/skill-bookings/{req['id']}/accept", headers=buyer_h)
    assert r.status_code == 400


def test_booking_rejected_for_non_seller(client, make_user, set_points):
    seller_h, seller = make_user()
    other_h, other = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    r = _request(client, other_h, skill["id"], buyer["id"])
    assert r.status_code == 403


def test_double_booking_conflicts(client, make_user, set_points):
    seller_h, seller = make_user()
    b1_h, b1 = make_user()
    b2_h, b2 = make_user()
    set_points(b1["id"], 5000)
    set_points(b2["id"], 5000)
    skill = _create_skill(client, seller_h)
    assert _request(client, seller_h, skill["id"], b1["id"]).status_code == 201
    assert _request(client, seller_h, skill["id"], b2["id"]).status_code == 409


# ---------- 완료 정산 ----------
def test_complete_settles_escrow_to_seller(client, make_user, set_points, get_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, buyer_h, skill["id"], buyer["id"], amount=3000).json()

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
    booking = _book(client, seller_h, buyer_h, skill["id"], buyer["id"]).json()
    r = client.post(f"/skill-bookings/{booking['id']}/complete", headers=seller_h)
    assert r.status_code == 403


def test_complete_twice_conflicts(client, make_user, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, buyer_h, skill["id"], buyer["id"]).json()
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
    booking = _book(client, seller_h, buyer_h, skill["id"], buyer["id"], amount=3000).json()

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
    booking = _book(client, seller_h, buyer_h, skill["id"], buyer["id"], amount=3000).json()

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
    booking = _book(client, seller_h, buyer_h, skill["id"], buyer["id"], amount=3000).json()

    r = client.delete(f"/skill-bookings/{booking['id']}", headers=buyer_h)
    assert r.status_code == 204
    assert get_points(buyer_h) == 5000
    assert client.get(f"/skill-items/{skill['id']}").json()["status"] == "closed"


def test_patch_booking_cannot_force_status(client, make_user, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, buyer_h, skill["id"], buyer["id"]).json()
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
    payee_headers, payee = make_user()
    payee["headers"] = payee_headers
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

    payee_h = payee["headers"]
    item = client.post(
        "/items",
        json={
            "title": "x",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=payee_h,
    ).json()
    payload = EscrowCreate(item_id=item["id"], payee_id=payee["id"], amount=1000)
    with pytest.raises(HTTPException) as exc:
        create_escrow(session, stale_payer, payload)
    assert exc.value.status_code == 400
    session.close()


# ---------- 보안: 동의 없는 차감 / 노쇼 악용 / 에스크로 권한 ----------
def test_seller_cannot_take_points_without_buyer_acceptance(
    client, make_user, set_points, get_points
):
    """판매자가 아무 회원에게나 예약을 걸고 '구매자 노쇼'로 신고해 포인트를
    가져가던 경로: 수락 전에는 차감도, 노쇼 처리도 불가능해야 한다."""
    seller_h, _ = make_user()
    victim_h, victim = make_user()
    set_points(victim["id"], 5000)
    skill = _create_skill(client, seller_h)
    req = _request(client, seller_h, skill["id"], victim["id"]).json()

    r = client.post(
        f"/skill-bookings/{req['id']}/no-show", json={"party": "buyer"}, headers=seller_h
    )
    assert r.status_code == 409
    assert get_points(victim_h) == 5000
    assert get_points(seller_h) == 0


def test_only_buyer_can_accept(client, make_user, set_points):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    req = _request(client, seller_h, skill["id"], buyer["id"]).json()
    assert client.post(
        f"/skill-bookings/{req['id']}/accept", headers=seller_h
    ).status_code == 403


def test_buyer_declines_request_reopens_item(client, make_user, set_points, get_points):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    req = _request(client, seller_h, skill["id"], buyer["id"]).json()

    assert client.delete(f"/skill-bookings/{req['id']}", headers=buyer_h).status_code == 204
    assert get_points(buyer_h) == 5000
    assert client.get(f"/skill-items/{skill['id']}").json()["status"] == "recruiting"


@pytest.mark.parametrize("reporter,party", [("seller", "seller"), ("buyer", "buyer")])
def test_no_show_only_reportable_against_counterparty(
    client, make_user, set_points, get_points, reporter, party
):
    """본인이 노쇼했다고 스스로 신고해 정산/환불을 끌어가지 못한다."""
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, buyer_h, skill["id"], buyer["id"]).json()

    headers = seller_h if reporter == "seller" else buyer_h
    r = client.post(
        f"/skill-bookings/{booking['id']}/no-show", json={"party": party}, headers=headers
    )
    assert r.status_code == 403
    assert get_points(buyer_h) == 2000  # 그대로 보관중


def test_outsider_cannot_see_booking(client, make_user, set_points):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    other_h, _ = make_user()
    set_points(buyer["id"], 5000)
    skill = _create_skill(client, seller_h)
    booking = _book(client, seller_h, buyer_h, skill["id"], buyer["id"]).json()
    assert client.get(f"/skill-bookings/{booking['id']}", headers=other_h).status_code == 404


def _direct_escrow(client, make_user, set_points):
    payer_h, payer = make_user()
    payee_h, payee = make_user()
    set_points(payer["id"], 1000)
    item = client.post(
        "/items",
        json={
            "title": "x",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=payee_h,
    ).json()
    r = client.post(
        "/escrows",
        json={"item_id": item["id"], "payee_id": payee["id"], "amount": 1000},
        headers=payer_h,
    )
    assert r.status_code == 201, r.text
    return payer_h, payee_h, r.json()


def test_payee_cannot_settle_escrow_to_self(client, make_user, set_points, get_points):
    payer_h, payee_h, escrow = _direct_escrow(client, make_user, set_points)
    r = client.patch(f"/escrows/{escrow['id']}", json={"status": "settled"}, headers=payee_h)
    assert r.status_code == 403
    assert get_points(payee_h) == 0

    r = client.patch(f"/escrows/{escrow['id']}", json={"status": "settled"}, headers=payer_h)
    assert r.status_code == 200
    assert get_points(payee_h) == 1000


def test_payer_cannot_refund_escrow_unilaterally(client, make_user, set_points, get_points):
    payer_h, payee_h, escrow = _direct_escrow(client, make_user, set_points)
    r = client.patch(f"/escrows/{escrow['id']}", json={"status": "refunded"}, headers=payer_h)
    assert r.status_code == 403
    assert get_points(payer_h) == 0

    r = client.patch(f"/escrows/{escrow['id']}", json={"status": "refunded"}, headers=payee_h)
    assert r.status_code == 200
    assert get_points(payer_h) == 1000


def test_escrow_payee_must_be_item_seller(client, make_user, set_points):
    payer_h, payer = make_user()
    _, stranger = make_user()
    seller_h, _ = make_user()
    set_points(payer["id"], 1000)
    item = client.post(
        "/items",
        json={
            "title": "x",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=seller_h,
    ).json()
    r = client.post(
        "/escrows",
        json={"item_id": item["id"], "payee_id": stranger["id"], "amount": 1000},
        headers=payer_h,
    )
    assert r.status_code == 400

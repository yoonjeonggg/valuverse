"""리뷰 작성 조건(완료된 거래 당사자) 검증 테스트."""

from datetime import timedelta

from app.core.timeutils import now


def _item(client, headers):
    return client.post(
        "/items",
        json={
            "title": "거래 상품",
            "start_price": 1000,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    ).json()


def _won_item(client, seller_h, buyer_h):
    """buyer 가 seller 의 상품을 낙찰받은 상태로 만든다."""
    item = _item(client, seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=buyer_h)
    client.post(f"/items/{item['id']}/close", headers=seller_h)
    return item


def _review(client, headers, **body):
    return client.post("/reviews", json=body, headers=headers)


# ---------- 일반 경매 ----------
def test_buyer_can_review_seller_after_win(client, make_user):
    seller_h, seller = make_user()
    buyer_h, _ = make_user()
    item = _won_item(client, seller_h, buyer_h)
    r = _review(
        client, buyer_h, target_user_id=seller["id"], item_id=item["id"], rating=5
    )
    assert r.status_code == 201, r.text


def test_seller_can_review_buyer(client, make_user):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    item = _won_item(client, seller_h, buyer_h)
    r = _review(
        client, seller_h, target_user_id=buyer["id"], item_id=item["id"], rating=4
    )
    assert r.status_code == 201, r.text


def test_review_rejected_before_auction_closed(client, make_user):
    seller_h, seller = make_user()
    buyer_h, _ = make_user()
    item = _item(client, seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=buyer_h)
    r = _review(
        client, buyer_h, target_user_id=seller["id"], item_id=item["id"], rating=5
    )
    assert r.status_code == 409


def test_outsider_cannot_review(client, make_user):
    seller_h, seller = make_user()
    buyer_h, _ = make_user()
    stranger_h, _ = make_user()
    item = _won_item(client, seller_h, buyer_h)
    r = _review(
        client, stranger_h, target_user_id=seller["id"], item_id=item["id"], rating=1
    )
    assert r.status_code == 403


def test_duplicate_review_rejected(client, make_user):
    seller_h, seller = make_user()
    buyer_h, _ = make_user()
    item = _won_item(client, seller_h, buyer_h)
    assert _review(
        client, buyer_h, target_user_id=seller["id"], item_id=item["id"], rating=5
    ).status_code == 201
    assert _review(
        client, buyer_h, target_user_id=seller["id"], item_id=item["id"], rating=3
    ).status_code == 409


# ---------- 스킬 거래 ----------
def test_review_after_completed_skill_booking(client, make_user, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 5000)
    skill = client.post(
        "/skill-items", json={"title": "과외", "start_price": 3000}, headers=seller_h
    ).json()
    booking = client.post(
        "/skill-bookings",
        json={
            "skill_item_id": skill["id"],
            "buyer_id": buyer["id"],
            "amount": 3000,
            "scheduled_at": (now() + timedelta(days=1)).isoformat(),
        },
        headers=seller_h,
    ).json()

    # 완료 전에는 불가
    early = _review(
        client, buyer_h, target_user_id=seller["id"], skill_item_id=skill["id"], rating=5
    )
    assert early.status_code == 409

    client.post(f"/skill-bookings/{booking['id']}/complete", headers=buyer_h)
    ok = _review(
        client, buyer_h, target_user_id=seller["id"], skill_item_id=skill["id"], rating=5
    )
    assert ok.status_code == 201, ok.text

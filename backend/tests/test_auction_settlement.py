"""일반/블라인드 경매 낙찰·마감·자동연장 테스트."""

from datetime import timedelta

import pytest

from app.core.timeutils import now


@pytest.fixture
def move_deadline(move_item):
    """items.end_time 이동 (conftest.move_item 위임)."""
    return move_item


def _create_item(client, headers, **overrides):
    body = {
        "title": "테스트 상품",
        "start_price": 1000,
        "buy_now_price": 5000,
        "end_time": (now() + timedelta(days=1)).isoformat(),
    }
    body.update(overrides)
    r = client.post("/items", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- 즉시구매 ----------
def test_buy_now_closes_auction_and_sets_winner(client, make_user):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    item = _create_item(client, seller_h)

    r = client.post(f"/items/{item['id']}/buy-now", headers=buyer_h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["final_price"] == 5000
    assert data["status"] == "closed"

    got = client.get(f"/items/{item['id']}").json()
    assert got["status"] == "closed"
    assert got["winner_id"] == buyer["id"]
    assert got["final_price"] == 5000


def test_buy_now_rejected_for_seller(client, make_user):
    seller_h, _ = make_user()
    item = _create_item(client, seller_h)
    r = client.post(f"/items/{item['id']}/buy-now", headers=seller_h)
    assert r.status_code == 400


def test_buy_now_rejected_without_buy_now_price(client, make_user):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = _create_item(client, seller_h, buy_now_price=None)
    r = client.post(f"/items/{item['id']}/buy-now", headers=buyer_h)
    assert r.status_code == 400


def test_buy_now_rejected_when_current_price_reaches_buy_now(client, make_user):
    seller_h, _ = make_user()
    b1, _ = make_user()
    b2, _ = make_user()
    item = _create_item(client, seller_h, buy_now_price=3000)
    assert client.post(
        f"/items/{item['id']}/bids", json={"amount": 3000}, headers=b1
    ).status_code == 201
    r = client.post(f"/items/{item['id']}/buy-now", headers=b2)
    assert r.status_code == 409


# ---------- 수동 마감 ----------
def test_close_item_picks_highest_bidder(client, make_user):
    seller_h, _ = make_user()
    b1_h, b1 = make_user()
    b2_h, b2 = make_user()
    item = _create_item(client, seller_h)

    client.post(f"/items/{item['id']}/bids", json={"amount": 1500}, headers=b1_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2500}, headers=b2_h)

    r = client.post(f"/items/{item['id']}/close", headers=seller_h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "closed"
    assert data["winner_id"] == b2["id"]
    assert data["final_price"] == 2500


def test_close_item_only_by_seller(client, make_user):
    seller_h, _ = make_user()
    other_h, _ = make_user()
    item = _create_item(client, seller_h)
    r = client.post(f"/items/{item['id']}/close", headers=other_h)
    assert r.status_code == 403


def test_close_item_twice_conflicts(client, make_user):
    seller_h, _ = make_user()
    item = _create_item(client, seller_h)
    assert client.post(f"/items/{item['id']}/close", headers=seller_h).status_code == 200
    r = client.post(f"/items/{item['id']}/close", headers=seller_h)
    assert r.status_code == 409


def test_close_with_no_bids_is_unsold(client, make_user):
    seller_h, _ = make_user()
    item = _create_item(client, seller_h)
    r = client.post(f"/items/{item['id']}/close", headers=seller_h)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "closed"
    assert data["winner_id"] is None
    assert data["final_price"] is None


# ---------- 조회 시 자동 마감 ----------
def test_get_item_auto_finalizes_after_deadline(client, make_user, move_deadline):
    seller_h, _ = make_user()
    bidder_h, bidder = make_user()
    item = _create_item(client, seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=bidder_h)

    move_deadline(item["id"], -10)  # 10초 전 마감

    got = client.get(f"/items/{item['id']}").json()
    assert got["status"] == "closed"
    assert got["winner_id"] == bidder["id"]
    assert got["final_price"] == 2000


def test_bid_rejected_after_deadline(client, make_user, move_deadline):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = _create_item(client, seller_h)
    move_deadline(item["id"], -5)
    r = client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=bidder_h)
    assert r.status_code == 409


# ---------- 자동 연장 (스나이핑 방지) ----------
def test_bid_in_final_window_extends_deadline(client, make_user, move_deadline):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = _create_item(client, seller_h)

    move_deadline(item["id"], 60)  # 마감 60초 전 (기본 윈도우 180초 이내)
    before = client.get(f"/items/{item['id']}").json()["end_time"]

    r = client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=bidder_h)
    assert r.status_code == 201

    after = client.get(f"/items/{item['id']}")
    body = after.json()
    assert body["extended_count"] == 1
    assert body["end_time"] > before


def test_bid_well_before_deadline_does_not_extend(client, make_user, move_deadline):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = _create_item(client, seller_h)

    move_deadline(item["id"], 3600)  # 1시간 전 - 연장 없음
    r = client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=bidder_h)
    assert r.status_code == 201
    assert client.get(f"/items/{item['id']}").json()["extended_count"] == 0


def test_extension_capped_at_max(client, make_user, move_deadline):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = _create_item(client, seller_h)

    amount = 1000
    for _ in range(12):
        move_deadline(item["id"], 60)
        amount += 100
        client.post(
            f"/items/{item['id']}/bids", json={"amount": amount}, headers=bidder_h
        )

    # 기본 상한 10회
    assert client.get(f"/items/{item['id']}").json()["extended_count"] == 10


# ---------- 블라인드 경매 1st-price 낙찰 ----------
def test_blind_auction_finalizes_first_price(client, make_user, move_deadline):
    seller_h, _ = make_user()
    b1_h, b1 = make_user()
    b2_h, b2 = make_user()
    item = _create_item(client, seller_h, auction_type="blind")

    client.post(f"/items/{item['id']}/blind-bids", json={"amount": 4000}, headers=b1_h)
    client.post(f"/items/{item['id']}/blind-bids", json={"amount": 7000}, headers=b2_h)

    move_deadline(item["id"], -1)

    got = client.get(f"/items/{item['id']}").json()
    assert got["status"] == "closed"
    assert got["winner_id"] == b2["id"]
    assert got["final_price"] == 7000

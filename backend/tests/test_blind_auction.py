"""블라인드 경매 - 1st-price / Vickrey(2nd-price) 낙찰 및 타입 분리 테스트."""

from datetime import timedelta

from app.core.timeutils import now


def _create(client, headers, **ov):
    body = {
        "title": "블라인드 상품",
        "start_price": 1000,
        "end_time": (now() + timedelta(days=1)).isoformat(),
    }
    body.update(ov)
    r = client.post("/items", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _blind_bid(client, headers, item_id, amount):
    return client.post(
        f"/items/{item_id}/blind-bids", json={"amount": amount}, headers=headers
    )


# ---------- 타입 분리 ----------
def test_general_bid_rejected_on_blind_item(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = _create(client, seller_h, auction_type="blind")
    r = client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=bidder_h)
    assert r.status_code == 409


def test_blind_bid_rejected_on_general_item(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = _create(client, seller_h, auction_type="general")
    r = _blind_bid(client, bidder_h, item["id"], 2000)
    assert r.status_code == 409


def test_buy_now_rejected_on_blind_item(client, make_user):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = _create(client, seller_h, auction_type="blind", buy_now_price=5000)
    r = client.post(f"/items/{item['id']}/buy-now", headers=buyer_h)
    assert r.status_code == 409


# ---------- 1st-price ----------
def test_first_price_winner_pays_own_bid(client, make_user, move_item):
    seller_h, _ = make_user()
    b1_h, b1 = make_user()
    b2_h, b2 = make_user()
    item = _create(client, seller_h, auction_type="blind", blind_price_rule="first")
    _blind_bid(client, b1_h, item["id"], 5000)
    _blind_bid(client, b2_h, item["id"], 8000)

    move_item(item["id"], -1)
    got = client.get(f"/items/{item['id']}").json()
    assert got["winner_id"] == b2["id"]
    assert got["final_price"] == 8000


# ---------- Vickrey 2nd-price ----------
def test_vickrey_winner_pays_second_price(client, make_user, move_item):
    seller_h, _ = make_user()
    b1_h, b1 = make_user()
    b2_h, b2 = make_user()
    b3_h, b3 = make_user()
    item = _create(client, seller_h, auction_type="blind", blind_price_rule="second")
    _blind_bid(client, b1_h, item["id"], 5000)
    _blind_bid(client, b2_h, item["id"], 9000)
    _blind_bid(client, b3_h, item["id"], 7000)

    move_item(item["id"], -1)
    got = client.get(f"/items/{item['id']}").json()
    assert got["winner_id"] == b2["id"]      # 최고가 제시자가 낙찰
    assert got["final_price"] == 7000        # 2위 금액으로 결제


def test_vickrey_single_bidder_pays_own_bid(client, make_user, move_item):
    seller_h, _ = make_user()
    b1_h, b1 = make_user()
    item = _create(client, seller_h, auction_type="blind", blind_price_rule="second")
    _blind_bid(client, b1_h, item["id"], 5000)

    move_item(item["id"], -1)
    got = client.get(f"/items/{item['id']}").json()
    assert got["winner_id"] == b1["id"]
    assert got["final_price"] == 5000


def test_vickrey_close_endpoint(client, make_user):
    seller_h, _ = make_user()
    b1_h, b1 = make_user()
    b2_h, b2 = make_user()
    item = _create(client, seller_h, auction_type="blind", blind_price_rule="second")
    _blind_bid(client, b1_h, item["id"], 4000)
    _blind_bid(client, b2_h, item["id"], 6000)

    r = client.post(f"/items/{item['id']}/close", headers=seller_h)
    assert r.status_code == 200
    body = r.json()
    assert body["winner_id"] == b2["id"]
    assert body["final_price"] == 4000

"""알림 생성/조회 테스트 (FR-COM-03)."""

from datetime import timedelta

from app.core.timeutils import now


def _item(client, headers, **ov):
    body = {
        "title": "알림 테스트 상품",
        "start_price": 1000,
        "buy_now_price": 9000,
        "end_time": (now() + timedelta(days=1)).isoformat(),
    }
    body.update(ov)
    return client.post("/items", json=body, headers=headers).json()


def _notifs(client, headers, unread=False):
    url = "/users/me/notifications" + ("?unread=true" if unread else "")
    r = client.get(url, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- 입찰 경쟁 ----------
def test_outbid_notifies_previous_top_bidder(client, make_user):
    seller_h, _ = make_user()
    b1_h, b1 = make_user()
    b2_h, _ = make_user()
    item = _item(client, seller_h)

    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=b1_h)
    # b1 은 아직 알림 없음
    assert _notifs(client, b1_h) == []

    client.post(f"/items/{item['id']}/bids", json={"amount": 3000}, headers=b2_h)
    notes = _notifs(client, b1_h)
    assert len(notes) == 1
    assert notes[0]["type"] == "bid_outbid"
    assert notes[0]["related_id"] == item["id"]
    assert notes[0]["is_read"] is False


def test_no_self_outbid_notification(client, make_user):
    seller_h, _ = make_user()
    b1_h, _ = make_user()
    item = _item(client, seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=b1_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2500}, headers=b1_h)
    assert _notifs(client, b1_h) == []


# ---------- 낙찰 ----------
def test_close_notifies_winner_and_seller(client, make_user):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = _item(client, seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=buyer_h)
    client.post(f"/items/{item['id']}/close", headers=seller_h)

    won = _notifs(client, buyer_h)
    assert [n["type"] for n in won] == ["won"]
    sold = [n["type"] for n in _notifs(client, seller_h)]
    assert "sold" in sold


def test_buy_now_notifies_seller(client, make_user):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = _item(client, seller_h)
    client.post(f"/items/{item['id']}/buy-now", headers=buyer_h)
    assert [n["type"] for n in _notifs(client, seller_h)] == ["sold"]


# ---------- 스킬 ----------
def test_skill_booking_and_settlement_notifications(client, make_user, set_points):
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
    assert [n["type"] for n in _notifs(client, buyer_h)] == ["booking"]

    client.post(f"/skill-bookings/{booking['id']}/complete", headers=buyer_h)
    assert "settlement" in [n["type"] for n in _notifs(client, seller_h)]


# ---------- 예측 정산 ----------
def test_settlement_notifies_all_bettors(client, make_user, set_points, move_pred):
    admin_h, _ = make_user(admin=True)
    w_h, w = make_user()
    l_h, l = make_user()
    set_points(w["id"], 5000)
    set_points(l["id"], 5000)
    pred = client.post(
        "/predictions",
        json={"title": "명제", "end_time": (now() + timedelta(days=1)).isoformat()},
        headers=admin_h,
    ).json()
    client.post(
        f"/predictions/{pred['id']}/bets",
        json={"position": "yes", "amount": 1000},
        headers=w_h,
    )
    client.post(
        f"/predictions/{pred['id']}/bets",
        json={"position": "no", "amount": 1000},
        headers=l_h,
    )
    move_pred(pred["id"], -1)
    client.post(
        f"/predictions/{pred['id']}/settle", json={"result": "yes"}, headers=admin_h
    )

    assert [n["type"] for n in _notifs(client, w_h)] == ["bet_result"]
    assert "적중" in _notifs(client, w_h)[0]["message"]
    assert [n["type"] for n in _notifs(client, l_h)] == ["bet_result"]


# ---------- 읽음 처리 ----------
def test_mark_read_and_unread_count(client, make_user):
    seller_h, _ = make_user()
    b1_h, _ = make_user()
    b2_h, _ = make_user()
    item = _item(client, seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=b1_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 3000}, headers=b2_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 4000}, headers=b1_h)

    assert client.get(
        "/users/me/notifications/unread-count", headers=b1_h
    ).json()["unread"] == 1

    nid = _notifs(client, b1_h)[0]["id"]
    r = client.post(f"/notifications/{nid}/read", headers=b1_h)
    assert r.status_code == 200
    assert r.json()["is_read"] is True
    assert _notifs(client, b1_h, unread=True) == []


def test_cannot_read_others_notification(client, make_user):
    seller_h, _ = make_user()
    b1_h, _ = make_user()
    b2_h, _ = make_user()
    other_h, _ = make_user()
    item = _item(client, seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=b1_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 3000}, headers=b2_h)

    nid = _notifs(client, b1_h)[0]["id"]
    assert client.post(f"/notifications/{nid}/read", headers=other_h).status_code == 403


def test_read_all(client, make_user):
    seller_h, _ = make_user()
    b1_h, _ = make_user()
    others = [make_user()[0] for _ in range(3)]
    item = _item(client, seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 1500}, headers=b1_h)
    amount = 1500
    for h in others:
        amount += 500
        client.post(f"/items/{item['id']}/bids", json={"amount": amount}, headers=h)

    assert client.get(
        "/users/me/notifications/unread-count", headers=b1_h
    ).json()["unread"] >= 1
    client.post("/notifications/read-all", headers=b1_h)
    assert client.get(
        "/users/me/notifications/unread-count", headers=b1_h
    ).json()["unread"] == 0

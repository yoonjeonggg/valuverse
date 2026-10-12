"""경매 상품 수정/삭제, 입찰 취소, 블라인드 조회의 예외 경로 테스트."""

from datetime import timedelta

from app.core.config import settings
from app.core.timeutils import now
from tests.conftest import in_days


def _past() -> str:
    return (now() - timedelta(minutes=1)).isoformat()


# ---------- 생성 검증 ----------
def test_create_item_rejects_past_end_time(client, make_user):
    h, _ = make_user()
    r = client.post(
        "/items", json={"title": "x", "start_price": 1000, "end_time": _past()}, headers=h
    )
    assert r.status_code == 400


def test_create_item_rejects_buy_now_not_above_start(client, make_user):
    h, _ = make_user()
    body = {"title": "x", "start_price": 1000, "buy_now_price": 1000, "end_time": in_days(1)}
    assert client.post("/items", json=body, headers=h).status_code == 400


def test_create_item_requires_login(client):
    body = {"title": "x", "start_price": 1000, "end_time": in_days(1)}
    assert client.post("/items", json=body).status_code == 401


def test_create_item_validation_error_shape(client, make_user):
    h, _ = make_user()
    r = client.post("/items", json={"title": "", "start_price": -1}, headers=h)
    assert r.status_code == 422
    fields = {e["field"] for e in r.json()["detail"]}
    assert {"title", "start_price", "end_time"} <= fields


# ---------- 조회 ----------
def test_get_missing_item_is_404(client):
    assert client.get("/items/999").status_code == 404


def test_list_items_filters_by_category(client, make_user, make_item):
    h, _ = make_user()
    make_item(h, category="book")
    make_item(h, category="toy")
    rows = client.get("/items?category=book").json()
    assert [r["category"] for r in rows] == ["book"]


def test_list_bids_for_missing_item_is_404(client):
    assert client.get("/items/999/bids").status_code == 404


def test_list_my_bids(client, make_user, make_item):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = make_item(seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=buyer_h)
    mine = client.get("/users/me/bids", headers=buyer_h).json()
    assert [b["amount"] for b in mine] == [2000]
    assert client.get("/users/me/bids", headers=seller_h).json() == []


# ---------- 수정 ----------
def test_owner_updates_item(client, make_user, make_item):
    h, _ = make_user()
    item = make_item(h)
    r = client.patch(f"/items/{item['id']}", json={"title": "새 제목"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "새 제목"


def test_non_owner_cannot_update_item(client, make_user, make_item):
    owner_h, _ = make_user()
    other_h, _ = make_user()
    item = make_item(owner_h)
    r = client.patch(f"/items/{item['id']}", json={"title": "x"}, headers=other_h)
    assert r.status_code == 403


def test_update_rejected_after_bids(client, make_user, make_item):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = make_item(seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=buyer_h)
    r = client.patch(f"/items/{item['id']}", json={"title": "x"}, headers=seller_h)
    assert r.status_code == 409


def test_update_rejected_after_close(client, make_user, make_item):
    h, _ = make_user()
    item = make_item(h)
    client.post(f"/items/{item['id']}/close", headers=h)
    r = client.patch(f"/items/{item['id']}", json={"title": "x"}, headers=h)
    assert r.status_code == 409


def test_update_rejects_past_end_time(client, make_user, make_item):
    h, _ = make_user()
    item = make_item(h)
    r = client.patch(f"/items/{item['id']}", json={"end_time": _past()}, headers=h)
    assert r.status_code == 400


def test_update_rejects_low_buy_now_price(client, make_user, make_item):
    h, _ = make_user()
    item = make_item(h, start_price=5000)
    r = client.patch(f"/items/{item['id']}", json={"buy_now_price": 4000}, headers=h)
    assert r.status_code == 400
    # 즉시구매가를 없애는 것은 허용
    r = client.patch(f"/items/{item['id']}", json={"buy_now_price": None}, headers=h)
    assert r.status_code == 200, r.text


# ---------- 삭제 ----------
def test_delete_item_without_bids_removes_it(client, make_user, make_item):
    h, _ = make_user()
    item = make_item(h)
    assert client.delete(f"/items/{item['id']}", headers=h).status_code == 204
    assert client.get(f"/items/{item['id']}").status_code == 404


def test_delete_item_with_bids_is_soft(client, make_user, make_item, db):
    from app.models.auction import Item

    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = make_item(seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=buyer_h)
    assert client.delete(f"/items/{item['id']}", headers=seller_h).status_code == 204
    assert client.get(f"/items/{item['id']}").status_code == 404
    row = db.get(Item, item["id"])
    assert row.is_deleted is True
    assert row.status == "closed"


def test_non_owner_cannot_delete_item(client, make_user, make_item):
    owner_h, _ = make_user()
    other_h, _ = make_user()
    item = make_item(owner_h)
    assert client.delete(f"/items/{item['id']}", headers=other_h).status_code == 403


# ---------- 입찰 취소 ----------
def _bid(client, item_id, headers, amount):
    r = client.post(f"/items/{item_id}/bids", json={"amount": amount}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_cancel_bid_restores_previous_price(client, make_user, make_item):
    seller_h, _ = make_user()
    b1_h, _ = make_user()
    b2_h, _ = make_user()
    item = make_item(seller_h)
    _bid(client, item["id"], b1_h, 2000)
    top = _bid(client, item["id"], b2_h, 3000)

    assert client.delete(f"/bids/{top['id']}", headers=b2_h).status_code == 204
    assert client.get(f"/items/{item['id']}").json()["current_price"] == 2000


def test_cancel_only_bid_restores_start_price(client, make_user, make_item):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = make_item(seller_h, start_price=1500)
    bid = _bid(client, item["id"], buyer_h, 2000)
    client.delete(f"/bids/{bid['id']}", headers=buyer_h)
    assert client.get(f"/items/{item['id']}").json()["current_price"] == 1500


def test_cancel_bid_twice_conflicts(client, make_user, make_item):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = make_item(seller_h)
    bid = _bid(client, item["id"], buyer_h, 2000)
    client.delete(f"/bids/{bid['id']}", headers=buyer_h)
    assert client.delete(f"/bids/{bid['id']}", headers=buyer_h).status_code == 409


def test_cannot_cancel_others_bid(client, make_user, make_item):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = make_item(seller_h)
    bid = _bid(client, item["id"], buyer_h, 2000)
    assert client.delete(f"/bids/{bid['id']}", headers=seller_h).status_code == 404


def test_cancel_bid_after_window_conflicts(client, make_user, make_item, monkeypatch):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = make_item(seller_h)
    bid = _bid(client, item["id"], buyer_h, 2000)
    monkeypatch.setattr(settings, "bid_cancel_window_seconds", -1)
    assert client.delete(f"/bids/{bid['id']}", headers=buyer_h).status_code == 409


def test_cancel_bid_after_close_conflicts(client, make_user, make_item):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = make_item(seller_h)
    bid = _bid(client, item["id"], buyer_h, 2000)
    client.post(f"/items/{item['id']}/close", headers=seller_h)
    assert client.delete(f"/bids/{bid['id']}", headers=buyer_h).status_code == 409


# ---------- 상단 노출권 ----------
def test_spotlight_rejected_on_closed_item(client, make_user, make_item, set_points):
    h, user = make_user()
    set_points(user["id"], 100_000)
    item = make_item(h)
    client.post(f"/items/{item['id']}/close", headers=h)
    assert client.post(f"/items/{item['id']}/spotlight", headers=h).status_code == 409


def test_spotlight_extends_remaining_time(client, make_user, make_item, set_points):
    h, user = make_user()
    set_points(user["id"], 100_000)
    item = make_item(h)
    first = client.post(f"/items/{item['id']}/spotlight", headers=h).json()["spotlight_until"]
    second = client.post(f"/items/{item['id']}/spotlight", headers=h).json()["spotlight_until"]
    assert second > first


# ---------- 블라인드 ----------
def _blind(make_item, headers):
    return make_item(headers, auction_type="blind")


def test_blind_rank_without_bid_is_404(client, make_user, make_item):
    seller_h, _ = make_user()
    other_h, _ = make_user()
    item = _blind(make_item, seller_h)
    assert client.get(f"/items/{item['id']}/blind-bids/my-rank", headers=other_h).status_code == 404


def test_blind_rank_reports_position(client, make_user, make_item):
    seller_h, _ = make_user()
    low_h, _ = make_user()
    high_h, _ = make_user()
    item = _blind(make_item, seller_h)
    client.post(f"/items/{item['id']}/blind-bids", json={"amount": 2000}, headers=low_h)
    client.post(f"/items/{item['id']}/blind-bids", json={"amount": 5000}, headers=high_h)
    body = client.get(f"/items/{item['id']}/blind-bids/my-rank", headers=low_h).json()
    assert body["rank"] == 2
    assert body["total_bids"] == 2


def test_blind_results_before_close_conflicts(client, make_user, make_item):
    seller_h, _ = make_user()
    item = _blind(make_item, seller_h)
    assert client.get(f"/items/{item['id']}/blind-bids/results").status_code == 409


def test_blind_results_after_close_are_ranked(client, make_user, make_item):
    seller_h, _ = make_user()
    a_h, _ = make_user()
    b_h, _ = make_user()
    item = _blind(make_item, seller_h)
    client.post(f"/items/{item['id']}/blind-bids", json={"amount": 2000}, headers=a_h)
    client.post(f"/items/{item['id']}/blind-bids", json={"amount": 5000}, headers=b_h)
    client.post(f"/items/{item['id']}/close", headers=seller_h)
    rows = client.get(f"/items/{item['id']}/blind-bids/results").json()
    assert [(r["rank"], r["amount"]) for r in rows] == [(1, 5000), (2, 2000)]


def test_blind_bid_on_own_item_rejected(client, make_user, make_item):
    seller_h, _ = make_user()
    item = _blind(make_item, seller_h)
    r = client.post(f"/items/{item['id']}/blind-bids", json={"amount": 2000}, headers=seller_h)
    assert r.status_code == 400


def test_cancel_blind_bid_twice_conflicts(client, make_user, make_item):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = _blind(make_item, seller_h)
    bid = client.post(
        f"/items/{item['id']}/blind-bids", json={"amount": 2000}, headers=buyer_h
    ).json()
    assert client.delete(f"/blind-bids/{bid['id']}", headers=buyer_h).status_code == 204
    assert client.delete(f"/blind-bids/{bid['id']}", headers=buyer_h).status_code == 409


def test_cancel_blind_bid_after_close_conflicts(client, make_user, make_item):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    item = _blind(make_item, seller_h)
    bid = client.post(
        f"/items/{item['id']}/blind-bids", json={"amount": 2000}, headers=buyer_h
    ).json()
    client.post(f"/items/{item['id']}/close", headers=seller_h)
    assert client.delete(f"/blind-bids/{bid['id']}", headers=buyer_h).status_code == 409

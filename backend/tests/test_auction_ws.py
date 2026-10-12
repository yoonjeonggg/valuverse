"""실시간 입찰 WebSocket 테스트 (WS /items/{id}/bid)."""

from functools import partial

from tests.conftest import create_item


def _token(headers) -> str:
    return headers["Authorization"].split(" ", 1)[1]


_item = partial(create_item, buy_now_price=9000)


def test_ws_sends_snapshot_on_connect(client, make_user):
    seller_h, _ = make_user()
    item = _item(client, seller_h)
    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        snap = ws.receive_json()
        assert snap["type"] == "snapshot"
        assert snap["item_id"] == item["id"]
        assert snap["current_price"] == 1000


def test_ws_bid_broadcasts_to_all_clients(client, make_user):
    seller_h, _ = make_user()
    bidder_h, bidder = make_user()
    item = _item(client, seller_h)

    with client.websocket_connect(f"/items/{item['id']}/bid") as watcher:
        assert watcher.receive_json()["type"] == "snapshot"

        with client.websocket_connect(f"/items/{item['id']}/bid") as actor:
            assert actor.receive_json()["type"] == "snapshot"
            actor.send_json({"token": _token(bidder_h), "amount": 2500})

            evt = watcher.receive_json()
            assert evt["type"] == "bid"
            assert evt["amount"] == 2500
            assert evt["bidder_id"] == bidder["id"]
            assert evt["current_price"] == 2500

    # REST 로도 반영됐는지 확인
    assert client.get(f"/items/{item['id']}").json()["current_price"] == 2500


def test_rest_bid_pushes_to_ws_client(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _bidder = make_user()
    item = _item(client, seller_h)

    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        assert ws.receive_json()["type"] == "snapshot"
        r = client.post(f"/items/{item['id']}/bids", json={"amount": 3000}, headers=bidder_h)
        assert r.status_code == 201
        evt = ws.receive_json()
        assert evt["type"] == "bid"
        assert evt["amount"] == 3000


def test_ws_bid_without_token_errors(client, make_user):
    seller_h, _ = make_user()
    item = _item(client, seller_h)
    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        ws.receive_json()
        ws.send_json({"amount": 2000})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "인증" in err["detail"]


def test_ws_low_bid_returns_error(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = _item(client, seller_h)
    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        ws.receive_json()
        ws.send_json({"token": _token(bidder_h), "amount": 500})  # start_price 미만
        err = ws.receive_json()
        assert err["type"] == "error"


def test_ws_close_broadcasts_closed(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = _item(client, seller_h)
    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        ws.receive_json()
        client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=bidder_h)
        assert ws.receive_json()["type"] == "bid"
        client.post(f"/items/{item['id']}/close", headers=seller_h)
        evt = ws.receive_json()
        assert evt["type"] == "closed"
        assert evt["final_price"] == 2000


def test_ws_unknown_item_errors(client, make_user):
    make_user()
    with client.websocket_connect("/items/9999/bid") as ws:
        err = ws.receive_json()
        assert err["type"] == "error"


def test_ws_malformed_message_keeps_connection(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = _item(client, seller_h)
    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        ws.receive_json()
        for bad in ("not json", "[1, 2]", '"text"'):
            ws.send_text(bad)
            err = ws.receive_json()
            assert err["type"] == "error"
            assert "JSON" in err["detail"]
        # 형식 오류 뒤에도 같은 연결로 정상 입찰이 된다.
        ws.send_json({"token": _token(bidder_h), "amount": 2000})
        assert ws.receive_json()["type"] == "bid"

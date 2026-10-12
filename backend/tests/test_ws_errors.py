"""실시간 입찰 WS 의 예외 경로와 ConnectionManager 의 장애 처리 테스트."""

import asyncio
import logging

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import auction_service, ws_manager
from app.services.ws_manager import ConnectionManager
from tests.conftest import create_item
from tests.test_ws_pubsub import _FakeBroker, _FakeRedis, _FakeWS, _settle


def _token(headers) -> str:
    return headers["Authorization"].split(" ", 1)[1]


def _boom(*_args, **_kwargs):
    raise RuntimeError("SELECT secret FROM internal_table")


# ---------- WS 엔드포인트 ----------
def test_ws_invalid_amount_keeps_connection(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = create_item(client, seller_h)
    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        ws.receive_json()  # snapshot
        for bad in ({}, {"amount": "abc"}, {"amount": None}):
            ws.send_json({"token": _token(bidder_h), **bad})
            assert ws.receive_json() == {"type": "error", "detail": "amount 가 올바르지 않습니다."}

        # 연결은 유지되어 정상 입찰이 이어서 처리된다
        ws.send_json({"token": _token(bidder_h), "amount": 2000})
        assert ws.receive_json()["type"] == "bid"


def test_ws_token_from_query_string(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = create_item(client, seller_h)
    with client.websocket_connect(f"/items/{item['id']}/bid?token={_token(bidder_h)}") as ws:
        ws.receive_json()
        ws.send_json({"amount": 2000})
        assert ws.receive_json()["amount"] == 2000


def test_ws_deactivated_user_cannot_bid(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = create_item(client, seller_h)
    client.delete("/users/me", headers=bidder_h)
    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        ws.receive_json()
        ws.send_json({"token": _token(bidder_h), "amount": 2000})
        assert ws.receive_json()["detail"] == "인증이 필요합니다."


def test_ws_internal_bid_error_is_not_leaked(client, make_user, monkeypatch, caplog):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = create_item(client, seller_h)
    monkeypatch.setattr(auction_service, "create_bid", _boom)
    caplog.set_level(logging.ERROR, logger="app.routers.auction_ws")

    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        ws.receive_json()
        ws.send_json({"token": _token(bidder_h), "amount": 2000})
        msg = ws.receive_json()

    assert msg == {"type": "error", "detail": "입찰을 처리하지 못했습니다."}
    assert "internal_table" not in str(msg)
    assert any(r.exc_info for r in caplog.records)  # 서버 로그에는 스택이 남는다


def test_ws_snapshot_internal_error(client, make_user, monkeypatch):
    seller_h, _ = make_user()
    item = create_item(client, seller_h)
    monkeypatch.setattr(auction_service, "get_item", _boom)
    with client.websocket_connect(f"/items/{item['id']}/bid") as ws:
        assert ws.receive_json() == {"type": "error", "detail": "상품을 찾을 수 없습니다."}


# ---------- ConnectionManager ----------
class _DeadWS(_FakeWS):
    async def send_json(self, payload: dict) -> None:
        raise RuntimeError("socket closed")


def test_dead_socket_is_dropped_without_affecting_others():
    async def scenario():
        mgr = ConnectionManager()
        alive, dead = _FakeWS(), _DeadWS()
        await mgr.connect(1, alive)
        await mgr.connect(1, dead)

        await mgr.broadcast_async(1, {"type": "bid"})
        assert alive.received == [{"type": "bid"}]
        assert mgr._rooms[1] == {alive}

        mgr.disconnect(1, alive)
        assert 1 not in mgr._rooms  # 빈 방은 정리된다

    asyncio.run(scenario())


def test_broadcast_without_loop_is_noop():
    ConnectionManager().broadcast(1, {"type": "bid"})  # 예외 없이 무시


def test_broadcast_from_inside_event_loop():
    async def scenario():
        mgr = ConnectionManager()
        mgr.bind_loop(asyncio.get_running_loop())
        ws = _FakeWS()
        await mgr.connect(3, ws)
        mgr.broadcast(3, {"type": "closed"})
        await _settle()
        assert ws.received == [{"type": "closed"}]

    asyncio.run(scenario())


class _FlakyRedis(_FakeRedis):
    """첫 구독은 끊기고 두 번째부터 정상인 Redis."""

    def __init__(self, broker):
        super().__init__(broker)
        self.attempts = 0

    def pubsub(self):
        self.attempts += 1
        if self.attempts == 1:
            raise ConnectionError("redis restarting")
        return super().pubsub()


def test_pubsub_reconnects_after_failure(monkeypatch, caplog):
    monkeypatch.setattr(ws_manager, "_RECONNECT_DELAY_SECONDS", 0)
    caplog.set_level(logging.ERROR, logger="app.services.ws_manager")

    async def scenario():
        broker = _FakeBroker()
        redis = _FlakyRedis(broker)
        mgr = ConnectionManager()
        await mgr.start_pubsub(redis)
        ws = _FakeWS()
        await mgr.connect(1, ws)

        await mgr.broadcast_async(1, {"type": "bid"})
        await _settle()
        await mgr.stop_pubsub()
        return redis.attempts, ws.received

    attempts, received = asyncio.run(scenario())
    assert attempts == 2
    assert received == [{"type": "bid"}]
    assert any("재연결" in r.getMessage() for r in caplog.records)


def test_lifespan_starts_and_stops_redis_pubsub(monkeypatch):
    fake = _FakeRedis(_FakeBroker())
    monkeypatch.setattr(settings, "ws_broadcast_backend", "redis")
    monkeypatch.setattr("redis.asyncio.Redis.from_url", lambda url: fake)

    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert ws_manager.manager._redis is fake
    assert ws_manager.manager._redis is None

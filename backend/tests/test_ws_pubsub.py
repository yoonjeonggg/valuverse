"""로드밸런싱 환경의 WS 브로드캐스트: Redis pub/sub 로 인스턴스 간 전달되는지 확인한다.

실제 Redis 대신 같은 프로세스 안의 가짜 브로커를 쓰고, ConnectionManager 두 개를
서로 다른 백엔드 인스턴스로 본다.
"""

import asyncio
import json

from app.services.ws_manager import CHANNEL, ConnectionManager


class _FakeBroker:
    def __init__(self) -> None:
        self.queues: list[asyncio.Queue] = []


class _FakePubSub:
    def __init__(self, broker: _FakeBroker) -> None:
        self._broker = broker
        self._queue: asyncio.Queue = asyncio.Queue()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self._broker.queues.remove(self._queue)

    async def subscribe(self, channel: str) -> None:
        assert channel == CHANNEL
        self._broker.queues.append(self._queue)

    async def listen(self):
        yield {"type": "subscribe", "data": 1}
        while True:
            yield await self._queue.get()


class _FakeRedis:
    def __init__(self, broker: _FakeBroker, fail_publish: bool = False) -> None:
        self._broker = broker
        self._fail_publish = fail_publish

    def pubsub(self):
        return _FakePubSub(self._broker)

    async def publish(self, channel: str, data: str) -> None:
        if self._fail_publish:
            raise ConnectionError("redis down")
        for q in self._broker.queues:
            q.put_nowait({"type": "message", "channel": channel, "data": data})

    async def aclose(self) -> None:
        pass


class _FakeWS:
    def __init__(self) -> None:
        self.received: list[dict] = []

    async def accept(self) -> None:
        pass

    async def send_json(self, payload: dict) -> None:
        self.received.append(payload)


async def _settle():
    for _ in range(5):
        await asyncio.sleep(0)


def test_broadcast_reaches_clients_on_other_instance():
    async def scenario():
        broker = _FakeBroker()
        a, b = ConnectionManager(), ConnectionManager()
        await a.start_pubsub(_FakeRedis(broker))
        await b.start_pubsub(_FakeRedis(broker))

        on_a, on_b, other_room = _FakeWS(), _FakeWS(), _FakeWS()
        await a.connect(1, on_a)
        await b.connect(1, on_b)
        await b.connect(2, other_room)

        # 인스턴스 A 에서 입찰이 처리됨 -> B 에 붙은 클라이언트도 받아야 한다.
        await a.broadcast_async(1, {"type": "bid", "amount": 3000})
        await _settle()

        assert on_a.received == [{"type": "bid", "amount": 3000}]
        assert on_b.received == [{"type": "bid", "amount": 3000}]
        assert other_room.received == []

        await a.stop_pubsub()
        await b.stop_pubsub()

    asyncio.run(scenario())


def test_publish_failure_falls_back_to_local_delivery():
    async def scenario():
        mgr = ConnectionManager()
        await mgr.start_pubsub(_FakeRedis(_FakeBroker(), fail_publish=True))
        ws = _FakeWS()
        await mgr.connect(1, ws)

        await mgr.broadcast_async(1, {"type": "bid"})
        assert ws.received == [{"type": "bid"}]
        await mgr.stop_pubsub()

    asyncio.run(scenario())


def test_message_payload_is_json_serializable_with_datetimes():
    from datetime import UTC, datetime

    async def scenario():
        broker = _FakeBroker()
        mgr = ConnectionManager()
        await mgr.start_pubsub(_FakeRedis(broker))
        ws = _FakeWS()
        await mgr.connect(7, ws)

        when = datetime(2026, 10, 2, tzinfo=UTC)
        await mgr.broadcast_async(7, {"type": "bid", "at": when})
        await _settle()
        assert ws.received == [json.loads(json.dumps({"type": "bid", "at": when}, default=str))]
        await mgr.stop_pubsub()

    asyncio.run(scenario())

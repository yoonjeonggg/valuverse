"""경매 실시간 입찰용 WebSocket 연결 관리 (FR-AUC-02, NFR-01).

동기 서비스 코드(auction_service)에서도 브로드캐스트할 수 있도록,
앱 시작 시 메인 이벤트 루프를 붙잡아 두고 `broadcast()` 는 그 루프에
코루틴을 스레드세이프하게 넘긴다.

로드밸런서 뒤에서 백엔드를 여러 대 띄우면 WS 연결이 인스턴스마다 흩어진다.
`WS_BROADCAST_BACKEND=redis` 면 브로드캐스트를 Redis 채널에 발행하고, 모든 인스턴스가
그 채널을 구독해 자기에게 붙은 소켓에만 전달한다. (기본값 memory 는 단일 인스턴스용)
"""

import asyncio
import contextlib
import json
import logging
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

CHANNEL = "valuverse:auction_ws"
_RECONNECT_DELAY_SECONDS = 1.0


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._redis = None  # redis.asyncio.Redis (pub/sub 모드일 때만)
        self._listener: asyncio.Task | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # ---------- Redis pub/sub ----------
    async def start_pubsub(self, redis_client) -> None:
        """Redis 채널 구독을 시작한다. 앱 lifespan 시작 시 호출."""
        self._redis = redis_client
        ready = asyncio.Event()
        self._listener = asyncio.create_task(self._listen(ready))
        # 구독이 걸린 뒤에 요청을 받아야 기동 직후 브로드캐스트를 놓치지 않는다.
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(ready.wait(), timeout=5)

    async def stop_pubsub(self) -> None:
        if self._listener:
            self._listener.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener
            self._listener = None
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def _listen(self, ready: asyncio.Event) -> None:
        while True:
            try:
                async with self._redis.pubsub() as pubsub:
                    await pubsub.subscribe(CHANNEL)
                    ready.set()
                    logger.info("WS 브로드캐스트 채널 구독 시작 (%s)", CHANNEL)
                    async for message in pubsub.listen():
                        if message.get("type") != "message":
                            continue
                        data = json.loads(message["data"])
                        await self._send_room(int(data["item_id"]), data["payload"])
            except asyncio.CancelledError:
                raise
            except Exception:
                # Redis 재시작/네트워크 단절 시 재접속한다.
                logger.exception("WS 브로드캐스트 구독 끊김, 재연결 시도")
                await asyncio.sleep(_RECONNECT_DELAY_SECONDS)

    async def _publish(self, item_id: int, payload: dict) -> None:
        try:
            await self._redis.publish(
                CHANNEL,
                json.dumps({"item_id": item_id, "payload": payload}, default=str),
            )
        except Exception:
            # Redis 장애 시 최소한 같은 인스턴스에 붙은 클라이언트에는 전달한다.
            logger.exception("WS 브로드캐스트 발행 실패, 로컬 전송으로 대체 (item_id=%s)", item_id)
            await self._send_room(item_id, payload)

    # ---------- 연결 관리 ----------
    async def connect(self, item_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._rooms[item_id].add(ws)

    def disconnect(self, item_id: int, ws: WebSocket) -> None:
        self._rooms[item_id].discard(ws)
        if not self._rooms[item_id]:
            self._rooms.pop(item_id, None)

    async def _send_room(self, item_id: int, payload: dict) -> None:
        dead = []
        for ws in list(self._rooms.get(item_id, ())):
            try:
                await ws.send_json(payload)
            except (WebSocketDisconnect, RuntimeError, OSError):
                # 이미 끊긴 소켓 (starlette 는 닫힌 소켓 send 에 RuntimeError, uvicorn 은 OSError 계열)
                dead.append(ws)
        for ws in dead:
            self.disconnect(item_id, ws)

    async def broadcast_async(self, item_id: int, payload: dict) -> None:
        if self._redis is not None:
            await self._publish(item_id, payload)
        else:
            await self._send_room(item_id, payload)

    def broadcast(self, item_id: int, payload: dict) -> None:
        """동기 컨텍스트에서 호출. 이벤트 루프가 없으면 조용히 무시한다."""
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is loop:
            loop.create_task(self.broadcast_async(item_id, payload))
        else:
            # 결과를 기다리지 않는다: 다른 스레드(요청 처리 스레드)를
            # WS 팬아웃이 끝날 때까지 블로킹할 이유가 없다 (예외는 broadcast_async 가 흡수).
            asyncio.run_coroutine_threadsafe(self.broadcast_async(item_id, payload), loop)


manager = ConnectionManager()

"""경매 실시간 입찰용 WebSocket 연결 관리 (FR-AUC-02, NFR-01).

동기 서비스 코드(auction_service)에서도 브로드캐스트할 수 있도록,
앱 시작 시 메인 이벤트 루프를 붙잡아 두고 `broadcast()` 는 그 루프에
코루틴을 스레드세이프하게 넘긴다.
"""

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

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
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(item_id, ws)

    async def broadcast_async(self, item_id: int, payload: dict) -> None:
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
            loop.create_task(self._send_room(item_id, payload))
        else:
            # 결과를 기다리지 않는다: 다른 스레드(요청 처리 스레드)를
            # WS 팬아웃이 끝날 때까지 블로킹할 이유가 없다 (예외는 _send_room 이 흡수).
            asyncio.run_coroutine_threadsafe(self._send_room(item_id, payload), loop)


manager = ConnectionManager()

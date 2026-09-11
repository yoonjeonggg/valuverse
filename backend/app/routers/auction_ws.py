"""실시간 입찰 WebSocket 엔드포인트: WS /items/{id}/bid (FR-AUC-02)."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.deps import lookup_user_by_token
from app.database import get_db
from app.models.user import User
from app.schemas.auction import BidCreate
from app.services import auction_service
from app.services.ws_manager import manager

router = APIRouter()


def _snapshot(item) -> dict:
    return {
        "type": "snapshot",
        "item_id": item.id,
        "title": item.title,
        "current_price": item.current_price,
        "status": item.status,
        "end_time": item.end_time.isoformat() if item.end_time else None,
        "extended_count": item.extended_count,
        "auction_type": item.auction_type,
    }


def _user_from_token(db: Session, token: str | None) -> User | None:
    user = lookup_user_by_token(db, token)
    return user if user and user.is_active else None


@router.websocket("/items/{item_id}/bid")
async def auction_bid_ws(
    websocket: WebSocket, item_id: int, db: Session = Depends(get_db)
):
    await manager.connect(item_id, websocket)
    try:
        try:
            item = await run_in_threadpool(auction_service.get_item, db, item_id)
            snapshot = _snapshot(item)
        except Exception:
            await websocket.send_json(
                {"type": "error", "detail": "상품을 찾을 수 없습니다."}
            )
            return
        finally:
            # 읽기 트랜잭션을 즉시 닫아 다른 요청과의 경합을 피한다.
            db.rollback()

        await websocket.send_json(snapshot)

        while True:
            msg = await websocket.receive_json()
            token = msg.get("token") or websocket.query_params.get("token")
            user = _user_from_token(db, token)
            db.rollback()
            if not user:
                await websocket.send_json(
                    {"type": "error", "detail": "인증이 필요합니다."}
                )
                continue
            try:
                amount = int(msg["amount"])
            except (KeyError, TypeError, ValueError):
                await websocket.send_json(
                    {"type": "error", "detail": "amount 가 올바르지 않습니다."}
                )
                continue

            try:
                # create_bid 가 성공 시 방 전체에 브로드캐스트한다.
                await run_in_threadpool(
                    auction_service.create_bid,
                    db,
                    item_id,
                    user.id,
                    BidCreate(amount=amount),
                )
            except Exception as exc:
                db.rollback()
                detail = getattr(exc, "detail", str(exc))
                await websocket.send_json({"type": "error", "detail": detail})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(item_id, websocket)

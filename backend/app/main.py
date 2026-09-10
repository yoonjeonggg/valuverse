import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  - 모든 모델을 메타데이터에 등록
from app.core.config import settings
from app.database import Base, engine
from app.routers.user import auth_router, user_router
from app.routers.auction import item_router, bid_router
from app.routers.auction_ws import router as auction_ws_router
from app.services.ws_manager import manager as ws_manager
from app.routers.skill import skill_item_router, booking_router, escrow_router
from app.routers.prediction import prediction_router, bet_router
from app.routers.point import router as point_router
from app.routers.review import router as review_router
from app.routers.report import router as report_router
from app.routers.notification import router as notification_router
from app.routers.ai import router as ai_router

if settings.auto_create_tables:
    # 빠른 실행용. 마이그레이션(alembic)을 쓸 때는 AUTO_CREATE_TABLES=false 로 둔다.
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 동기 서비스 코드에서 브로드캐스트할 수 있도록 메인 루프를 붙잡아 둔다.
    ws_manager.bind_loop(asyncio.get_running_loop())
    yield


app = FastAPI(
    title="AI 경매 플랫폼 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(item_router)
app.include_router(bid_router)
app.include_router(auction_ws_router)
app.include_router(skill_item_router)
app.include_router(booking_router)
app.include_router(escrow_router)
app.include_router(prediction_router)
app.include_router(bet_router)
app.include_router(point_router)
app.include_router(review_router)
app.include_router(report_router)
app.include_router(notification_router)
app.include_router(ai_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

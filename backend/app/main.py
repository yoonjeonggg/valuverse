from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  - 모든 모델을 메타데이터에 등록
from app.core.config import settings
from app.database import Base, engine
from app.routers.user import auth_router, user_router
from app.routers.auction import item_router, bid_router
from app.routers.skill import skill_item_router, booking_router, escrow_router
from app.routers.prediction import prediction_router, bet_router
from app.routers.point import router as point_router
from app.routers.review import router as review_router
from app.routers.report import router as report_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI 경매 플랫폼 API",
    version="0.1.0",
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
app.include_router(skill_item_router)
app.include_router(booking_router)
app.include_router(escrow_router)
app.include_router(prediction_router)
app.include_router(bet_router)
app.include_router(point_router)
app.include_router(review_router)
app.include_router(report_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

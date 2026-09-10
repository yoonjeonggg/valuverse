from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ai import (
    PriceSuggestionResponse,
    AbuseCheckRequest,
    AbuseCheckResponse,
)
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["AI 보조"])


@router.get("/price-suggestion", response_model=PriceSuggestionResponse)
def price_suggestion(
    category: str = Query(...),
    auction_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """과거 낙찰가 기반 시세/시작가 추천 (FR-BLD-05)."""
    return ai_service.suggest_price(db, category, auction_type)


@router.post("/abuse-check", response_model=AbuseCheckResponse)
def abuse_check(
    payload: AbuseCheckRequest,
    user: User = Depends(get_current_user),
):
    """규칙 기반 어뷰징 문구 탐지 (FR-AI-03)."""
    return ai_service.check_abuse(payload.text)

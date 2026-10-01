from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.ai import (
    AbuseCheckRequest,
    AbuseCheckResponse,
    ChatRequest,
    ChatResponse,
    DescriptionSuggestionRequest,
    DescriptionSuggestionResponse,
    PriceSuggestionResponse,
    SkillTagRequest,
    SkillTagResponse,
)
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["AI 보조"])


@router.get("/price-suggestion", response_model=PriceSuggestionResponse)
def price_suggestion(
    db: DbSession,
    category: str = Query(...),
    auction_type: str | None = Query(default=None),
):
    """과거 낙찰가 기반 시세/시작가 추천 (FR-BLD-05)."""
    return ai_service.suggest_price(db, category, auction_type)


@router.post("/abuse-check", response_model=AbuseCheckResponse)
def abuse_check(payload: AbuseCheckRequest, user: CurrentUser):
    """규칙 기반 어뷰징 문구 탐지 (FR-AI-03)."""
    return ai_service.check_abuse(payload.text)


@router.post("/description-suggestion", response_model=DescriptionSuggestionResponse)
def description_suggestion(
    payload: DescriptionSuggestionRequest,
    user: CurrentUser,
    db: DbSession,
):
    """상품 설명 자동 생성/보완 제안 (FR-AI-01)."""
    return ai_service.generate_description(
        db,
        payload.title,
        payload.category,
        payload.keywords,
        payload.existing_description,
    )


@router.post("/skill-tag-suggestion", response_model=SkillTagResponse)
def skill_tag_suggestion(payload: SkillTagRequest, user: CurrentUser):
    """스킬 소개글 기반 카테고리/난이도 자동 태깅 (FR-SKL-06)."""
    return ai_service.tag_skill_intro(payload.intro_text)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: DbSession):
    """AI 챗봇 입찰 상담 - 규칙 기반 FAQ 매칭 + 답변 근거 표기 (디자인 요구사항 명세서 4.7)."""
    return ai_service.answer_chat(db, payload.message, payload.item_id, payload.item_type)

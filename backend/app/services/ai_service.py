"""AI 보조 기능 - 현재는 통계/규칙 기반 구현.

개발명세서상 AI Gateway(Ollama LLM/RAG/CV)는 별도 서비스로 분리 예정이며,
여기서는 LLM 없이 계산 가능한 범위(과거 낙찰가 기반 시세 추천, 규칙 기반
어뷰징 문구 탐지)만 제공한다. FR-BLD-05 / FR-AI-03 참고.
"""

import statistics

from sqlalchemy.orm import Session

from app.models.auction import Item

_MIN_SAMPLES = 3


def suggest_price(
    db: Session, category: str, auction_type: str | None = None
) -> dict:
    q = db.query(Item.final_price).filter(
        Item.category == category,
        Item.status == "closed",
        Item.final_price.isnot(None),
    )
    if auction_type:
        q = q.filter(Item.auction_type == auction_type)
    prices = [row[0] for row in q.all()]

    base = {
        "category": category,
        "auction_type": auction_type,
        "sample_size": len(prices),
        "enough_data": len(prices) >= _MIN_SAMPLES,
    }
    if len(prices) < _MIN_SAMPLES:
        return base

    median = int(statistics.median(prices))
    base.update(
        {
            "avg_final_price": int(statistics.fmean(prices)),
            "median_final_price": median,
            "min_final_price": min(prices),
            "max_final_price": max(prices),
            # 시작가는 시세보다 낮게, 즉시구매가는 높게 제안
            "suggested_start_price": max(1, round(median * 0.7)),
            "suggested_buy_now_price": round(median * 1.3),
        }
    )
    return base


# 카테고리 -> 위험 문구 목록 (부분 문자열 매칭, 소문자 비교)
ABUSE_KEYWORDS: dict[str, list[str]] = {
    "external_contact": [
        "직거래", "계좌이체", "현금거래", "카톡", "카카오톡", "텔레그램",
        "라인아이디", "개인연락", "외부거래", "번호주세요",
    ],
    "scam_signal": [
        "선입금", "입금먼저", "환불불가", "노쇼시연락", "급처", "급매",
        "보증금요구", "수수료없이",
    ],
    "prohibited": [
        "가품", "짝퉁", "레플리카", "미개봉아님", "as불가",
    ],
}


def check_abuse(text: str) -> dict:
    low = text.lower()
    matched: list[str] = []
    categories: list[str] = []
    for cat, terms in ABUSE_KEYWORDS.items():
        hits = [t for t in terms if t.lower() in low]
        if hits:
            matched.extend(hits)
            categories.append(cat)
    return {
        "flagged": bool(matched),
        "score": len(matched),
        "matched_terms": matched,
        "categories": categories,
    }


# 설명에 이 키워드 중 하나도 없으면 보완을 제안한다.
_DESCRIPTION_CHECKLIST: list[tuple[list[str], str]] = [
    (["상태", "미개봉", "중고", "새제품", "사용감"], "제품/서비스 상태를 구체적으로 설명해 주세요."),
    (["환불", "교환", "취소", "as"], "환불/교환/취소 정책을 명시하면 분쟁을 줄일 수 있습니다."),
    (["사진", "이미지", "촬영"], "실제 사진 첨부 여부를 안내하면 신뢰도가 올라갑니다."),
    (["직거래", "택배", "배송"], "거래/배송 방식을 안내해 주세요."),
]


def generate_description(
    db: Session,
    title: str,
    category: str | None = None,
    keywords: list[str] | None = None,
    existing_description: str | None = None,
) -> dict:
    """상품 설명 초안 생성 + 기존 설명 보완 제안 (FR-AI-01, 템플릿 기반).

    LLM 없이 제목/카테고리/키워드와 과거 낙찰가 통계(suggest_price)를 조합해
    초안을 만들고, 기존 설명에 빠진 항목을 체크리스트로 짚어준다.
    """
    keywords = keywords or []
    parts = [title.strip()]
    if category:
        parts.append(f"카테고리: {category}")
    if keywords:
        parts.append("특징: " + ", ".join(keywords))

    market = suggest_price(db, category) if category else None
    if market and market["enough_data"]:
        parts.append(
            f"참고 시세: 유사 상품 평균 낙찰가 {market['avg_final_price']}원"
            f" (추천 시작가 {market['suggested_start_price']}원)"
        )

    low_existing = (existing_description or "").lower()
    suggestions = [
        tip for terms, tip in _DESCRIPTION_CHECKLIST if not any(t in low_existing for t in terms)
    ]

    return {
        "draft_description": " / ".join(parts),
        "suggestions": suggestions,
        "market_context": market,
    }


# 스킬 소개글 -> 카테고리 키워드 매핑 (부분 문자열 매칭)
_SKILL_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "디자인": ["디자인", "로고", "포스터", "일러스트", "편집디자인"],
    "번역/통역": ["번역", "통역", "영어", "중국어", "일본어"],
    "과외/교육": ["과외", "수학", "영어회화", "코딩", "강의", "레슨", "튜터링"],
    "촬영/영상": ["촬영", "영상편집", "브이로그", "사진촬영"],
    "청소/정리": ["청소", "정리수납", "이사청소"],
    "수리/설치": ["수리", "설치", "정비", "as"],
    "상담/코칭": ["상담", "코칭", "멘토링", "컨설팅"],
}

# 난이도 키워드 (먼저 매칭되는 쪽 우선)
_SKILL_LEVEL_KEYWORDS: list[tuple[str, list[str]]] = [
    ("고급", ["전문가", "자격증", "경력", "숙련", "마스터"]),
    ("초급", ["초보", "누구나", "입문", "쉽게"]),
]


def tag_skill_intro(text: str) -> dict:
    """스킬 소개글 기반 카테고리/난이도 자동 태깅 (FR-SKL-06, 키워드 매칭 기반)."""
    low = text.lower()
    scores = {
        cat: sum(1 for kw in kws if kw.lower() in low)
        for cat, kws in _SKILL_CATEGORY_KEYWORDS.items()
    }
    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        best_category = "기타"

    level = "중급"
    for lvl, kws in _SKILL_LEVEL_KEYWORDS:
        if any(kw.lower() in low for kw in kws):
            level = lvl
            break

    return {
        "suggested_category": best_category,
        "suggested_level": level,
        "category_scores": scores,
    }

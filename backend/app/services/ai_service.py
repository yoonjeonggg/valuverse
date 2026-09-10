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

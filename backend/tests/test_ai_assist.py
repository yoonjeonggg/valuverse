"""AI 보조(통계·규칙 기반) 테스트 - 시세 추천 / 어뷰징 탐지."""

from datetime import timedelta

from app.core.timeutils import now


def _closed_sale(client, seller_h, buyer_h, category, price):
    item = client.post(
        "/items",
        json={
            "title": "판매품",
            "category": category,
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=seller_h,
    ).json()
    client.post(f"/items/{item['id']}/bids", json={"amount": price}, headers=buyer_h)
    client.post(f"/items/{item['id']}/close", headers=seller_h)


# ---------- 시세 추천 ----------
def test_price_suggestion_needs_enough_data(client, make_user):
    seller_h, _ = make_user()
    buyer_h, _ = make_user()
    _closed_sale(client, seller_h, buyer_h, "camera", 10000)
    r = client.get("/ai/price-suggestion", params={"category": "camera"})
    assert r.status_code == 200
    body = r.json()
    assert body["enough_data"] is False
    assert body["sample_size"] == 1


def test_price_suggestion_computes_from_history(client, make_user):
    seller_h, _ = make_user()
    b1, _ = make_user()
    b2, _ = make_user()
    b3, _ = make_user()
    for b, p in [(b1, 10000), (b2, 20000), (b3, 30000)]:
        _closed_sale(client, seller_h, b, "guitar", p)

    body = client.get("/ai/price-suggestion", params={"category": "guitar"}).json()
    assert body["enough_data"] is True
    assert body["sample_size"] == 3
    assert body["median_final_price"] == 20000
    assert body["avg_final_price"] == 20000
    assert body["suggested_start_price"] == 14000
    assert body["suggested_buy_now_price"] == 26000


def test_price_suggestion_requires_category(client):
    assert client.get("/ai/price-suggestion").status_code == 422


def test_price_suggestion_unknown_category_no_data(client):
    body = client.get(
        "/ai/price-suggestion", params={"category": "nonexistent"}
    ).json()
    assert body["sample_size"] == 0
    assert body["enough_data"] is False


# ---------- 어뷰징 문구 탐지 ----------
def test_abuse_check_flags_external_contact(client, make_user):
    h, _ = make_user()
    r = client.post(
        "/ai/abuse-check",
        json={"text": "직거래만 가능해요 카톡 주세요"},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["flagged"] is True
    assert body["score"] >= 2
    assert "external_contact" in body["categories"]


def test_abuse_check_clean_text(client, make_user):
    h, _ = make_user()
    body = client.post(
        "/ai/abuse-check",
        json={"text": "정품 카메라 판매합니다. 상태 좋아요."},
        headers=h,
    ).json()
    assert body["flagged"] is False
    assert body["score"] == 0


def test_abuse_check_requires_auth(client):
    assert client.post("/ai/abuse-check", json={"text": "직거래"}).status_code == 401


# ---------- 상품 설명 자동 생성/보완 제안 ----------
def test_description_suggestion_drafts_from_title_and_market(client, make_user):
    seller_h, _ = make_user()
    b1, _ = make_user()
    b2, _ = make_user()
    b3, _ = make_user()
    for b, p in [(b1, 10000), (b2, 20000), (b3, 30000)]:
        _closed_sale(client, seller_h, b, "guitar", p)

    h, _ = make_user()
    r = client.post(
        "/ai/description-suggestion",
        json={"title": "통기타 팝니다", "category": "guitar", "keywords": ["상태 좋음"]},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert "통기타 팝니다" in body["draft_description"]
    assert "20000" in body["draft_description"]
    assert body["market_context"]["enough_data"] is True
    assert len(body["suggestions"]) > 0


def test_description_suggestion_fewer_tips_when_existing_description_is_complete(client, make_user):
    h, _ = make_user()
    body = client.post(
        "/ai/description-suggestion",
        json={
            "title": "노트북 팝니다",
            "existing_description": "사용감 있는 중고 상태이며 사진 첨부했습니다. "
            "택배 거래만 가능하고 단순 변심 환불은 불가합니다.",
        },
        headers=h,
    ).json()
    assert body["suggestions"] == []


def test_description_suggestion_requires_auth(client):
    assert (
        client.post("/ai/description-suggestion", json={"title": "제목"}).status_code == 401
    )


# ---------- 스킬 소개글 카테고리/난이도 태깅 ----------
def test_skill_tag_suggestion_detects_category_and_level(client, make_user):
    h, _ = make_user()
    r = client.post(
        "/ai/skill-tag-suggestion",
        json={"intro_text": "10년 경력의 전문가가 로고 디자인을 도와드립니다."},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["suggested_category"] == "디자인"
    assert body["suggested_level"] == "고급"


def test_skill_tag_suggestion_defaults_to_기타_when_no_keyword_matches(client, make_user):
    h, _ = make_user()
    body = client.post(
        "/ai/skill-tag-suggestion",
        json={"intro_text": "그냥 이것저것 도와드립니다."},
        headers=h,
    ).json()
    assert body["suggested_category"] == "기타"
    assert body["suggested_level"] == "중급"


def test_skill_tag_suggestion_requires_auth(client):
    assert (
        client.post("/ai/skill-tag-suggestion", json={"intro_text": "번역 가능합니다"}).status_code
        == 401
    )


# ---------- AI 챗봇(입찰 상담) ----------
def test_chat_matches_faq_and_returns_reference(client):
    r = client.post("/ai/chat", json={"message": "블라인드 경매는 순위만 보이나요?"})
    assert r.status_code == 200
    body = r.json()
    assert "블라인드 경매 안내" in body["references"]
    assert "순위" in body["answer"]


def test_chat_falls_back_to_default_when_no_faq_matches(client):
    body = client.post("/ai/chat", json={"message": "안녕하세요"}).json()
    assert body["references"] == ["일반 안내"]


def test_chat_includes_item_context_when_item_id_given(client, make_user):
    seller_h, _ = make_user()
    item = client.post(
        "/items",
        json={
            "title": "빈티지 카메라",
            "start_price": 1000,
            "end_time": "2999-01-01T00:00:00+09:00",
        },
        headers=seller_h,
    ).json()

    body = client.post(
        "/ai/chat", json={"message": "즉시구매 되나요?", "item_id": item["id"]}
    ).json()
    assert "빈티지 카메라" in body["answer"]
    assert body["item_id"] == item["id"]
    assert "즉시구매 안내" in body["references"]


def test_chat_supports_skill_item_context(client, make_user):
    seller_h, _ = make_user()
    skill = client.post(
        "/skill-items",
        json={"title": "로고 디자인", "start_price": 5000},
        headers=seller_h,
    ).json()

    body = client.post(
        "/ai/chat",
        json={"message": "에스크로는 언제 풀리나요?", "item_id": skill["id"], "item_type": "skill_item"},
    ).json()
    assert "로고 디자인" in body["answer"]
    assert "에스크로/정산 안내" in body["references"]


def test_chat_does_not_require_auth(client):
    assert client.post("/ai/chat", json={"message": "안녕하세요"}).status_code == 200


def test_chat_requires_message(client):
    assert client.post("/ai/chat", json={}).status_code == 422

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

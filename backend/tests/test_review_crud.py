"""리뷰 작성 검증·수정·삭제·조회의 예외 경로 테스트."""

from datetime import timedelta

import pytest

from app.core.timeutils import now
from app.models.review import Review
from app.models.user import User
from tests.conftest import TestingSessionLocal


@pytest.fixture
def traded(client, make_user, make_item):
    """seller 의 상품을 buyer 가 낙찰받은 상태. (seller_h, seller, buyer_h, buyer, item)"""
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    item = make_item(seller_h)
    client.post(f"/items/{item['id']}/bids", json={"amount": 2000}, headers=buyer_h)
    client.post(f"/items/{item['id']}/close", headers=seller_h)
    return seller_h, seller, buyer_h, buyer, item


def _write(client, traded, rating=5):
    _, seller, buyer_h, _, item = traded
    r = client.post(
        "/reviews",
        json={"target_user_id": seller["id"], "item_id": item["id"], "rating": rating},
        headers=buyer_h,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _rating(user_id: int) -> float:
    session = TestingSessionLocal()
    try:
        return session.get(User, user_id).rating
    finally:
        session.close()


# ---------- 작성 검증 ----------
def test_review_needs_exactly_one_target(client, make_user):
    h, _ = make_user()
    _, other = make_user()
    both = {"target_user_id": other["id"], "item_id": 1, "skill_item_id": 1, "rating": 5}
    neither = {"target_user_id": other["id"], "rating": 5}
    assert client.post("/reviews", json=both, headers=h).status_code == 422
    assert client.post("/reviews", json=neither, headers=h).status_code == 422


def test_cannot_review_self(client, make_user):
    h, me = make_user()
    r = client.post(
        "/reviews", json={"target_user_id": me["id"], "item_id": 1, "rating": 5}, headers=h
    )
    assert r.status_code == 400


def test_review_unknown_target_is_404(client, make_user):
    h, _ = make_user()
    r = client.post("/reviews", json={"target_user_id": 9999, "item_id": 1, "rating": 5}, headers=h)
    assert r.status_code == 404


@pytest.mark.parametrize("rating", [0, 6])
def test_review_rating_range(client, make_user, rating):
    h, _ = make_user()
    _, other = make_user()
    r = client.post(
        "/reviews", json={"target_user_id": other["id"], "item_id": 1, "rating": rating}, headers=h
    )
    assert r.status_code == 422


# ---------- 조회 ----------
def test_list_reviews_filters(client, traded):
    review = _write(client, traded)
    _, seller, _, buyer, item = traded
    assert [r["id"] for r in client.get(f"/reviews?target_user_id={seller['id']}").json()] == [
        review["id"]
    ]
    assert client.get(f"/reviews?target_user_id={buyer['id']}").json() == []
    assert len(client.get(f"/reviews?item_id={item['id']}").json()) == 1
    assert client.get("/reviews?skill_item_id=1").json() == []


# ---------- 수정 ----------
def test_author_updates_review_and_rating_recalculates(client, traded):
    review = _write(client, traded, rating=5)
    _, seller, buyer_h, _, _ = traded
    assert _rating(seller["id"]) == 5.0

    r = client.patch(f"/reviews/{review['id']}", json={"rating": 2}, headers=buyer_h)
    assert r.status_code == 200, r.text
    assert _rating(seller["id"]) == 2.0


def test_non_author_cannot_update_review(client, traded):
    review = _write(client, traded)
    seller_h = traded[0]
    assert (
        client.patch(f"/reviews/{review['id']}", json={"rating": 1}, headers=seller_h).status_code
        == 403
    )


def test_update_after_edit_window_conflicts(client, traded):
    review = _write(client, traded)
    session = TestingSessionLocal()
    session.query(Review).filter(Review.id == review["id"]).update(
        {"created_at": now() - timedelta(days=30)}
    )
    session.commit()
    session.close()
    buyer_h = traded[2]
    assert (
        client.patch(f"/reviews/{review['id']}", json={"rating": 1}, headers=buyer_h).status_code
        == 409
    )


def test_update_missing_review_is_404(client, make_user):
    h, _ = make_user()
    assert client.patch("/reviews/999", json={"rating": 1}, headers=h).status_code == 404


# ---------- 삭제 ----------
def test_author_deletes_review_and_rating_resets(client, traded):
    review = _write(client, traded)
    _, seller, buyer_h, _, _ = traded
    assert client.delete(f"/reviews/{review['id']}", headers=buyer_h).status_code == 204
    assert _rating(seller["id"]) == 0.0
    # 이미 지운 리뷰는 없는 것으로 본다
    assert client.delete(f"/reviews/{review['id']}", headers=buyer_h).status_code == 404


def test_admin_can_delete_any_review(client, traded, make_user):
    review = _write(client, traded)
    admin_h, _ = make_user(admin=True)
    assert client.delete(f"/reviews/{review['id']}", headers=admin_h).status_code == 204


def test_other_user_cannot_delete_review(client, traded):
    review = _write(client, traded)
    seller_h = traded[0]
    assert client.delete(f"/reviews/{review['id']}", headers=seller_h).status_code == 403

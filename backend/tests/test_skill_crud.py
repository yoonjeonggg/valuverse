"""스킬 상품 수정/삭제·예약 변경·에스크로 조회의 예외 경로 테스트."""

from datetime import timedelta

from app.core.timeutils import now
from app.models.skill import Escrow
from tests.conftest import create_skill, request_booking


# ---------- 스킬 상품 ----------
def test_list_skill_items_filters(client, make_user):
    h, _ = make_user()
    create_skill(client, h, category="dev")
    create_skill(client, h, category="music")
    rows = client.get("/skill-items?category=dev").json()
    assert [r["category"] for r in rows] == ["dev"]
    assert len(client.get("/skill-items?status=recruiting").json()) == 2
    assert client.get("/skill-items?status=closed").json() == []


def test_get_missing_skill_item_is_404(client):
    assert client.get("/skill-items/999").status_code == 404


def test_owner_updates_recruiting_skill(client, make_user):
    h, _ = make_user()
    skill = create_skill(client, h)
    r = client.patch(f"/skill-items/{skill['id']}", json={"title": "새 제목"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "새 제목"


def test_non_owner_cannot_update_or_delete_skill(client, make_user):
    owner_h, _ = make_user()
    other_h, _ = make_user()
    skill = create_skill(client, owner_h)
    assert (
        client.patch(
            f"/skill-items/{skill['id']}", json={"title": "x"}, headers=other_h
        ).status_code
        == 403
    )
    assert client.delete(f"/skill-items/{skill['id']}", headers=other_h).status_code == 403


def test_skill_locked_once_booking_requested(client, make_user):
    seller_h, _ = make_user()
    _, buyer = make_user()
    skill = create_skill(client, seller_h)
    assert request_booking(client, seller_h, skill["id"], buyer["id"]).status_code == 201

    assert (
        client.patch(
            f"/skill-items/{skill['id']}", json={"title": "x"}, headers=seller_h
        ).status_code
        == 409
    )
    assert client.delete(f"/skill-items/{skill['id']}", headers=seller_h).status_code == 409


def test_delete_skill_hides_it(client, make_user):
    h, _ = make_user()
    skill = create_skill(client, h)
    assert client.delete(f"/skill-items/{skill['id']}", headers=h).status_code == 204
    assert client.get(f"/skill-items/{skill['id']}").status_code == 404


# ---------- 예약 ----------
def test_cannot_book_self(client, make_user):
    seller_h, seller = make_user()
    skill = create_skill(client, seller_h)
    assert request_booking(client, seller_h, skill["id"], seller["id"]).status_code == 400


def test_book_unknown_buyer_is_404(client, make_user):
    seller_h, _ = make_user()
    skill = create_skill(client, seller_h)
    assert request_booking(client, seller_h, skill["id"], 9999).status_code == 404


def test_list_my_bookings_shows_both_parties(client, make_user):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    outsider_h, _ = make_user()
    skill = create_skill(client, seller_h)
    booking = request_booking(client, seller_h, skill["id"], buyer["id"]).json()

    for h in (seller_h, buyer_h):
        assert [b["id"] for b in client.get("/skill-bookings", headers=h).json()] == [booking["id"]]
    assert client.get("/skill-bookings", headers=outsider_h).json() == []


def test_reschedule_open_booking(client, make_user):
    seller_h, _ = make_user()
    _, buyer = make_user()
    skill = create_skill(client, seller_h)
    booking = request_booking(client, seller_h, skill["id"], buyer["id"]).json()
    new_time = (now() + timedelta(days=5)).isoformat()
    r = client.patch(
        f"/skill-bookings/{booking['id']}", json={"scheduled_at": new_time}, headers=seller_h
    )
    assert r.status_code == 200, r.text


def test_cannot_change_closed_booking(client, make_user):
    seller_h, _ = make_user()
    _, buyer = make_user()
    skill = create_skill(client, seller_h)
    booking = request_booking(client, seller_h, skill["id"], buyer["id"]).json()
    assert client.delete(f"/skill-bookings/{booking['id']}", headers=seller_h).status_code == 204

    r = client.patch(
        f"/skill-bookings/{booking['id']}",
        json={"scheduled_at": now().isoformat()},
        headers=seller_h,
    )
    assert r.status_code == 409
    assert client.delete(f"/skill-bookings/{booking['id']}", headers=seller_h).status_code == 409
    assert client.post(f"/skill-bookings/{booking['id']}/accept", headers=seller_h).status_code in (
        403,
        409,
    )


def test_accept_twice_conflicts(client, make_user, set_points):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 10_000)
    skill = create_skill(client, seller_h)
    booking = request_booking(client, seller_h, skill["id"], buyer["id"]).json()
    assert (
        client.post(f"/skill-bookings/{booking['id']}/accept", headers=buyer_h).status_code == 200
    )
    assert (
        client.post(f"/skill-bookings/{booking['id']}/accept", headers=buyer_h).status_code == 409
    )


# ---------- 에스크로 ----------
def test_escrow_visible_only_to_parties(client, make_user, make_item, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    outsider_h, _ = make_user()
    set_points(buyer["id"], 10_000)
    item = make_item(seller_h)
    escrow = client.post(
        "/escrows",
        json={"item_id": item["id"], "payee_id": seller["id"], "amount": 1000},
        headers=buyer_h,
    ).json()

    assert client.get(f"/escrows/{escrow['id']}", headers=buyer_h).status_code == 200
    assert client.get(f"/escrows/{escrow['id']}", headers=seller_h).status_code == 200
    assert client.get(f"/escrows/{escrow['id']}", headers=outsider_h).status_code == 404


def test_escrow_settle_twice_conflicts(client, make_user, make_item, set_points):
    seller_h, seller = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 10_000)
    item = make_item(seller_h)
    escrow = client.post(
        "/escrows",
        json={"item_id": item["id"], "payee_id": seller["id"], "amount": 1000},
        headers=buyer_h,
    ).json()
    url = f"/escrows/{escrow['id']}"
    assert client.patch(url, json={"status": "settled"}, headers=buyer_h).status_code == 200
    assert client.patch(url, json={"status": "settled"}, headers=buyer_h).status_code == 409


def test_skill_escrow_cannot_be_moved_directly(client, make_user, set_points, db):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 10_000)
    skill = create_skill(client, seller_h)
    booking = request_booking(client, seller_h, skill["id"], buyer["id"]).json()
    assert (
        client.post(f"/skill-bookings/{booking['id']}/accept", headers=buyer_h).status_code == 200
    )

    escrow_id = db.query(Escrow.id).filter(Escrow.booking_id == booking["id"]).scalar()
    r = client.patch(f"/escrows/{escrow_id}", json={"status": "settled"}, headers=buyer_h)
    assert r.status_code == 409

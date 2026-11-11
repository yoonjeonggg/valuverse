"""스킬 경매 입찰·마감·낙찰자 예약 흐름 테스트 (FR-SKL-07)."""

from datetime import timedelta

from app.core.config import settings
from app.core.timeutils import now
from app.models.skill import SkillItem
from app.services import skill_service
from tests.conftest import (
    TestingSessionLocal,
    award_skill,
    create_skill,
    in_days,
    post_booking,
)


def _bid(client, headers, skill_id, amount):
    return client.post(f"/skill-items/{skill_id}/bids", json={"amount": amount}, headers=headers)


def _notif_types(client, headers):
    return [n["type"] for n in client.get("/users/me/notifications", headers=headers).json()]


# ---------- 등록 ----------
def test_new_skill_starts_at_start_price(client, make_user):
    h, _ = make_user()
    skill = create_skill(client, h, start_price=5000)
    assert skill["status"] == "recruiting"
    assert skill["current_price"] == 5000
    assert skill["winner_id"] is None


def test_skill_requires_future_end_time(client, make_user):
    h, _ = make_user()
    body = {"title": "과외", "start_price": 1000}
    assert client.post("/skill-items", json=body, headers=h).status_code == 422
    past = {**body, "end_time": (now() - timedelta(minutes=1)).isoformat()}
    assert client.post("/skill-items", json=past, headers=h).status_code == 400


def test_update_end_time_must_be_future(client, make_user):
    h, _ = make_user()
    skill = create_skill(client, h)
    past = (now() - timedelta(minutes=1)).isoformat()
    r = client.patch(f"/skill-items/{skill['id']}", json={"end_time": past}, headers=h)
    assert r.status_code == 400


# ---------- 입찰 ----------
def test_first_bid_may_equal_start_price(client, make_user, set_points):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 10_000)
    skill = create_skill(client, seller_h, start_price=3000)

    assert _bid(client, buyer_h, skill["id"], 2999).status_code == 400
    r = _bid(client, buyer_h, skill["id"], 3000)
    assert r.status_code == 201, r.text
    assert client.get(f"/skill-items/{skill['id']}").json()["current_price"] == 3000


def test_next_bid_must_exceed_current_price(client, make_user, set_points):
    seller_h, _ = make_user()
    a_h, a = make_user()
    b_h, b = make_user()
    set_points(a["id"], 10_000)
    set_points(b["id"], 10_000)
    skill = create_skill(client, seller_h, start_price=3000)

    assert _bid(client, a_h, skill["id"], 4000).status_code == 201
    assert _bid(client, b_h, skill["id"], 4000).status_code == 400
    assert _bid(client, b_h, skill["id"], 4500).status_code == 201
    assert client.get(f"/skill-items/{skill['id']}").json()["current_price"] == 4500


def test_seller_cannot_bid_on_own_skill(client, make_user, set_points):
    seller_h, seller = make_user()
    set_points(seller["id"], 10_000)
    skill = create_skill(client, seller_h)
    assert _bid(client, seller_h, skill["id"], 5000).status_code == 400


def test_bid_rejected_without_enough_points(client, make_user, set_points):
    """낙찰가는 포인트로 결제되므로 낼 수 없는 금액으로는 입찰할 수 없다."""
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 2000)
    skill = create_skill(client, seller_h, start_price=3000)
    r = _bid(client, buyer_h, skill["id"], 3000)
    assert r.status_code == 400
    assert "포인트" in r.json()["detail"]


def test_bid_on_missing_skill_is_404(client, make_user):
    h, _ = make_user()
    assert _bid(client, h, 999, 1000).status_code == 404


def test_outbid_bidder_is_notified(client, make_user, set_points):
    seller_h, _ = make_user()
    a_h, a = make_user()
    b_h, b = make_user()
    set_points(a["id"], 10_000)
    set_points(b["id"], 10_000)
    skill = create_skill(client, seller_h)

    _bid(client, a_h, skill["id"], 3000)
    _bid(client, a_h, skill["id"], 3500)  # 본인 입찰을 올리는 건 경쟁 알림 대상 아님
    assert "bid_outbid" not in _notif_types(client, a_h)
    _bid(client, b_h, skill["id"], 4000)
    assert "bid_outbid" in _notif_types(client, a_h)


def test_list_bids_highest_first_and_my_bids(client, make_user, set_points):
    seller_h, _ = make_user()
    a_h, a = make_user()
    b_h, b = make_user()
    set_points(a["id"], 10_000)
    set_points(b["id"], 10_000)
    skill = create_skill(client, seller_h)
    _bid(client, a_h, skill["id"], 3000)
    _bid(client, b_h, skill["id"], 5000)

    rows = client.get(f"/skill-items/{skill['id']}/bids").json()
    assert [(r["bidder_id"], r["amount"]) for r in rows] == [(b["id"], 5000), (a["id"], 3000)]

    mine = client.get("/users/me/skill-bids", headers=a_h).json()
    assert [r["amount"] for r in mine] == [3000]


def test_bid_near_deadline_extends_end_time(client, make_user, set_points, move_skill):
    """스나이핑 방지: 마감 임박 입찰이면 일반 경매와 같은 규칙으로 연장한다."""
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 10_000)
    skill = create_skill(client, seller_h)
    move_skill(skill["id"], 30)

    assert _bid(client, buyer_h, skill["id"], 3000).status_code == 201
    item = client.get(f"/skill-items/{skill['id']}").json()
    assert item["extended_count"] == 1
    assert item["status"] == "recruiting"


def test_extension_stops_at_max(client, make_user, set_points, move_skill, db):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 100_000)
    skill = create_skill(client, seller_h)
    db.query(SkillItem).filter(SkillItem.id == skill["id"]).update(
        {"extended_count": settings.auction_max_extensions}
    )
    db.commit()
    move_skill(skill["id"], 30)

    assert _bid(client, buyer_h, skill["id"], 3000).status_code == 201
    item = client.get(f"/skill-items/{skill['id']}").json()
    assert item["extended_count"] == settings.auction_max_extensions


def test_bid_after_deadline_conflicts_and_awards(client, make_user, set_points, move_skill):
    seller_h, _ = make_user()
    a_h, a = make_user()
    b_h, b = make_user()
    set_points(a["id"], 10_000)
    set_points(b["id"], 10_000)
    skill = create_skill(client, seller_h)
    _bid(client, a_h, skill["id"], 3000)
    move_skill(skill["id"], -1)

    assert _bid(client, b_h, skill["id"], 9000).status_code == 409
    item = client.get(f"/skill-items/{skill['id']}").json()
    assert item["status"] == "awarded"
    assert item["winner_id"] == a["id"]


# ---------- 마감 ----------
def test_close_awards_highest_bidder(client, make_user, set_points):
    seller_h, _ = make_user()
    a_h, a = make_user()
    b_h, b = make_user()
    set_points(a["id"], 10_000)
    set_points(b["id"], 10_000)
    skill = create_skill(client, seller_h)
    _bid(client, a_h, skill["id"], 3000)
    _bid(client, b_h, skill["id"], 4200)

    r = client.post(f"/skill-items/{skill['id']}/close", headers=seller_h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "awarded"
    assert body["winner_id"] == b["id"]
    assert body["final_price"] == 4200
    assert "won" in _notif_types(client, b_h)
    assert "sold" in _notif_types(client, seller_h)
    assert "won" not in _notif_types(client, a_h)


def test_close_without_bids_is_unsold(client, make_user):
    seller_h, _ = make_user()
    skill = create_skill(client, seller_h)
    r = client.post(f"/skill-items/{skill['id']}/close", headers=seller_h)
    assert r.status_code == 200
    assert r.json()["status"] == "closed"
    assert r.json()["winner_id"] is None
    assert post_booking(client, seller_h, skill["id"]).status_code == 409


def test_only_seller_closes_once(client, make_user):
    seller_h, _ = make_user()
    other_h, _ = make_user()
    skill = create_skill(client, seller_h)
    assert client.post(f"/skill-items/{skill['id']}/close", headers=other_h).status_code == 403
    assert client.post(f"/skill-items/{skill['id']}/close", headers=seller_h).status_code == 200
    assert client.post(f"/skill-items/{skill['id']}/close", headers=seller_h).status_code == 409


def test_expired_items_are_finalized_before_status_filter(
    client, make_user, set_points, move_skill
):
    """마감 시간이 지난 상품은 목록 조회 시 낙찰/유찰로 확정돼 상태 필터에 맞게 나온다."""
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 10_000)
    sold = create_skill(client, seller_h)
    unsold = create_skill(client, seller_h)
    live = create_skill(client, seller_h)
    _bid(client, buyer_h, sold["id"], 3000)
    move_skill(sold["id"], -1)
    move_skill(unsold["id"], -1)

    def ids(status):
        return {r["id"] for r in client.get(f"/skill-items?status={status}").json()}

    assert ids("recruiting") == {live["id"]}
    assert ids("awarded") == {sold["id"]}
    assert ids("closed") == {unsold["id"]}


def test_concurrent_finalize_does_not_award_twice(client, make_user, set_points, move_skill):
    """다른 요청이 먼저 확정했으면, 낡은 객체로 확정을 시도해도 다시 확정하지 않는다."""
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 10_000)
    skill = create_skill(client, seller_h)
    _bid(client, buyer_h, skill["id"], 3000)
    move_skill(skill["id"], -1)

    stale_session = TestingSessionLocal()
    stale = stale_session.get(SkillItem, skill["id"])
    assert stale.status == "recruiting"  # 아직 확정 전 상태를 들고 있다

    assert client.get(f"/skill-items/{skill['id']}").json()["status"] == "awarded"

    result = skill_service._finalize_if_ended(stale_session, stale)
    assert result.status == "awarded"
    stale_session.close()
    assert _notif_types(client, buyer_h).count("won") == 1


def test_legacy_skill_without_end_time_closes_manually(client, make_user, set_points, db):
    """마감 시간이 없는 예전 상품도 입찰을 받고(연장 없음) 판매자가 직접 마감한다."""
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 10_000)
    skill = create_skill(client, seller_h)
    db.query(SkillItem).filter(SkillItem.id == skill["id"]).update({"end_time": None})
    db.commit()

    assert _bid(client, buyer_h, skill["id"], 3000).status_code == 201
    item = client.get(f"/skill-items/{skill['id']}").json()
    assert item["status"] == "recruiting"
    assert item["extended_count"] == 0
    closed = client.post(f"/skill-items/{skill['id']}/close", headers=seller_h).json()
    assert closed["winner_id"] == buyer["id"]


def test_cannot_edit_after_close(client, make_user):
    seller_h, _ = make_user()
    skill = create_skill(client, seller_h)
    client.post(f"/skill-items/{skill['id']}/close", headers=seller_h)
    r = client.patch(f"/skill-items/{skill['id']}", json={"title": "x"}, headers=seller_h)
    assert r.status_code == 409


# ---------- 낙찰자 예약 ----------
def test_booking_before_close_conflicts(client, make_user, set_points):
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    set_points(buyer["id"], 10_000)
    skill = create_skill(client, seller_h)
    _bid(client, buyer_h, skill["id"], 3000)
    assert post_booking(client, seller_h, skill["id"]).status_code == 409


def test_booking_goes_to_winner_at_final_price(client, make_user, set_points):
    """판매자가 구매자·금액을 보내도 무시되고, 낙찰자·낙찰가로만 예약된다."""
    seller_h, _ = make_user()
    buyer_h, buyer = make_user()
    _, stranger = make_user()
    set_points(buyer["id"], 10_000)
    skill = create_skill(client, seller_h)
    award_skill(client, seller_h, buyer_h, skill["id"], amount=4800)

    r = client.post(
        "/skill-bookings",
        json={
            "skill_item_id": skill["id"],
            "scheduled_at": in_days(2),
            "buyer_id": stranger["id"],
            "amount": 1,
        },
        headers=seller_h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["buyer_id"] == buyer["id"]
    assert r.json()["amount"] == 4800

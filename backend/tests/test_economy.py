"""포인트 이코노미 - 출석/미션/광고 적립, 상단 노출권 소모 테스트."""

from datetime import timedelta

from app.core.config import settings
from app.core.timeutils import now
from tests.conftest import TestingSessionLocal


def _seed_attendance(user_id: int, days_ago: int, streak: int):
    session = TestingSessionLocal()
    from app.models.economy import Attendance

    d = (now().date() - timedelta(days=days_ago)).isoformat()
    session.add(
        Attendance(user_id=user_id, check_date=d, streak=streak, reward=0)
    )
    session.commit()
    session.close()


# ---------- 출석 ----------
def test_check_in_grants_base_reward(client, make_user, get_points):
    h, _ = make_user()
    r = client.post("/points/check-in", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["streak"] == 1
    assert body["reward"] == settings.point_checkin_base
    assert get_points(h) == settings.point_checkin_base


def test_check_in_twice_same_day_conflicts(client, make_user):
    h, _ = make_user()
    assert client.post("/points/check-in", headers=h).status_code == 200
    assert client.post("/points/check-in", headers=h).status_code == 409


def test_check_in_streak_bonus(client, make_user):
    h, user = make_user()
    _seed_attendance(user["id"], days_ago=1, streak=3)  # 어제 3일차
    r = client.post("/points/check-in", headers=h)
    body = r.json()
    assert body["streak"] == 4
    expected = settings.point_checkin_base + settings.point_checkin_streak_bonus * 3
    assert body["reward"] == expected


def test_check_in_streak_resets_after_gap(client, make_user):
    h, user = make_user()
    _seed_attendance(user["id"], days_ago=3, streak=5)  # 3일 전이 마지막
    r = client.post("/points/check-in", headers=h)
    assert r.json()["streak"] == 1


def test_check_in_status_before_and_after_check_in(client, make_user):
    h, _ = make_user()
    before = client.get("/points/check-in/status", headers=h).json()
    assert before == {"checked_in_today": False, "streak": 0}

    client.post("/points/check-in", headers=h)
    after = client.get("/points/check-in/status", headers=h).json()
    assert after == {"checked_in_today": True, "streak": 1}


def test_check_in_status_reflects_existing_streak(client, make_user):
    h, user = make_user()
    _seed_attendance(user["id"], days_ago=1, streak=3)
    status = client.get("/points/check-in/status", headers=h).json()
    assert status == {"checked_in_today": False, "streak": 3}


# ---------- 미션 ----------
def test_missions_list_reports_achievement(client, make_user):
    h, _ = make_user()
    missions = client.get("/points/missions", headers=h).json()
    keys = {m["key"] for m in missions}
    assert keys == {"first_bid", "first_item", "first_review"}
    assert all(m["achieved"] is False for m in missions)


def test_claim_mission_requires_achievement(client, make_user):
    h, _ = make_user()
    r = client.post("/points/missions/first_item/claim", headers=h)
    assert r.status_code == 409


def test_claim_first_item_mission(client, make_user, get_points):
    h, _ = make_user()
    client.post(
        "/items",
        json={
            "title": "x",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=h,
    )
    r = client.post("/points/missions/first_item/claim", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["reward"] == 50
    assert get_points(h) == 50


def test_claim_mission_twice_conflicts(client, make_user):
    seller_h, _ = make_user()
    bidder_h, _ = make_user()
    item = client.post(
        "/items",
        json={
            "title": "x",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=seller_h,
    ).json()
    client.post(f"/items/{item['id']}/bids", json={"amount": 200}, headers=bidder_h)

    assert client.post(
        "/points/missions/first_bid/claim", headers=bidder_h
    ).status_code == 200
    assert client.post(
        "/points/missions/first_bid/claim", headers=bidder_h
    ).status_code == 409


def test_claim_unknown_mission_404(client, make_user):
    h, _ = make_user()
    assert client.post("/points/missions/nope/claim", headers=h).status_code == 404


# ---------- 광고 ----------
def test_ad_reward_daily_limit(client, make_user, get_points):
    h, _ = make_user()
    for i in range(settings.point_ad_daily_limit):
        r = client.post("/points/ad-reward", headers=h)
        assert r.status_code == 200, r.text
    r = client.post("/points/ad-reward", headers=h)
    assert r.status_code == 409
    assert get_points(h) == settings.point_ad_reward * settings.point_ad_daily_limit


# ---------- 상단 노출권 ----------
def test_spotlight_costs_points_and_lifts_item(client, make_user, set_points):
    seller_h, seller = make_user()
    set_points(seller["id"], 500)

    old = client.post(
        "/items",
        json={
            "title": "old",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=seller_h,
    ).json()
    new = client.post(
        "/items",
        json={
            "title": "new",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=seller_h,
    ).json()

    # 기본 정렬: 최신(new) 이 먼저
    assert client.get("/items").json()[0]["id"] == new["id"]

    r = client.post(f"/items/{old['id']}/spotlight", headers=seller_h)
    assert r.status_code == 200, r.text
    assert r.json()["balance"] == 500 - settings.spotlight_cost

    # 노출권 구매 후: old 가 최상단
    assert client.get("/items").json()[0]["id"] == old["id"]


def test_spotlight_rejected_without_points(client, make_user):
    seller_h, _ = make_user()
    item = client.post(
        "/items",
        json={
            "title": "x",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=seller_h,
    ).json()
    r = client.post(f"/items/{item['id']}/spotlight", headers=seller_h)
    assert r.status_code == 400


def test_spotlight_only_by_owner(client, make_user, set_points):
    seller_h, _ = make_user()
    other_h, other = make_user()
    set_points(other["id"], 500)
    item = client.post(
        "/items",
        json={
            "title": "x",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=seller_h,
    ).json()
    r = client.post(f"/items/{item['id']}/spotlight", headers=other_h)
    assert r.status_code == 403


# ---------- 원시 트랜잭션 잠금 ----------
def test_raw_point_transaction_forbidden_for_normal_user(client, make_user):
    h, _ = make_user()
    r = client.post(
        "/point-transactions",
        json={"amount": 999999, "type": "admin", "memo": "cheat"},
        headers=h,
    )
    assert r.status_code == 403


def test_raw_point_transaction_allowed_for_admin(client, make_user, get_points):
    admin_h, _ = make_user(admin=True)
    _, target = make_user()
    r = client.post(
        "/point-transactions",
        json={"user_id": target["id"], "amount": 300, "type": "admin", "memo": "보상"},
        headers=admin_h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["balance_after"] == 300

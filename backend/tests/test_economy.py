"""포인트 이코노미 - 출석/미션/광고 적립, 상단 노출권 소모 테스트."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.timeutils import now
from app.models.user import User
from tests.conftest import TestingSessionLocal


def _spend_concurrently(user_id: int, remaining_points: int):
    """다른 세션이 이미 잔액을 이만큼만 남기고 커밋해버린 상황을 흉내낸다
    (동시 요청 하나가 먼저 통과해 잔액을 다 써버린 것과 동일한 DB 상태)."""
    session = TestingSessionLocal()
    session.query(User).filter(User.id == user_id).update({"points": remaining_points})
    session.commit()
    session.close()


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
    assert body["next_check_in_reward"] == (
        settings.point_checkin_base + settings.point_checkin_streak_bonus * 4
    )


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


def test_check_in_status_shows_broken_streak_as_zero(client, make_user):
    h, user = make_user()
    _seed_attendance(user["id"], days_ago=3, streak=5)  # 사흘 전이 마지막 → 이미 끊긴 스트릭
    status = client.get("/points/check-in/status", headers=h).json()
    assert status == {"checked_in_today": False, "streak": 0}


def test_check_in_race_returns_conflict_not_500(client, make_user, monkeypatch):
    """동시에 두 번 출석 요청이 들어와 중복 확인 로직을 모두 통과해도,
    DB의 UNIQUE(user_id, check_date) 제약으로 걸러지면 409여야 한다 (500 아님)."""
    h, _ = make_user()
    assert client.post("/points/check-in", headers=h).status_code == 200

    from app.services import economy_service

    monkeypatch.setattr(economy_service, "_latest_attendance", lambda db, user_id: None)
    r = client.post("/points/check-in", headers=h)
    assert r.status_code == 409, r.text


# ---------- 미션 ----------
def test_missions_list_reports_achievement(client, make_user):
    h, _ = make_user()
    missions = client.get("/points/missions", headers=h).json()
    keys = {m["key"] for m in missions}
    assert keys == {"first_bid", "first_item", "first_review"}
    assert all(m["achieved"] is False for m in missions)


def test_missions_list_reflects_each_condition(client, make_user):
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
    client.post("/points/missions/first_item/claim", headers=h)
    missions = {m["key"]: m for m in client.get("/points/missions", headers=h).json()}
    assert missions["first_item"]["achieved"] is True
    assert missions["first_item"]["claimed"] is True
    assert missions["first_bid"]["achieved"] is False
    assert missions["first_review"]["achieved"] is False


def test_cancelled_bid_does_not_achieve_first_bid_mission(client, make_user):
    """입찰 후 바로 취소하는 것만으로 미션 보상을 받을 수 없어야 한다."""
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
    bid = client.post(
        f"/items/{item['id']}/bids", json={"amount": 200}, headers=bidder_h
    ).json()

    session = TestingSessionLocal()
    from app.models.auction import Bid

    session.query(Bid).filter(Bid.id == bid["id"]).update({"is_cancelled": True})
    session.commit()
    session.close()

    assert client.post(
        "/points/missions/first_bid/claim", headers=bidder_h
    ).status_code == 409


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


def test_claim_mission_race_returns_conflict_not_500(client, make_user, monkeypatch):
    """동시에 두 번 수령 요청이 들어와 중복 확인 로직을 모두 통과해도,
    DB의 UNIQUE(user_id, mission_key) 제약으로 걸러지면 409여야 한다 (500 아님)."""
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
    assert client.post("/points/missions/first_item/claim", headers=h).status_code == 200

    from app.services import economy_service

    monkeypatch.setattr(
        economy_service, "_already_claimed", lambda db, user_id, key: False
    )
    r = client.post("/points/missions/first_item/claim", headers=h)
    assert r.status_code == 409, r.text


# ---------- 광고 ----------
def test_ad_reward_daily_limit(client, make_user, get_points, monkeypatch):
    monkeypatch.setattr(settings, "point_ad_min_interval_seconds", 0)
    h, _ = make_user()
    for i in range(settings.point_ad_daily_limit):
        r = client.post("/points/ad-reward", headers=h)
        assert r.status_code == 200, r.text
    r = client.post("/points/ad-reward", headers=h)
    assert r.status_code == 409
    assert get_points(h) == settings.point_ad_reward * settings.point_ad_daily_limit


def test_check_in_does_not_overwrite_concurrent_spend(client, make_user, set_points):
    """적립 시 메모리상 stale 잔액에 더해 덮어쓰면, 그 사이 다른 요청이 커밋한
    차감이 사라진다(lost update). 적립은 DB 의 최신 잔액에 더해져야 한다."""
    _, user = make_user()
    set_points(user["id"], 500)

    from app.services.economy_service import check_in

    session = TestingSessionLocal()
    stale_user = session.query(User).filter(User.id == user["id"]).one()
    assert stale_user.points == 500

    _spend_concurrently(user["id"], remaining_points=100)  # 다른 요청이 400P 사용

    body = check_in(session, stale_user)
    assert body["balance"] == 100 + settings.point_checkin_base
    session.close()

    check = TestingSessionLocal()
    assert (
        check.query(User.points).filter(User.id == user["id"]).scalar()
        == 100 + settings.point_checkin_base
    )
    check.close()


def test_ad_reward_cooldown_blocks_rapid_calls(client, make_user, get_points):
    """광고 시청은 서버가 검증할 수 없으므로 광고 길이보다 빠른 연속 호출은 429."""
    h, _ = make_user()
    assert client.post("/points/ad-reward", headers=h).status_code == 200
    r = client.post("/points/ad-reward", headers=h)
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert get_points(h) == settings.point_ad_reward


# ---------- 포인트 센터 요약 ----------
def test_points_summary(client, make_user):
    h, _ = make_user()
    before = client.get("/users/me/points/summary", headers=h).json()
    assert before == {
        "balance": 0,
        "checked_in_today": False,
        "streak": 0,
        "streak_cap": settings.point_checkin_streak_cap,
        "next_check_in_reward": settings.point_checkin_base,
        "ad_views_today": 0,
        "ad_daily_limit": settings.point_ad_daily_limit,
        "ad_reward": settings.point_ad_reward,
        "ad_next_available_at": None,
    }

    client.post("/points/check-in", headers=h)
    client.post("/points/ad-reward", headers=h)
    after = client.get("/users/me/points/summary", headers=h).json()
    assert after["checked_in_today"] is True
    assert after["streak"] == 1
    assert after["next_check_in_reward"] == (
        settings.point_checkin_base + settings.point_checkin_streak_bonus
    )
    assert after["ad_views_today"] == 1
    assert after["ad_next_available_at"] is not None  # 방금 받았으므로 쿨다운 중
    assert after["balance"] == settings.point_checkin_base + settings.point_ad_reward


def test_points_summary_requires_login(client):
    assert client.get("/users/me/points/summary").status_code == 401


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


def test_spotlight_race_rejects_using_fresh_balance(client, make_user, set_points):
    """요청 시작 시점엔 잔액이 충분해 보였어도(메모리상 stale 값), 그 사이 다른
    요청이 이미 잔액을 다 써버렸다면 최신 잔액 기준으로 거부해야 한다.
    (잠금 없이 stale 한 user.points 를 그대로 신뢰하면 이중 차감이 가능했다.)"""
    seller_h, seller = make_user()
    set_points(seller["id"], settings.spotlight_cost)
    item = client.post(
        "/items",
        json={
            "title": "x",
            "start_price": 100,
            "end_time": (now() + timedelta(days=1)).isoformat(),
        },
        headers=seller_h,
    ).json()

    from app.services.auction_service import buy_spotlight

    session = TestingSessionLocal()
    stale_user = session.query(User).filter(User.id == seller["id"]).one()
    assert stale_user.points == settings.spotlight_cost  # 메모리상으론 잔액 충분

    _spend_concurrently(seller["id"], remaining_points=0)  # "동시에" 이미 다 써버림

    with pytest.raises(HTTPException) as exc:
        buy_spotlight(session, item["id"], stale_user)
    assert exc.value.status_code == 400
    session.close()


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
    # 누가 조정했는지 이력에 남는다
    assert r.json()["memo"].startswith("[관리자 #")


@pytest.mark.parametrize(
    "payload",
    [
        {"amount": 100, "type": "ad", "memo": "적립 유형 위조"},
        {"amount": 100, "type": "attendance", "memo": "적립 유형 위조"},
        {"amount": 0, "type": "admin", "memo": "0P"},
        {"amount": settings.point_admin_adjust_max + 1, "type": "admin", "memo": "한도 초과"},
        {"amount": 100, "type": "admin"},  # 사유 누락
        {"amount": 100, "type": "admin", "memo": ""},
    ],
)
def test_raw_point_transaction_rejects_invalid_admin_payload(client, make_user, payload):
    admin_h, _ = make_user(admin=True)
    _, target = make_user()
    r = client.post(
        "/point-transactions", json={"user_id": target["id"], **payload}, headers=admin_h
    )
    assert r.status_code == 422, r.text


def test_point_transaction_history_is_paginated(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "point_ad_min_interval_seconds", 0)
    h, _ = make_user()
    for _ in range(3):
        client.post("/points/ad-reward", headers=h)
    page = client.get("/users/me/point-transactions?limit=2", headers=h).json()
    assert len(page) == 2
    rest = client.get("/users/me/point-transactions?skip=2&limit=2", headers=h).json()
    assert len(rest) == 1
    assert client.get(
        "/users/me/point-transactions?limit=1000", headers=h
    ).status_code == 422

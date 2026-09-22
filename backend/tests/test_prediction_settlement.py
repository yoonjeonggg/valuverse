"""예측시장 파리뮤추얼 배당·정산 테스트."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.timeutils import now
from app.models.user import User
from tests.conftest import TestingSessionLocal


@pytest.fixture
def move_deadline(move_pred):
    """predictions.end_time 이동 (conftest.move_pred 위임)."""
    return move_pred


def _create_prediction(client, admin_h, **overrides):
    body = {
        "title": "테스트 명제",
        "end_time": (now() + timedelta(days=1)).isoformat(),
    }
    body.update(overrides)
    r = client.post("/predictions", json=body, headers=admin_h)
    assert r.status_code == 201, r.text
    return r.json()


def _bet(client, headers, pid, position, amount):
    r = client.post(
        f"/predictions/{pid}/bets",
        json={"position": position, "amount": amount},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------- 배당률 ----------
def test_odds_reflect_pool_ratio(client, make_user, set_points):
    admin_h, _ = make_user(admin=True)
    u1_h, u1 = make_user()
    u2_h, u2 = make_user()
    set_points(u1["id"], 10000)
    set_points(u2["id"], 10000)

    pred = _create_prediction(client, admin_h)
    _bet(client, u1_h, pred["id"], "yes", 3000)
    _bet(client, u2_h, pred["id"], "no", 1000)

    odds = client.get(f"/predictions/{pred['id']}/odds").json()
    assert odds["yes_pool"] == 3000
    assert odds["no_pool"] == 1000
    assert odds["total_pool"] == 4000
    assert odds["yes_backers"] == 1
    assert odds["yes_odds"] == round(4000 / 3000, 2)
    assert odds["no_odds"] == round(4000 / 1000, 2)


def test_odds_null_when_one_side_empty(client, make_user, set_points):
    admin_h, _ = make_user(admin=True)
    u1_h, u1 = make_user()
    set_points(u1["id"], 10000)
    pred = _create_prediction(client, admin_h)
    _bet(client, u1_h, pred["id"], "yes", 2000)

    odds = client.get(f"/predictions/{pred['id']}/odds").json()
    assert odds["yes_odds"] == 1.0  # total_pool == yes_pool
    assert odds["no_odds"] is None


def test_bet_race_rejects_using_fresh_balance(client, make_user, set_points):
    """요청 시작 시점엔 잔액이 충분해 보였어도(메모리상 stale 값), 그 사이 다른
    요청이 이미 잔액을 다 써버렸다면 최신 잔액 기준으로 거부해야 한다."""
    admin_h, _ = make_user(admin=True)
    u_h, u = make_user()
    set_points(u["id"], 2000)
    pred = _create_prediction(client, admin_h)

    from app.services.prediction_service import create_bet
    from app.schemas.prediction import PredictionBetCreate

    session = TestingSessionLocal()
    stale_user = session.query(User).filter(User.id == u["id"]).one()
    assert stale_user.points == 2000  # 메모리상으론 베팅 가능해 보임

    other = TestingSessionLocal()
    other.query(User).filter(User.id == u["id"]).update({"points": 0})
    other.commit()
    other.close()

    payload = PredictionBetCreate(position="yes", amount=2000)
    with pytest.raises(HTTPException) as exc:
        create_bet(session, pred["id"], stale_user, payload)
    assert exc.value.status_code == 400
    session.close()


# ---------- 정산 ----------
def test_settle_pays_winners_parimutuel(
    client, make_user, set_points, get_points, move_deadline
):
    admin_h, _ = make_user(admin=True)
    yes1_h, yes1 = make_user()
    yes2_h, yes2 = make_user()
    no1_h, no1 = make_user()
    for u in (yes1, yes2, no1):
        set_points(u["id"], 10000)

    pred = _create_prediction(client, admin_h)
    _bet(client, yes1_h, pred["id"], "yes", 2000)   # 잔액 8000
    _bet(client, yes2_h, pred["id"], "yes", 2000)   # 잔액 8000
    _bet(client, no1_h, pred["id"], "no", 4000)     # 잔액 6000

    move_deadline(pred["id"], -1)

    r = client.post(
        f"/predictions/{pred['id']}/settle", json={"result": "yes"}, headers=admin_h
    )
    assert r.status_code == 200, r.text
    summary = r.json()
    assert summary["total_pool"] == 8000
    assert summary["winning_pool"] == 4000
    assert summary["winners"] == 2
    assert summary["losers"] == 1
    assert summary["refunded"] is False
    # 각 승자: 2000 * 8000 // 4000 = 4000 배당
    assert summary["total_payout"] == 8000

    assert get_points(yes1_h) == 8000 + 4000
    assert get_points(yes2_h) == 8000 + 4000
    assert get_points(no1_h) == 6000  # 패배, 변화 없음


def test_settle_refunds_all_when_no_winners(
    client, make_user, set_points, get_points, move_deadline
):
    admin_h, _ = make_user(admin=True)
    no1_h, no1 = make_user()
    no2_h, no2 = make_user()
    set_points(no1["id"], 10000)
    set_points(no2["id"], 10000)

    pred = _create_prediction(client, admin_h)
    _bet(client, no1_h, pred["id"], "no", 3000)
    _bet(client, no2_h, pred["id"], "no", 5000)

    move_deadline(pred["id"], -1)

    r = client.post(
        f"/predictions/{pred['id']}/settle", json={"result": "yes"}, headers=admin_h
    )
    assert r.status_code == 200, r.text
    assert r.json()["refunded"] is True
    assert get_points(no1_h) == 10000
    assert get_points(no2_h) == 10000


def test_settle_before_deadline_conflicts(client, make_user):
    admin_h, _ = make_user(admin=True)
    pred = _create_prediction(client, admin_h)
    r = client.post(
        f"/predictions/{pred['id']}/settle", json={"result": "yes"}, headers=admin_h
    )
    assert r.status_code == 409


def test_settle_twice_conflicts(client, make_user, move_deadline):
    admin_h, _ = make_user(admin=True)
    pred = _create_prediction(client, admin_h)
    move_deadline(pred["id"], -1)

    assert client.post(
        f"/predictions/{pred['id']}/settle", json={"result": "yes"}, headers=admin_h
    ).status_code == 200
    r = client.post(
        f"/predictions/{pred['id']}/settle", json={"result": "no"}, headers=admin_h
    )
    assert r.status_code == 409


def test_settle_requires_admin(client, make_user):
    admin_h, _ = make_user(admin=True)
    user_h, _ = make_user()
    pred = _create_prediction(client, admin_h)
    r = client.post(
        f"/predictions/{pred['id']}/settle", json={"result": "yes"}, headers=user_h
    )
    assert r.status_code == 403


def test_settled_prediction_result_recorded(
    client, make_user, set_points, move_deadline
):
    admin_h, _ = make_user(admin=True)
    u_h, u = make_user()
    set_points(u["id"], 10000)
    pred = _create_prediction(client, admin_h)
    _bet(client, u_h, pred["id"], "yes", 1000)

    move_deadline(pred["id"], -1)
    client.post(
        f"/predictions/{pred['id']}/settle", json={"result": "yes"}, headers=admin_h
    )

    got = client.get(f"/predictions/{pred['id']}").json()
    assert got["status"] == "settled"
    assert got["result"] == "yes"

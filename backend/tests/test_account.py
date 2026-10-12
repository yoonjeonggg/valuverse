"""인증 실패·회원 탈퇴·프로필·포인트 조회의 예외 경로 테스트."""

from app.core.security import create_access_token


def test_missing_token_is_401(client):
    r = client.get("/users/me")
    assert r.status_code == 401


def test_malformed_token_is_401(client):
    r = client.get("/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_token_for_unknown_user_is_401(client):
    token = create_access_token("ghost@test.com")
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_wrong_password_login_is_401(client, make_user):
    _, user = make_user(password="pw12345!")
    r = client.post("/auth/login", json={"email": user["email"], "password": "wrong-pw"})
    assert r.status_code == 401


def test_deactivated_account_is_locked_out(client, make_user):
    h, user = make_user(password="pw12345!")
    assert client.delete("/users/me", headers=h).status_code == 204

    # 기존 토큰은 403, 재로그인은 실패
    assert client.get("/users/me", headers=h).status_code == 403
    r = client.post("/auth/login", json={"email": user["email"], "password": "pw12345!"})
    assert r.status_code == 401


def test_update_profile_image(client, make_user):
    h, _ = make_user()
    r = client.patch("/users/me", json={"profile_image": "https://img.test/a.png"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["profile_image"] == "https://img.test/a.png"


def test_public_profile_missing_user_is_404(client):
    assert client.get("/users/9999").status_code == 404


def test_point_balance(client, make_user, set_points):
    h, user = make_user()
    set_points(user["id"], 1234)
    body = client.get("/users/me/points/balance", headers=h).json()
    assert body == {"user_id": user["id"], "balance": 1234}


def test_admin_cannot_push_balance_negative(client, make_user, set_points):
    admin_h, _ = make_user(admin=True)
    _, target = make_user()
    set_points(target["id"], 100)
    r = client.post(
        "/point-transactions",
        json={"user_id": target["id"], "amount": -500, "memo": "회수"},
        headers=admin_h,
    )
    assert r.status_code == 400


def test_admin_adjust_unknown_user_is_404(client, make_user):
    admin_h, _ = make_user(admin=True)
    r = client.post(
        "/point-transactions",
        json={"user_id": 9999, "amount": 100, "memo": "지급"},
        headers=admin_h,
    )
    assert r.status_code == 404


def test_point_history_type_filter(client, make_user):
    h, _ = make_user()
    client.post("/points/check-in", headers=h)
    rows = client.get("/users/me/point-transactions?type=attendance", headers=h).json()
    assert rows
    assert all(r["type"] == "attendance" for r in rows)
    assert client.get("/users/me/point-transactions?type=bet", headers=h).json() == []


def test_point_service_blocks_non_admin_adjusting_others(db, make_user):
    """라우터가 관리자만 통과시키지만 서비스도 자체적으로 막는다 (다른 호출 경로 대비)."""
    import pytest

    from app.core.errors import Forbidden
    from app.models.user import User
    from app.schemas.point import PointTransactionCreate
    from app.services import point_service

    _, me = make_user()
    _, other = make_user()
    payload = PointTransactionCreate(user_id=other["id"], amount=100, memo="x")
    with pytest.raises(Forbidden):
        point_service.create_transaction(db, db.get(User, me["id"]), payload)

"""계정 - 비밀번호 변경 / 가입 중복 테스트."""

from app.models.user import User
from tests.conftest import TestingSessionLocal


def _email_of(user_id: int) -> str:
    session = TestingSessionLocal()
    email = session.query(User.email).filter(User.id == user_id).scalar()
    session.close()
    return email


def test_password_change_requires_current_password(client, make_user):
    """토큰만 탈취당해도 비밀번호까지 바꿔 계정을 빼앗기지 않아야 한다."""
    h, user = make_user(password="pw12345!")
    email = _email_of(user["id"])

    r = client.patch("/users/me", json={"password": "newpass123!"}, headers=h)
    assert r.status_code == 400
    r = client.patch(
        "/users/me",
        json={"password": "newpass123!", "current_password": "wrong-pass"},
        headers=h,
    )
    assert r.status_code == 400
    assert client.post(
        "/auth/login", json={"email": email, "password": "pw12345!"}
    ).status_code == 200

    r = client.patch(
        "/users/me",
        json={"password": "newpass123!", "current_password": "pw12345!"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert client.post(
        "/auth/login", json={"email": email, "password": "newpass123!"}
    ).status_code == 200


def test_nickname_change_does_not_need_password(client, make_user):
    h, _ = make_user()
    r = client.patch("/users/me", json={"nickname": "새닉네임"}, headers=h)
    assert r.status_code == 200
    assert r.json()["nickname"] == "새닉네임"


def test_duplicate_signup_conflicts(client):
    body = {"email": "dup@example.com", "password": "pw12345!", "nickname": "dup"}
    assert client.post("/auth/signup", json=body).status_code == 201
    assert client.post("/auth/signup", json=body).status_code == 409

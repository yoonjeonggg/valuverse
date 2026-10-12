"""테스트 공용 픽스처.

- 인메모리 SQLite(StaticPool) 로 DB 를 격리한다.
- `get_db` 의존성을 테스트 세션으로 교체한다.
- 앱 임포트 전에 환경 변수를 지정해 로컬 `.env`/파일 DB 의 영향을 없앤다.
- 도메인 테스트가 공통으로 쓰는 생성 헬퍼(상품/명제)도 여기 둔다.
"""

import os
from functools import partial

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import pwd_context
from app.database import Base, get_db
from app.main import app

# 가입/로그인마다 bcrypt 기본 비용(12라운드)을 치르면 전체 테스트가 몇 분씩 걸린다.
# 해시 검증 로직은 같고 비용만 최소로 낮춘다.
pwd_context.update(bcrypt__rounds=4)

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _db_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------- 사용자 헬퍼 ----------
_counter = {"n": 0}


def _unique_email() -> str:
    _counter["n"] += 1
    return f"user{_counter['n']}@test.com"


@pytest.fixture
def make_user(client):
    """(headers, user_dict) 를 반환하는 회원 생성 헬퍼."""

    def _make(password: str = "pw12345!", admin: bool = False):
        email = _unique_email()
        signup = client.post(
            "/auth/signup",
            json={"email": email, "password": password, "nickname": email.split("@")[0]},
        )
        assert signup.status_code == 201, signup.text
        user = signup.json()

        if admin:
            session = TestingSessionLocal()
            from app.models.user import User

            session.query(User).filter(User.id == user["id"]).update({"is_admin": True})
            session.commit()
            session.close()

        login = client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, user

    return _make


@pytest.fixture
def set_points():
    """테스트용으로 사용자 포인트 잔액을 직접 지정한다."""

    def _set(user_id: int, points: int):
        session = TestingSessionLocal()
        from app.models.user import User

        session.query(User).filter(User.id == user_id).update({"points": points})
        session.commit()
        session.close()

    return _set


@pytest.fixture
def get_points(client):
    def _get(headers) -> int:
        r = client.get("/users/me", headers=headers)
        assert r.status_code == 200, r.text
        return r.json()["points"]

    return _get


def _deadline_mover(model):
    from datetime import timedelta

    from app.core.timeutils import now

    def _move(row_id: int, seconds: int):
        session = TestingSessionLocal()
        session.query(model).filter(model.id == row_id).update(
            {"end_time": now() + timedelta(seconds=seconds)}
        )
        session.commit()
        session.close()

    return _move


@pytest.fixture
def move_pred():
    """predictions.end_time 을 현재 기준 delta(초) 만큼 이동."""
    from app.models.prediction import Prediction

    return _deadline_mover(Prediction)


@pytest.fixture
def move_item():
    """items.end_time 을 현재 기준 delta(초) 만큼 이동."""
    from app.models.auction import Item

    return _deadline_mover(Item)


# ---------- 생성 헬퍼 ----------
def in_days(days: float) -> str:
    from datetime import timedelta

    from app.core.timeutils import now

    return (now() + timedelta(days=days)).isoformat()


def create_item(client, headers, **overrides):
    """일반 경매 상품을 만들고 응답 JSON 을 돌려준다. 필드는 키워드로 덮어쓴다."""
    body = {"title": "테스트 상품", "start_price": 1000, "end_time": in_days(1)}
    body.update(overrides)
    r = client.post("/items", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def create_skill(client, headers, **overrides):
    body = {"title": "1:1 파이썬 과외", "start_price": 3000}
    body.update(overrides)
    r = client.post("/skill-items", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def request_booking(client, seller_headers, skill_id, buyer_id, amount=3000):
    """판매자의 스킬 예약 요청 (구매자 수락 전이라 포인트는 아직 차감되지 않는다). 응답을 그대로 돌려준다."""
    return client.post(
        "/skill-bookings",
        json={
            "skill_item_id": skill_id,
            "buyer_id": buyer_id,
            "amount": amount,
            "scheduled_at": in_days(2),
        },
        headers=seller_headers,
    )


@pytest.fixture
def make_item(client):
    """`create_item` 의 픽스처 버전 (client 를 넘기지 않아도 된다)."""
    return partial(create_item, client)


@pytest.fixture
def make_prediction(client):
    def _make(admin_headers, **overrides):
        body = {"title": "내일 비가 온다", "end_time": in_days(1)}
        body.update(overrides)
        r = client.post("/predictions", json=body, headers=admin_headers)
        assert r.status_code == 201, r.text
        return r.json()

    return _make

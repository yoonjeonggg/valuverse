import json
import logging

from fastapi import APIRouter

from app.core.logging_setup import JsonFormatter, RequestIdFilter
from app.main import app

_boom_router = APIRouter()


@_boom_router.get("/__test__/boom")
def _boom():
    raise RuntimeError("boom")


app.include_router(_boom_router)


def _request_records(caplog):
    return [r for r in caplog.records if r.name == "app.request"]


def test_request_id_generated_and_echoed(client, caplog):
    caplog.set_level(logging.INFO, logger="app.request")
    res = client.get("/items")
    assert res.status_code == 200
    rid = res.headers["X-Request-ID"]
    assert rid

    [rec] = _request_records(caplog)
    assert rec.status == 200
    assert rec.method == "GET"
    assert rec.path == "/items"
    assert rec.duration_ms >= 0


def test_request_id_from_header_is_reused(client):
    res = client.get("/items", headers={"X-Request-ID": "abc123"})
    assert res.headers["X-Request-ID"] == "abc123"


def test_authenticated_request_logs_user_id(client, caplog):
    client.post(
        "/auth/signup",
        json={"email": "log@example.com", "password": "password123", "nickname": "로그"},
    )
    token = client.post(
        "/auth/login", json={"email": "log@example.com", "password": "password123"}
    ).json()["access_token"]

    caplog.set_level(logging.INFO, logger="app.request")
    caplog.clear()
    res = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    [rec] = _request_records(caplog)
    assert rec.user_id == res.json()["id"]


def test_login_failure_does_not_log_credentials(client, caplog):
    caplog.set_level(logging.INFO)
    client.post("/auth/login", json={"email": "who@example.com", "password": "secret-pw"})
    text = caplog.text
    assert "로그인 실패" in text
    assert "who@example.com" not in text
    assert "secret-pw" not in text


def test_unhandled_exception_logged_and_returns_500(client, caplog):
    caplog.set_level(logging.INFO, logger="app.request")
    res = client.get("/__test__/boom")
    assert res.status_code == 500
    assert res.json()["request_id"] == res.headers["X-Request-ID"]

    error = next(r for r in caplog.records if r.levelno == logging.ERROR)
    assert error.exc_info is not None
    [access] = [r for r in _request_records(caplog) if hasattr(r, "status")]
    assert access.status == 500
    assert access.levelno == logging.WARNING


def test_json_formatter_includes_extra_fields():
    record = logging.LogRecord("app.request", logging.INFO, __file__, 1, "hi %s", ("x",), None)
    record.status = 201
    RequestIdFilter().filter(record)
    data = json.loads(JsonFormatter().format(record))
    assert data["message"] == "hi x"
    assert data["status"] == 201
    assert data["level"] == "INFO"
    assert data["request_id"] == "-"

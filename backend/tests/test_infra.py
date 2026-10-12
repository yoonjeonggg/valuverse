"""설정·로깅·보안·DB 세션 같은 기반 코드 테스트."""

import json
import logging
import sys

import pytest
from sqlalchemy.orm import Session

from app.core import logging_setup
from app.core.config import settings
from app.core.logging_setup import JsonFormatter, setup_logging
from app.core.security import warn_if_default_secret
from app.database import get_db


def test_health_is_logged_quietly(client, caplog):
    caplog.set_level(logging.DEBUG, logger="app.request")
    assert client.get("/health").json() == {"status": "ok"}
    rec = next(r for r in caplog.records if r.name == "app.request")
    assert rec.levelno == logging.DEBUG


def test_get_db_closes_session():
    gen = get_db()
    db = next(gen)
    assert isinstance(db, Session)
    gen.close()  # finally 블록 실행
    assert not db.in_transaction()


def test_default_secret_key_warns():
    with pytest.warns(UserWarning, match="SECRET_KEY"):
        assert warn_if_default_secret("dev-secret-change-me") is True
    assert warn_if_default_secret("something-else") is False


def _raise_boom():
    raise ValueError("boom")


def test_json_formatter_includes_traceback():
    try:
        _raise_boom()
    except ValueError:
        record = logging.LogRecord("app", logging.ERROR, __file__, 1, "실패", None, sys.exc_info())
    data = json.loads(JsonFormatter().format(record))
    assert data["message"] == "실패"
    assert "ValueError: boom" in data["exc_info"]


def test_setup_logging_writes_to_file(tmp_path, monkeypatch):
    log_file = tmp_path / "logs" / "app.log"  # 상위 디렉터리가 없어도 만들어야 한다
    monkeypatch.setattr(settings, "log_file", str(log_file))
    monkeypatch.setattr(settings, "log_format", "json")
    try:
        setup_logging()
        logging.getLogger("app.test").warning("파일 로그 확인")
    finally:
        # 다른 테스트에 영향이 없도록 원래 설정으로 되돌리고 파일 핸들러를 닫는다.
        monkeypatch.undo()
        logging_setup.setup_logging()

    line = log_file.read_text(encoding="utf-8").strip().splitlines()[-1]
    assert json.loads(line)["message"] == "파일 로그 확인"
